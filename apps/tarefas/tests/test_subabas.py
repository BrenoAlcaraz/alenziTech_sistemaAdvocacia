"""
Testes da faixa de sub-abas de Tarefas (spec
`tarefas-subabas-habilitacao.md`): "Recentes (últimas 24h)"/
"Atribuídas a mim por terceiros" sempre visíveis; "Delegadas por mim"/
"Ver tarefas de outra pessoa" condicionadas à mesma habilitação já
aprovada (`tarefas_atribuir_outros`) — nenhuma habilitação nova.

Segue o mesmo padrão de fixtures de apps/agenda/tests/test_subabas.py.
"""

from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import (
    HabilitacaoPapel,
    PapelAcesso,
    PermissaoPapel,
    UsuarioPapel,
)
from apps.accounts.permissoes_constants import (
    HAB_TAREFAS_ATRIBUIR_OUTROS,
    MODULO_TAREFAS,
    NIVEL_SOMENTE_SEUS,
    NIVEL_TODOS,
)
from apps.tarefas.models import Tarefa


class TarefasSubabasBase(TenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio
        domain_obj = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = domain_obj.domain if domain_obj else "localhost"

    def _user(self, username):
        return User.objects.create_user(username=username, password="testpass")

    def _new_papel(self, nome):
        return PapelAcesso.objects.create(nome=nome, ativo=True)

    def _assign_papel(self, user, papel):
        return UsuarioPapel.objects.create(usuario=user, papel=papel, ativo=True)

    def _pp(self, papel, modulo, *, nivel=NIVEL_TODOS):
        return PermissaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=modulo, ativo=True, nivel=nivel
        )

    def _hp(self, papel, modulo, item):
        return HabilitacaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=modulo, item=item, ativo=True
        )

    def _dar_acesso_tarefas(self, user, *, nivel=NIVEL_TODOS):
        papel = self._new_papel(f"Papel Tarefas {user.username}")
        self._assign_papel(user, papel)
        self._pp(papel, MODULO_TAREFAS, nivel=nivel)
        return papel

    def _tarefa(self, *, responsavel, atribuidor=None, criador=None, **kwargs):
        defaults = {"titulo": "Tarefa Teste"}
        defaults.update(kwargs)
        return Tarefa.objects.create(
            responsavel=responsavel,
            atribuidor=atribuidor,
            criador=criador or atribuidor,
            atribuido_em=timezone.now(),
            **defaults,
        )


class TestSubabaNovidades(TarefasSubabasBase):
    """"Recentes (últimas 24h)" — sempre visível, qualquer origem."""

    @classmethod
    def get_test_schema_name(cls):
        return "tarefas_subaba_novidades"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Tarefas Subaba Novidades"
        tenant.slug = "tarefas-subaba-novidades"

    def setUp(self):
        super().setUp()
        self.user = self._user("usuario_novidades")
        self._dar_acesso_tarefas(self.user)
        self.client.force_login(self.user)

    def test_tarefa_recente_como_responsavel_aparece(self):
        recente = self._tarefa(
            titulo="Recente", responsavel=self.user, atribuidor=self.user
        )
        r = self.client.get("/tarefas/lista/", HTTP_HOST=self.http_host)
        self.assertIn(recente, r.context["tarefas_novidades"])

    def test_tarefa_antiga_nao_aparece(self):
        antiga = self._tarefa(
            titulo="Antiga", responsavel=self.user, atribuidor=self.user
        )
        Tarefa.objects.filter(pk=antiga.pk).update(
            atribuido_em=timezone.now() - timedelta(hours=30)
        )
        r = self.client.get("/tarefas/lista/", HTTP_HOST=self.http_host)
        self.assertNotIn(antiga, r.context["tarefas_novidades"])

    def test_tarefa_de_outro_responsavel_nao_aparece(self):
        colega = self._user("colega_novidades")
        de_outro = self._tarefa(
            titulo="De outro responsável", responsavel=colega, atribuidor=self.user
        )
        r = self.client.get("/tarefas/lista/", HTTP_HOST=self.http_host)
        self.assertNotIn(de_outro, r.context["tarefas_novidades"])


class TestSubabaAtribuidasPorTerceiros(TarefasSubabasBase):
    """"Atribuídas a mim por terceiros" — sempre visível, só quando o atribuidor é outra pessoa."""

    @classmethod
    def get_test_schema_name(cls):
        return "tarefas_subaba_terceiro"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Tarefas Subaba Terceiro"
        tenant.slug = "tarefas-subaba-terceiro"

    def setUp(self):
        super().setUp()
        self.user = self._user("usuario_terceiro")
        self.colega = self._user("colega_terceiro")
        self._dar_acesso_tarefas(self.user)
        self.client.force_login(self.user)

    def test_atribuida_por_outro_aparece(self):
        t = self._tarefa(
            titulo="De Terceiro", responsavel=self.user, atribuidor=self.colega
        )
        r = self.client.get("/tarefas/lista/", HTTP_HOST=self.http_host)
        self.assertIn(t, r.context["tarefas_terceiro"])

    def test_atribuida_pelo_proprio_usuario_nao_aparece(self):
        t = self._tarefa(
            titulo="Própria", responsavel=self.user, atribuidor=self.user
        )
        r = self.client.get("/tarefas/lista/", HTTP_HOST=self.http_host)
        self.assertNotIn(t, r.context["tarefas_terceiro"])

    def test_sem_atribuidor_registrado_nao_aparece(self):
        t = self._tarefa(titulo="Legada", responsavel=self.user, atribuidor=None)
        r = self.client.get("/tarefas/lista/", HTTP_HOST=self.http_host)
        self.assertNotIn(t, r.context["tarefas_terceiro"])


class TestSubabaDelegadasPorMim(TarefasSubabasBase):
    """
    "Delegadas por mim" — só para quem tem `tarefas_atribuir_outros`;
    mostra qualquer status, inclusive cancelada.
    """

    @classmethod
    def get_test_schema_name(cls):
        return "tarefas_subaba_delegadas"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Tarefas Subaba Delegadas"
        tenant.slug = "tarefas-subaba-delegadas"

    def setUp(self):
        super().setUp()
        self.gestor = self._user("gestor_delegadas")
        self.colega = self._user("colega_delegadas")
        self.comum = self._user("comum_delegadas")

        papel_gestor = self._dar_acesso_tarefas(self.gestor)
        self._hp(papel_gestor, MODULO_TAREFAS, HAB_TAREFAS_ATRIBUIR_OUTROS)

        self._dar_acesso_tarefas(self.comum)

    def test_aba_nao_aparece_para_quem_nao_pode_delegar(self):
        self.client.force_login(self.comum)
        r = self.client.get("/tarefas/lista/", HTTP_HOST=self.http_host)
        self.assertNotIn("tarefas_delegadas", r.context)
        self.assertNotContains(r, "Delegadas por mim")

    def test_aba_mostra_tarefa_delegada_mesmo_cancelada(self):
        self.client.force_login(self.gestor)
        delegada = self._tarefa(
            titulo="Delegada Cancelada",
            responsavel=self.colega,
            atribuidor=self.gestor,
            status="cancelada",
        )
        r = self.client.get("/tarefas/lista/", HTTP_HOST=self.http_host)
        self.assertIn(delegada, r.context["tarefas_delegadas"])

    def test_aba_nao_mostra_tarefa_propria(self):
        self.client.force_login(self.gestor)
        propria = self._tarefa(
            titulo="Própria do Gestor", responsavel=self.gestor, atribuidor=self.gestor
        )
        r = self.client.get("/tarefas/lista/", HTTP_HOST=self.http_host)
        self.assertNotIn(propria, r.context["tarefas_delegadas"])


class TestSubabaVerTarefasDeOutraPessoa(TarefasSubabasBase):
    """
    "Ver tarefas de outra pessoa" — mesma habilitação de "Delegadas por
    mim" (`tarefas_atribuir_outros`), não a Permissão "Gerir" usada pelo
    atalho do Painel do gestor em `?usuario=` no quadro.
    """

    @classmethod
    def get_test_schema_name(cls):
        return "tarefas_subaba_outros"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Tarefas Subaba Outros"
        tenant.slug = "tarefas-subaba-outros"

    def setUp(self):
        super().setUp()
        self.gestor = self._user("gestor_outros")
        self.comum = self._user("comum_outros")
        self.colega = self._user("colega_outros")

        papel_gestor = self._dar_acesso_tarefas(self.gestor)
        self._hp(papel_gestor, MODULO_TAREFAS, HAB_TAREFAS_ATRIBUIR_OUTROS)

        self._dar_acesso_tarefas(self.comum, nivel=NIVEL_SOMENTE_SEUS)

    def test_aba_nao_aparece_para_usuario_comum(self):
        self.client.force_login(self.comum)
        r = self.client.get("/tarefas/lista/", HTTP_HOST=self.http_host)
        self.assertNotIn("usuarios_outros", r.context)
        self.assertNotContains(r, "Ver tarefas de outra pessoa")

    def test_aba_aparece_para_quem_pode_atribuir_a_outros(self):
        self.client.force_login(self.gestor)
        r = self.client.get("/tarefas/lista/", HTTP_HOST=self.http_host)
        self.assertIn("usuarios_outros", r.context)
        self.assertContains(r, "Ver tarefas de outra pessoa")

    def test_usuario_comum_tem_parametro_usuario_ignorado(self):
        self.client.force_login(self.comum)
        tarefa_colega = self._tarefa(
            titulo="Do colega", responsavel=self.colega, atribuidor=self.colega
        )
        r = self.client.get(
            "/tarefas/lista/", {"usuario": self.colega.pk}, HTTP_HOST=self.http_host
        )
        self.assertIsNone(r.context["usuario_filtro"])
        self.assertNotIn(tarefa_colega, r.context["tarefas"])

    def test_selecionar_usuario_filtra_a_lista_e_ativa_a_aba(self):
        self.client.force_login(self.gestor)
        tarefa_colega = self._tarefa(
            titulo="Do colega", responsavel=self.colega, atribuidor=self.colega
        )
        r = self.client.get(
            "/tarefas/lista/", {"usuario": self.colega.pk}, HTTP_HOST=self.http_host
        )
        self.assertEqual(r.context["aba_ativa"], "outros")
        self.assertEqual(r.context["usuario_filtro"], self.colega)
        self.assertIn(tarefa_colega, r.context["tarefas"])


class TestFaixaSubabasVisivelNoQuadro(TarefasSubabasBase):
    """
    Regressão (revisão do sócio de 2026-09-17, docs/STATUS.md): a faixa
    de sub-abas precisa aparecer tanto na visão de lista quanto na de
    quadro (kanban) — `quadro` não montava o contexto nem incluía o
    template parcial, então a faixa sumia ao trocar de visão.
    """

    @classmethod
    def get_test_schema_name(cls):
        return "tarefas_subaba_quadro"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Tarefas Subaba Quadro"
        tenant.slug = "tarefas-subaba-quadro"

    def setUp(self):
        super().setUp()
        self.comum = self._user("comum_quadro")
        self._dar_acesso_tarefas(self.comum)
        self.gestor = self._user("gestor_quadro")
        papel_gestor = self._dar_acesso_tarefas(self.gestor)
        self._hp(papel_gestor, MODULO_TAREFAS, HAB_TAREFAS_ATRIBUIR_OUTROS)
        self.colega = self._user("colega_quadro")

    def test_recentes_e_terceiros_sempre_visiveis_no_quadro(self):
        self.client.force_login(self.comum)
        r = self.client.get("/tarefas/", HTTP_HOST=self.http_host)
        self.assertContains(r, "Recentes (últimas 24h)")
        self.assertContains(r, "Atribuídas a mim por terceiros")

    def test_delegadas_e_outros_ocultas_sem_habilitacao_no_quadro(self):
        self.client.force_login(self.comum)
        r = self.client.get("/tarefas/", HTTP_HOST=self.http_host)
        self.assertNotContains(r, "Delegadas por mim")
        self.assertNotContains(r, "Ver tarefas de outra pessoa")

    def test_delegadas_e_outros_visiveis_com_habilitacao_no_quadro(self):
        self.client.force_login(self.gestor)
        r = self.client.get("/tarefas/", HTTP_HOST=self.http_host)
        self.assertContains(r, "Delegadas por mim")
        self.assertContains(r, "Ver tarefas de outra pessoa")

    def test_selecionar_colega_na_subaba_filtra_o_quadro(self):
        # Mesma habilitação da sub-aba "Ver tarefas de outra pessoa"
        # (tarefas_atribuir_outros) — sem gerir/Admin, distinta do
        # atalho do Painel do gestor (ver test_usuario_filtro.py).
        self.client.force_login(self.gestor)
        tarefa_colega = self._tarefa(
            titulo="Do colega no quadro", responsavel=self.colega, atribuidor=self.colega,
            status="em_andamento",
        )
        r = self.client.get(
            "/tarefas/", {"usuario": self.colega.pk}, HTTP_HOST=self.http_host
        )
        self.assertEqual(r.context["aba_ativa"], "outros")
        self.assertEqual(r.context["usuario_filtro"], self.colega)
        self.assertIn(tarefa_colega, r.context["tarefas_por_status"]["em_andamento"])


class TestNovaTarefaParaOutraPessoa(TarefasSubabasBase):
    """
    "+ Nova tarefa para esta pessoa": campo "Atribuir a" pré-preenchido e
    travado no usuário selecionado — mesmo padrão de
    apps/agenda/views.py::_usuario_travado.
    """

    @classmethod
    def get_test_schema_name(cls):
        return "tarefas_subaba_nova_para_outro"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Tarefas Subaba Nova Para Outro"
        tenant.slug = "tarefas-subaba-nova-para-outro"

    def setUp(self):
        super().setUp()
        self.gestor = self._user("gestor_nova_outro")
        self.colega = self._user("colega_nova_outro")
        papel_gestor = self._dar_acesso_tarefas(self.gestor)
        self._hp(papel_gestor, MODULO_TAREFAS, HAB_TAREFAS_ATRIBUIR_OUTROS)
        self.client.force_login(self.gestor)

    def test_formulario_vem_com_campo_travado(self):
        r = self.client.get(
            "/tarefas/nova/", {"para_usuario": self.colega.pk}, HTTP_HOST=self.http_host
        )
        self.assertEqual(r.context["usuario_travado"], self.colega)
        self.assertTrue(r.context["form"].fields["destinatario"].disabled)
        self.assertTrue(r.context["form"].fields["atribuidos"].disabled)

    def test_submeter_outro_destinatario_e_ignorado_permanece_travado(self):
        outro = self._user("outro_terceiro")
        resposta = self.client.post(
            "/tarefas/nova/",
            {
                "para_usuario": self.colega.pk,
                "titulo": "Tarefa para o colega",
                "descricao": "",
                "prioridade": "media",
                "prazo": "",
                "cliente": "",
                "processo": "",
                "destinatario": outro.pk,
            },
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(resposta.status_code, 302)
        tarefa = Tarefa.objects.get(titulo="Tarefa para o colega")
        self.assertEqual(tarefa.responsavel_id, self.colega.pk)
        self.assertEqual(tarefa.participantes.count(), 0)
