import shutil
import tempfile
from pathlib import PurePosixPath

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.test import override_settings
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PerfilUsuario


_MEDIA_TMP = tempfile.mkdtemp(prefix="lawsystem_test_avatar_")


def tearDownModule():
    shutil.rmtree(_MEDIA_TMP, ignore_errors=True)


@override_settings(DEBUG=True)
class TestAvatarProtegido(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "accounts_storage"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Accounts Storage"
        tenant.slug = "accounts-storage"

    def setUp(self):
        self._media_override = override_settings(MEDIA_ROOT=_MEDIA_TMP)
        self._media_override.enable()
        self.addCleanup(self._media_override.disable)
        super().setUp()
        self.user = User.objects.create_user("usuario_avatar", password="testpass")
        self.perfil, _ = PerfilUsuario.objects.get_or_create(user=self.user)

    def test_avatar_novo_usa_namespace_protegido_do_tenant(self):
        self.perfil.avatar.save("foto.png", ContentFile(b"avatar"), save=True)

        self.assertEqual(
            str(PurePosixPath(self.perfil.avatar.name).parent),
            "tenants/accounts_storage/protegido/accounts/avatares",
        )
        self.assertIsNone(self.perfil.avatar.url)

    def test_avatar_nao_possui_endpoint_publico_por_media_url(self):
        self.perfil.avatar.save("foto.png", ContentFile(b"avatar"), save=True)

        resposta = self.client.get(
            f"/media/{self.perfil.avatar.name}",
            HTTP_HOST=self.domain.domain,
        )

        self.assertEqual(resposta.status_code, 404)

    def test_avatar_legado_permanece_associado_sem_endpoint_publico(self):
        nome_legado = "avatares/avatar-legado.png"
        self.perfil.avatar.storage.save(nome_legado, ContentFile(b"avatar-legado"))
        self.perfil.avatar = nome_legado
        self.perfil.save(update_fields=["avatar"])
        self.perfil.refresh_from_db()

        resposta = self.client.get(
            f"/media/{self.perfil.avatar.name}",
            HTTP_HOST=self.domain.domain,
        )

        self.assertEqual(self.perfil.avatar.name, nome_legado)
        self.assertEqual(resposta.status_code, 404)
