from pathlib import PurePosixPath

from django.core.files.storage import FileSystemStorage
from django.db import connection
from django.urls import reverse
from django.utils.deconstruct import deconstructible


PUBLICO = "publico"
PROTEGIDO = "protegido"
_NAMESPACES_VALIDOS = {PUBLICO, PROTEGIDO}


def _schema_name_do_tenant(instance):
    escritorio = getattr(instance, "escritorio", None)
    schema_name = getattr(escritorio, "schema_name", None)
    if not schema_name:
        schema_name = getattr(connection, "schema_name", None)
    if not schema_name or schema_name == "public":
        raise ValueError("Um tenant resolvido é obrigatório para armazenar arquivos.")
    return schema_name


@deconstructible
class CaminhoArquivoTenant:
    """Gera nomes segregados; a política de entrega pertence ao storage/view."""

    def __init__(self, namespace, diretorio):
        if namespace not in _NAMESPACES_VALIDOS:
            raise ValueError(f"Namespace de arquivo inválido: {namespace}")
        self.namespace = namespace
        self.diretorio = diretorio.strip("/")

    def __call__(self, instance, filename):
        nome = PurePosixPath(filename.replace("\\", "/")).name
        if not nome:
            raise ValueError("O arquivo precisa ter um nome.")
        return str(PurePosixPath(
            "tenants",
            _schema_name_do_tenant(instance),
            self.namespace,
            self.diretorio,
            nome,
        ))


@deconstructible
class StorageProtegido(FileSystemStorage):
    """Armazena arquivos sem oferecer uma URL pública direta."""

    def url(self, name):
        return None


@deconstructible
class StorageIdentidadeVisual(FileSystemStorage):
    """Expõe somente a rota que resolve o ativo pelo tenant da requisição."""

    def __init__(self, tipo_arquivo):
        self.tipo_arquivo = tipo_arquivo
        super().__init__()

    def url(self, name):
        return reverse(
            "saas_tenants:arquivo_identidade_visual",
            kwargs={"tipo_arquivo": self.tipo_arquivo},
        )
