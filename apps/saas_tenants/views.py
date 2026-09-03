import mimetypes

from django.core.exceptions import ObjectDoesNotExist
from django.http import FileResponse, Http404


_CAMPOS_IDENTIDADE_VISUAL = {
    "logo": "logo",
    "favicon": "favicon",
    "fundo-login": "imagem_fundo_login",
}


def arquivo_identidade_visual(request, tipo_arquivo):
    campo = _CAMPOS_IDENTIDADE_VISUAL.get(tipo_arquivo)
    if campo is None:
        raise Http404

    tenant = getattr(request, "tenant", None)
    try:
        configuracao = tenant.configuracao_visual
    except (AttributeError, ObjectDoesNotExist):
        raise Http404

    arquivo = getattr(configuracao, campo)
    if not arquivo:
        raise Http404

    content_type, _ = mimetypes.guess_type(arquivo.name)
    try:
        arquivo_aberto = arquivo.open("rb")
    except (FileNotFoundError, OSError):
        raise Http404

    return FileResponse(
        arquivo_aberto,
        content_type=content_type or "application/octet-stream",
        filename=arquivo.name.rsplit("/", 1)[-1],
    )
