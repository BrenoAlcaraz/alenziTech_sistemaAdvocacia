"""
Ciclo de recebimento de honorários (PDR-0035): recebimento de honorário
exclusivo do Administrador também nas parcelas geradas, "Já recebido" no
cadastro, situação calculada e documento de origem.

Mesmo padrão de fixtures de test_honorarios_parcial_correcao.py.
"""

import shutil
import tempfile
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PapelAcesso, PerfilUsuario, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import MODULO_FINANCEIRO, NIVEL_DADOS_TODOS
from apps.financeiro.models import Honorario, LancamentoFinanceiro
from apps.financeiro.services import (
    gerar_lancamentos_do_honorario, honorarios_da_janela, situacao_do_honorario,
)
from apps.saas_tenants.models import Dominio

_MEDIA_TMP = tempfile.mkdtemp(prefix="lawsystem_test_media_ciclo_")


@override_settings(MEDIA_ROOT=_MEDIA_TMP)
class CicloRecebimentoBase(TenantTestCase):
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
        self.hoje = timezone.localdate()
        self.admin = self._usuario("admin_escritorio", admin=True)
        self.comum = self._usuario("financeiro_comum", admin=False)

    def _usuario(self, username, *, admin):
        user = User.objects.create_user(username=username, password="testpass")
        papel = PapelAcesso.objects.create(nome=f"Papel {username}", ativo=True)
        UsuarioPapel.objects.create(usuario=user, papel=papel, ativo=True)
        PermissaoPapel.objects.create(papel=papel, modulo=MODULO_FINANCEIRO, ativo=True, nivel=NIVEL_DADOS_TODOS)
        PerfilUsuario.objects.filter(user=user).update(is_admin_escritorio=admin)
        return user

    def _post(self, url, dados, usuario):
        self.client.force_login(usuario)
        return self.client.post(url, dados, HTTP_HOST=self.http_host)

    def _parcelado(self, parcelas=3):
        honorario = Honorario.objects.create(
            tipo="contratual", modalidade="valor", classificacao="parcelado",
            numero_parcelas=parcelas, valor_estimado="6000.00", data_prevista=self.hoje,
        )
        gerar_lancamentos_do_honorario(honorario)
        return honorario

    def _cadastro(self, **extra):
        dados = {
            "tipo": "contratual", "modalidade": "valor", "classificacao": "unica",
            "valor_estimado": "3000.00", "data_prevista": self.hoje.isoformat(),
        }
        dados.update(extra)
        return dados


class TestParcelaDeHonorarioSoAdministrador(CicloRecebimentoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "honorarios_ciclo_parcela"

    def test_usuario_comum_nao_marca_parcela_como_paga(self):
        parcela = self._parcelado().lancamentos.first()
        r = self._post(f"/financeiro/lancamentos/{parcela.pk}/marcar-pago/", {}, self.comum)
        self.assertEqual(r.status_code, 403)
        parcela.refresh_from_db()
        self.assertEqual(parcela.status, "pendente")

    def test_administrador_marca_parcela_como_paga(self):
        parcela = self._parcelado().lancamentos.first()
        self._post(f"/financeiro/lancamentos/{parcela.pk}/marcar-pago/", {}, self.admin)
        parcela.refresh_from_db()
        self.assertEqual(parcela.status, "pago")

    def test_usuario_comum_nao_marca_pago_pela_edicao(self):
        parcela = self._parcelado().lancamentos.first()
        dados = {
            "tipo": "receita", "descricao": parcela.descricao, "valor": parcela.valor,
            "data_vencimento": parcela.data_vencimento.isoformat(), "categoria": "honorario",
            "status": "pago", "data_pagamento": self.hoje.isoformat(), "classificacao": "parcelado",
        }
        r = self._post(f"/financeiro/lancamentos/{parcela.pk}/editar/", dados, self.comum)
        self.assertEqual(r.status_code, 200)
        parcela.refresh_from_db()
        self.assertEqual(parcela.status, "pendente")

    def test_usuario_comum_nao_reabre_nem_exclui_parcela_paga(self):
        parcela = self._parcelado().lancamentos.first()
        parcela.status, parcela.data_pagamento = "pago", self.hoje
        parcela.save()
        self.assertEqual(self._post(f"/financeiro/lancamentos/{parcela.pk}/reabrir/", {}, self.comum).status_code, 403)
        self.assertEqual(self._post(f"/financeiro/lancamentos/{parcela.pk}/excluir/", {}, self.comum).status_code, 403)
        parcela.refresh_from_db()
        self.assertEqual(parcela.status, "pago")

    def test_lancamento_comum_segue_sem_restricao(self):
        lancamento = LancamentoFinanceiro.objects.create(
            tipo="receita", descricao="Consultoria", valor="100.00", data_vencimento=self.hoje, categoria="consultoria",
        )
        self._post(f"/financeiro/lancamentos/{lancamento.pk}/marcar-pago/", {}, self.comum)
        lancamento.refresh_from_db()
        self.assertEqual(lancamento.status, "pago")


class TestRecebimentoDeHonorarioUnico(CicloRecebimentoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "honorarios_ciclo_unico"

    def _confirmar(self, honorario, valor):
        return self._post(
            f"/financeiro/honorarios/{honorario.pk}/confirmar-recebimento/",
            {"valor_efetivo": "3000.00", "valor_recebido_agora": valor, "data_recebida": self.hoje.isoformat()},
            self.admin,
        )

    def test_confirmacao_gera_lancamento_vinculado_ao_honorario(self):
        honorario = Honorario.objects.create(tipo="contratual", valor_estimado="3000.00")
        self._confirmar(honorario, "1000.00")
        recebimento = honorario.lancamentos.get()
        self.assertEqual((recebimento.status, recebimento.valor), ("pago", Decimal("1000.00")))

    def test_recebimento_de_honorario_unico_nao_se_desfaz_pelo_lancamento(self):
        honorario = Honorario.objects.create(tipo="contratual", valor_estimado="3000.00")
        self._confirmar(honorario, "1000.00")
        recebimento = honorario.lancamentos.get()
        self.assertEqual(self._post(f"/financeiro/lancamentos/{recebimento.pk}/reabrir/", {}, self.admin).status_code, 403)
        self.assertEqual(self._post(f"/financeiro/lancamentos/{recebimento.pk}/excluir/", {}, self.admin).status_code, 403)

    def test_painel_segue_contando_o_pendente_do_parcialmente_recebido(self):
        honorario = Honorario.objects.create(tipo="contratual", valor_estimado="3000.00", data_prevista=self.hoje)
        self._confirmar(honorario, "1000.00")
        totais = honorarios_da_janela(self.hoje, self.hoje)
        self.assertEqual(totais, {"previsto": Decimal("3000.00"), "recebido": Decimal("1000.00")})


class TestJaRecebidoNoCadastro(CicloRecebimentoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "honorarios_ciclo_cadastro"

    def test_administrador_cadastra_unico_ja_recebido_com_comprovante(self):
        comprovante = SimpleUploadedFile("pix.pdf", b"%PDF-1.4", content_type="application/pdf")
        r = self._post("/financeiro/honorarios/novo/", self._cadastro(
            ja_recebido="on", data_recebimento=self.hoje.isoformat(), comprovante_recebimento=comprovante,
        ), self.admin)
        self.assertEqual(r.status_code, 302)
        honorario = Honorario.objects.get()
        self.assertEqual((honorario.status, honorario.valor_recebido), ("recebido", Decimal("3000.00")))
        recebimento = honorario.lancamentos.get()
        self.assertEqual(recebimento.status, "pago")
        self.assertTrue(recebimento.comprovante_pagamento)

    def test_administrador_cadastra_parcelado_com_so_a_primeira_paga(self):
        self._post("/financeiro/honorarios/novo/", self._cadastro(
            classificacao="parcelado", numero_parcelas="3", valor_estimado="6000.00",
            ja_recebido="on", data_recebimento=self.hoje.isoformat(),
        ), self.admin)
        status = list(Honorario.objects.get().lancamentos.order_by("data_vencimento").values_list("status", flat=True))
        self.assertEqual(status, ["pago", "pendente", "pendente"])

    def test_usuario_comum_nao_registra_recebimento_no_cadastro(self):
        r = self._post("/financeiro/honorarios/novo/", self._cadastro(
            ja_recebido="on", data_recebimento=self.hoje.isoformat(),
        ), self.comum)
        self.assertEqual(r.status_code, 302)
        honorario = Honorario.objects.get()
        self.assertEqual((honorario.status, honorario.valor_recebido), ("previsto", Decimal("0")))
        self.assertFalse(honorario.lancamentos.exists())

    def test_data_de_recebimento_futura_e_recusada(self):
        amanha = self.hoje + timedelta(days=1)
        r = self._post("/financeiro/honorarios/novo/", self._cadastro(
            ja_recebido="on", data_recebimento=amanha.isoformat(),
        ), self.admin)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Honorario.objects.exists())

    def test_documento_de_origem_e_baixado(self):
        contrato = SimpleUploadedFile("contrato.pdf", b"%PDF-1.4", content_type="application/pdf")
        self._post("/financeiro/honorarios/novo/", self._cadastro(documento=contrato), self.comum)
        honorario = Honorario.objects.get()
        r = self.client.get(f"/financeiro/honorarios/{honorario.pk}/documento/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)


class TestSituacaoCalculada(CicloRecebimentoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "honorarios_ciclo_situacao"

    def test_unico_vencido_com_saldo(self):
        honorario = Honorario(tipo="contratual", valor_estimado="100.00", data_prevista=date(2020, 1, 1))
        self.assertEqual(situacao_do_honorario(honorario, self.hoje, Decimal("100.00")), "vencido")

    def test_unico_parcial_a_vencer(self):
        honorario = Honorario(
            tipo="contratual", valor_estimado=Decimal("100.00"), valor_recebido=Decimal("40.00"),
            data_prevista=self.hoje + timedelta(days=5),
        )
        self.assertEqual(situacao_do_honorario(honorario, self.hoje, Decimal("60.00")), "parcial")

    def test_parcelado_pelas_parcelas(self):
        honorario = self._parcelado()
        self.assertEqual(situacao_do_honorario(honorario, self.hoje), "a_vencer")
        honorario.lancamentos.filter(lancamento_origem__isnull=True).update(status="pago")
        self.assertEqual(situacao_do_honorario(honorario, self.hoje), "parcial")
        honorario.lancamentos.update(status="pago")
        self.assertEqual(situacao_do_honorario(honorario, self.hoje), "recebido")
        honorario.lancamentos.update(status="pendente", data_vencimento=date(2020, 1, 1))
        self.assertEqual(situacao_do_honorario(honorario, self.hoje), "vencido")
