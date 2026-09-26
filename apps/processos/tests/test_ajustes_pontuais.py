"""Título em maiúsculas, número de processo único, aba "Apensos e
relacionados", voltar para a lista e peça fixa do Laboratório."""

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PerfilUsuario
from apps.clientes.models import Cliente
from apps.processos.forms import ProcessoForm
from apps.processos.models import Processo
from apps.saas_tenants.models import Dominio


class TestFormularioDoProcesso(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "processos_ajustes_form"

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(username="u_form", password="x")
        self.cliente = Cliente.objects.create(tipo="PF", nome_razao_social="Cliente", responsavel=self.user)

    def _form(self, instance=None, **dados):
        base = {
            "titulo": "Ação", "clientes": [self.cliente.pk], "area_direito": "CÍVEL",
            "fase": "conhecimento", "instancia": "1ª Instância",
            "gratuidade_justica_status": "nao_requerida",
        }
        return ProcessoForm(data=base | dados, instance=instance)

    def test_titulo_sempre_em_maiusculas(self):
        form = self._form(titulo=" Ação de cobrança contra réu ")
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["titulo"], "AÇÃO DE COBRANÇA CONTRA RÉU")

    def test_numero_ja_cadastrado_e_rejeitado_com_ou_sem_mascara(self):
        Processo.objects.create(titulo="A", numero="0001234-56.2024.8.26.0100", criado_por=self.user)
        self.assertIn("numero", self._form(numero="00012345620248260100").errors)
        self.assertIn("numero", self._form(numero="0001234-56.2024.8.26.0100").errors)

    def test_numero_de_processo_arquivado_tambem_conta(self):
        Processo.objects.create(titulo="A", numero="123", status="arquivado", criado_por=self.user)
        self.assertIn("numero", self._form(numero="123").errors)

    def test_edicao_mantem_o_proprio_numero(self):
        processo = Processo.objects.create(titulo="A", numero="123", criado_por=self.user)
        self.assertTrue(self._form(instance=processo, numero="123").is_valid())

    def test_numero_vazio_nao_e_duplicado(self):
        Processo.objects.create(titulo="A", numero="", criado_por=self.user)
        self.assertTrue(self._form(numero="").is_valid())


class TestTelasDoProcesso(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "processos_ajustes_telas"

    def setUp(self):
        super().setUp()
        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"
        self.user = User.objects.create_user(username="admin_ajustes", password="x")
        PerfilUsuario.objects.filter(user=self.user).update(is_admin_escritorio=True)
        self.client.force_login(self.user)
        self.processo = Processo.objects.create(titulo="AÇÃO", criado_por=self.user)

    def _html(self, url):
        resposta = self.client.get(url, HTTP_HOST=self.http_host)
        self.assertEqual(resposta.status_code, 200)
        return resposta.content.decode()

    def test_detalhe_tem_aba_apensos_e_relacionados_e_voltar_para_lista(self):
        conteudo = self._html(f"/processos/{self.processo.pk}/")
        self.assertIn("Apensos e relacionados", conteudo)
        self.assertIn('href="/processos/" class="inline-flex items-center gap-1 mb-3', conteudo)
        self.assertIn("Voltar para processos", conteudo)

    def test_laboratorio_produz_sempre_peticao_inicial(self):
        conteudo = self._html("/processos/?aba=laboratorio")
        self.assertIn("data-lab-tipo-peca>Petição inicial<", conteudo)
        self.assertNotIn("Contestação", conteudo)
