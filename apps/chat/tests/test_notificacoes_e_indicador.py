"""
Testes de notificação de nova mensagem e indicador de não lida no Chat —
feature descrita em specs/chat-notificacoes-e-leitura.md (ticket #11:
depende do marco de leitura por participante do ticket #10).

Segue o mesmo padrão de fixtures de apps/chat/tests/test_conversas.py.
"""

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PapelAcesso, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import MODULO_CHAT
from apps.chat.models import Conversa
from apps.notificacoes.models import Notificacao


class ChatNotificacoesBase(TenantTestCase):
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


class TestNotificacaoConversaIndividual(ChatNotificacoesBase):
    @classmethod
    def get_test_schema_name(cls):
        return "chat_notif_individual"

    def setUp(self):
        super().setUp()
        self.ana = self._user("ana")
        self.bruno = self._user("bruno")
        for user in (self.ana, self.bruno):
            self._dar_acesso_chat(user)
        self.client.force_login(self.ana)
        self.client.post(
            "/chat/nova/individual/", {"usuario": self.bruno.pk}, HTTP_HOST=self.http_host
        )
        self.conversa = Conversa.objects.get(tipo=Conversa.TIPO_INDIVIDUAL)

    def test_enviar_mensagem_notifica_o_outro_participante(self):
        self.client.post(
            f"/chat/{self.conversa.pk}/", {"conteudo": "oi bruno"}, HTTP_HOST=self.http_host
        )
        self.assertTrue(Notificacao.objects.filter(destinatario=self.bruno).exists())

    def test_enviar_mensagem_nao_notifica_o_proprio_autor(self):
        self.client.post(
            f"/chat/{self.conversa.pk}/", {"conteudo": "oi bruno"}, HTTP_HOST=self.http_host
        )
        self.assertFalse(Notificacao.objects.filter(destinatario=self.ana).exists())


class TestNotificacaoConversaGrupo(ChatNotificacoesBase):
    @classmethod
    def get_test_schema_name(cls):
        return "chat_notif_grupo"

    def setUp(self):
        super().setUp()
        self.ana = self._user("ana")
        self.bruno = self._user("bruno")
        self.carla = self._user("carla")
        for user in (self.ana, self.bruno, self.carla):
            self._dar_acesso_chat(user)
        self.client.force_login(self.ana)
        self.client.post(
            "/chat/nova/grupo/",
            {"titulo": "Equipe", "participantes": [self.bruno.pk, self.carla.pk]},
            HTTP_HOST=self.http_host,
        )
        self.conversa = Conversa.objects.get(tipo=Conversa.TIPO_GRUPO)

    def test_enviar_mensagem_no_grupo_notifica_todos_exceto_o_autor(self):
        self.client.post(
            f"/chat/{self.conversa.pk}/", {"conteudo": "bom dia equipe"}, HTTP_HOST=self.http_host
        )
        self.assertTrue(Notificacao.objects.filter(destinatario=self.bruno).exists())
        self.assertTrue(Notificacao.objects.filter(destinatario=self.carla).exists())
        self.assertFalse(Notificacao.objects.filter(destinatario=self.ana).exists())


class TestNotificacaoSalaGlobal(ChatNotificacoesBase):
    @classmethod
    def get_test_schema_name(cls):
        return "chat_notif_global"

    def setUp(self):
        super().setUp()
        self.ana = self._user("ana")
        self.bruno = self._user("bruno")
        for user in (self.ana, self.bruno):
            self._dar_acesso_chat(user)

    def test_enviar_mensagem_na_sala_global_nao_gera_notificacao(self):
        self.client.force_login(self.ana)
        self.client.get("/chat/global/", HTTP_HOST=self.http_host)
        self.client.post(
            "/chat/global/", {"conteudo": "oi a todos"}, HTTP_HOST=self.http_host
        )
        self.assertFalse(Notificacao.objects.exists())


class TestIndicadorDeNaoLidaNaLista(ChatNotificacoesBase):
    @classmethod
    def get_test_schema_name(cls):
        return "chat_indicador_lista"

    def setUp(self):
        super().setUp()
        self.ana = self._user("ana")
        self.bruno = self._user("bruno")
        for user in (self.ana, self.bruno):
            self._dar_acesso_chat(user)
        self.client.force_login(self.ana)
        self.client.post(
            "/chat/nova/individual/", {"usuario": self.bruno.pk}, HTTP_HOST=self.http_host
        )
        self.conversa = Conversa.objects.get(tipo=Conversa.TIPO_INDIVIDUAL)

    def _tem_nao_lida(self, response, conversa_pk):
        for conversa in response.context["conversas"]:
            if conversa.pk == conversa_pk:
                return conversa.tem_nao_lida
        raise AssertionError("conversa não encontrada na lista")

    def test_mensagem_do_outro_participante_marca_conversa_como_nao_lida(self):
        self.client.force_login(self.bruno)
        self.client.post(
            f"/chat/{self.conversa.pk}/", {"conteudo": "oi ana"}, HTTP_HOST=self.http_host
        )

        self.client.force_login(self.ana)
        r = self.client.get("/chat/", HTTP_HOST=self.http_host)
        self.assertTrue(self._tem_nao_lida(r, self.conversa.pk))

    def test_abrir_a_conversa_remove_o_indicador_de_nao_lida(self):
        self.client.force_login(self.bruno)
        self.client.post(
            f"/chat/{self.conversa.pk}/", {"conteudo": "oi ana"}, HTTP_HOST=self.http_host
        )

        self.client.force_login(self.ana)
        self.client.get(f"/chat/{self.conversa.pk}/", HTTP_HOST=self.http_host)
        r = self.client.get("/chat/", HTTP_HOST=self.http_host)
        self.assertFalse(self._tem_nao_lida(r, self.conversa.pk))

    def test_propria_mensagem_enviada_nao_marca_a_conversa_como_nao_lida_para_o_autor(self):
        r = self.client.post(
            f"/chat/{self.conversa.pk}/", {"conteudo": "oi bruno"}, HTTP_HOST=self.http_host
        )
        r = self.client.get("/chat/", HTTP_HOST=self.http_host)
        self.assertFalse(self._tem_nao_lida(r, self.conversa.pk))

    def test_sala_global_recebe_indicador_de_nao_lida_sem_gerar_notificacao(self):
        self.client.force_login(self.bruno)
        self.client.post("/chat/global/", {"conteudo": "oi a todos"}, HTTP_HOST=self.http_host)

        self.client.force_login(self.ana)
        r = self.client.get("/chat/", HTTP_HOST=self.http_host)
        self.assertTrue(r.context["sala_global"].tem_nao_lida)
        self.assertFalse(Notificacao.objects.exists())
