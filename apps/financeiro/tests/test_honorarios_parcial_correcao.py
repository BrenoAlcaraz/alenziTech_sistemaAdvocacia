"""
Testes de recebimento parcial e correção monetária/juros de
Honorários (PDR-0022) — complementa
apps/financeiro/tests/test_honorarios.py (PDR-0007), que cobre a
autorização exclusiva do Administrador e a notificação, ambas
inalteradas por este PDR.

Segue o mesmo padrão de fixtures de
apps/financeiro/tests/test_honorarios.py sobre
django_tenants.test.cases.TenantTestCase.
"""

import shutil
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PapelAcesso, PerfilUsuario, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import MODULO_FINANCEIRO, NIVEL_DADOS_TODOS
from apps.financeiro.models import Honorario, LancamentoFinanceiro
from apps.saas_tenants.models import Dominio

_MEDIA_TMP = tempfile.mkdtemp(prefix="lawsystem_test_media_honorarios_")


@override_settings(MEDIA_ROOT=_MEDIA_TMP)
class HonorariosParcialCorrecaoBase(TenantTestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_MEDIA_TMP, ignore_errors=True)

    def setUp(self):
        self._media_override = override_settings(MEDIA_ROOT=_MEDIA_TMP)
        self._media_override.enable()
        self.addCleanup(self._media_override.disable)
        super().setUp()
        domain_obj = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = domain_obj.domain if domain_obj else "localhost"
        self.admin = User.objects.create_user(username="admin_escritorio", password="testpass")
        papel = PapelAcesso.objects.create(nome="Papel Financeiro Admin", ativo=True)
        UsuarioPapel.objects.create(usuario=self.admin, papel=papel, ativo=True)
        PermissaoPapel.objects.create(
            papel=papel, modulo=MODULO_FINANCEIRO, ativo=True, nivel=NIVEL_DADOS_TODOS,
        )
        PerfilUsuario.objects.filter(user=self.admin).update(is_admin_escritorio=True)
        self.client.force_login(self.admin)

    def _confirmar(self, honorario, **dados):
        return self.client.post(
            f"/financeiro/honorarios/{honorario.pk}/confirmar-recebimento/", dados, HTTP_HOST=self.http_host,
        )


class TestRecebimentoParcial(HonorariosParcialCorrecaoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "honorarios_parcial"

    def test_confirmacao_parcial_mantem_status_previsto(self):
        honorario = Honorario.objects.create(tipo="contratual", valor_estimado="5000.00")

        r = self._confirmar(
            honorario, valor_efetivo="5000.00", valor_recebido_agora="2000.00", data_recebida="2026-04-01",
        )
        self.assertEqual(r.status_code, 302)
        honorario.refresh_from_db()
        self.assertEqual(honorario.status, "previsto")
        self.assertEqual(str(honorario.valor_recebido), "2000.00")

    def test_segunda_confirmacao_completa_marca_recebido(self):
        honorario = Honorario.objects.create(tipo="contratual", valor_estimado="5000.00")
        self._confirmar(honorario, valor_efetivo="5000.00", valor_recebido_agora="2000.00", data_recebida="2026-04-01")

        r = self._confirmar(
            honorario, valor_efetivo="5000.00", valor_recebido_agora="3000.00", data_recebida="2026-05-01",
        )
        self.assertEqual(r.status_code, 302)
        honorario.refresh_from_db()
        self.assertEqual(honorario.status, "recebido")
        self.assertEqual(str(honorario.valor_recebido), "5000.00")

    def test_cada_confirmacao_gera_seu_proprio_lancamento(self):
        honorario = Honorario.objects.create(tipo="contratual", valor_estimado="5000.00")
        antes = LancamentoFinanceiro.objects.count()

        self._confirmar(honorario, valor_efetivo="5000.00", valor_recebido_agora="2000.00", data_recebida="2026-04-01")
        self._confirmar(honorario, valor_efetivo="5000.00", valor_recebido_agora="3000.00", data_recebida="2026-05-01")

        self.assertEqual(LancamentoFinanceiro.objects.count(), antes + 2)
        valores = set(
            LancamentoFinanceiro.objects.filter(descricao__startswith="Honorário").values_list("valor", flat=True)
        )
        self.assertIn(2000, {float(v) for v in valores} | valores)

    def test_valor_recebido_agora_em_branco_confirma_o_pendente_inteiro(self):
        """Comportamento idêntico a antes do PDR-0022: sem informar o
        valor parcial, confirma o valor efetivo inteiro de uma vez."""
        honorario = Honorario.objects.create(tipo="contratual", valor_estimado="2000.00")
        r = self._confirmar(honorario, valor_efetivo="2000.00", data_recebida="2026-09-10")
        self.assertEqual(r.status_code, 302)
        honorario.refresh_from_db()
        self.assertEqual(honorario.status, "recebido")
        self.assertEqual(str(honorario.valor_recebido), "2000.00")

    def test_valor_recebido_nao_pode_ultrapassar_valor_efetivo(self):
        honorario = Honorario.objects.create(tipo="contratual", valor_estimado="1000.00")
        r = self._confirmar(
            honorario, valor_efetivo="1000.00", valor_recebido_agora="1500.00", data_recebida="2026-09-10",
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context["form"].errors)
        honorario.refresh_from_db()
        self.assertEqual(honorario.status, "previsto")
        self.assertEqual(str(honorario.valor_recebido), "0.00")

    def test_comprovante_anexado_vai_para_o_lancamento_gerado(self):
        honorario = Honorario.objects.create(tipo="contratual", valor_estimado="1000.00")
        r = self.client.post(
            f"/financeiro/honorarios/{honorario.pk}/confirmar-recebimento/",
            {"valor_efetivo": "1000.00", "data_recebida": "2026-09-10",
             "anexo": SimpleUploadedFile("comprovante.pdf", b"conteudo", content_type="application/pdf")},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        lancamento = LancamentoFinanceiro.objects.filter(descricao__startswith="Honorário").latest("criado_em")
        self.assertTrue(lancamento.comprovante_pagamento)


class TestCorrecaoMonetaria(HonorariosParcialCorrecaoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "honorarios_correcao"

    def test_sem_taxa_nao_ha_correcao(self):
        honorario = Honorario.objects.create(tipo="sucumbencial", valor_estimado="1000.00")
        self._confirmar(honorario, valor_efetivo="1000.00", data_recebida="2026-09-10")
        honorario.refresh_from_db()
        self.assertEqual(str(honorario.valor_efetivo), "1000.00")

    def test_definir_taxa_pela_primeira_vez_nao_corrige_retroativamente(self):
        """A taxa só passa a valer a partir de agora — não corrige um
        período em que o honorário ainda não tinha taxa configurada."""
        honorario = Honorario.objects.create(tipo="sucumbencial", valor_estimado="5000.00")
        self._confirmar(
            honorario, valor_efetivo="5000.00", valor_recebido_agora="2000.00", data_recebida="2026-04-01",
            taxa_mensal="1.00", data_termo="2026-01-01",
        )
        honorario.refresh_from_db()
        self.assertEqual(str(honorario.valor_efetivo), "5000.00")

    def test_segunda_confirmacao_aplica_correcao_sobre_o_pendente(self):
        honorario = Honorario.objects.create(tipo="sucumbencial", valor_estimado="5000.00")
        self._confirmar(
            honorario, valor_efetivo="5000.00", valor_recebido_agora="2000.00", data_recebida="2026-04-01",
            taxa_mensal="1.00", data_termo="2026-01-01",
        )

        r = self._confirmar(
            honorario, valor_efetivo="5000.00", data_recebida="2026-07-01",
            taxa_mensal="1.00", data_termo="2026-01-01",
        )
        self.assertEqual(r.status_code, 302)
        honorario.refresh_from_db()
        # pendente antes = 5000 - 2000 = 3000; 3 meses (abr -> jul) a 1% = 90.00
        self.assertEqual(str(honorario.valor_efetivo), "5090.00")
        self.assertEqual(honorario.status, "recebido")
        self.assertEqual(str(honorario.valor_recebido), "5090.00")

    def test_editar_taxa_e_restrito_ao_administrador(self):
        nao_admin = User.objects.create_user(username="financeiro_comum", password="testpass")
        papel = PapelAcesso.objects.create(nome="Papel Financeiro Comum", ativo=True)
        UsuarioPapel.objects.create(usuario=nao_admin, papel=papel, ativo=True)
        PermissaoPapel.objects.create(
            papel=papel, modulo=MODULO_FINANCEIRO, ativo=True, nivel=NIVEL_DADOS_TODOS,
        )
        self.client.force_login(nao_admin)

        honorario = Honorario.objects.create(tipo="sucumbencial", valor_estimado="1000.00")
        r = self._confirmar(
            honorario, valor_efetivo="1000.00", data_recebida="2026-09-10",
            taxa_mensal="5.00", data_termo="2026-01-01",
        )
        self.assertEqual(r.status_code, 403)
        honorario.refresh_from_db()
        self.assertIsNone(honorario.taxa_mensal)
