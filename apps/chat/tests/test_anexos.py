"""
Testes de anexo de arquivo em mensagem do Chat — feature descrita em
specs/chat-anexos-mensagem.md (ticket #12, independente dos tickets
#10/#11 de leitura e notificação).

Reaproveita o padrão de teste de upload com MEDIA_ROOT temporário já
usado em apps/financeiro/tests/test_solicitacoes.py. Fixtures de
conversa seguem apps/chat/tests/test_conversas.py.
"""

import shutil
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PapelAcesso, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import MODULO_CHAT
from apps.chat.models import Conversa, Mensagem

_MEDIA_TMP = tempfile.mkdtemp(prefix="lawsystem_test_media_")


def _anexo(nome="documento.pdf", conteudo=b"conteudo-teste"):
    return SimpleUploadedFile(nome, conteudo, content_type="application/pdf")


@override_settings(MEDIA_ROOT=_MEDIA_TMP)
class ChatAnexosBase(TenantTestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_MEDIA_TMP, ignore_errors=True)

    def setUp(self):
        self._media_override = override_settings(MEDIA_ROOT=_MEDIA_TMP)
        self._media_override.enable()
        self.addCleanup(self._media_override.disable)
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


class TestEnvioDeMensagemComAnexo(ChatAnexosBase):
    @classmethod
    def get_test_schema_name(cls):
        return "chat_anexo_envio"

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

    def test_enviar_so_com_anexo_sem_texto_cria_mensagem(self):
        r = self.client.post(
            f"/chat/{self.conversa.pk}/",
            {"conteudo": "", "anexo": _anexo()},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        mensagem = Mensagem.objects.get(conversa=self.conversa)
        self.assertEqual(mensagem.conteudo, "")
        self.assertTrue(mensagem.anexo)

    def test_enviar_sem_texto_e_sem_anexo_continua_dando_erro(self):
        r = self.client.post(
            f"/chat/{self.conversa.pk}/", {"conteudo": ""}, HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Mensagem.objects.filter(conversa=self.conversa).exists())

    def test_anexo_maior_que_o_limite_e_rejeitado(self):
        anexo_grande = _anexo("grande.pdf", conteudo=b"0" * (10 * 1024 * 1024 + 1))
        r = self.client.post(
            f"/chat/{self.conversa.pk}/",
            {"conteudo": "", "anexo": anexo_grande},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Mensagem.objects.filter(conversa=self.conversa).exists())

    def test_anexo_usa_namespace_protegido_do_tenant(self):
        self.client.post(
            f"/chat/{self.conversa.pk}/",
            {"conteudo": "segue o arquivo", "anexo": _anexo()},
            HTTP_HOST=self.http_host,
        )
        mensagem = Mensagem.objects.get(conversa=self.conversa)
        self.assertTrue(
            mensagem.anexo.name.startswith("tenants/chat_anexo_envio/protegido/chat/mensagens/")
        )
        self.assertIsNone(mensagem.anexo.url)


class TestDownloadDeAnexoConversaIndividual(ChatAnexosBase):
    @classmethod
    def get_test_schema_name(cls):
        return "chat_anexo_download_ind"

    def setUp(self):
        super().setUp()
        self.ana = self._user("ana")
        self.bruno = self._user("bruno")
        self.carla = self._user("carla")
        for user in (self.ana, self.bruno, self.carla):
            self._dar_acesso_chat(user)
        self.client.force_login(self.ana)
        self.client.post(
            "/chat/nova/individual/", {"usuario": self.bruno.pk}, HTTP_HOST=self.http_host
        )
        self.conversa = Conversa.objects.get(tipo=Conversa.TIPO_INDIVIDUAL)
        self.client.post(
            f"/chat/{self.conversa.pk}/",
            {"conteudo": "", "anexo": _anexo(conteudo=b"conteudo-do-anexo")},
            HTTP_HOST=self.http_host,
        )
        self.mensagem = Mensagem.objects.get(conversa=self.conversa)

    def test_participante_baixa_o_anexo(self):
        self.client.force_login(self.bruno)
        r = self.client.get(
            f"/chat/mensagem/{self.mensagem.pk}/anexo/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(b"".join(r.streaming_content), b"conteudo-do-anexo")

    def test_estranho_recebe_404_ao_tentar_baixar_o_anexo(self):
        self.client.force_login(self.carla)
        r = self.client.get(
            f"/chat/mensagem/{self.mensagem.pk}/anexo/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 404)

    def test_anonimo_e_redirecionado_ao_login(self):
        self.client.logout()
        r = self.client.get(
            f"/chat/mensagem/{self.mensagem.pk}/anexo/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login/", r.url)

    def test_mensagem_sem_anexo_retorna_404_no_download(self):
        self.client.post(
            f"/chat/{self.conversa.pk}/", {"conteudo": "só texto"}, HTTP_HOST=self.http_host
        )
        mensagem_sem_anexo = Mensagem.objects.get(conteudo="só texto")
        r = self.client.get(
            f"/chat/mensagem/{mensagem_sem_anexo.pk}/anexo/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 404)


class TestDownloadDeAnexoSalaGlobal(ChatAnexosBase):
    @classmethod
    def get_test_schema_name(cls):
        return "chat_anexo_download_global"

    def setUp(self):
        super().setUp()
        self.ana = self._user("ana")
        self.bruno = self._user("bruno")
        for user in (self.ana, self.bruno):
            self._dar_acesso_chat(user)
        self.client.force_login(self.ana)
        self.client.post(
            "/chat/global/",
            {"conteudo": "", "anexo": _anexo(conteudo=b"conteudo-global")},
            HTTP_HOST=self.http_host,
        )
        self.mensagem = Mensagem.objects.get(conversa__tipo=Conversa.TIPO_GLOBAL)

    def test_qualquer_usuario_do_modulo_baixa_anexo_da_sala_global(self):
        self.client.force_login(self.bruno)
        r = self.client.get(
            f"/chat/mensagem/{self.mensagem.pk}/anexo/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(b"".join(r.streaming_content), b"conteudo-global")
