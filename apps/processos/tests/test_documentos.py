"""
Testes de gestão de documentos do processo (specs/documentos-processo.md).

Cobre autorização de módulo, as duas habilitações granulares novas
(`processos_documento_adicionar`/`processos_documento_excluir`), o
escopo de mutação (Administrador ou responsável do processo — mesmo
QuerySet de `editar`/`adicionar_movimentacao`), o escopo de leitura no
download (mesmo QuerySet de `detalhe`, 404 fora do escopo) e a exclusão
em cascata ao excluir o Processo.

Reaproveita o padrão de fixture de
apps/processos/tests/test_autorizacao.py e o padrão de upload com
MEDIA_ROOT temporário de apps/chat/tests/test_anexos.py.
"""

import os
import shutil
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import (
    HabilitacaoPapel,
    PapelAcesso,
    PerfilUsuario,
    PermissaoPapel,
    UsuarioPapel,
)
from apps.accounts.permissoes_constants import (
    HAB_PROCESSOS_DOCUMENTO_ADICIONAR,
    HAB_PROCESSOS_DOCUMENTO_EXCLUIR,
    MODULO_PROCESSOS,
    NIVEL_TODOS,
)
from apps.clientes.models import Cliente
from apps.processos.models import Documento, Processo

_MEDIA_TMP = tempfile.mkdtemp(prefix="lawsystem_test_media_")


def _arquivo(nome="peticao.pdf", conteudo=b"conteudo-teste"):
    return SimpleUploadedFile(nome, conteudo, content_type="application/pdf")


@override_settings(MEDIA_ROOT=_MEDIA_TMP)
class DocumentosBase(TenantTestCase):
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

    def _set_admin_flag(self, user, value=True):
        PerfilUsuario.objects.filter(user=user).update(is_admin_escritorio=value)

    def _new_papel(self, nome, *, ativo=True):
        return PapelAcesso.objects.create(nome=nome, ativo=ativo)

    def _assign_papel(self, user, papel, *, ativo=True):
        return UsuarioPapel.objects.create(usuario=user, papel=papel, ativo=ativo)

    def _pp(self, papel, modulo, *, ativo=True, nivel=NIVEL_TODOS):
        return PermissaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=modulo, ativo=ativo, nivel=nivel
        )

    def _hp(self, papel, modulo, item, *, ativo=True):
        return HabilitacaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=modulo, item=item, ativo=ativo
        )

    def _dar_modulo_processos(self, user):
        papel = self._new_papel(f"Papel Processos {user.username}")
        self._assign_papel(user, papel)
        self._pp(papel, MODULO_PROCESSOS)
        return papel

    def _cliente(self, *, responsavel, **kwargs):
        defaults = {"nome_razao_social": "Cliente Teste Documentos", "tipo": "PF"}
        defaults.update(kwargs)
        return Cliente.objects.create(responsavel=responsavel, **defaults)

    def _processo(self, *, responsavel, cliente=None, **kwargs):
        defaults = {"titulo": "Processo Teste Documentos"}
        defaults.update(kwargs)
        return Processo.objects.create(responsavel=responsavel, cliente=cliente, **defaults)

    def _documento(self, processo, *, autor=None, conteudo=b"conteudo-teste"):
        return Documento.objects.create(
            processo=processo, arquivo=_arquivo(conteudo=conteudo), autor=autor
        )


class TestDocumentoModuloNegado(DocumentosBase):
    @classmethod
    def get_test_schema_name(cls):
        return "documentos_modulo_negado"

    def setUp(self):
        super().setUp()
        self.user = self._user("sem_modulo_processos")
        self.client.force_login(self.user)
        self.cliente = self._cliente(responsavel=self.user)
        self.processo = self._processo(responsavel=self.user, cliente=self.cliente)
        self.documento = self._documento(self.processo, autor=self.user)

    def test_adicionar_negado(self):
        r = self.client.post(
            f"/processos/{self.processo.pk}/documentos/nova/",
            {"arquivo": _arquivo(), "tipo": "peticao"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 403)

    def test_excluir_negado(self):
        r = self.client.post(
            f"/processos/{self.processo.pk}/documentos/{self.documento.pk}/excluir/",
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 403)
        self.assertTrue(Documento.objects.filter(pk=self.documento.pk).exists())

    def test_baixar_negado(self):
        r = self.client.get(
            f"/processos/documentos/{self.documento.pk}/baixar/",
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 403)


class TestDocumentoHabilitacaoAusente(DocumentosBase):
    """Módulo processos autorizado, mas sem as habilitações granulares
    de documento — módulo aberto não equivale a poder anexar/excluir."""

    @classmethod
    def get_test_schema_name(cls):
        return "documentos_sem_habilitacao"

    def setUp(self):
        super().setUp()
        self.user = self._user("modulo_sem_habilitacao_documento")
        self._dar_modulo_processos(self.user)
        self.client.force_login(self.user)
        self.cliente = self._cliente(responsavel=self.user)
        self.processo = self._processo(responsavel=self.user, cliente=self.cliente)
        self.documento = self._documento(self.processo, autor=self.user)

    def test_adicionar_negado_nao_cria(self):
        antes = self.processo.documentos.count()
        r = self.client.post(
            f"/processos/{self.processo.pk}/documentos/nova/",
            {"arquivo": _arquivo(), "tipo": "peticao"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.processo.documentos.count(), antes)

    def test_excluir_negado_nao_apaga(self):
        r = self.client.post(
            f"/processos/{self.processo.pk}/documentos/{self.documento.pk}/excluir/",
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 403)
        self.assertTrue(Documento.objects.filter(pk=self.documento.pk).exists())

    def test_download_continua_permitido_so_com_modulo(self):
        # Baixar é leitura (mesmo escopo do detalhe do processo) — não
        # depende das habilitações de adicionar/excluir.
        r = self.client.get(
            f"/processos/documentos/{self.documento.pk}/baixar/",
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 200)


class TestDocumentoMutacaoEscopo(DocumentosBase):
    """Usuário com as duas habilitações concedidas, mas o processo é
    alheio (não é responsável nem Administrador) — mutação usa o mesmo
    QuerySet de `_processos_mutaveis`, então cai fora do escopo (404)."""

    @classmethod
    def get_test_schema_name(cls):
        return "documentos_mutacao_alheia"

    def setUp(self):
        super().setUp()
        self.user = self._user("com_habilitacao_documento")
        self.outro = self._user("responsavel_alheio_documento")
        papel = self._dar_modulo_processos(self.user)
        self._hp(papel, MODULO_PROCESSOS, HAB_PROCESSOS_DOCUMENTO_ADICIONAR)
        self._hp(papel, MODULO_PROCESSOS, HAB_PROCESSOS_DOCUMENTO_EXCLUIR)
        self.client.force_login(self.user)
        self.cliente = self._cliente(responsavel=self.outro)
        self.processo = self._processo(responsavel=self.outro, cliente=self.cliente)
        self.documento = self._documento(self.processo, autor=self.outro)

    def test_adicionar_em_processo_alheio_retorna_404_e_nao_cria(self):
        antes = self.processo.documentos.count()
        r = self.client.post(
            f"/processos/{self.processo.pk}/documentos/nova/",
            {"arquivo": _arquivo(), "tipo": "peticao"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 404)
        self.assertEqual(self.processo.documentos.count(), antes)

    def test_excluir_em_processo_alheio_retorna_404_e_preserva(self):
        r = self.client.post(
            f"/processos/{self.processo.pk}/documentos/{self.documento.pk}/excluir/",
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 404)
        self.assertTrue(Documento.objects.filter(pk=self.documento.pk).exists())


class TestDocumentoFluxoAutorizadoCompleto(DocumentosBase):
    """Usuário responsável pelo processo, com as duas habilitações —
    caminho autorizado completo de adicionar/excluir."""

    @classmethod
    def get_test_schema_name(cls):
        return "documentos_fluxo_completo"

    def setUp(self):
        super().setUp()
        self.user = self._user("responsavel_com_habilitacoes")
        papel = self._dar_modulo_processos(self.user)
        self._hp(papel, MODULO_PROCESSOS, HAB_PROCESSOS_DOCUMENTO_ADICIONAR)
        self._hp(papel, MODULO_PROCESSOS, HAB_PROCESSOS_DOCUMENTO_EXCLUIR)
        self.client.force_login(self.user)
        self.cliente = self._cliente(responsavel=self.user)
        self.processo = self._processo(responsavel=self.user, cliente=self.cliente)

    def test_adicionar_cria_documento_com_autor_e_tipo(self):
        r = self.client.post(
            f"/processos/{self.processo.pk}/documentos/nova/",
            {"arquivo": _arquivo(), "tipo": "procuracao", "descricao": "Procuração ad judicia"},
            HTTP_HOST=self.http_host,
        )
        self.assertRedirects(
            r,
            f"/processos/{self.processo.pk}/?aba=documentos",
            fetch_redirect_response=False,
        )
        documento = Documento.objects.get(processo=self.processo)
        self.assertEqual(documento.autor, self.user)
        self.assertEqual(documento.tipo, "procuracao")
        self.assertTrue(
            documento.arquivo.name.startswith(
                "tenants/documentos_fluxo_completo/protegido/processos/documentos/"
            )
        )
        self.assertIsNone(documento.arquivo.url)

    def test_excluir_remove_documento(self):
        documento = self._documento(self.processo, autor=self.user)
        caminho_arquivo = documento.arquivo.path
        self.assertTrue(os.path.exists(caminho_arquivo))
        r = self.client.post(
            f"/processos/{self.processo.pk}/documentos/{documento.pk}/excluir/",
            HTTP_HOST=self.http_host,
        )
        self.assertRedirects(
            r,
            f"/processos/{self.processo.pk}/?aba=documentos",
            fetch_redirect_response=False,
        )
        self.assertFalse(Documento.objects.filter(pk=documento.pk).exists())
        self.assertFalse(os.path.exists(caminho_arquivo))

    def test_detalhe_lista_documentos_e_mostra_acoes(self):
        self._documento(self.processo, autor=self.user)
        r = self.client.get(
            f"/processos/{self.processo.pk}/?aba=documentos", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["documentos_total"], 1)
        self.assertTrue(r.context["pode_adicionar_documento"])
        self.assertTrue(r.context["pode_excluir_documento"])
        self.assertIn("+ Adicionar documento", r.content.decode())


class TestDocumentoAdministrador(DocumentosBase):
    """Administrador do escritório sempre pode anexar/excluir,
    independente das duas habilitações granulares e independente de ser
    o responsável do processo — mesmo padrão de `editar`/`arquivar`."""

    @classmethod
    def get_test_schema_name(cls):
        return "documentos_admin"

    def setUp(self):
        super().setUp()
        self.admin = self._user("admin_documentos")
        self._set_admin_flag(self.admin)
        self.outro = self._user("responsavel_processo_admin")
        self.client.force_login(self.admin)
        self.cliente = self._cliente(responsavel=self.outro)
        self.processo = self._processo(responsavel=self.outro, cliente=self.cliente)

    def test_admin_adiciona_documento_em_processo_alheio(self):
        r = self.client.post(
            f"/processos/{self.processo.pk}/documentos/nova/",
            {"arquivo": _arquivo(), "tipo": "outro"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.processo.documentos.count(), 1)

    def test_admin_exclui_documento_em_processo_alheio(self):
        documento = self._documento(self.processo, autor=self.outro)
        r = self.client.post(
            f"/processos/{self.processo.pk}/documentos/{documento.pk}/excluir/",
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        self.assertFalse(Documento.objects.filter(pk=documento.pk).exists())


class TestDocumentoDownloadEscopoDeLeitura(DocumentosBase):
    """Download segue o mesmo escopo de leitura do detalhe do processo
    (somente_seus/todos) — usuário fora do escopo recebe 404, mesmo
    conhecendo o identificador do documento."""

    @classmethod
    def get_test_schema_name(cls):
        return "documentos_download_escopo"

    def setUp(self):
        super().setUp()
        self.dono = self._user("dono_do_processo")
        self.estranho = self._user("estranho_ao_processo")
        from apps.accounts.permissoes_constants import NIVEL_SOMENTE_SEUS
        papel_estranho = self._new_papel("Papel Estranho")
        self._assign_papel(self.estranho, papel_estranho)
        self._pp(papel_estranho, MODULO_PROCESSOS, nivel=NIVEL_SOMENTE_SEUS)
        self.cliente = self._cliente(responsavel=self.dono)
        self.processo = self._processo(responsavel=self.dono, cliente=self.cliente)
        self.documento = self._documento(
            self.processo, autor=self.dono, conteudo=b"conteudo-confidencial"
        )

    def test_estranho_recebe_404_ao_baixar(self):
        self.client.force_login(self.estranho)
        r = self.client.get(
            f"/processos/documentos/{self.documento.pk}/baixar/",
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 404)

    def test_dono_baixa_o_conteudo_correto(self):
        self._dar_modulo_processos(self.dono)
        self.client.force_login(self.dono)
        r = self.client.get(
            f"/processos/documentos/{self.documento.pk}/baixar/",
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(b"".join(r.streaming_content), b"conteudo-confidencial")

    def test_anonimo_e_redirecionado_ao_login(self):
        self.client.logout()
        r = self.client.get(
            f"/processos/documentos/{self.documento.pk}/baixar/",
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login/", r.url)


class TestDocumentoExclusaoEmCascata(DocumentosBase):
    """Excluir o Processo remove também seus documentos (on_delete=CASCADE),
    sem deixar registro órfão no banco nem arquivo órfão no storage —
    o signal post_delete (apps/processos/signals.py) cobre a cascata,
    não só a exclusão direta pela view."""

    @classmethod
    def get_test_schema_name(cls):
        return "documentos_cascata"

    def test_excluir_processo_remove_documentos_e_arquivos(self):
        dono = self._user("dono_cascata")
        cliente = self._cliente(responsavel=dono)
        processo = self._processo(responsavel=dono, cliente=cliente)
        documento = self._documento(processo, autor=dono)
        caminho_arquivo = documento.arquivo.path
        self.assertTrue(os.path.exists(caminho_arquivo))

        processo.delete()

        self.assertFalse(Documento.objects.filter(pk=documento.pk).exists())
        self.assertFalse(os.path.exists(caminho_arquivo))
