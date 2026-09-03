"""
Testes de Solicitações financeiras (PDR-0006, fluxo em PDR-0015).

Cobre: transições de estado no model, escopo de visibilidade por nível
(`solicitacoes` vs `dados`), autorização das rotas novas e o efeito do
nível `dados`/`solicitacoes` já existente no kernel sobre as rotas
antigas de caixa geral (`index`, `custas`, lançamentos), que passam a
negar acesso a quem só tem nível `solicitacoes`.

Segue o mesmo padrão de fixtures de
apps/financeiro/tests/test_autorizacao.py sobre
django_tenants.test.cases.TenantTestCase.
"""

import shutil
import tempfile

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import TransactionTestCase, override_settings
from django_tenants.test.cases import TenantTestCase
from django_tenants.utils import schema_context, tenant_context

from apps.accounts.models import HabilitacaoPapel, PapelAcesso, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import (
    HAB_FINANCEIRO_REABRIR_LANCAMENTO_PAGO,
    MODULO_FINANCEIRO,
    NIVEL_DADOS_PROPRIOS,
    NIVEL_DADOS_TODOS,
    NIVEL_SOLICITACOES,
)
from apps.financeiro.models import LancamentoFinanceiro, SolicitacaoFinanceira
from apps.notificacoes.models import Notificacao
from apps.saas_tenants.models import Dominio, Escritorio

_MEDIA_TMP = tempfile.mkdtemp(prefix="lawsystem_test_media_")


def _anexo(nome="boleto.pdf"):
    return SimpleUploadedFile(nome, b"conteudo-teste", content_type="application/pdf")


@override_settings(MEDIA_ROOT=_MEDIA_TMP)
class SolicitacaoFinanceiraBase(TenantTestCase):
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

    def _user(self, username):
        return User.objects.create_user(username=username, password="testpass")

    def _new_papel(self, nome):
        return PapelAcesso.objects.create(nome=nome, ativo=True)

    def _conceder_modulo(self, user, *, nivel, habilitacoes=None):
        papel = self._new_papel(f"Papel Financeiro {user.username}")
        UsuarioPapel.objects.create(usuario=user, papel=papel, ativo=True)
        PermissaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=MODULO_FINANCEIRO, ativo=True, nivel=nivel
        )
        for item in habilitacoes or []:
            HabilitacaoPapel.objects.create(
                papel=papel, tipo_conta=None, modulo=MODULO_FINANCEIRO, item=item, ativo=True
            )
        return papel

    def _solicitacao(self, *, solicitante, **kwargs):
        defaults = {
            "tipo": "reembolso",
            "descricao": "Reembolso Teste",
            "valor": "150.00",
            "data_gasto": "2026-08-20",
            "anexo": _anexo("comprovante.pdf"),
            "solicitante": solicitante,
        }
        defaults.update(kwargs)
        return SolicitacaoFinanceira.objects.create(**defaults)


# ── Model: transições de estado ────────────────────────────────────────────────

class TestSolicitacaoFinanceiraTransicoes(SolicitacaoFinanceiraBase):
    @classmethod
    def get_test_schema_name(cls):
        return "solicitacoes_transicoes"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Solicitacoes Transicoes"
        tenant.slug = "solicitacoes-transicoes"

    def setUp(self):
        super().setUp()
        self.user = self._user("solicitante")

    def test_nasce_solicitada(self):
        s = self._solicitacao(solicitante=self.user)
        self.assertEqual(s.status, "solicitada")
        self.assertIsNone(s.lancamento)

    def test_anexo_novo_usa_namespace_protegido_do_tenant(self):
        solicitacao = self._solicitacao(solicitante=self.user)

        self.assertTrue(solicitacao.anexo.name.startswith(
            "tenants/solicitacoes_transicoes/protegido/financeiro/solicitacoes/"
        ))
        self.assertIsNone(solicitacao.anexo.url)

    def test_fluxo_completo_ate_paga_cria_um_lancamento(self):
        s = self._solicitacao(solicitante=self.user)
        antes = LancamentoFinanceiro.objects.count()

        s.avancar_para("em_analise")
        s.avancar_para("aprovada")
        s.avancar_para("paga")

        s.refresh_from_db()
        self.assertEqual(s.status, "paga")
        self.assertIsNotNone(s.lancamento)
        self.assertEqual(LancamentoFinanceiro.objects.count(), antes + 1)
        self.assertEqual(s.lancamento.status, "pago")
        self.assertEqual(s.lancamento.tipo, "despesa")
        self.assertEqual(s.lancamento.valor, s.valor)
        self.assertEqual(s.lancamento.responsavel, self.user)

    def test_fluxo_rejeitado_nao_cria_lancamento(self):
        s = self._solicitacao(solicitante=self.user)
        antes = LancamentoFinanceiro.objects.count()

        s.avancar_para("em_analise")
        s.avancar_para("rejeitada")

        s.refresh_from_db()
        self.assertEqual(s.status, "rejeitada")
        self.assertIsNone(s.lancamento)
        self.assertEqual(LancamentoFinanceiro.objects.count(), antes)

    def test_nao_pula_etapa_solicitada_para_aprovada(self):
        s = self._solicitacao(solicitante=self.user)
        self.assertFalse(s.pode_transicionar_para("aprovada"))
        with self.assertRaises(ValueError):
            s.avancar_para("aprovada")

    def test_nao_pula_etapa_direto_para_paga(self):
        s = self._solicitacao(solicitante=self.user)
        s.avancar_para("em_analise")
        s.avancar_para("aprovada")
        self.assertTrue(s.pode_transicionar_para("paga"))

        s2 = self._solicitacao(solicitante=self.user)
        self.assertFalse(s2.pode_transicionar_para("paga"))

    def test_rejeitada_e_terminal(self):
        s = self._solicitacao(solicitante=self.user)
        s.avancar_para("em_analise")
        s.avancar_para("rejeitada")
        self.assertFalse(s.pode_transicionar_para("aprovada"))
        self.assertFalse(s.pode_transicionar_para("paga"))

    def test_criar_solicitacao_nao_gera_lancamento(self):
        antes = LancamentoFinanceiro.objects.count()
        self._solicitacao(solicitante=self.user)
        self.assertEqual(LancamentoFinanceiro.objects.count(), antes)


# ── Views: autorização e escopo ─────────────────────────────────────────────────

class TestSolicitacoesEscopoNivelSolicitacoes(SolicitacaoFinanceiraBase):
    """Usuário com nível `solicitacoes`: cria e acompanha só as próprias."""

    @classmethod
    def get_test_schema_name(cls):
        return "solicitacoes_nivel_solicitacoes"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Solicitacoes Nivel Solicitacoes"
        tenant.slug = "solicitacoes-nivel-solicitacoes"

    def setUp(self):
        super().setUp()
        self.user = self._user("advogado_sem_caixa")
        self._conceder_modulo(self.user, nivel=NIVEL_SOLICITACOES)
        self.client.force_login(self.user)

        self.outro = self._user("outro_advogado")
        self._conceder_modulo(self.outro, nivel=NIVEL_SOLICITACOES)

        self.minha = self._solicitacao(solicitante=self.user, descricao="Minha solicitação")
        self.alheia = self._solicitacao(solicitante=self.outro, descricao="Solicitação alheia")

    def test_index_redireciona_para_solicitacoes(self):
        r = self.client.get("/financeiro/", HTTP_HOST=self.http_host)
        self.assertRedirects(r, "/financeiro/solicitacoes/", fetch_redirect_response=False)

    def test_custas_negado(self):
        r = self.client.get("/financeiro/custas/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_form_lancamento_negado(self):
        r = self.client.get("/financeiro/lancamentos/novo/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_lista_mostra_so_as_proprias(self):
        r = self.client.get("/financeiro/solicitacoes/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        descricoes = {s.descricao for s in r.context["solicitacoes"]}
        self.assertIn("Minha solicitação", descricoes)
        self.assertNotIn("Solicitação alheia", descricoes)

    def test_detalhe_da_propria_autorizado(self):
        r = self.client.get(f"/financeiro/solicitacoes/{self.minha.pk}/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)

    def test_detalhe_alheia_nao_encontrada(self):
        r = self.client.get(f"/financeiro/solicitacoes/{self.alheia.pk}/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 404)

    def test_anexo_da_propria_autorizado(self):
        r = self.client.get(f"/financeiro/solicitacoes/{self.minha.pk}/anexo/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)

    def test_anexo_legado_da_propria_continua_autorizado(self):
        nome_legado = "solicitacoes_financeiras/2026/08/comprovante-legado.pdf"
        self.minha.anexo.storage.save(nome_legado, ContentFile(b"conteudo-legado"))
        self.minha.anexo = nome_legado
        self.minha.save(update_fields=["anexo"])

        resposta = self.client.get(
            f"/financeiro/solicitacoes/{self.minha.pk}/anexo/",
            HTTP_HOST=self.http_host,
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(b"".join(resposta.streaming_content), b"conteudo-legado")

    def test_anexo_nao_e_servido_diretamente_por_media_url(self):
        resposta = self.client.get(
            f"/media/{self.minha.anexo.name}",
            HTTP_HOST=self.http_host,
        )

        self.assertEqual(resposta.status_code, 404)

    def test_usuario_anonimo_nao_recebe_conteudo_do_anexo(self):
        self.client.logout()

        resposta = self.client.get(
            f"/financeiro/solicitacoes/{self.minha.pk}/anexo/",
            HTTP_HOST=self.http_host,
        )

        self.assertEqual(resposta.status_code, 302)
        self.assertIn("/login/", resposta.url)

    def test_anexo_alheio_nao_encontrado(self):
        r = self.client.get(f"/financeiro/solicitacoes/{self.alheia.pk}/anexo/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 404)

    def test_nao_pode_processar_a_propria(self):
        r = self.client.post(
            f"/financeiro/solicitacoes/{self.minha.pk}/processar/",
            {"acao": "analisar"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 403)
        self.minha.refresh_from_db()
        self.assertEqual(self.minha.status, "solicitada")

    def test_criar_solicitacao_pagamento_completa(self):
        from apps.clientes.models import Cliente
        from apps.processos.models import Processo

        cliente = Cliente.objects.create(nome_razao_social="Cliente Teste", responsavel=self.user)
        processo = Processo.objects.create(
            titulo="Processo Teste", cliente=cliente, responsavel=self.user,
        )
        antes = SolicitacaoFinanceira.objects.count()
        r = self.client.post(
            "/financeiro/solicitacoes/nova/",
            {
                "tipo": "pagamento",
                "descricao": "Custa judicial urgente",
                "valor": "300.00",
                "cliente": cliente.pk,
                "processo": processo.pk,
                "vencimento": "2026-10-10",
                "anexo": _anexo("boleto.pdf"),
                "observacao": "",
            },
            HTTP_HOST=self.http_host,
        )
        self.assertRedirects(r, "/financeiro/solicitacoes/", fetch_redirect_response=False)
        self.assertEqual(SolicitacaoFinanceira.objects.count(), antes + 1)
        nova = SolicitacaoFinanceira.objects.get(descricao="Custa judicial urgente")
        self.assertEqual(nova.solicitante, self.user)
        self.assertEqual(nova.status, "solicitada")

    def test_criar_solicitacao_pagamento_sem_processo_falha(self):
        antes = SolicitacaoFinanceira.objects.count()
        r = self.client.post(
            "/financeiro/solicitacoes/nova/",
            {
                "tipo": "pagamento",
                "descricao": "Pagamento incompleto",
                "valor": "100.00",
                "vencimento": "2026-10-10",
                "anexo": _anexo("boleto.pdf"),
                "observacao": "",
            },
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(SolicitacaoFinanceira.objects.count(), antes)
        self.assertTrue(r.context["form"].errors)

    def test_criar_solicitacao_reembolso_sem_data_gasto_falha(self):
        antes = SolicitacaoFinanceira.objects.count()
        r = self.client.post(
            "/financeiro/solicitacoes/nova/",
            {
                "tipo": "reembolso",
                "descricao": "Reembolso incompleto",
                "valor": "80.00",
                "anexo": _anexo("comprovante.pdf"),
                "observacao": "",
            },
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(SolicitacaoFinanceira.objects.count(), antes)
        self.assertTrue(r.context["form"].errors)


class TestSolicitacoesEscopoNivelDados(SolicitacaoFinanceiraBase):
    """Usuário com nível `dados`: enxerga e processa todas as solicitações."""

    @classmethod
    def get_test_schema_name(cls):
        return "solicitacoes_nivel_dados"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Solicitacoes Nivel Dados"
        tenant.slug = "solicitacoes-nivel-dados"

    def setUp(self):
        super().setUp()
        self.financeiro = self._user("financeiro_dados")
        self._conceder_modulo(self.financeiro, nivel=NIVEL_DADOS_TODOS)
        self.client.force_login(self.financeiro)

        self.solicitante = self._user("advogado")
        self._conceder_modulo(self.solicitante, nivel=NIVEL_SOLICITACOES)
        self.solicitacao = self._solicitacao(solicitante=self.solicitante)

    def test_index_autorizado(self):
        r = self.client.get("/financeiro/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)

    def test_lista_mostra_todas(self):
        r = self.client.get("/financeiro/solicitacoes/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        self.assertIn(self.solicitacao, list(r.context["solicitacoes"]))

    def test_detalhe_de_qualquer_solicitacao_autorizado(self):
        r = self.client.get(f"/financeiro/solicitacoes/{self.solicitacao.pk}/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)

    def test_anexo_de_qualquer_solicitacao_autorizado(self):
        r = self.client.get(f"/financeiro/solicitacoes/{self.solicitacao.pk}/anexo/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)

    def test_processa_fluxo_completo(self):
        pk = self.solicitacao.pk
        for acao, status_esperado in [
            ("analisar", "em_analise"),
            ("aprovar", "aprovada"),
            ("pagar", "paga"),
        ]:
            r = self.client.post(
                f"/financeiro/solicitacoes/{pk}/processar/", {"acao": acao}, HTTP_HOST=self.http_host
            )
            self.assertEqual(r.status_code, 302)
            self.solicitacao.refresh_from_db()
            self.assertEqual(self.solicitacao.status, status_esperado)

        self.assertIsNotNone(self.solicitacao.lancamento)
        self.assertEqual(self.solicitacao.lancamento.status, "pago")

    def test_pular_etapa_negado(self):
        r = self.client.post(
            f"/financeiro/solicitacoes/{self.solicitacao.pk}/processar/",
            {"acao": "pagar"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 403)
        self.solicitacao.refresh_from_db()
        self.assertEqual(self.solicitacao.status, "solicitada")

    def test_reabrir_lancamento_gerado_por_solicitacao_negado(self):
        self.solicitacao.avancar_para("em_analise")
        self.solicitacao.avancar_para("aprovada")
        self.solicitacao.avancar_para("paga")
        lancamento = self.solicitacao.lancamento

        r = self.client.post(
            f"/financeiro/lancamentos/{lancamento.pk}/reabrir/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 403)
        lancamento.refresh_from_db()
        self.assertEqual(lancamento.status, "pago")

    def test_excluir_lancamento_gerado_por_solicitacao_negado(self):
        self.solicitacao.avancar_para("em_analise")
        self.solicitacao.avancar_para("aprovada")
        self.solicitacao.avancar_para("paga")
        lancamento = self.solicitacao.lancamento

        r = self.client.post(
            f"/financeiro/lancamentos/{lancamento.pk}/excluir/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 403)
        self.assertTrue(LancamentoFinanceiro.objects.filter(pk=lancamento.pk).exists())

    def test_reabrir_lancamento_com_habilitacao_autorizado_e_notifica_solicitante(self):
        habilitado = self._user("financeiro_habilitado")
        self._conceder_modulo(
            habilitado, nivel=NIVEL_DADOS_TODOS, habilitacoes=[HAB_FINANCEIRO_REABRIR_LANCAMENTO_PAGO]
        )
        self.client.force_login(habilitado)

        self.solicitacao.avancar_para("em_analise")
        self.solicitacao.avancar_para("aprovada")
        self.solicitacao.avancar_para("paga")
        lancamento = self.solicitacao.lancamento
        antes = Notificacao.objects.count()

        r = self.client.post(
            f"/financeiro/lancamentos/{lancamento.pk}/reabrir/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 302)
        lancamento.refresh_from_db()
        self.assertEqual(lancamento.status, "pendente")
        self.assertIsNone(lancamento.data_pagamento)

        self.solicitacao.refresh_from_db()
        self.assertEqual(self.solicitacao.status, "paga")

        self.assertEqual(Notificacao.objects.count(), antes + 1)
        notificacao = Notificacao.objects.latest("criado_em")
        self.assertEqual(notificacao.destinatario, self.solicitante)

    def test_reabrir_lancamento_pelo_proprio_solicitante_nao_notifica_a_si_mesmo(self):
        solicitante_habilitado = self._user("solicitante_habilitado")
        self._conceder_modulo(
            solicitante_habilitado,
            nivel=NIVEL_DADOS_TODOS,
            habilitacoes=[HAB_FINANCEIRO_REABRIR_LANCAMENTO_PAGO],
        )
        solicitacao = self._solicitacao(solicitante=solicitante_habilitado)
        solicitacao.avancar_para("em_analise")
        solicitacao.avancar_para("aprovada")
        solicitacao.avancar_para("paga")
        lancamento = solicitacao.lancamento

        self.client.force_login(solicitante_habilitado)
        antes = Notificacao.objects.count()

        r = self.client.post(
            f"/financeiro/lancamentos/{lancamento.pk}/reabrir/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 302)
        lancamento.refresh_from_db()
        self.assertEqual(lancamento.status, "pendente")
        self.assertEqual(Notificacao.objects.count(), antes)

    def test_reabrir_lancamento_sem_origem_nao_exige_habilitacao(self):
        lancamento = LancamentoFinanceiro.objects.create(
            tipo="despesa",
            descricao="Despesa avulsa",
            valor="80.00",
            data_vencimento="2026-08-25",
            status="pago",
            data_pagamento="2026-08-25",
        )
        r = self.client.post(
            f"/financeiro/lancamentos/{lancamento.pk}/reabrir/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 302)
        lancamento.refresh_from_db()
        self.assertEqual(lancamento.status, "pendente")


class TestSolicitacoesEscopoNivelDadosProprios(SolicitacaoFinanceiraBase):
    """
    Nível `dados_proprios` não restringe Solicitações — o eixo novo
    (specs/escopo-financeiro-lancamentos.md) só afeta LancamentoFinanceiro;
    SolicitacaoFinanceira continua com seu próprio escopo por
    `solicitante`, igual para os dois níveis "dados".
    """

    @classmethod
    def get_test_schema_name(cls):
        return "solicitacoes_nivel_dados_proprios"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Solicitacoes Nivel Dados Proprios"
        tenant.slug = "solicitacoes-nivel-dados-proprios"

    def setUp(self):
        super().setUp()
        self.financeiro = self._user("financeiro_dados_proprios")
        self._conceder_modulo(self.financeiro, nivel=NIVEL_DADOS_PROPRIOS)
        self.client.force_login(self.financeiro)

        self.solicitante = self._user("advogado")
        self._conceder_modulo(self.solicitante, nivel=NIVEL_SOLICITACOES)
        self.solicitacao = self._solicitacao(solicitante=self.solicitante)

    def test_lista_mostra_solicitacoes_de_outros_usuarios(self):
        r = self.client.get("/financeiro/solicitacoes/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        self.assertIn(self.solicitacao, list(r.context["solicitacoes"]))

    def test_processa_solicitacao_de_outro_usuario(self):
        r = self.client.post(
            f"/financeiro/solicitacoes/{self.solicitacao.pk}/processar/",
            {"acao": "analisar"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        self.solicitacao.refresh_from_db()
        self.assertEqual(self.solicitacao.status, "em_analise")


class TestSolicitacoesModuloNegado(SolicitacaoFinanceiraBase):
    """Usuário sem nenhum acesso ao módulo financeiro — nega em todas as rotas."""

    @classmethod
    def get_test_schema_name(cls):
        return "solicitacoes_modulo_negado"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Solicitacoes Modulo Negado"
        tenant.slug = "solicitacoes-modulo-negado"

    def setUp(self):
        super().setUp()
        self.user = self._user("sem_financeiro")
        self.client.force_login(self.user)
        self.solicitacao = self._solicitacao(solicitante=self.user)

    def test_lista_negada(self):
        r = self.client.get("/financeiro/solicitacoes/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_form_negado(self):
        r = self.client.get("/financeiro/solicitacoes/nova/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_detalhe_negado(self):
        r = self.client.get(f"/financeiro/solicitacoes/{self.solicitacao.pk}/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_anexo_negado(self):
        r = self.client.get(f"/financeiro/solicitacoes/{self.solicitacao.pk}/anexo/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_processar_negado(self):
        r = self.client.post(
            f"/financeiro/solicitacoes/{self.solicitacao.pk}/processar/",
            {"acao": "analisar"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 403)


class TestAnexoSolicitacaoIsolamentoMultiTenant(SolicitacaoFinanceiraBase):
    @classmethod
    def _fixture_setup(cls):
        return TransactionTestCase._fixture_setup.__func__(cls)

    def _fixture_teardown(self):
        return TransactionTestCase._fixture_teardown(self)

    @classmethod
    def get_test_schema_name(cls):
        return "solicitacoes_storage_iso_a"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Solicitações Storage A"
        tenant.slug = "solicitacoes-storage-a"

    def test_mesmo_id_e_nome_entregam_apenas_conteudo_do_tenant_do_dominio(self):
        usuario_a = self._user("financeiro_storage_a")
        self._conceder_modulo(usuario_a, nivel=NIVEL_DADOS_TODOS)
        solicitacao_a = self._solicitacao(
            solicitante=usuario_a,
            anexo=SimpleUploadedFile("mesmo.pdf", b"conteudo-a"),
        )

        tenant_b = Escritorio(
            schema_name="solicitacoes_storage_iso_b",
            nome="Solicitações Storage B",
            slug="solicitacoes-storage-b",
        )
        with schema_context("public"):
            tenant_b.save()
            dominio_b = Dominio.objects.create(
                tenant=tenant_b,
                domain="solicitacoes-storage-b.test.com",
                is_primary=True,
            )

        try:
            with tenant_context(tenant_b):
                usuario_b = self._user("financeiro_storage_b")
                self._conceder_modulo(usuario_b, nivel=NIVEL_DADOS_TODOS)
                solicitacao_b = self._solicitacao(
                    solicitante=usuario_b,
                    anexo=SimpleUploadedFile("mesmo.pdf", b"conteudo-b"),
                )

            self.client.force_login(usuario_a)
            resposta_a = self.client.get(
                f"/financeiro/solicitacoes/{solicitacao_a.pk}/anexo/",
                HTTP_HOST=self.http_host,
            )
            conteudo_a = b"".join(resposta_a.streaming_content)

            self.client.logout()
            with tenant_context(tenant_b):
                self.client.force_login(usuario_b)
            resposta_b = self.client.get(
                f"/financeiro/solicitacoes/{solicitacao_b.pk}/anexo/",
                HTTP_HOST=dominio_b.domain,
            )
            conteudo_b = b"".join(resposta_b.streaming_content)

            self.assertEqual(solicitacao_a.pk, solicitacao_b.pk)
            self.assertEqual(conteudo_a, b"conteudo-a")
            self.assertEqual(conteudo_b, b"conteudo-b")
            self.assertNotEqual(solicitacao_a.anexo.name, solicitacao_b.anexo.name)
        finally:
            with schema_context("public"):
                tenant_b.delete(force_drop=True)
            connection.set_tenant(self.tenant)
