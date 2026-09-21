"""
Testes de exibição do comprovante de pagamento na aba Custas Judiciais
do processo (specs/processos-custas-comprovante-pagamento.md).

Cobre: card só mostra "quem pagou" e o link do comprovante para
solicitações com status "paga"; download do comprovante segue o mesmo
escopo de leitura do detalhe do processo (não o escopo dados_próprios/
dados_todos do módulo Financeiro) e não exige o módulo Financeiro.
"""

import shutil
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PapelAcesso, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import (
    MODULO_PROCESSOS,
    NIVEL_SOMENTE_SEUS,
    NIVEL_TODOS,
)
from apps.clientes.models import Cliente
from apps.financeiro.models import SolicitacaoFinanceira
from apps.processos.models import Processo

_MEDIA_TMP = tempfile.mkdtemp(prefix="lawsystem_test_media_custas_")


def _arquivo(nome="boleto.pdf", conteudo=b"boleto-fake"):
    return SimpleUploadedFile(nome, conteudo, content_type="application/pdf")


@override_settings(MEDIA_ROOT=_MEDIA_TMP)
class CustasComprovanteBase(TenantTestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_MEDIA_TMP, ignore_errors=True)

    def setUp(self):
        self._media_override = override_settings(MEDIA_ROOT=_MEDIA_TMP)
        self._media_override.enable()
        self.addCleanup(self._media_override.disable)
        super().setUp()
        from apps.saas_tenants.models import Dominio
        domain_obj = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = domain_obj.domain if domain_obj else "localhost"

    def _user(self, username):
        return User.objects.create_user(username=username, password="testpass")

    def _new_papel(self, nome):
        return PapelAcesso.objects.create(nome=nome, ativo=True)

    def _assign_papel(self, user, papel):
        return UsuarioPapel.objects.create(usuario=user, papel=papel, ativo=True)

    def _pp(self, papel, modulo, *, nivel=NIVEL_TODOS):
        return PermissaoPapel.objects.create(
            papel=papel, modulo=modulo, ativo=True, nivel=nivel
        )

    def _dar_modulo_processos(self, user, *, nivel=NIVEL_TODOS):
        papel = self._new_papel(f"Papel Processos {user.username}")
        self._assign_papel(user, papel)
        self._pp(papel, MODULO_PROCESSOS, nivel=nivel)
        return papel

    def _cliente(self, *, responsavel):
        return Cliente.objects.create(
            responsavel=responsavel, nome_razao_social="Cliente Teste Custas", tipo="PF"
        )

    def _processo(self, *, responsavel, cliente):
        processo = Processo.objects.create(responsavel=responsavel, titulo="Processo Teste Custas")
        processo.clientes.add(cliente)
        return processo

    def _solicitacao(self, *, processo, cliente, solicitante, status="solicitada", **kwargs):
        defaults = {
            "tipo": "pagamento",
            "descricao": "Custas de distribuição",
            "valor": "150.00",
            "status": status,
            "cliente": cliente,
            "processo": processo,
            "solicitante": solicitante,
            "anexo": _arquivo(),
        }
        defaults.update(kwargs)
        return SolicitacaoFinanceira.objects.create(**defaults)


class TestCardExibeComprovanteSoQuandoPaga(CustasComprovanteBase):
    @classmethod
    def get_test_schema_name(cls):
        return "custas_comprovante_card"

    def setUp(self):
        super().setUp()
        self.dono = self._user("dono_custas_card")
        self._dar_modulo_processos(self.dono)
        self.client.force_login(self.dono)
        self.cliente = self._cliente(responsavel=self.dono)
        self.processo = self._processo(responsavel=self.dono, cliente=self.cliente)

    def test_solicitacao_paga_mostra_aviso_pago_por_e_link_comprovante(self):
        solicitacao = self._solicitacao(
            processo=self.processo,
            cliente=self.cliente,
            solicitante=self.dono,
            status="paga",
            pago_por="escritorio",
            comprovante_pagamento=_arquivo("comprovante.pdf"),
        )
        r = self.client.get(
            f"/processos/{self.processo.pk}/?aba=custas", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 200)
        conteudo = r.content.decode()
        self.assertIn("Paga", conteudo)
        self.assertIn("Pago pelo Escritório", conteudo)
        self.assertIn(
            f"/processos/custas/{solicitacao.pk}/comprovante/", conteudo
        )

    def test_solicitacao_nao_paga_nao_mostra_comprovante_nem_aviso(self):
        for status in ("solicitada", "em_analise", "aprovada", "rejeitada"):
            with self.subTest(status=status):
                solicitacao = self._solicitacao(
                    processo=self.processo,
                    cliente=self.cliente,
                    solicitante=self.dono,
                    status=status,
                )
                r = self.client.get(
                    f"/processos/{self.processo.pk}/?aba=custas", HTTP_HOST=self.http_host
                )
                conteudo = r.content.decode()
                self.assertNotIn(
                    f"/processos/custas/{solicitacao.pk}/comprovante/", conteudo
                )
                solicitacao.delete()


class TestDownloadComprovanteSeguraEscopoDoProcesso(CustasComprovanteBase):
    """Download segue o escopo de leitura do processo (não o de Financeiro:
    não exige o módulo Financeiro, nem se limita a dados_próprios)."""

    @classmethod
    def get_test_schema_name(cls):
        return "custas_comprovante_download"

    def setUp(self):
        super().setUp()
        self.dono = self._user("dono_download_comprovante")
        self.estranho = self._user("estranho_download_comprovante")
        self._dar_modulo_processos(self.estranho, nivel=NIVEL_SOMENTE_SEUS)
        self.cliente = self._cliente(responsavel=self.dono)
        self.processo = self._processo(responsavel=self.dono, cliente=self.cliente)
        self.solicitacao = self._solicitacao(
            processo=self.processo,
            cliente=self.cliente,
            solicitante=self.dono,
            status="paga",
            pago_por="cliente",
            comprovante_pagamento=_arquivo("comprovante-confidencial.pdf", b"conteudo-confidencial"),
        )

    def test_dono_do_processo_baixa_sem_ter_acesso_ao_modulo_financeiro(self):
        self._dar_modulo_processos(self.dono)
        self.client.force_login(self.dono)
        r = self.client.get(
            f"/processos/custas/{self.solicitacao.pk}/comprovante/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(b"".join(r.streaming_content), b"conteudo-confidencial")

    def test_estranho_ao_processo_recebe_404(self):
        self.client.force_login(self.estranho)
        r = self.client.get(
            f"/processos/custas/{self.solicitacao.pk}/comprovante/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 404)

    def test_sem_modulo_processos_recebe_403(self):
        self.client.force_login(self.dono)
        r = self.client.get(
            f"/processos/custas/{self.solicitacao.pk}/comprovante/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 403)

    def test_sem_comprovante_recebe_404(self):
        self._dar_modulo_processos(self.dono)
        self.client.force_login(self.dono)
        outra = self._solicitacao(
            processo=self.processo, cliente=self.cliente, solicitante=self.dono, status="aprovada",
        )
        r = self.client.get(
            f"/processos/custas/{outra.pk}/comprovante/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 404)

    def test_anonimo_e_redirecionado_ao_login(self):
        r = self.client.get(
            f"/processos/custas/{self.solicitacao.pk}/comprovante/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login/", r.url)
