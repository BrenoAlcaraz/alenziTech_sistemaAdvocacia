from .cores import tema


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

    return {
        "tenant": tenant,
        "config_visual": config,
        "tema": tema(
            getattr(config, "cor_primaria", ""), getattr(config, "cor_secundaria", ""),
        ),
    }
