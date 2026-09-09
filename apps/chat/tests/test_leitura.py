"""
Testes do marco de leitura por participante no Chat — feature descrita em
specs/chat-notificacoes-e-leitura.md (ticket #10: só o modelo de leitura
por participante e a marcação ao abrir a conversa; indicador visual e
notificação são o próximo ticket).

Segue o mesmo padrão de fixtures de apps/chat/tests/test_conversas.py.
"""

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PapelAcesso, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import MODULO_CHAT
from apps.chat.models import Conversa, LeituraConversa, Mensagem


class ChatLeituraBase(TenantTestCase):
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


class TestMarcoDeLeituraConversaIndividual(ChatLeituraBase):
    @classmethod
    def get_test_schema_name(cls):
        return "chat_leitura_individual"

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

    def test_abrir_conversa_cria_marco_de_leitura_para_quem_abriu(self):
        self.client.get(f"/chat/{self.conversa.pk}/", HTTP_HOST=self.http_host)
        self.assertTrue(
            LeituraConversa.objects.filter(conversa=self.conversa, usuario=self.ana).exists()
        )

    def test_abrir_conversa_nao_cria_marco_de_leitura_para_o_outro_participante(self):
        self.client.get(f"/chat/{self.conversa.pk}/", HTTP_HOST=self.http_host)
        self.assertFalse(
            LeituraConversa.objects.filter(conversa=self.conversa, usuario=self.bruno).exists()
        )

    def test_abrir_conversa_de_novo_atualiza_o_mesmo_marco_sem_duplicar(self):
        self.client.get(f"/chat/{self.conversa.pk}/", HTTP_HOST=self.http_host)
        primeiro = LeituraConversa.objects.get(conversa=self.conversa, usuario=self.ana)

        self.client.get(f"/chat/{self.conversa.pk}/", HTTP_HOST=self.http_host)

        self.assertEqual(
            LeituraConversa.objects.filter(conversa=self.conversa, usuario=self.ana).count(), 1
        )
        atualizado = LeituraConversa.objects.get(conversa=self.conversa, usuario=self.ana)
        self.assertGreaterEqual(atualizado.lida_em, primeiro.lida_em)


class TestMarcoDeLeituraConversaGrupo(ChatLeituraBase):
    @classmethod
    def get_test_schema_name(cls):
        return "chat_leitura_grupo"

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

    def test_cada_participante_tem_marco_de_leitura_independente(self):
        self.client.force_login(self.bruno)
        self.client.get(f"/chat/{self.conversa.pk}/", HTTP_HOST=self.http_host)

        self.assertTrue(
            LeituraConversa.objects.filter(conversa=self.conversa, usuario=self.bruno).exists()
        )
        self.assertFalse(
            LeituraConversa.objects.filter(conversa=self.conversa, usuario=self.ana).exists()
        )
        self.assertFalse(
            LeituraConversa.objects.filter(conversa=self.conversa, usuario=self.carla).exists()
        )


class TestMarcoDeLeituraSalaGlobal(ChatLeituraBase):
    @classmethod
    def get_test_schema_name(cls):
        return "chat_leitura_global"

    def setUp(self):
        super().setUp()
        self.ana = self._user("ana")
        self._dar_acesso_chat(self.ana)
        self.client.force_login(self.ana)

    def test_abrir_sala_global_cria_marco_de_leitura(self):
        self.client.get("/chat/global/", HTTP_HOST=self.http_host)
        sala = Conversa.objects.get(tipo=Conversa.TIPO_GLOBAL)
        self.assertTrue(
            LeituraConversa.objects.filter(conversa=sala, usuario=self.ana).exists()
        )


class TestMensagemSemCampoLida(ChatLeituraBase):
    """`Mensagem.lida` era um booleano único sem uso em nenhuma view —
    substituído por LeituraConversa (por participante)."""

    @classmethod
    def get_test_schema_name(cls):
        return "chat_leitura_sem_campo_antigo"

    def test_mensagem_nao_tem_mais_campo_lida(self):
        campos = {f.name for f in Mensagem._meta.get_fields()}
        self.assertNotIn("lida", campos)
