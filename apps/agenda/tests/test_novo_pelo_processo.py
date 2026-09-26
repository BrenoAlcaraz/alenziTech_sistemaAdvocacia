"""Compromisso aberto pelo card do processo: processo e clientes (todos os
do processo) travados; o item aparece para cada cliente do processo."""

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PapelAcesso, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import (
    MODULO_AGENDA,
    MODULO_CLIENTES,
    MODULO_PROCESSOS,
    NIVEL_TODOS,
)
from apps.agenda.models import ItemAgenda
from apps.agenda.services import agenda_do_vinculo
from apps.clientes.models import Cliente
from apps.processos.models import Processo


class TestNovoCompromissoPeloProcesso(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "agenda_novo_pelo_processo"

    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio

        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"
        self.usuario = User.objects.create_user("adv_novo_processo", password="x")
        papel = PapelAcesso.objects.create(nome="Papel novo pelo processo")
        UsuarioPapel.objects.create(usuario=self.usuario, papel=papel)
        for modulo in (MODULO_PROCESSOS, MODULO_CLIENTES, MODULO_AGENDA):
            PermissaoPapel.objects.create(papel=papel, modulo=modulo, ativo=True, nivel=NIVEL_TODOS)
        self.cliente_a = Cliente.objects.create(nome_razao_social="Cliente A", tipo="PF", responsavel=self.usuario)
        self.cliente_b = Cliente.objects.create(nome_razao_social="Cliente B", tipo="PF", responsavel=self.usuario)
        self.processo = Processo.objects.create(criado_por=self.usuario, titulo="PROCESSO COMPARTILHADO")
        self.processo.clientes.add(self.cliente_a, self.cliente_b)
        self.outro = Processo.objects.create(criado_por=self.usuario, titulo="OUTRO")
        self.client.force_login(self.usuario)

    def _url(self):
        return f"/agenda/novo/?tipo=tarefa&processo={self.processo.pk}"

    def test_formulario_mostra_processo_e_todos_os_clientes_travados(self):
        resposta = self.client.get(self._url(), HTTP_HOST=self.http_host)
        conteudo = resposta.content.decode()
        self.assertIn("data-vinculo-fixo", conteudo)
        vinculo = conteudo[conteudo.index("data-vinculo-fixo"):]
        self.assertIn("Cliente A", vinculo)
        self.assertIn("Cliente B", vinculo)
        self.assertTrue(resposta.context["form"].fields["processo"].disabled)
        self.assertTrue(resposta.context["form"].fields["cliente"].disabled)

    def test_post_forjado_nao_troca_processo_nem_cliente(self):
        cliente_c = Cliente.objects.create(nome_razao_social="Cliente C", tipo="PF", responsavel=self.usuario)
        self.client.post(self._url(), {
            "tipo": "tarefa", "titulo": "Protocolar", "processo": self.outro.pk, "cliente": cliente_c.pk,
        }, HTTP_HOST=self.http_host)
        item = ItemAgenda.objects.get(titulo="Protocolar")
        self.assertEqual(item.processo, self.processo)
        self.assertEqual(item.cliente, self.cliente_a)

    def test_item_do_processo_aparece_para_todos_os_clientes(self):
        ItemAgenda.objects.create(
            tipo="tarefa", titulo="Reunião", responsavel=self.usuario,
            processo=self.processo, cliente=self.cliente_a,
        )
        agenda_b = agenda_do_vinculo(self.usuario, cliente=self.cliente_b)
        self.assertEqual([i.titulo for i in agenda_b["itens"]], ["Reunião"])
        resposta = self.client.get(f"/agenda/?cliente={self.cliente_b.pk}&visao=lista", HTTP_HOST=self.http_host)
        self.assertIn("Reunião", resposta.content.decode())

    def test_sem_processo_o_formulario_continua_livre(self):
        resposta = self.client.get("/agenda/novo/?tipo=tarefa", HTTP_HOST=self.http_host)
        self.assertFalse(resposta.context["form"].fields["processo"].disabled)
        self.assertNotIn("data-vinculo-fixo", resposta.content.decode())
