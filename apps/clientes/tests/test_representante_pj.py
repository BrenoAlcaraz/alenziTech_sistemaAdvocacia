"""
Testes do formulário PF/PJ distinto com dados do representante
(specs/clientes-formulario-pf-pj-representante.md).

Cobre: PF continua com o formulário atual (sem campos de representante);
PJ oculta os campos exclusivos de PF (estado civil, profissão, RG,
nacionalidade/estrangeiro) e valida CPF do representante com o mesmo
dígito verificador do CPF/CNPJ do cliente; campos fora de escopo do
tipo são limpos no servidor mesmo que enviados manualmente; cliente PJ
já cadastrado antes desta mudança continua acessível com os campos de
representante em branco.
"""

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import HabilitacaoPapel, PapelAcesso, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import (
    HAB_CLIENTES_CRIAR,
    HAB_CLIENTES_EDITAR,
    MODULO_CLIENTES,
    NIVEL_TODOS,
)
from apps.clientes.forms import ClienteForm
from apps.clientes.models import Cliente


class ClienteFormBase(TenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio
        domain_obj = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = domain_obj.domain if domain_obj else "localhost"

    def _user(self, username):
        return User.objects.create_user(username=username, password="testpass")

    def _dar_permissoes(self, user):
        papel = PapelAcesso.objects.create(nome=f"Papel {user.username}", ativo=True)
        UsuarioPapel.objects.create(usuario=user, papel=papel, ativo=True)
        PermissaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=MODULO_CLIENTES, ativo=True, nivel=NIVEL_TODOS
        )
        HabilitacaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=MODULO_CLIENTES, item=HAB_CLIENTES_CRIAR, ativo=True
        )
        HabilitacaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=MODULO_CLIENTES, item=HAB_CLIENTES_EDITAR, ativo=True
        )
        return papel

    def _dados_pf(self, **overrides):
        dados = {"tipo": "PF", "nome_razao_social": "Fulano de Tal"}
        dados.update(overrides)
        return dados

    def _dados_pj(self, **overrides):
        dados = {
            "tipo": "PJ",
            "nome_razao_social": "Empresa Teste LTDA",
            "representante_nome": "Ciclano Representante",
            "representante_cpf": "111.444.777-35",  # CPF válido (dígito verificador)
            "representante_cargo": "Sócio-administrador",
        }
        dados.update(overrides)
        return dados


class TestFormularioPFSemMudanca(ClienteFormBase):
    @classmethod
    def get_test_schema_name(cls):
        return "clientes_form_pf_sem_mudanca"

    def test_pf_valido_sem_campos_de_representante(self):
        form = ClienteForm(data=self._dados_pf())
        self.assertTrue(form.is_valid(), form.errors)

    def test_pf_ignora_dados_de_representante_enviados_manualmente(self):
        form = ClienteForm(data=self._dados_pf(
            representante_nome="Não deveria salvar",
            representante_cpf="111.444.777-35",
            representante_cargo="Procurador",
        ))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["representante_nome"], "")
        self.assertEqual(form.cleaned_data["representante_cpf"], "")
        self.assertEqual(form.cleaned_data["representante_cargo"], "")


class TestFormularioPJRepresentante(ClienteFormBase):
    @classmethod
    def get_test_schema_name(cls):
        return "clientes_form_pj_representante"

    def test_pj_valido_com_dados_do_representante(self):
        form = ClienteForm(data=self._dados_pj())
        self.assertTrue(form.is_valid(), form.errors)

    def test_pj_cpf_representante_invalido_reporta_erro(self):
        form = ClienteForm(data=self._dados_pj(representante_cpf="111.111.111-11"))
        self.assertFalse(form.is_valid())
        self.assertIn("representante_cpf", form.errors)

    def test_pj_limpa_campos_exclusivos_de_pessoa_fisica(self):
        form = ClienteForm(data=self._dados_pj(
            estrangeiro="on",
            nacionalidade="Portuguesa",
            estado_civil="casado",
            profissao="Engenheiro",
            rg="12.345.678-9",
        ))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertFalse(form.cleaned_data["estrangeiro"])
        self.assertEqual(form.cleaned_data["nacionalidade"], "Brasileira")
        self.assertEqual(form.cleaned_data["estado_civil"], "")
        self.assertEqual(form.cleaned_data["profissao"], "")
        self.assertEqual(form.cleaned_data["rg"], "")

    def test_pj_cnpj_invalido_reporta_erro_como_hoje(self):
        form = ClienteForm(data=self._dados_pj(cpf_cnpj="00.000.000/0000-00"))
        self.assertFalse(form.is_valid())
        self.assertIn("cpf_cnpj", form.errors)

    def test_representante_telefone_invalido_reporta_erro(self):
        form = ClienteForm(data=self._dados_pj(representante_telefone="123"))
        self.assertFalse(form.is_valid())
        self.assertIn("representante_telefone", form.errors)


class TestClientePJExistenteContinuaAcessivel(ClienteFormBase):
    """Cliente PJ criado antes desta mudança (sem dados de representante)
    continua acessível e editável, com os campos em branco."""

    @classmethod
    def get_test_schema_name(cls):
        return "clientes_pj_existente_representante"

    def setUp(self):
        super().setUp()
        self.user = self._user("dono_pj_existente")
        self._dar_permissoes(self.user)
        self.client.force_login(self.user)
        self.cliente_pj = Cliente.objects.create(
            responsavel=self.user, tipo="PJ", nome_razao_social="Empresa Já Cadastrada LTDA",
        )

    def test_representante_vazio_por_padrao(self):
        self.assertEqual(self.cliente_pj.representante_nome, "")
        self.assertEqual(self.cliente_pj.representante_cpf, "")

    def test_detalhe_continua_acessivel(self):
        r = self.client.get(f"/clientes/{self.cliente_pj.pk}/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)

    def test_editar_get_mostra_formulario(self):
        r = self.client.get(f"/clientes/{self.cliente_pj.pk}/editar/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "secao-representante")

    def test_editar_preenchendo_representante_pela_primeira_vez(self):
        r = self.client.post(
            f"/clientes/{self.cliente_pj.pk}/editar/",
            self._dados_pj(),
            HTTP_HOST=self.http_host,
        )
        self.assertRedirects(
            r, f"/clientes/{self.cliente_pj.pk}/", fetch_redirect_response=False
        )
        self.cliente_pj.refresh_from_db()
        self.assertEqual(self.cliente_pj.representante_nome, "Ciclano Representante")
