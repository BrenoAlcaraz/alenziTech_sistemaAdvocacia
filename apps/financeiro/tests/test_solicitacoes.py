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

from django import forms
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
    MODULO_PROCESSOS,
    NIVEL_DADOS_PROPRIOS,
    NIVEL_DADOS_TODOS,
    NIVEL_SOLICITACOES,
    NIVEL_TODOS,
)
from apps.clientes.models import Cliente
from apps.financeiro.models import CustaJudicial, LancamentoFinanceiro, SolicitacaoFinanceira
from apps.notificacoes.models import Notificacao
from apps.processos.models import Processo
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
            papel=papel, modulo=MODULO_FINANCEIRO, ativo=True, nivel=nivel
        )
        for item in habilitacoes or []:
            HabilitacaoPapel.objects.create(
                papel=papel, modulo=MODULO_FINANCEIRO, item=item, ativo=True
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
            titulo="Processo Teste", responsavel=self.user,
        )
        processo.clientes.add(cliente)
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

    def test_editar_negado(self):
        r = self.client.get(f"/financeiro/solicitacoes/{self.solicitacao.pk}/editar/", HTTP_HOST=self.http_host)
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


# ── Pagamento de custa judicial: comprovante + quem pagou (relato do sócio) ─────

class TestPagamentoDeCustaJudicial(SolicitacaoFinanceiraBase):
    """Marcar como paga uma solicitação de pagamento (a "custa judicial"
    vista pelo processo) exige comprovante de pagamento e se a custa foi
    paga pelo escritório ou pelo cliente, e replica o pagamento como
    CustaJudicial do cliente (PDR-0005) — só "escritorio" reduz o saldo
    (débito a cobrar), "cliente" fica no histórico sem afetar o saldo.
    Reembolso não passa por essa exigência."""

    @classmethod
    def get_test_schema_name(cls):
        return "solicitacoes_pagamento_custa"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Solicitacoes Pagamento Custa"
        tenant.slug = "solicitacoes-pagamento-custa"

    def setUp(self):
        super().setUp()
        self.financeiro = self._user("financeiro_dados")
        self._conceder_modulo(self.financeiro, nivel=NIVEL_DADOS_TODOS)
        self.client.force_login(self.financeiro)

        self.solicitante = self._user("advogado")
        self._conceder_modulo(self.solicitante, nivel=NIVEL_SOLICITACOES)

        self.cliente = Cliente.objects.create(nome_razao_social="Cliente Custa", responsavel=self.solicitante)
        self.processo = Processo.objects.create(titulo="Processo Custa", responsavel=self.solicitante)
        self.processo.clientes.add(self.cliente)

        self.solicitacao = self._solicitacao(
            solicitante=self.solicitante,
            tipo="pagamento",
            descricao="Custa de citação",
            cliente=self.cliente,
            processo=self.processo,
            vencimento="2026-10-10",
            anexo=_anexo("boleto.pdf"),
        )
        self.solicitacao.avancar_para("em_analise")
        self.solicitacao.avancar_para("aprovada")

    def test_avancar_para_paga_sem_pago_por_levanta_erro(self):
        with self.assertRaises(ValueError):
            self.solicitacao.avancar_para("paga", comprovante_pagamento=_anexo("comprovante.pdf"))
        self.solicitacao.refresh_from_db()
        self.assertEqual(self.solicitacao.status, "aprovada")

    def test_avancar_para_paga_sem_comprovante_levanta_erro(self):
        with self.assertRaises(ValueError):
            self.solicitacao.avancar_para("paga", pago_por="escritorio")
        self.solicitacao.refresh_from_db()
        self.assertEqual(self.solicitacao.status, "aprovada")

    def test_marcar_paga_sem_comprovante_na_view_nao_avanca_status(self):
        r = self.client.post(
            f"/financeiro/solicitacoes/{self.solicitacao.pk}/processar/",
            {"acao": "pagar", "pago_por": "escritorio"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        self.solicitacao.refresh_from_db()
        self.assertEqual(self.solicitacao.status, "aprovada")

    def test_marcar_paga_sem_pago_por_na_view_nao_avanca_status(self):
        r = self.client.post(
            f"/financeiro/solicitacoes/{self.solicitacao.pk}/processar/",
            {"acao": "pagar", "comprovante_pagamento": _anexo("comprovante.pdf")},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        self.solicitacao.refresh_from_db()
        self.assertEqual(self.solicitacao.status, "aprovada")

    def test_marcar_paga_pelo_escritorio_gera_debito_no_saldo_do_cliente(self):
        antes = CustaJudicial.objects.count()
        r = self.client.post(
            f"/financeiro/solicitacoes/{self.solicitacao.pk}/processar/",
            {
                "acao": "pagar",
                "pago_por": "escritorio",
                "comprovante_pagamento": _anexo("comprovante.pdf"),
            },
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        self.solicitacao.refresh_from_db()
        self.assertEqual(self.solicitacao.status, "paga")
        self.assertEqual(self.solicitacao.pago_por, "escritorio")
        self.assertTrue(self.solicitacao.comprovante_pagamento)

        self.assertEqual(CustaJudicial.objects.count(), antes + 1)
        custa = CustaJudicial.objects.latest("criado_em")
        self.assertEqual(custa.tipo, "adiantamento")
        self.assertEqual(custa.cliente_id, self.cliente.pk)
        self.assertEqual(custa.processo_id, self.processo.pk)
        self.assertEqual(custa.valor, self.solicitacao.valor)
        self.assertTrue(custa.anexo)

    def test_marcar_paga_pelo_cliente_fica_so_no_historico(self):
        r = self.client.post(
            f"/financeiro/solicitacoes/{self.solicitacao.pk}/processar/",
            {
                "acao": "pagar",
                "pago_por": "cliente",
                "comprovante_pagamento": _anexo("comprovante.pdf"),
            },
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        custa = CustaJudicial.objects.latest("criado_em")
        self.assertEqual(custa.tipo, "paga_pelo_cliente")

    def test_avancar_para_paga_sem_cliente_nao_gera_custa_judicial(self):
        avulsa = self._solicitacao(
            solicitante=self.solicitante, tipo="pagamento", vencimento="2026-10-10",
        )
        avulsa.avancar_para("em_analise")
        avulsa.avancar_para("aprovada")
        antes = CustaJudicial.objects.count()

        avulsa.avancar_para("paga", pago_por="escritorio", comprovante_pagamento=_anexo("comprovante.pdf"))

        self.assertEqual(CustaJudicial.objects.count(), antes)

    def test_reembolso_marcar_paga_nao_exige_comprovante_extra(self):
        reembolso = self._solicitacao(solicitante=self.solicitante)  # tipo default: reembolso
        reembolso.avancar_para("em_analise")
        reembolso.avancar_para("aprovada")
        antes = CustaJudicial.objects.count()

        r = self.client.post(
            f"/financeiro/solicitacoes/{reembolso.pk}/processar/",
            {"acao": "pagar"},
            HTTP_HOST=self.http_host,
        )

        self.assertEqual(r.status_code, 302)
        reembolso.refresh_from_db()
        self.assertEqual(reembolso.status, "paga")
        self.assertEqual(CustaJudicial.objects.count(), antes)


# ── "+ Nova solicitação" a partir da aba Custas Judiciais do processo ──────────

class TestNovaSolicitacaoAPartirDoProcesso(SolicitacaoFinanceiraBase):
    """Tipo, processo e cliente vêm travados quando a solicitação nasce
    de `?processo=<id>` — esse caminho é sempre uma custa a pagar, para o
    processo e cliente que originaram o pedido, sem a opção de trocar
    (relato do sócio: o formulário replicava o do Financeiro geral, que
    permite editar tudo)."""

    @classmethod
    def get_test_schema_name(cls):
        return "solicitacoes_nova_do_processo"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Solicitacoes Nova Do Processo"
        tenant.slug = "solicitacoes-nova-do-processo"

    def setUp(self):
        super().setUp()
        self.user = self._user("advogado")
        self._conceder_modulo(self.user, nivel=NIVEL_SOLICITACOES)
        self.client.force_login(self.user)

        self.cliente = Cliente.objects.create(nome_razao_social="Cliente Único", responsavel=self.user)
        self.processo = Processo.objects.create(titulo="Processo Único", responsavel=self.user)
        self.processo.clientes.add(self.cliente)

    def test_form_vem_travado_em_pagamento_processo_e_cliente(self):
        r = self.client.get(
            f"/financeiro/solicitacoes/nova/?processo={self.processo.pk}", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 200)
        form = r.context["form"]
        self.assertIsInstance(form.fields["tipo"].widget, forms.HiddenInput)
        self.assertIsInstance(form.fields["processo"].widget, forms.HiddenInput)
        self.assertIsInstance(form.fields["cliente"].widget, forms.HiddenInput)
        self.assertEqual(form.initial["tipo"], "pagamento")
        self.assertEqual(form.initial["processo"], self.processo.pk)
        self.assertEqual(form.initial["cliente"], self.cliente.pk)

    def test_sem_processo_form_continua_livre(self):
        r = self.client.get("/financeiro/solicitacoes/nova/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        form = r.context["form"]
        self.assertNotIsInstance(form.fields["tipo"].widget, forms.HiddenInput)
        self.assertNotIsInstance(form.fields["processo"].widget, forms.HiddenInput)
        self.assertNotIsInstance(form.fields["cliente"].widget, forms.HiddenInput)

    def test_criar_solicitacao_pelo_processo_preenche_cliente_automaticamente(self):
        antes = SolicitacaoFinanceira.objects.count()
        r = self.client.post(
            "/financeiro/solicitacoes/nova/",
            {
                "processo_fixo": self.processo.pk,
                "tipo": "pagamento",
                "descricao": "Custa de citação",
                "valor": "250.00",
                "cliente": self.cliente.pk,
                "processo": self.processo.pk,
                "vencimento": "2026-10-15",
                "anexo": _anexo("boleto.pdf"),
                "observacao": "",
            },
            HTTP_HOST=self.http_host,
        )
        self.assertRedirects(r, "/financeiro/solicitacoes/", fetch_redirect_response=False)
        self.assertEqual(SolicitacaoFinanceira.objects.count(), antes + 1)
        nova = SolicitacaoFinanceira.objects.get(descricao="Custa de citação")
        self.assertEqual(nova.tipo, "pagamento")
        self.assertEqual(nova.cliente_id, self.cliente.pk)
        self.assertEqual(nova.processo_id, self.processo.pk)

    def test_processo_com_varios_clientes_mantem_cliente_selecionavel_entre_eles(self):
        outro_cliente = Cliente.objects.create(nome_razao_social="Segundo Cliente", responsavel=self.user)
        self.processo.clientes.add(outro_cliente)

        r = self.client.get(
            f"/financeiro/solicitacoes/nova/?processo={self.processo.pk}", HTTP_HOST=self.http_host
        )
        form = r.context["form"]
        self.assertNotIsInstance(form.fields["cliente"].widget, forms.HiddenInput)
        self.assertIsInstance(form.fields["processo"].widget, forms.HiddenInput)
        ids_disponiveis = set(form.fields["cliente"].queryset.values_list("pk", flat=True))
        self.assertEqual(ids_disponiveis, {self.cliente.pk, outro_cliente.pk})


# ── Retorno ao processo de origem via `next` (specs/retorno-ao-processo-nova-solicitacao-custas.md) ──

class TestNovaSolicitacaoRetornoAoProcesso(SolicitacaoFinanceiraBase):
    """Voltar/cancelar/salvar em `financeiro:form_solicitacao` deve
    devolver ao processo de origem quando o link veio com `?next=`
    (mecanismo genérico já usado em tarefas), preservando o destino
    padrão (`financeiro/solicitacoes/`) quando não há origem."""

    @classmethod
    def get_test_schema_name(cls):
        return "solicitacoes_retorno_processo"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Solicitacoes Retorno Processo"
        tenant.slug = "solicitacoes-retorno-processo"

    def setUp(self):
        super().setUp()
        self.user = self._user("advogado")
        self._conceder_modulo(self.user, nivel=NIVEL_SOLICITACOES)
        # Um papel por usuário: Processos entra no papel que já dá Financeiro.
        papel = UsuarioPapel.objects.get(usuario=self.user, ativo=True).papel
        PermissaoPapel.objects.create(
            papel=papel, modulo=MODULO_PROCESSOS, ativo=True, nivel=NIVEL_TODOS
        )
        self.client.force_login(self.user)

        self.cliente = Cliente.objects.create(nome_razao_social="Cliente Único", responsavel=self.user)
        self.processo = Processo.objects.create(titulo="Processo Único", responsavel=self.user)
        self.processo.clientes.add(self.cliente)
        self.origem = f"/processos/{self.processo.pk}/?aba=custas"

    def test_link_na_aba_custas_do_processo_propaga_next(self):
        r = self.client.get(self.origem, HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        self.assertContains(
            r,
            f'/financeiro/solicitacoes/nova/?processo={self.processo.pk}&next=/processos/{self.processo.pk}/%3Faba%3Dcustas',
        )

    def test_get_com_next_valido_expoe_next_url_no_contexto(self):
        r = self.client.get(
            f"/financeiro/solicitacoes/nova/?processo={self.processo.pk}&next={self.origem}",
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["next_url"], self.origem)
        self.assertContains(r, f'value="{self.origem}"')

    def test_get_com_next_de_outro_host_e_ignorado(self):
        r = self.client.get(
            "/financeiro/solicitacoes/nova/?next=https://evil.example.com/",
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 200)
        self.assertIsNone(r.context["next_url"])

    def test_sem_next_contexto_fica_none(self):
        r = self.client.get("/financeiro/solicitacoes/nova/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        self.assertIsNone(r.context["next_url"])

    def test_salvar_com_next_redireciona_ao_processo_de_origem(self):
        r = self.client.post(
            "/financeiro/solicitacoes/nova/",
            {
                "processo_fixo": self.processo.pk,
                "next": self.origem,
                "tipo": "pagamento",
                "descricao": "Custa de citação",
                "valor": "250.00",
                "cliente": self.cliente.pk,
                "processo": self.processo.pk,
                "vencimento": "2026-10-15",
                "anexo": _anexo("boleto.pdf"),
                "observacao": "",
            },
            HTTP_HOST=self.http_host,
        )
        self.assertRedirects(r, self.origem, fetch_redirect_response=False)

    def test_salvar_com_next_de_outro_host_cai_no_destino_padrao(self):
        r = self.client.post(
            "/financeiro/solicitacoes/nova/",
            {
                "processo_fixo": self.processo.pk,
                "next": "https://evil.example.com/",
                "tipo": "pagamento",
                "descricao": "Custa de citação maliciosa",
                "valor": "250.00",
                "cliente": self.cliente.pk,
                "processo": self.processo.pk,
                "vencimento": "2026-10-15",
                "anexo": _anexo("boleto.pdf"),
                "observacao": "",
            },
            HTTP_HOST=self.http_host,
        )
        self.assertRedirects(r, "/financeiro/solicitacoes/", fetch_redirect_response=False)


# ── Edição de solicitação enquanto pendente (specs/edicao-solicitacao-financeira-pendente.md) ──

class TestEditarSolicitacao(SolicitacaoFinanceiraBase):
    """Editar campos de uma SolicitacaoFinanceira é permitido só em
    `solicitada`/`em_analise`; a partir de `aprovada`/`rejeitada`/`paga` a
    edição é bloqueada. Reaproveita SolicitacaoFinanceiraForm e a mesma
    trava de tipo/processo/cliente já usada na criação a partir da aba
    Custas Judiciais."""

    @classmethod
    def get_test_schema_name(cls):
        return "solicitacoes_editar"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Solicitacoes Editar"
        tenant.slug = "solicitacoes-editar"

    def setUp(self):
        super().setUp()
        self.user = self._user("advogado")
        self._conceder_modulo(self.user, nivel=NIVEL_SOLICITACOES)
        self.client.force_login(self.user)

        self.outro = self._user("outro_advogado")
        self._conceder_modulo(self.outro, nivel=NIVEL_SOLICITACOES)

        self.cliente = Cliente.objects.create(nome_razao_social="Cliente Único", responsavel=self.user)
        self.processo = Processo.objects.create(titulo="Processo Único", responsavel=self.user)
        self.processo.clientes.add(self.cliente)

    def _url(self, solicitacao):
        return f"/financeiro/solicitacoes/{solicitacao.pk}/editar/"

    def _pagamento(self, **kwargs):
        defaults = dict(
            tipo="pagamento", descricao="Custa de citação", cliente=self.cliente,
            processo=self.processo, vencimento="2026-10-15",
        )
        defaults.update(kwargs)
        return self._solicitacao(solicitante=self.user, **defaults)

    def test_get_editar_solicitada_autorizado(self):
        s = self._solicitacao(solicitante=self.user)
        r = self.client.get(self._url(s), HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["form"].instance.pk, s.pk)

    def test_get_editar_em_analise_autorizado(self):
        s = self._solicitacao(solicitante=self.user)
        s.avancar_para("em_analise")
        r = self.client.get(self._url(s), HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)

    def test_editar_aprovada_negado(self):
        s = self._pagamento()
        s.avancar_para("em_analise")
        s.avancar_para("aprovada")
        r = self.client.get(self._url(s), HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_editar_rejeitada_negado(self):
        s = self._solicitacao(solicitante=self.user)
        s.avancar_para("em_analise")
        s.avancar_para("rejeitada")
        r = self.client.get(self._url(s), HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_editar_paga_negado(self):
        s = self._solicitacao(solicitante=self.user)
        s.avancar_para("em_analise")
        s.avancar_para("aprovada")
        s.avancar_para("paga")
        r = self.client.get(self._url(s), HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_post_editar_fora_da_janela_negado(self):
        s = self._pagamento()
        s.avancar_para("em_analise")
        s.avancar_para("aprovada")
        r = self.client.post(
            self._url(s), {"descricao": "Tentativa de alterar"}, HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 403)
        s.refresh_from_db()
        self.assertEqual(s.descricao, "Custa de citação")

    def test_editar_alheia_nao_encontrada(self):
        alheia = self._solicitacao(solicitante=self.outro)
        r = self.client.get(self._url(alheia), HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 404)

    def test_post_editar_atualiza_descricao_e_valor_sem_criar_nova(self):
        s = self._solicitacao(solicitante=self.user, descricao="Original", valor="100.00")
        antes = SolicitacaoFinanceira.objects.count()
        r = self.client.post(
            self._url(s),
            {
                "tipo": "reembolso",
                "descricao": "Descrição corrigida",
                "valor": "180.00",
                "data_gasto": "2026-08-20",
                "anexo": _anexo("comprovante-novo.pdf"),
                "observacao": "",
            },
            HTTP_HOST=self.http_host,
        )
        self.assertRedirects(r, f"/financeiro/solicitacoes/{s.pk}/", fetch_redirect_response=False)
        self.assertEqual(SolicitacaoFinanceira.objects.count(), antes)
        s.refresh_from_db()
        self.assertEqual(s.descricao, "Descrição corrigida")
        self.assertEqual(str(s.valor), "180.00")
        self.assertEqual(s.status, "solicitada")

    def test_editar_pagamento_com_processo_trava_tipo_processo_cliente(self):
        s = self._pagamento()
        r = self.client.get(self._url(s), HTTP_HOST=self.http_host)
        form = r.context["form"]
        self.assertIsInstance(form.fields["tipo"].widget, forms.HiddenInput)
        self.assertIsInstance(form.fields["processo"].widget, forms.HiddenInput)
        self.assertIsInstance(form.fields["cliente"].widget, forms.HiddenInput)
        self.assertEqual(form.initial["processo"], self.processo.pk)
        self.assertEqual(form.initial["cliente"], self.cliente.pk)

    def test_editar_pagamento_nao_permite_trocar_processo(self):
        s = self._pagamento()
        outro_cliente = Cliente.objects.create(nome_razao_social="Outro Cliente", responsavel=self.user)
        outro_processo = Processo.objects.create(titulo="Outro Processo", responsavel=self.user)
        outro_processo.clientes.add(outro_cliente)

        r = self.client.post(
            self._url(s),
            {
                "tipo": "pagamento",
                "descricao": "Tentando trocar processo",
                "valor": "300.00",
                "cliente": outro_cliente.pk,
                "processo": outro_processo.pk,
                "vencimento": "2026-10-15",
                "observacao": "",
            },
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context["form"].errors)
        s.refresh_from_db()
        self.assertEqual(s.processo_id, self.processo.pk)
        self.assertEqual(s.cliente_id, self.cliente.pk)

    def test_editar_pagamento_processo_perdeu_cliente_nao_reatribui_silenciosamente(self):
        """O processo pode perder o cliente da solicitação depois de criada
        (ProcessoForm permite editar `clientes` livremente). Travar mesmo
        assim reatribuiria o campo oculto de cliente para o único cliente
        restante do processo sem o usuário perceber — a edição deve deixar
        de travar e expor o campo para correção manual."""
        outro_cliente = Cliente.objects.create(nome_razao_social="Outro Cliente", responsavel=self.user)
        self.processo.clientes.add(outro_cliente)
        s = self._pagamento(cliente=outro_cliente)
        self.processo.clientes.remove(outro_cliente)

        r = self.client.get(self._url(s), HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        form = r.context["form"]
        self.assertNotIsInstance(form.fields["cliente"].widget, forms.HiddenInput)
        self.assertNotIsInstance(form.fields["processo"].widget, forms.HiddenInput)
        self.assertEqual(form.initial["cliente"], outro_cliente.pk)

    def test_editar_reembolso_campos_livres_mesmo_com_processo_associado(self):
        s = self._solicitacao(solicitante=self.user, processo=self.processo, cliente=self.cliente)
        r = self.client.get(self._url(s), HTTP_HOST=self.http_host)
        form = r.context["form"]
        self.assertNotIsInstance(form.fields["tipo"].widget, forms.HiddenInput)
        self.assertNotIsInstance(form.fields["processo"].widget, forms.HiddenInput)
        self.assertNotIsInstance(form.fields["cliente"].widget, forms.HiddenInput)

    def test_card_detalhe_mostra_editar_quando_solicitada(self):
        s = self._solicitacao(solicitante=self.user)
        r = self.client.get(f"/financeiro/solicitacoes/{s.pk}/", HTTP_HOST=self.http_host)
        self.assertContains(r, self._url(s))

    def test_card_detalhe_mostra_editar_quando_em_analise(self):
        s = self._solicitacao(solicitante=self.user)
        s.avancar_para("em_analise")
        r = self.client.get(f"/financeiro/solicitacoes/{s.pk}/", HTTP_HOST=self.http_host)
        self.assertContains(r, self._url(s))

    def test_card_detalhe_esconde_editar_quando_aprovada_rejeitada_ou_paga(self):
        aprovada = self._pagamento(descricao="Aprovada")
        aprovada.avancar_para("em_analise")
        aprovada.avancar_para("aprovada")

        rejeitada = self._solicitacao(solicitante=self.user, descricao="Rejeitada")
        rejeitada.avancar_para("em_analise")
        rejeitada.avancar_para("rejeitada")

        paga = self._solicitacao(solicitante=self.user, descricao="Paga")
        paga.avancar_para("em_analise")
        paga.avancar_para("aprovada")
        paga.avancar_para("paga")

        for s in (aprovada, rejeitada, paga):
            r = self.client.get(f"/financeiro/solicitacoes/{s.pk}/", HTTP_HOST=self.http_host)
            self.assertNotContains(r, self._url(s))
