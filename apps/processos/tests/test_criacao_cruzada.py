"""
Testes de criação cruzada Cliente↔Processo com pré-preenchimento
(specs/cliente-processo-criacao-cruzada.md).

Cobre o lado servidor de cada atalho:
- `processos:novo?cliente=<id>` pré-seleciona esse cliente no form
  (Clientes → "Novo processo"); id inválido/inativo é ignorado sem erro.
- `clientes:novo?next=<url>` carrega o `next` no form e, ao salvar,
  redireciona para `<url>?cliente_criado=<pk>` em vez do padrão
  (Processos → "Novo cliente"); `next` inseguro é ignorado.
- Nenhuma autorização nova: as checagens de `processos_criar`/
  `clientes_criar` de hoje continuam as únicas.

O restauro do rascunho em si (sessionStorage) é client-side puro — sem
executor de JS nos testes deste projeto, não é coberto aqui.
"""

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import HabilitacaoPapel, PapelAcesso, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import (
    HAB_CLIENTES_CRIAR,
    HAB_PROCESSOS_CRIAR,
    MODULO_CLIENTES,
    MODULO_PROCESSOS,
    NIVEL_TODOS,
)
from apps.clientes.models import Cliente
from apps.processos.models import Processo

_PROCESSO_FORM_BASE = {
    "area_direito": "CÍVEL",
    "fase": "conhecimento",
    "instancia": "1ª Instância",
    "gratuidade_justica_status": "nao_requerida",
}


class CriacaoCruzadaBase(TenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio
        domain_obj = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = domain_obj.domain if domain_obj else "localhost"

    def _user(self, username):
        return User.objects.create_user(username=username, password="testpass")

    def _dar_modulo(self, user, modulo, *, habilitacao=None):
        papel = PapelAcesso.objects.create(nome=f"Papel {modulo} {user.username}", ativo=True)
        UsuarioPapel.objects.create(usuario=user, papel=papel, ativo=True)
        PermissaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=modulo, ativo=True, nivel=NIVEL_TODOS
        )
        if habilitacao:
            HabilitacaoPapel.objects.create(
                papel=papel, tipo_conta=None, modulo=modulo, item=habilitacao, ativo=True
            )
        return papel

    def _dar_permissoes_completas(self, user):
        self._dar_modulo(user, MODULO_CLIENTES, habilitacao=HAB_CLIENTES_CRIAR)
        self._dar_modulo(user, MODULO_PROCESSOS, habilitacao=HAB_PROCESSOS_CRIAR)

    def _cliente(self, *, responsavel, **kwargs):
        defaults = {"nome_razao_social": "Cliente Criação Cruzada", "tipo": "PF"}
        defaults.update(kwargs)
        return Cliente.objects.create(responsavel=responsavel, **defaults)


class TestNovoProcessoComClientePreSelecionado(CriacaoCruzadaBase):
    @classmethod
    def get_test_schema_name(cls):
        return "criacao_cruzada_processo_cliente"

    def setUp(self):
        super().setUp()
        self.user = self._user("dono_criacao_cruzada_processo")
        self._dar_permissoes_completas(self.user)
        self.client.force_login(self.user)
        self.cliente = self._cliente(responsavel=self.user)

    def test_query_param_cliente_pre_seleciona_no_form(self):
        r = self.client.get(
            f"/processos/novo/?cliente={self.cliente.pk}", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["form"].initial.get("clientes"), [str(self.cliente.pk)])
        self.assertContains(r, f'value="{self.cliente.pk}" selected')

    def test_botao_novo_processo_aparece_na_aba_processos_do_cliente(self):
        r = self.client.get(
            f"/clientes/{self.cliente.pk}/?aba=processos", HTTP_HOST=self.http_host
        )
        self.assertContains(r, f"/processos/novo/?cliente={self.cliente.pk}")

    def test_cliente_inexistente_e_ignorado_sem_erro(self):
        r = self.client.get("/processos/novo/?cliente=999999", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("clientes", r.context["form"].initial)

    def test_cliente_inativo_e_ignorado_sem_erro(self):
        inativo = self._cliente(responsavel=self.user, nome_razao_social="Inativo", ativo=False)
        r = self.client.get(
            f"/processos/novo/?cliente={inativo.pk}", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("clientes", r.context["form"].initial)

    def test_sem_query_param_forms_continua_igual_a_hoje(self):
        r = self.client.get("/processos/novo/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("clientes", r.context["form"].initial)


class TestNovoClienteComNextParaProcesso(CriacaoCruzadaBase):
    @classmethod
    def get_test_schema_name(cls):
        return "criacao_cruzada_cliente_next"

    def setUp(self):
        super().setUp()
        self.user = self._user("dono_criacao_cruzada_cliente")
        self._dar_permissoes_completas(self.user)
        self.client.force_login(self.user)

    def test_get_com_next_carrega_campo_oculto(self):
        r = self.client.get(
            "/clientes/novo/?next=/processos/novo/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'name="next" value="/processos/novo/"')

    def test_post_com_next_redireciona_com_cliente_criado(self):
        r = self.client.post(
            "/clientes/novo/",
            {"tipo": "PF", "nome_razao_social": "Novo Via Processo", "next": "/processos/novo/"},
            HTTP_HOST=self.http_host,
        )
        criado = Cliente.objects.get(nome_razao_social="Novo Via Processo")
        self.assertRedirects(
            r, f"/processos/novo/?cliente_criado={criado.pk}", fetch_redirect_response=False
        )

    def test_post_sem_next_mantem_redirect_padrao(self):
        r = self.client.post(
            "/clientes/novo/",
            {"tipo": "PF", "nome_razao_social": "Novo Padrao"},
            HTTP_HOST=self.http_host,
        )
        self.assertRedirects(r, "/clientes/", fetch_redirect_response=False)

    def test_next_inseguro_e_ignorado(self):
        r = self.client.post(
            "/clientes/novo/",
            {
                "tipo": "PF", "nome_razao_social": "Novo Next Inseguro",
                "next": "http://evil.example.com/roubar",
            },
            HTTP_HOST=self.http_host,
        )
        self.assertRedirects(r, "/clientes/", fetch_redirect_response=False)

    def test_cancelar_com_next_volta_para_origem(self):
        r = self.client.get(
            "/clientes/novo/?next=/processos/novo/", HTTP_HOST=self.http_host
        )
        self.assertContains(r, 'href="/processos/novo/" class="btn-secondary"')

    def test_cliente_criado_via_fluxo_cruzado_aparece_selecionavel_no_processo(self):
        r_post = self.client.post(
            "/clientes/novo/",
            {"tipo": "PF", "nome_razao_social": "Selecionavel Depois", "next": "/processos/novo/"},
            HTTP_HOST=self.http_host,
        )
        criado = Cliente.objects.get(nome_razao_social="Selecionavel Depois")
        r = self.client.get(r_post.url, HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, f'value="{criado.pk}"')


class TestAutorizacaoNaoAmpliada(CriacaoCruzadaBase):
    """Os atalhos não criam nenhuma autorização nova — as checagens de
    módulo/habilitação continuam as mesmas de hoje em cada tela."""

    @classmethod
    def get_test_schema_name(cls):
        return "criacao_cruzada_autorizacao"

    def test_sem_processos_criar_nao_ve_botao_novo_processo_no_cliente(self):
        user = self._user("sem_processos_criar")
        self._dar_modulo(user, MODULO_CLIENTES, habilitacao=HAB_CLIENTES_CRIAR)
        self.client.force_login(user)
        cliente = self._cliente(responsavel=user)
        r = self.client.get(
            f"/clientes/{cliente.pk}/?aba=processos", HTTP_HOST=self.http_host
        )
        self.assertNotContains(r, "Novo processo")

    def test_novo_processo_com_query_param_ainda_exige_processos_criar(self):
        user = self._user("sem_habilitacao_processos_criar")
        self._dar_modulo(user, MODULO_PROCESSOS)  # módulo sem a habilitação de criar
        self.client.force_login(user)
        cliente = self._cliente(responsavel=user)
        r = self.client.get(
            f"/processos/novo/?cliente={cliente.pk}", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 403)

    def test_novo_cliente_com_next_ainda_exige_clientes_criar(self):
        user = self._user("sem_habilitacao_clientes_criar")
        self._dar_modulo(user, MODULO_CLIENTES)  # módulo sem a habilitação de criar
        self.client.force_login(user)
        r = self.client.get(
            "/clientes/novo/?next=/processos/novo/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 403)
