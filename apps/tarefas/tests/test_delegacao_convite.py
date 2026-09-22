"""
Convite de delegação em Tarefas (specs/delegacao-por-convite-agenda-
tarefas.md, issue #29): delegar para outro usuário passa a exigir
convite, exceto Administrador->qualquer um e gerente->subordinado não-
gerente da própria Equipe (issue #28, apps/accounts/delegacao.py).

Segue o mesmo padrão de fixtures de apps/tarefas/tests/test_delegacao.py.
"""

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import (
    ConviteDelegacao,
    Equipe,
    HabilitacaoPapel,
    MembroEquipe,
    PapelAcesso,
    PerfilUsuario,
    PermissaoPapel,
    UsuarioPapel,
)
from apps.accounts.permissoes_constants import HAB_TAREFAS_ATRIBUIR_OUTROS, MODULO_TAREFAS, NIVEL_SOMENTE_SEUS, NIVEL_TODOS
from apps.tarefas.models import Tarefa


class TarefasConviteBase(TenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio

        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"

    def _user(self, username):
        return User.objects.create_user(username=username, password="testpass")

    def _set_admin(self, user):
        PerfilUsuario.objects.filter(user=user).update(is_admin_escritorio=True)
        user._state.fields_cache.pop("perfil", None)

    def _dar_acesso_modulo(self, user, *, nivel=NIVEL_TODOS):
        papel = PapelAcesso.objects.create(nome=f"Papel {user.username}")
        UsuarioPapel.objects.create(usuario=user, papel=papel)
        PermissaoPapel.objects.create(papel=papel, modulo=MODULO_TAREFAS, ativo=True, nivel=nivel)
        return papel

    def _dar_acesso_com_atribuir_outros(self, user):
        papel = self._dar_acesso_modulo(user)
        HabilitacaoPapel.objects.create(
            papel=papel, modulo=MODULO_TAREFAS, item=HAB_TAREFAS_ATRIBUIR_OUTROS, ativo=True
        )
        return papel

    def _payload(self, *, destinatario, titulo="Tarefa Convite"):
        return {
            "titulo": titulo,
            "descricao": "",
            "prioridade": "media",
            "prazo": "",
            "cliente": "",
            "processo": "",
            "atribuidos": [destinatario.pk],
            "destinatario": destinatario.pk,
        }

    def _criar(self, *, destinatario, titulo="Tarefa Convite"):
        return self.client.post(
            "/tarefas/nova/", self._payload(destinatario=destinatario, titulo=titulo), HTTP_HOST=self.http_host
        )


class TestCriacaoExigeConvite(TarefasConviteBase):
    """Usuário comum (sem admin, sem gerência sobre o destinatário)
    delegando para outro usuário: gera convite pendente, tarefa fica
    oculta da lista ativa do destinatário até aceite."""

    @classmethod
    def get_test_schema_name(cls):
        return "tarefas_convite_exige"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Tarefas Convite Exige"
        tenant.slug = "tarefas-convite-exige"

    def setUp(self):
        super().setUp()
        self.delegante = self._user("delegante_convite")
        self.destinatario = self._user("destinatario_convite")
        self._dar_acesso_com_atribuir_outros(self.delegante)
        self.client.force_login(self.delegante)

    def test_convite_pendente_e_criado_e_vinculado_a_tarefa(self):
        self._criar(destinatario=self.destinatario)
        tarefa = Tarefa.objects.get(titulo="Tarefa Convite")
        self.assertIsNotNone(tarefa.convite_delegacao)
        self.assertEqual(tarefa.convite_delegacao.status, ConviteDelegacao.STATUS_PENDENTE)
        self.assertEqual(tarefa.convite_delegacao.delegante_id, self.delegante.pk)
        self.assertEqual(tarefa.convite_delegacao.destinatario_id, self.destinatario.pk)
        self.assertEqual(tarefa.responsavel_id, self.destinatario.pk)

    def test_tarefa_nao_aparece_nas_listas_ativas_do_destinatario(self):
        self._criar(destinatario=self.destinatario)
        self.client.logout()
        # destinatário também precisa do módulo aberto para acessar as telas
        self._dar_acesso_com_atribuir_outros(self.destinatario)
        self.client.force_login(self.destinatario)

        r = self.client.get("/tarefas/lista/", HTTP_HOST=self.http_host)
        titulos_novidades = [t.titulo for t in r.context["tarefas_novidades"]]
        titulos_terceiro = [t.titulo for t in r.context["tarefas_terceiro"]]
        self.assertNotIn("Tarefa Convite", titulos_novidades)
        self.assertNotIn("Tarefa Convite", titulos_terceiro)

    def test_tarefa_aparece_em_delegadas_por_mim_com_status_pendente(self):
        self._criar(destinatario=self.destinatario)
        r = self.client.get("/tarefas/lista/", HTTP_HOST=self.http_host)
        titulos = [t.titulo for t in r.context["tarefas_delegadas"]]
        self.assertIn("Tarefa Convite", titulos)
        self.assertContains(r, "Convite pendente")

    def test_convite_aparece_na_aba_convites_recebidos_do_destinatario(self):
        self._criar(destinatario=self.destinatario)
        self.client.logout()
        self._dar_acesso_com_atribuir_outros(self.destinatario)
        self.client.force_login(self.destinatario)
        r = self.client.get("/tarefas/lista/", HTTP_HOST=self.http_host)
        convites = r.context["convites_recebidos"]
        self.assertEqual(len(convites), 1)
        self.assertEqual(convites[0].item.titulo, "Tarefa Convite")

    def test_destinatario_nao_consegue_acessar_tarefa_pendente_diretamente(self):
        self._criar(destinatario=self.destinatario)
        tarefa = Tarefa.objects.get(titulo="Tarefa Convite")
        self.client.logout()
        self._dar_acesso_com_atribuir_outros(self.destinatario)
        self.client.force_login(self.destinatario)
        r = self.client.get(f"/tarefas/{tarefa.pk}/editar/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 404)


class TestResponderConvite(TarefasConviteBase):
    @classmethod
    def get_test_schema_name(cls):
        return "tarefas_convite_responder"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Tarefas Convite Responder"
        tenant.slug = "tarefas-convite-responder"

    def setUp(self):
        super().setUp()
        self.delegante = self._user("delegante_responder")
        self.destinatario = self._user("destinatario_responder")
        self.terceiro = self._user("terceiro_responder")
        self._dar_acesso_com_atribuir_outros(self.delegante)
        self._dar_acesso_modulo(self.destinatario, nivel=NIVEL_SOMENTE_SEUS)
        self._dar_acesso_modulo(self.terceiro, nivel=NIVEL_SOMENTE_SEUS)
        self.client.force_login(self.delegante)
        self._criar(destinatario=self.destinatario)
        self.tarefa = Tarefa.objects.get(titulo="Tarefa Convite")
        self.client.logout()

    def test_destinatario_aceita_e_tarefa_passa_a_aparecer(self):
        self.client.force_login(self.destinatario)
        r = self.client.post(
            f"/tarefas/convites/{self.tarefa.convite_delegacao_id}/responder/",
            {"acao": "aceitar"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        self.tarefa.convite_delegacao.refresh_from_db()
        self.assertEqual(self.tarefa.convite_delegacao.status, ConviteDelegacao.STATUS_ACEITO)

        r = self.client.get("/tarefas/lista/", HTTP_HOST=self.http_host)
        titulos = [t.titulo for t in r.context["tarefas_novidades"]]
        self.assertIn("Tarefa Convite", titulos)

    def test_destinatario_recusa_com_justificativa(self):
        self.client.force_login(self.destinatario)
        r = self.client.post(
            f"/tarefas/convites/{self.tarefa.convite_delegacao_id}/responder/",
            {"acao": "recusar", "justificativa": "Sem tempo disponível."},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        self.tarefa.convite_delegacao.refresh_from_db()
        self.assertEqual(self.tarefa.convite_delegacao.status, ConviteDelegacao.STATUS_RECUSADO)
        self.assertEqual(self.tarefa.convite_delegacao.justificativa_recusa, "Sem tempo disponível.")

    def test_destinatario_recusa_sem_justificativa_e_valido(self):
        self.client.force_login(self.destinatario)
        r = self.client.post(
            f"/tarefas/convites/{self.tarefa.convite_delegacao_id}/responder/",
            {"acao": "recusar"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        self.tarefa.convite_delegacao.refresh_from_db()
        self.assertEqual(self.tarefa.convite_delegacao.status, ConviteDelegacao.STATUS_RECUSADO)
        self.assertEqual(self.tarefa.convite_delegacao.justificativa_recusa, "")

    def test_terceiro_nao_pode_responder_convite_alheio(self):
        self.client.force_login(self.terceiro)
        r = self.client.post(
            f"/tarefas/convites/{self.tarefa.convite_delegacao_id}/responder/",
            {"acao": "aceitar"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 404)
        self.tarefa.convite_delegacao.refresh_from_db()
        self.assertEqual(self.tarefa.convite_delegacao.status, ConviteDelegacao.STATUS_PENDENTE)


class TestDelegacaoDireta(TarefasConviteBase):
    """Administrador e gerente->subordinado da própria Equipe: tarefa
    ativa desde a criação, sem convite."""

    @classmethod
    def get_test_schema_name(cls):
        return "tarefas_convite_direta"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Tarefas Convite Direta"
        tenant.slug = "tarefas-convite-direta"

    def setUp(self):
        super().setUp()
        self.admin = self._user("admin_direta")
        self._set_admin(self.admin)
        self.destinatario = self._user("destinatario_direta")

        self.gerente = self._user("gerente_direta")
        self._dar_acesso_com_atribuir_outros(self.gerente)
        self.subordinado = self._user("subordinado_direta")
        equipe = Equipe.objects.create(nome="Equipe Direta")
        MembroEquipe.objects.create(usuario=self.gerente, equipe=equipe, eh_gerente=True, ativo=True)
        MembroEquipe.objects.create(usuario=self.subordinado, equipe=equipe, eh_gerente=False, ativo=True)

    def test_admin_delega_direto_sem_convite(self):
        self.client.force_login(self.admin)
        self._criar(destinatario=self.destinatario)
        tarefa = Tarefa.objects.get(titulo="Tarefa Convite")
        self.assertIsNone(tarefa.convite_delegacao)

    def test_gerente_delega_direto_para_subordinado_da_propria_equipe(self):
        self.client.force_login(self.gerente)
        self._criar(destinatario=self.subordinado)
        tarefa = Tarefa.objects.get(titulo="Tarefa Convite")
        self.assertIsNone(tarefa.convite_delegacao)

    def test_auto_atribuicao_nunca_gera_convite(self):
        comum = self._user("comum_auto_atribuicao")
        self._dar_acesso_com_atribuir_outros(comum)
        self.client.force_login(comum)
        self._criar(destinatario=comum, titulo="Tarefa Para Mim Mesmo")
        tarefa = Tarefa.objects.get(titulo="Tarefa Para Mim Mesmo")
        self.assertIsNone(tarefa.convite_delegacao)
