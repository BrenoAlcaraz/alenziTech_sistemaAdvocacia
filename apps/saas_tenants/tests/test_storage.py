import shutil
import tempfile
from pathlib import Path, PurePosixPath
from types import SimpleNamespace

from django.core.files.base import ContentFile
from django.db import connection
from django.test import SimpleTestCase, TransactionTestCase, override_settings
from django_tenants.test.cases import TenantTestCase
from django_tenants.utils import schema_context

from apps.saas_tenants.models import ConfiguracaoVisual, Dominio, Escritorio
from apps.saas_tenants.storage import (
    CaminhoArquivoTenant,
    PROTEGIDO,
    PUBLICO,
    StorageIdentidadeVisual,
)


_MEDIA_TMP = tempfile.mkdtemp(prefix="lawsystem_test_storage_")


def tearDownModule():
    shutil.rmtree(_MEDIA_TMP, ignore_errors=True)


class MediaRootIsolado:
    def setUp(self):
        self._media_override = override_settings(MEDIA_ROOT=_MEDIA_TMP)
        self._media_override.enable()
        self.addCleanup(self._media_override.disable)
        super().setUp()


class TestCaminhoArquivoTenant(SimpleTestCase):
    def test_mesmo_nome_fica_em_namespaces_distintos_por_tenant(self):
        upload = CaminhoArquivoTenant(PROTEGIDO, "documentos")
        tenant_a = SimpleNamespace(escritorio=SimpleNamespace(schema_name="tenant_a"))
        tenant_b = SimpleNamespace(escritorio=SimpleNamespace(schema_name="tenant_b"))

        caminho_a = upload(tenant_a, "mesmo-nome.pdf")
        caminho_b = upload(tenant_b, "mesmo-nome.pdf")

        self.assertEqual(caminho_a, "tenants/tenant_a/protegido/documentos/mesmo-nome.pdf")
        self.assertEqual(caminho_b, "tenants/tenant_b/protegido/documentos/mesmo-nome.pdf")
        self.assertNotEqual(caminho_a, caminho_b)

    def test_descarta_diretorios_informados_no_nome_do_upload(self):
        upload = CaminhoArquivoTenant(PUBLICO, "identidade-visual/logos")
        instance = SimpleNamespace(escritorio=SimpleNamespace(schema_name="tenant_a"))

        caminho = upload(instance, "origem/externa/marca.png")

        self.assertEqual(
            caminho,
            "tenants/tenant_a/publico/identidade-visual/logos/marca.png",
        )

    def test_rejeita_namespace_desconhecido(self):
        with self.assertRaises(ValueError):
            CaminhoArquivoTenant("compartilhado", "documentos")

    def test_rejeita_upload_sem_tenant_resolvido(self):
        upload = CaminhoArquivoTenant(PROTEGIDO, "documentos")

        with self.assertRaises(ValueError):
            upload(SimpleNamespace(), "arquivo.pdf")

    def test_storage_publico_expoe_somente_rota_tenant_aware(self):
        storage = StorageIdentidadeVisual("logo")

        self.assertEqual(storage.url("qualquer/caminho.png"), "/identidade-visual/logo/")


@override_settings(DEBUG=True)
class TestIdentidadeVisualTenantAware(MediaRootIsolado, TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi_storage_publico"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Escritório Storage"
        tenant.slug = "escritorio-storage"

    def setUp(self):
        super().setUp()
        self.configuracao = ConfiguracaoVisual.objects.create(escritorio=self.tenant)
        self.assertEqual(Path(self.configuracao.logo.storage.location), Path(_MEDIA_TMP))

    def _salvar_arquivo(self, campo, nome, conteudo):
        arquivo = getattr(self.configuracao, campo)
        arquivo.save(nome, ContentFile(conteudo), save=True)
        self.configuracao.refresh_from_db()
        return getattr(self.configuracao, campo)

    def _conteudo(self, response):
        return b"".join(response.streaming_content)

    def test_upload_publico_usa_namespace_do_tenant(self):
        logo = self._salvar_arquivo("logo", "marca.png", b"logo-tenant")

        self.assertEqual(
            str(PurePosixPath(logo.name).parent),
            "tenants/wi_storage_publico/publico/identidade-visual/logos",
        )
        self.assertEqual(PurePosixPath(logo.name).suffix, ".png")

    def test_rota_publica_entrega_arquivo_do_tenant_resolvido(self):
        self._salvar_arquivo("logo", "marca.png", b"logo-tenant")

        response = self.client.get(
            "/identidade-visual/logo/",
            HTTP_HOST=self.domain.domain,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._conteudo(response), b"logo-tenant")
        self.assertEqual(response.headers["Content-Type"], "image/png")

    def test_arquivo_legado_continua_disponivel_pela_rota_tenant_aware(self):
        storage = StorageIdentidadeVisual("logo")
        storage.save("logos/marca-legada.png", ContentFile(b"logo-legado"))
        self.configuracao.logo = "logos/marca-legada.png"
        self.configuracao.save(update_fields=["logo"])

        response = self.client.get(
            "/identidade-visual/logo/",
            HTTP_HOST=self.domain.domain,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._conteudo(response), b"logo-legado")

    def test_tipo_ausente_ou_desconhecido_retorna_404(self):
        sem_arquivo = self.client.get(
            "/identidade-visual/favicon/",
            HTTP_HOST=self.domain.domain,
        )
        desconhecido = self.client.get(
            "/identidade-visual/arquivo-qualquer/",
            HTTP_HOST=self.domain.domain,
        )

        self.assertEqual(sem_arquivo.status_code, 404)
        self.assertEqual(desconhecido.status_code, 404)

    def test_arquivo_ausente_no_storage_retorna_404(self):
        self.configuracao.logo = "logos/arquivo-ausente.png"
        self.configuracao.save(update_fields=["logo"])

        response = self.client.get(
            "/identidade-visual/logo/",
            HTTP_HOST=self.domain.domain,
        )

        self.assertEqual(response.status_code, 404)

    def test_media_url_nao_serve_arquivo_diretamente_em_debug(self):
        logo = self._salvar_arquivo("logo", "marca.png", b"logo-tenant")

        response = self.client.get(
            f"/media/{logo.name}",
            HTTP_HOST=self.domain.domain,
        )

        self.assertEqual(response.status_code, 404)

    def test_login_usa_urls_publicas_da_identidade_visual(self):
        self._salvar_arquivo("logo", "marca.png", b"logo-tenant")
        self._salvar_arquivo("favicon", "favicon.png", b"favicon-tenant")
        self._salvar_arquivo("imagem_fundo_login", "fundo.png", b"fundo-tenant")

        response = self.client.get("/login/", HTTP_HOST=self.domain.domain)

        self.assertContains(response, "/identidade-visual/logo/")
        self.assertContains(response, "/identidade-visual/favicon/")
        self.assertContains(response, "/identidade-visual/fundo-login/")


@override_settings(DEBUG=True)
class TestIdentidadeVisualIsolamentoMultiTenant(MediaRootIsolado, TenantTestCase):
    @classmethod
    def _fixture_setup(cls):
        return TransactionTestCase._fixture_setup.__func__(cls)

    def _fixture_teardown(self):
        return TransactionTestCase._fixture_teardown(self)

    @classmethod
    def get_test_schema_name(cls):
        return "wi_storage_iso_a"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Storage A"
        tenant.slug = "storage-a"

    def test_dominios_com_mesmo_nome_de_arquivo_recebem_conteudo_do_proprio_tenant(self):
        config_a = ConfiguracaoVisual.objects.create(escritorio=self.tenant)
        config_a.logo.save("marca.png", ContentFile(b"logo-a"), save=True)

        tenant_b = Escritorio(
            schema_name="wi_storage_iso_b",
            nome="Storage B",
            slug="storage-b",
        )
        with schema_context("public"):
            tenant_b.save()
            dominio_b = Dominio.objects.create(
                tenant=tenant_b,
                domain="storage-b.test.com",
                is_primary=True,
            )
            config_b = ConfiguracaoVisual.objects.create(escritorio=tenant_b)
            config_b.logo.save("marca.png", ContentFile(b"logo-b"), save=True)

        try:
            response_a = self.client.get(
                "/identidade-visual/logo/",
                HTTP_HOST=self.domain.domain,
            )
            response_b = self.client.get(
                "/identidade-visual/logo/",
                HTTP_HOST=dominio_b.domain,
            )

            self.assertEqual(b"".join(response_a.streaming_content), b"logo-a")
            self.assertEqual(b"".join(response_b.streaming_content), b"logo-b")
            self.assertNotEqual(config_a.logo.name, config_b.logo.name)
        finally:
            with schema_context("public"):
                tenant_b.delete(force_drop=True)
            connection.set_tenant(self.tenant)
