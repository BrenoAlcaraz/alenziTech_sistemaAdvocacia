"""
Testes de anexo (boleto/comprovante) em LancamentoFinanceiro e
CustaJudicial, e da tag "solicitado por" na lista de lançamentos
(specs/financeiro-visao-grafica-navegacao-temporal.md).

Segue o mesmo padrão de fixtures/override de MEDIA_ROOT de
apps/financeiro/tests/test_solicitacoes.py.
"""

import os
import shutil
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PapelAcesso, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import MODULO_FINANCEIRO, NIVEL_DADOS_TODOS
from apps.financeiro.models import CustaJudicial, LancamentoFinanceiro, SolicitacaoFinanceira

_MEDIA_TMP = tempfile.mkdtemp(prefix="lawsystem_test_media_anexos_")


def _arquivo(nome="boleto.pdf"):
    return SimpleUploadedFile(nome, b"conteudo-teste", content_type="application/pdf")


@override_settings(MEDIA_ROOT=_MEDIA_TMP)
class AnexosFinanceiroBase(TenantTestCase):
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
        self.user = User.objects.create_user(username="financeiro_user", password="testpass")
        papel = PapelAcesso.objects.create(nome="Papel Financeiro", ativo=True)
        UsuarioPapel.objects.create(usuario=self.user, papel=papel, ativo=True)
        PermissaoPapel.objects.create(
            papel=papel, modulo=MODULO_FINANCEIRO, ativo=True, nivel=NIVEL_DADOS_TODOS,
        )
        self.client.force_login(self.user)

    def _lancamento(self, **kwargs):
        defaults = {
            "tipo": "despesa",
            "descricao": "Lançamento Teste",
            "valor": "100.00",
            "data_vencimento": "2026-09-15",
            "status": "pendente",
        }
        defaults.update(kwargs)
        return LancamentoFinanceiro.objects.create(**defaults)

    def _custa(self, **kwargs):
        defaults = {
            "descricao": "Custa Teste",
            "valor": "50.00",
            "data": "2026-09-01",
            "tipo": "adiantamento",
        }
        defaults.update(kwargs)
        return CustaJudicial.objects.create(**defaults)


class TestAnexoLancamento(AnexosFinanceiroBase):
    def test_download_do_anexo_existente(self):
        lancamento = self._lancamento(anexo=_arquivo())
        r = self.client.get(f"/financeiro/lancamentos/{lancamento.pk}/anexo/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)

    def test_download_sem_anexo_e_404(self):
        lancamento = self._lancamento()
        r = self.client.get(f"/financeiro/lancamentos/{lancamento.pk}/anexo/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 404)

    def test_acao_inline_anexa_sem_navegar_para_edicao(self):
        lancamento = self._lancamento()
        r = self.client.post(
            f"/financeiro/lancamentos/{lancamento.pk}/anexar/",
            {"anexo": _arquivo("comprovante.pdf")},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        lancamento.refresh_from_db()
        self.assertTrue(lancamento.anexo)

    def test_excluir_lancamento_remove_arquivo_do_storage(self):
        lancamento = self._lancamento(anexo=_arquivo())
        caminho_arquivo = lancamento.anexo.path
        self.assertTrue(os.path.exists(caminho_arquivo))

        lancamento.delete()

        self.assertFalse(os.path.exists(caminho_arquivo))

    def test_download_do_comprovante_existente(self):
        lancamento = self._lancamento(status="pago", comprovante_pagamento=_arquivo())
        r = self.client.get(
            f"/financeiro/lancamentos/{lancamento.pk}/comprovante-pagamento/", HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 200)

    def test_download_sem_comprovante_e_404(self):
        lancamento = self._lancamento(status="pago")
        r = self.client.get(
            f"/financeiro/lancamentos/{lancamento.pk}/comprovante-pagamento/", HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 404)

    def test_acao_inline_anexa_comprovante_com_lancamento_pago(self):
        lancamento = self._lancamento(status="pago")
        r = self.client.post(
            f"/financeiro/lancamentos/{lancamento.pk}/anexar-comprovante/",
            {"comprovante_pagamento": _arquivo("comprovante.pdf")},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        lancamento.refresh_from_db()
        self.assertTrue(lancamento.comprovante_pagamento)

    def test_acao_inline_de_comprovante_ignora_lancamento_nao_pago(self):
        lancamento = self._lancamento(status="pendente")
        r = self.client.post(
            f"/financeiro/lancamentos/{lancamento.pk}/anexar-comprovante/",
            {"comprovante_pagamento": _arquivo("comprovante.pdf")},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        lancamento.refresh_from_db()
        self.assertFalse(lancamento.comprovante_pagamento)

    def test_excluir_lancamento_remove_comprovante_do_storage(self):
        lancamento = self._lancamento(status="pago", comprovante_pagamento=_arquivo())
        caminho_arquivo = lancamento.comprovante_pagamento.path
        self.assertTrue(os.path.exists(caminho_arquivo))

        lancamento.delete()

        self.assertFalse(os.path.exists(caminho_arquivo))


class TestAnexoCusta(AnexosFinanceiroBase):
    def test_download_do_anexo_existente(self):
        custa = self._custa(anexo=_arquivo())
        r = self.client.get(f"/financeiro/custas/{custa.pk}/anexo/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)

    def test_download_sem_anexo_e_404(self):
        custa = self._custa()
        r = self.client.get(f"/financeiro/custas/{custa.pk}/anexo/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 404)

    def test_excluir_custa_remove_arquivo_do_storage(self):
        custa = self._custa(anexo=_arquivo())
        caminho_arquivo = custa.anexo.path
        self.assertTrue(os.path.exists(caminho_arquivo))

        custa.delete()

        self.assertFalse(os.path.exists(caminho_arquivo))


class TestTagSolicitadoPor(AnexosFinanceiroBase):
    def test_lancamento_de_solicitacao_exibe_tag_solicitado_por(self):
        solicitante = User.objects.create_user(username="quem_solicitou", password="testpass")
        solicitacao = SolicitacaoFinanceira.objects.create(
            tipo="reembolso", descricao="Diligência", valor="80.00",
            data_gasto="2026-09-10", anexo=_arquivo(), solicitante=solicitante,
        )
        solicitacao.avancar_para("em_analise")
        solicitacao.avancar_para("aprovada")
        solicitacao.avancar_para("paga")

        r = self.client.get("/financeiro/", HTTP_HOST=self.http_host)
        self.assertContains(r, "SOLICITADO POR")
        self.assertContains(r, "QUEM_SOLICITOU")

    def test_lancamento_avulso_nao_exibe_tag_solicitado_por(self):
        self._lancamento(descricao="Despesa avulsa")
        r = self.client.get("/financeiro/", HTTP_HOST=self.http_host)
        self.assertNotContains(r, "SOLICITADO POR")
