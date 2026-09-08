"""
Testes de conversas individuais e em grupo no Chat — feature descrita em
specs/chat-conversas-individuais-e-em-grupo.md: criação, listagem,
dedup de conversa individual e acesso restrito a quem participa (posse
via QuerySet, 404 e não 403 — mesmo padrão de
apps/agenda/tests/test_participantes.py).

Segue o mesmo padrão de fixtures de apps/chat/tests/test_autorizacao.py.
"""

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PapelAcesso, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import MODULO_CHAT
from apps.chat.models import Conversa, Mensagem


class ChatConversasBase(TenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio
        domain_obj = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = domain_obj.domain if domain_obj else "localhost"

    def _user(self, username, *, is_active=True):
        return User.objects.create_user(
            username=username, password="testpass", is_active=is_active
        )

    def _new_papel(self, nome, *, ativo=True):
        return PapelAcesso.objects.create(nome=nome, ativo=ativo)

    def _assign_papel(self, user, papel, *, ativo=True):
        return UsuarioPapel.objects.create(usuario=user, papel=papel, ativo=ativo)

    def _pp(self, papel, modulo, *, ativo=True, nivel=""):
        return PermissaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=modulo, ativo=ativo, nivel=nivel
        )

    def _dar_acesso_chat(self, user):
        papel = self._new_papel(f"Papel Chat {user.username}")
        self._assign_papel(user, papel)
        self._pp(papel, MODULO_CHAT)


class TestConversaIndividual(ChatConversasBase):
    @classmethod
    def get_test_schema_name(cls):
        return "chat_conv_individual"

    def setUp(self):
        super().setUp()
        self.ana = self._user("ana")
        self.bruno = self._user("bruno")
        self.carla = self._user("carla")
        for user in (self.ana, self.bruno, self.carla):
            self._dar_acesso_chat(user)

    def test_iniciar_conversa_individual_cria_conversa_com_os_dois_participantes(self):
        self.client.force_login(self.ana)
        r = self.client.post(
            "/chat/nova/individual/", {"usuario": self.bruno.pk}, HTTP_HOST=self.http_host
        )
        conversa = Conversa.objects.get(tipo=Conversa.TIPO_INDIVIDUAL)
        self.assertRedirects(
            r, f"/chat/{conversa.pk}/", fetch_redirect_response=False
        )
        self.assertEqual(
            set(conversa.participantes.values_list("pk", flat=True)),
            {self.ana.pk, self.bruno.pk},
        )

    def test_iniciar_conversa_individual_duas_vezes_reaproveita_a_existente(self):
        self.client.force_login(self.ana)
        self.client.post(
            "/chat/nova/individual/", {"usuario": self.bruno.pk}, HTTP_HOST=self.http_host
        )
        self.client.post(
            "/chat/nova/individual/", {"usuario": self.bruno.pk}, HTTP_HOST=self.http_host
        )
        self.assertEqual(Conversa.objects.filter(tipo=Conversa.TIPO_INDIVIDUAL).count(), 1)

    def test_mensagem_trocada_so_e_visivel_para_os_dois_participantes(self):
        self.client.force_login(self.ana)
        self.client.post(
            "/chat/nova/individual/", {"usuario": self.bruno.pk}, HTTP_HOST=self.http_host
        )
        conversa = Conversa.objects.get(tipo=Conversa.TIPO_INDIVIDUAL)
        self.client.post(
            f"/chat/{conversa.pk}/", {"conteudo": "oi bruno"}, HTTP_HOST=self.http_host
        )

        self.client.force_login(self.bruno)
        r = self.client.get(f"/chat/{conversa.pk}/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        conteudos = [m.conteudo for m in r.context["mensagens"]]
        self.assertIn("oi bruno", conteudos)

    def test_estranho_recebe_404_ao_acessar_conversa_alheia(self):
        self.client.force_login(self.ana)
        self.client.post(
            "/chat/nova/individual/", {"usuario": self.bruno.pk}, HTTP_HOST=self.http_host
        )
        conversa = Conversa.objects.get(tipo=Conversa.TIPO_INDIVIDUAL)

        self.client.force_login(self.carla)
        r = self.client.get(f"/chat/{conversa.pk}/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 404)

    def test_estranho_nao_envia_mensagem_em_conversa_alheia(self):
        self.client.force_login(self.ana)
        self.client.post(
            "/chat/nova/individual/", {"usuario": self.bruno.pk}, HTTP_HOST=self.http_host
        )
        conversa = Conversa.objects.get(tipo=Conversa.TIPO_INDIVIDUAL)

        self.client.force_login(self.carla)
        r = self.client.post(
            f"/chat/{conversa.pk}/", {"conteudo": "intrusa"}, HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 404)
        self.assertFalse(Mensagem.objects.filter(conteudo="intrusa").exists())


class TestConversaGrupo(ChatConversasBase):
    @classmethod
    def get_test_schema_name(cls):
        return "chat_conv_grupo"

    def setUp(self):
        super().setUp()
        self.ana = self._user("ana")
        self.bruno = self._user("bruno")
        self.carla = self._user("carla")
        self.daniel = self._user("daniel")
        for user in (self.ana, self.bruno, self.carla, self.daniel):
            self._dar_acesso_chat(user)

    def test_criar_grupo_com_titulo_e_participantes(self):
        self.client.force_login(self.ana)
        r = self.client.post(
            "/chat/nova/grupo/",
            {"titulo": "Equipe Trabalhista", "participantes": [self.bruno.pk, self.carla.pk]},
            HTTP_HOST=self.http_host,
        )
        conversa = Conversa.objects.get(tipo=Conversa.TIPO_GRUPO)
        self.assertRedirects(
            r, f"/chat/{conversa.pk}/", fetch_redirect_response=False
        )
        self.assertEqual(conversa.titulo, "Equipe Trabalhista")
        self.assertEqual(
            set(conversa.participantes.values_list("pk", flat=True)),
            {self.ana.pk, self.bruno.pk, self.carla.pk},
        )

    def test_criar_grupo_com_menos_de_2_participantes_falha(self):
        self.client.force_login(self.ana)
        r = self.client.post(
            "/chat/nova/grupo/",
            {"titulo": "Grupo Pequeno", "participantes": [self.bruno.pk]},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Conversa.objects.filter(tipo=Conversa.TIPO_GRUPO).exists())

    def test_quem_nao_participa_do_grupo_recebe_404(self):
        self.client.force_login(self.ana)
        self.client.post(
            "/chat/nova/grupo/",
            {"titulo": "Equipe Trabalhista", "participantes": [self.bruno.pk, self.carla.pk]},
            HTTP_HOST=self.http_host,
        )
        conversa = Conversa.objects.get(tipo=Conversa.TIPO_GRUPO)

        self.client.force_login(self.daniel)
        r = self.client.get(f"/chat/{conversa.pk}/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 404)


class TestListaDeConversas(ChatConversasBase):
    @classmethod
    def get_test_schema_name(cls):
        return "chat_conv_lista"

    def setUp(self):
        super().setUp()
        self.ana = self._user("ana")
        self.bruno = self._user("bruno")
        self.carla = self._user("carla")
        for user in (self.ana, self.bruno, self.carla):
            self._dar_acesso_chat(user)

    def test_lista_mostra_sala_global_e_conversas_do_usuario(self):
        self.client.force_login(self.ana)
        self.client.post(
            "/chat/nova/individual/", {"usuario": self.bruno.pk}, HTTP_HOST=self.http_host
        )

        r = self.client.get("/chat/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        self.assertIsNotNone(r.context["sala_global"])
        nomes = [c.nome_exibicao for c in r.context["conversas"]]
        self.assertIn(self.bruno.get_full_name() or f"@{self.bruno.username}", nomes)

    def test_lista_nao_mostra_conversa_alheia(self):
        self.client.force_login(self.ana)
        self.client.post(
            "/chat/nova/individual/", {"usuario": self.bruno.pk}, HTTP_HOST=self.http_host
        )

        self.client.force_login(self.carla)
        r = self.client.get("/chat/", HTTP_HOST=self.http_host)
        self.assertEqual(len(r.context["conversas"]), 0)
