"""
Testes de "Gerar procuração" na aba Documentos do Cliente
(specs/clientes-gerar-procuracao.md).

Cobre: sem modelo de Procuração cadastrado orienta a criar um, em vez de
falhar silenciosamente ou gerar texto genérico; com um (ou mais de um)
modelo, gera uma nova peça no acervo com nome/CPF-CNPJ/endereço do
cliente (e dados do representante, se PJ) à frente do conteúdo do
modelo escolhido, sem alterar o modelo original; autorização exige
modelos_criar + poder ver o cliente (escopo de Clientes).
"""

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import HabilitacaoPapel, PapelAcesso, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import (
    HAB_CLIENTES_CRIAR,
    HAB_MODELOS_CRIAR,
    MODULO_CLIENTES,
    MODULO_MODELOS,
    NIVEL_SOMENTE_SEUS,
    NIVEL_TODOS,
)
from apps.clientes.models import Cliente
from apps.modelos.models import CategoriaModeloPeca, ModeloPeca


class GerarProcuracaoBase(TenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio
        domain_obj = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = domain_obj.domain if domain_obj else "localhost"

    def _user(self, username):
        return User.objects.create_user(username=username, password="testpass")

    def _dar_modulo(self, user, modulo, *, habilitacao=None, nivel=NIVEL_TODOS):
        # Um papel por usuário: módulos extras entram no mesmo papel.
        vinculo = UsuarioPapel.objects.filter(usuario=user, ativo=True).first()
        if vinculo:
            papel = vinculo.papel
        else:
            papel = PapelAcesso.objects.create(nome=f"Papel {user.username}", ativo=True)
            UsuarioPapel.objects.create(usuario=user, papel=papel, ativo=True)
        PermissaoPapel.objects.create(
            papel=papel, modulo=modulo, ativo=True, nivel=nivel
        )
        if habilitacao:
            HabilitacaoPapel.objects.create(
                papel=papel, modulo=modulo, item=habilitacao, ativo=True
            )
        return papel

    def _dar_permissoes_completas(self, user, *, nivel_clientes=NIVEL_TODOS):
        self._dar_modulo(user, MODULO_CLIENTES, habilitacao=HAB_CLIENTES_CRIAR, nivel=nivel_clientes)
        self._dar_modulo(user, MODULO_MODELOS, habilitacao=HAB_MODELOS_CRIAR)

    def _cliente(self, *, responsavel, **kwargs):
        defaults = {
            "tipo": "PF", "nome_razao_social": "Fulano de Tal", "cpf_cnpj": "111.444.777-35",
            "logradouro": "Rua das Flores", "numero": "123", "bairro": "Centro",
            "cidade": "São Paulo", "estado": "SP", "cep": "01000-000",
        }
        defaults.update(kwargs)
        return Cliente.objects.create(responsavel=responsavel, **defaults)

    def _modelo_procuracao(self, *, criado_por, titulo="Procuração Ad Judicia", conteudo="<p>Texto padrão de poderes.</p>"):
        categoria = CategoriaModeloPeca.objects.get(nome="Procuração")
        return ModeloPeca.objects.create(
            titulo=titulo, categoria=categoria, area_direito="CÍVEL",
            conteudo=conteudo, criado_por=criado_por,
        )


class TestSemModeloDeProcuracao(GerarProcuracaoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "clientes_procuracao_sem_modelo"

    def setUp(self):
        super().setUp()
        self.user = self._user("dono_sem_modelo_procuracao")
        self._dar_permissoes_completas(self.user)
        self.client.force_login(self.user)
        self.cliente = self._cliente(responsavel=self.user)

    def test_get_orienta_a_criar_modelo_em_vez_de_gerar_texto_generico(self):
        r = self.client.get(
            f"/clientes/{self.cliente.pk}/gerar-procuracao/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "modelo")
        self.assertContains(r, "Criar modelo de Procuração")

    def test_post_nao_cria_peca_sem_modelo_base(self):
        antes = ModeloPeca.objects.count()
        r = self.client.post(
            f"/clientes/{self.cliente.pk}/gerar-procuracao/",
            {"modelo_base": "1"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(ModeloPeca.objects.count(), antes)

    def test_documentos_nao_mostra_botao_gerar_procuracao_sem_essa_checagem_impedir(self):
        # O botão aparece (autorização já concedida) mesmo sem modelo —
        # é a própria tela de destino que orienta a criar um.
        r = self.client.get(
            f"/clientes/{self.cliente.pk}/?aba=documentos", HTTP_HOST=self.http_host
        )
        self.assertContains(r, "Gerar procuração")


class TestComUmModeloDeProcuracaoPF(GerarProcuracaoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "clientes_procuracao_pf_um_modelo"

    def setUp(self):
        super().setUp()
        self.user = self._user("dono_procuracao_pf")
        self._dar_permissoes_completas(self.user)
        self.client.force_login(self.user)
        self.cliente = self._cliente(responsavel=self.user)
        self.modelo_base = self._modelo_procuracao(criado_por=self.user)

    def test_get_mostra_o_unico_modelo_pre_selecionado(self):
        r = self.client.get(
            f"/clientes/{self.cliente.pk}/gerar-procuracao/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, self.modelo_base.titulo)
        self.assertContains(r, 'checked')

    def test_post_gera_peca_com_dados_do_cliente_sem_alterar_original(self):
        conteudo_original = self.modelo_base.conteudo
        r = self.client.post(
            f"/clientes/{self.cliente.pk}/gerar-procuracao/",
            {"modelo_base": self.modelo_base.pk},
            HTTP_HOST=self.http_host,
        )
        peca = ModeloPeca.objects.exclude(pk=self.modelo_base.pk).get()
        self.assertRedirects(
            r, f"/modelos/{peca.pk}/", fetch_redirect_response=False
        )
        self.assertIn("Fulano de Tal", peca.conteudo)
        self.assertIn("111.444.777-35", peca.conteudo)
        self.assertIn("Rua das Flores", peca.conteudo)
        self.assertIn("Texto padrão de poderes.", peca.conteudo)
        self.assertEqual(peca.categoria, self.modelo_base.categoria)
        self.assertEqual(peca.criado_por, self.user)
        self.assertIn(self.cliente.nome_razao_social, peca.titulo)

        self.modelo_base.refresh_from_db()
        self.assertEqual(self.modelo_base.conteudo, conteudo_original)

    def test_pf_nao_mostra_bloco_de_representante(self):
        self.client.post(
            f"/clientes/{self.cliente.pk}/gerar-procuracao/",
            {"modelo_base": self.modelo_base.pk},
            HTTP_HOST=self.http_host,
        )
        peca = ModeloPeca.objects.exclude(pk=self.modelo_base.pk).get()
        self.assertNotIn("Representante", peca.conteudo)


class TestComModeloDeProcuracaoPJ(GerarProcuracaoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "clientes_procuracao_pj"

    def setUp(self):
        super().setUp()
        self.user = self._user("dono_procuracao_pj")
        self._dar_permissoes_completas(self.user)
        self.client.force_login(self.user)
        self.cliente = self._cliente(
            responsavel=self.user, tipo="PJ", nome_razao_social="Empresa Teste LTDA",
            cpf_cnpj="00.623.904/0001-73",
            representante_nome="Ciclano Representante", representante_cpf="111.444.777-35",
            representante_cargo="Sócio-administrador",
        )
        self.modelo_base = self._modelo_procuracao(criado_por=self.user)

    def test_pj_inclui_dados_do_representante_na_peca_gerada(self):
        self.client.post(
            f"/clientes/{self.cliente.pk}/gerar-procuracao/",
            {"modelo_base": self.modelo_base.pk},
            HTTP_HOST=self.http_host,
        )
        peca = ModeloPeca.objects.exclude(pk=self.modelo_base.pk).get()
        self.assertIn("Empresa Teste LTDA", peca.conteudo)
        self.assertIn("Ciclano Representante", peca.conteudo)
        self.assertIn("111.444.777-35", peca.conteudo)
        self.assertIn("Sócio-administrador", peca.conteudo)


class TestComMultiplosModelosDeProcuracao(GerarProcuracaoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "clientes_procuracao_varios_modelos"

    def setUp(self):
        super().setUp()
        self.user = self._user("dono_varios_modelos_procuracao")
        self._dar_permissoes_completas(self.user)
        self.client.force_login(self.user)
        self.cliente = self._cliente(responsavel=self.user)
        self.modelo_a = self._modelo_procuracao(criado_por=self.user, titulo="Procuração Padrão A", conteudo="<p>Conteúdo A.</p>")
        self.modelo_b = self._modelo_procuracao(criado_por=self.user, titulo="Procuração Padrão B", conteudo="<p>Conteúdo B.</p>")

    def test_get_lista_todos_os_modelos_para_escolher(self):
        r = self.client.get(
            f"/clientes/{self.cliente.pk}/gerar-procuracao/", HTTP_HOST=self.http_host
        )
        self.assertContains(r, self.modelo_a.titulo)
        self.assertContains(r, self.modelo_b.titulo)

    def test_post_usa_o_modelo_escolhido_nao_o_primeiro(self):
        self.client.post(
            f"/clientes/{self.cliente.pk}/gerar-procuracao/",
            {"modelo_base": self.modelo_b.pk},
            HTTP_HOST=self.http_host,
        )
        peca = ModeloPeca.objects.exclude(pk__in=[self.modelo_a.pk, self.modelo_b.pk]).get()
        self.assertIn("Conteúdo B.", peca.conteudo)
        self.assertNotIn("Conteúdo A.", peca.conteudo)


class TestAutorizacaoGerarProcuracao(GerarProcuracaoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "clientes_procuracao_autorizacao"

    def setUp(self):
        super().setUp()
        self.dono = self._user("dono_autorizacao_procuracao")
        self.cliente = self._cliente(responsavel=self.dono)
        self.modelo_base = self._modelo_procuracao(criado_por=self.dono)

    def test_sem_modulo_clientes_403(self):
        user = self._user("sem_modulo_clientes_procuracao")
        self._dar_modulo(user, MODULO_MODELOS, habilitacao=HAB_MODELOS_CRIAR)
        self.client.force_login(user)
        r = self.client.get(
            f"/clientes/{self.cliente.pk}/gerar-procuracao/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 403)

    def test_sem_modulo_modelos_403(self):
        user = self._user("sem_modulo_modelos_procuracao")
        self._dar_modulo(user, MODULO_CLIENTES, habilitacao=HAB_CLIENTES_CRIAR)
        self.client.force_login(user)
        r = self.client.get(
            f"/clientes/{self.cliente.pk}/gerar-procuracao/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 403)

    def test_sem_habilitacao_modelos_criar_403(self):
        user = self._user("sem_habilitacao_criar_procuracao")
        self._dar_modulo(user, MODULO_CLIENTES, habilitacao=HAB_CLIENTES_CRIAR)
        self._dar_modulo(user, MODULO_MODELOS)  # módulo sem a habilitação de criar
        self.client.force_login(user)
        r = self.client.get(
            f"/clientes/{self.cliente.pk}/gerar-procuracao/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 403)

    def test_cliente_fora_do_escopo_de_clientes_404(self):
        estranho = self._user("estranho_cliente_procuracao")
        self._dar_modulo(estranho, MODULO_CLIENTES, habilitacao=HAB_CLIENTES_CRIAR, nivel=NIVEL_SOMENTE_SEUS)
        self._dar_modulo(estranho, MODULO_MODELOS, habilitacao=HAB_MODELOS_CRIAR)
        self.client.force_login(estranho)
        r = self.client.get(
            f"/clientes/{self.cliente.pk}/gerar-procuracao/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 404)

    def test_anonimo_redirecionado_ao_login(self):
        r = self.client.get(
            f"/clientes/{self.cliente.pk}/gerar-procuracao/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login/", r.url)
