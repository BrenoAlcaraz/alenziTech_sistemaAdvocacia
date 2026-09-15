"""
Upload de foto de perfil — specs/configuracoes-perfil-e-habilitacoes.md:
expõe `PerfilUsuario.avatar` (já existia no modelo) no formulário de
edição de perfil pessoal; entrega protegida via view autenticada, mesmo
padrão de `chat.anexo_mensagem` (storage sem URL pública).
"""

import shutil
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PerfilUsuario

_GIF_1PX = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01"
    b"\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
)

_MEDIA_TMP = tempfile.mkdtemp(prefix="lawsystem_test_editar_perfil_")


def tearDownModule():
    shutil.rmtree(_MEDIA_TMP, ignore_errors=True)


@override_settings(MEDIA_ROOT=_MEDIA_TMP)
class EditarPerfilFotoBase(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "configuracoes_editar_perfil_foto"

    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio

        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"
        self.user = User.objects.create_user("usuario_perfil", password="testpass")
        self.client.force_login(self.user)

    def _foto(self, nome="foto.gif"):
        return SimpleUploadedFile(nome, _GIF_1PX, content_type="image/gif")


class TestUploadFotoPerfil(EditarPerfilFotoBase):
    def test_get_renderiza_sem_foto(self):
        r = self.client.get("/configuracoes/perfil/editar/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)

    def test_get_renderiza_com_foto_existente(self):
        perfil, _ = PerfilUsuario.objects.get_or_create(user=self.user)
        perfil.avatar.save("foto.gif", self._foto(), save=True)

        r = self.client.get("/configuracoes/perfil/editar/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)

    def test_upload_troca_a_foto_de_perfil(self):
        r = self.client.post(
            "/configuracoes/perfil/editar/",
            {"nome_completo": "Usuário Teste", "cargo": "Advogado", "avatar": self._foto()},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)

        perfil = PerfilUsuario.objects.get(user=self.user)
        self.assertTrue(perfil.avatar)

    def test_sem_arquivo_mantem_dados_de_texto_sem_erro(self):
        r = self.client.post(
            "/configuracoes/perfil/editar/",
            {"nome_completo": "Usuário Teste", "cargo": "Advogado"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(
            PerfilUsuario.objects.get(user=self.user).nome_completo, "Usuário Teste"
        )


class TestServirFotoPerfil(EditarPerfilFotoBase):
    def test_sem_foto_retorna_404(self):
        r = self.client.get("/configuracoes/perfil/foto/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 404)

    def test_com_foto_retorna_conteudo(self):
        perfil, _ = PerfilUsuario.objects.get_or_create(user=self.user)
        perfil.avatar.save("foto.gif", self._foto(), save=True)

        r = self.client.get("/configuracoes/perfil/foto/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(b"".join(r.streaming_content), _GIF_1PX)

    def test_exige_login(self):
        self.client.logout()
        r = self.client.get("/configuracoes/perfil/foto/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 302)
