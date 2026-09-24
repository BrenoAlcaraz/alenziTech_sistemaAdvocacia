from .cores import tema

# Palavras que não entram nas iniciais: "Silva & Souza Advogados" → "SS".
_FORA_DAS_INICIAIS = {"de", "da", "do", "das", "dos", "e", "&", "advogados", "advocacia"}


def iniciais(nome):
    """Até duas iniciais do nome do escritório, para o logo padrão."""
    palavras = [p for p in nome.split() if p.lower() not in _FORA_DAS_INICIAIS]
    if not palavras:
        palavras = nome.split()
    return "".join(p[0] for p in palavras[:2]).upper()


def tenant_config(request):
    """
    Injeta dados do tenant atual e sua configuração visual em todos os templates.
    Permite que sidebar, header e login exibam nome, logo e cores do escritório.
    """
    tenant = getattr(request, "tenant", None)
    config = None

    if tenant:
        try:
            config = tenant.configuracao_visual
        except Exception:
            config = None

    nome_escritorio = getattr(config, "nome_exibicao", "") or getattr(tenant, "nome", "")

    return {
        "tenant": tenant,
        "config_visual": config,
        "nome_escritorio": nome_escritorio,
        "iniciais_escritorio": iniciais(nome_escritorio),
        "tema": tema(
            getattr(config, "cor_primaria", ""), getattr(config, "cor_secundaria", ""),
        ),
    }
