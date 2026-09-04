"""
Testes de autorização de módulo para apps/financeiro/views.py.

Este arquivo cobre só a camada de tem_permissao_modulo(user, "financeiro"),
aplicada nas nove rotas existentes (index, custas, form_lancamento,
editar_lancamento, marcar_pago, cancelar_lancamento,
reabrir_lancamento, excluir_lancamento, form_custa). A habilitação
granular HAB_FINANCEIRO_REABRIR_LANCAMENTO_PAGO
(ITENS_POR_MODULO[MODULO_FINANCEIRO]), aplicada condicionalmente em
reabrir_lancamento (PDR-0006), é coberta em test_solicitacoes.py, não
aqui.

Segue o mesmo padrão de fixtures de apps/tarefas/tests/test_autorizacao.py
sobre django_tenants.test.cases.TenantTestCase.
"""

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PapelAcesso, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import MODULO_FINANCEIRO, NIVEL_DADOS_PROPRIOS, NIVEL_DADOS_TODOS
from apps.financeiro.models import CustaJudicial, LancamentoFinanceiro


class FinanceiroAutorizacaoBase(TenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio
        domain_obj = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = domain_obj.domain if domain_obj else "localhost"

    def _user(self, username):
        return User.objects.create_user(username=username, password="testpass")

    def _new_papel(self, nome):
        return PapelAcesso.objects.create(nome=nome, ativo=True)

    def _conceder_modulo(self, user, *, nivel=NIVEL_DADOS_TODOS):
        papel = self._new_papel(f"Papel Financeiro {user.username}")
        UsuarioPapel.objects.create(usuario=user, papel=papel, ativo=True)
        PermissaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=MODULO_FINANCEIRO, ativo=True, nivel=nivel
        )

    def _lancamento(self, **kwargs):
        defaults = {
            "tipo": "receita",
            "descricao": "Honorário Teste",
            "valor": "1000.00",
            "data_vencimento": "2026-09-30",
            "status": "pendente",
        }
        defaults.update(kwargs)
        return LancamentoFinanceiro.objects.create(**defaults)

    def _custa(self, **kwargs):
        defaults = {
            "descricao": "Custa Teste",
            "valor": "100.00",
            "data": "2026-09-01",
            "tipo": "adiantamento",
        }
        defaults.update(kwargs)
        return CustaJudicial.objects.create(**defaults)


class TestFinanceiroAutorizacaoModuloNegado(FinanceiroAutorizacaoBase):
    """
    Usuário autenticado sem autorização do módulo `financeiro` (nenhum
    UsuarioPapel) — as nove rotas negam com 403, inclusive POST direto.
    """

    @classmethod
    def get_test_schema_name(cls):
        return "financeiro_autorizacao_negado"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Financeiro Autorizacao Negado"
        tenant.slug = "financeiro-autorizacao-negado"

    def setUp(self):
        super().setUp()
        self.user = self._user("sem_modulo_financeiro")
        self.client.force_login(self.user)
        self.lancamento = self._lancamento()
        self.custa = self._custa()

    def test_index_negado(self):
        r = self.client.get("/financeiro/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_custas_negado(self):
        r = self.client.get("/financeiro/custas/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_form_lancamento_get_negado(self):
        r = self.client.get("/financeiro/lancamentos/novo/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_form_lancamento_post_negado_nao_cria(self):
        antes = LancamentoFinanceiro.objects.count()
        r = self.client.post(
            "/financeiro/lancamentos/novo/",
            {
                "tipo": "receita",
                "descricao": "Tentativa Negada",
                "valor": "500.00",
                "data_vencimento": "2026-10-01",
                "status": "pendente",
                "categoria": "honorario",
            },
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 403)
        self.assertEqual(LancamentoFinanceiro.objects.count(), antes)

    def test_editar_lancamento_negado(self):
        r = self.client.get(
            f"/financeiro/lancamentos/{self.lancamento.pk}/editar/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 403)

    def test_marcar_pago_negado_nao_altera_status(self):
        r = self.client.post(
            f"/financeiro/lancamentos/{self.lancamento.pk}/marcar-pago/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 403)
        self.lancamento.refresh_from_db()
        self.assertEqual(self.lancamento.status, "pendente")

    def test_cancelar_lancamento_negado(self):
        r = self.client.post(
            f"/financeiro/lancamentos/{self.lancamento.pk}/cancelar/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 403)

    def test_reabrir_lancamento_negado(self):
        self.lancamento.status = "pago"
        self.lancamento.save(update_fields=["status"])
        r = self.client.post(
            f"/financeiro/lancamentos/{self.lancamento.pk}/reabrir/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 403)

    def test_excluir_lancamento_negado_nao_apaga(self):
        r = self.client.post(
            f"/financeiro/lancamentos/{self.lancamento.pk}/excluir/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 403)
        self.assertTrue(LancamentoFinanceiro.objects.filter(pk=self.lancamento.pk).exists())

    def test_form_custa_negado(self):
        r = self.client.get("/financeiro/custas/nova/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)


class TestFinanceiroAutorizacaoModuloConcedido(FinanceiroAutorizacaoBase):
    """
    Usuário autorizado ao módulo `financeiro` (nível `dados_todos`, via
    papel dinâmico) preserva o comportamento HTTP existente das nove
    rotas.
    """

    @classmethod
    def get_test_schema_name(cls):
        return "financeiro_autorizacao_concedido"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Financeiro Autorizacao Concedido"
        tenant.slug = "financeiro-autorizacao-concedido"

    def setUp(self):
        super().setUp()
        self.user = self._user("com_modulo_financeiro")
        self._conceder_modulo(self.user)
        self.client.force_login(self.user)
        self.lancamento = self._lancamento()
        self.custa = self._custa()

    def test_index_autorizado(self):
        r = self.client.get("/financeiro/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, "financeiro/index.html")

    def test_custas_autorizado(self):
        r = self.client.get("/financeiro/custas/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, "financeiro/custas.html")

    def test_form_lancamento_post_autorizado(self):
        r = self.client.post(
            "/financeiro/lancamentos/novo/",
            {
                "tipo": "receita",
                "descricao": "Lançamento Autorizado",
                "valor": "500.00",
                "data_vencimento": "2026-10-01",
                "status": "pendente",
                "categoria": "honorario",
            },
            HTTP_HOST=self.http_host,
        )
        self.assertRedirects(r, "/financeiro/", fetch_redirect_response=False)
        self.assertTrue(LancamentoFinanceiro.objects.filter(descricao="Lançamento Autorizado").exists())

    def test_editar_lancamento_autorizado(self):
        r = self.client.get(
            f"/financeiro/lancamentos/{self.lancamento.pk}/editar/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 200)

    def test_marcar_pago_autorizado(self):
        r = self.client.post(
            f"/financeiro/lancamentos/{self.lancamento.pk}/marcar-pago/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 302)
        self.lancamento.refresh_from_db()
        self.assertEqual(self.lancamento.status, "pago")

    def test_cancelar_lancamento_autorizado(self):
        r = self.client.post(
            f"/financeiro/lancamentos/{self.lancamento.pk}/cancelar/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 302)
        self.lancamento.refresh_from_db()
        self.assertEqual(self.lancamento.status, "cancelado")

    def test_reabrir_lancamento_autorizado(self):
        self.lancamento.status = "pago"
        self.lancamento.save(update_fields=["status"])
        r = self.client.post(
            f"/financeiro/lancamentos/{self.lancamento.pk}/reabrir/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 302)
        self.lancamento.refresh_from_db()
        self.assertEqual(self.lancamento.status, "pendente")

    def test_excluir_lancamento_autorizado(self):
        r = self.client.post(
            f"/financeiro/lancamentos/{self.lancamento.pk}/excluir/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 302)
        self.assertFalse(LancamentoFinanceiro.objects.filter(pk=self.lancamento.pk).exists())

    def test_form_custa_post_autorizado(self):
        r = self.client.post(
            "/financeiro/custas/nova/",
            {
                "tipo": "adiantamento",
                "descricao": "Custa Autorizada",
                "valor": "200.00",
                "data": "2026-09-05",
            },
            HTTP_HOST=self.http_host,
        )
        self.assertRedirects(r, "/financeiro/custas/", fetch_redirect_response=False)
        self.assertTrue(CustaJudicial.objects.filter(descricao="Custa Autorizada").exists())


class TestFinanceiroEscopoDadosProprios(FinanceiroAutorizacaoBase):
    """
    Nível `dados_proprios`: LancamentoFinanceiro só é visível/mutável
    quando `responsavel == request.user` — mutação sobre lançamento de
    outro responsável retorna 404 (fora do escopo, mesmo padrão de
    Clientes/Processos). CustaJudicial não tem `responsavel` e não é
    afetada (spec: specs/escopo-financeiro-lancamentos.md).
    """

    @classmethod
    def get_test_schema_name(cls):
        return "financeiro_escopo_dados_proprios"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Financeiro Escopo Dados Proprios"
        tenant.slug = "financeiro-escopo-dados-proprios"

    def setUp(self):
        super().setUp()
        self.user = self._user("dados_proprios_user")
        self._conceder_modulo(self.user, nivel=NIVEL_DADOS_PROPRIOS)
        self.client.force_login(self.user)
        self.outro = self._user("outro_responsavel")
        self.meu = self._lancamento(descricao="Lançamento Próprio", responsavel=self.user, valor="1000.00")
        self.alheio = self._lancamento(descricao="Lançamento Alheio", responsavel=self.outro, valor="5000.00")

    def test_index_lista_so_lancamentos_proprios(self):
        r = self.client.get("/financeiro/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        lancamentos = list(r.context["lancamentos"])
        self.assertIn(self.meu, lancamentos)
        self.assertNotIn(self.alheio, lancamentos)

    def test_resumo_soma_apenas_lancamentos_proprios(self):
        r = self.client.get("/financeiro/", HTTP_HOST=self.http_host)
        self.assertEqual(r.context["resumo"]["a_receber"], "R$ 1.000,00")

    def test_editar_lancamento_proprio_autorizado(self):
        r = self.client.get(f"/financeiro/lancamentos/{self.meu.pk}/editar/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)

    def test_editar_lancamento_alheio_404(self):
        r = self.client.get(f"/financeiro/lancamentos/{self.alheio.pk}/editar/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 404)

    def test_marcar_pago_lancamento_alheio_404_nao_altera(self):
        r = self.client.post(
            f"/financeiro/lancamentos/{self.alheio.pk}/marcar-pago/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 404)
        self.alheio.refresh_from_db()
        self.assertEqual(self.alheio.status, "pendente")

    def test_excluir_lancamento_alheio_404_nao_apaga(self):
        r = self.client.post(
            f"/financeiro/lancamentos/{self.alheio.pk}/excluir/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 404)
        self.assertTrue(LancamentoFinanceiro.objects.filter(pk=self.alheio.pk).exists())

    def test_excluir_lancamento_proprio_autorizado(self):
        r = self.client.post(
            f"/financeiro/lancamentos/{self.meu.pk}/excluir/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 302)
        self.assertFalse(LancamentoFinanceiro.objects.filter(pk=self.meu.pk).exists())

    def test_custas_nao_e_afetada_pelo_escopo(self):
        """CustaJudicial não tem responsavel — dados_proprios continua vendo todas as custas."""
        custa_alheia = self._custa(descricao="Custa de outro usuário")
        r = self.client.get("/financeiro/custas/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        self.assertIn(custa_alheia, list(r.context["custas"]))
