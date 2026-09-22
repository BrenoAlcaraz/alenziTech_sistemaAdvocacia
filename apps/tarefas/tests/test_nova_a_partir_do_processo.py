"""
"+ Nova tarefa" do card de Tarefas relacionadas no detalhe do Processo
(docs/modules/processos.md): reaproveita o formulário padrão de
criação de Tarefas (`tarefas:nova`), só pré-preenchendo o campo
Processo via `?processo=<id>` (sem travar) e retornando ao detalhe do
processo via `?next=` ao salvar.
"""

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PapelAcesso, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import MODULO_TAREFAS, NIVEL_TODOS
from apps.clientes.models import Cliente
from apps.processos.models import Processo
from apps.tarefas.models import Tarefa


class NovaTarefaDoProcessoBase(TenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio

        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"

    def _user(self, username):
        return User.objects.create_user(username=username, password="testpass")

    def _dar_acesso_tarefas(self, user, *, nivel=NIVEL_TODOS):
        papel = PapelAcesso.objects.create(nome=f"Papel Tarefas {user.username}", ativo=True)
        UsuarioPapel.objects.create(usuario=user, papel=papel, ativo=True)
        PermissaoPapel.objects.create(papel=papel, modulo=MODULO_TAREFAS, ativo=True, nivel=nivel)
        return papel

    def _cliente(self, responsavel):
        return Cliente.objects.create(
            nome_razao_social="Cliente Nova Tarefa", tipo="PF", responsavel=responsavel, ativo=True
        )

    def _processo(self, responsavel, cliente):
        processo = Processo.objects.create(
            titulo="Processo Nova Tarefa", responsavel=responsavel, status="ativo"
        )
        processo.clientes.add(cliente)
        return processo


class TestCardExibeLinkNovaTarefa(NovaTarefaDoProcessoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "tarefas_nova_do_processo_card"

    def setUp(self):
        super().setUp()
        self.usuario = self._user("resp_card_nova_tarefa")
        self._dar_acesso_tarefas(self.usuario)
        from apps.accounts.permissoes_constants import MODULO_PROCESSOS

        papel = PapelAcesso.objects.create(nome="Papel Processos Card", ativo=True)
        UsuarioPapel.objects.create(usuario=self.usuario, papel=papel, ativo=True)
        PermissaoPapel.objects.create(
            papel=papel, modulo=MODULO_PROCESSOS, ativo=True, nivel=NIVEL_TODOS
        )
        self.cliente = self._cliente(self.usuario)
        self.processo = self._processo(self.usuario, self.cliente)
        self.client.force_login(self.usuario)

    def test_link_aponta_para_form_padrao_com_processo_preenchido(self):
        resposta = self.client.get(f"/processos/{self.processo.pk}/", HTTP_HOST=self.http_host)
        esperado = (
            f'/tarefas/nova/?processo={self.processo.pk}'
            f'&next=/processos/{self.processo.pk}/'
        )
        self.assertContains(resposta, esperado)


class TestFormularioPadraoPreenchidoPeloProcesso(NovaTarefaDoProcessoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "tarefas_nova_do_processo_form"

    def setUp(self):
        super().setUp()
        self.usuario = self._user("resp_form_nova_tarefa")
        self._dar_acesso_tarefas(self.usuario)
        self.cliente = self._cliente(self.usuario)
        self.processo = self._processo(self.usuario, self.cliente)
        self.client.force_login(self.usuario)

    def test_get_preenche_processo_sem_travar_o_campo(self):
        resposta = self.client.get(
            "/tarefas/nova/", {"processo": self.processo.pk}, HTTP_HOST=self.http_host
        )
        form = resposta.context["form"]
        self.assertEqual(str(form.initial.get("processo")), str(self.processo.pk))
        self.assertFalse(form.fields["processo"].disabled)

    def test_post_cria_tarefa_vinculada_e_volta_para_o_processo(self):
        next_url = f"/processos/{self.processo.pk}/"
        resposta = self.client.post(
            "/tarefas/nova/",
            {
                "processo": self.processo.pk,
                "next": next_url,
                "titulo": "Tarefa a partir do processo",
                "descricao": "",
                "prioridade": "media",
                "prazo": "",
                "cliente": "",
                "atribuidos": [self.usuario.pk],
                "destinatario": self.usuario.pk,
            },
            HTTP_HOST=self.http_host,
        )
        self.assertRedirects(resposta, next_url, fetch_redirect_response=False)
        tarefa = Tarefa.objects.get(titulo="Tarefa a partir do processo")
        self.assertEqual(tarefa.processo_id, self.processo.pk)
        self.assertEqual(tarefa.cliente_id, self.cliente.pk)
