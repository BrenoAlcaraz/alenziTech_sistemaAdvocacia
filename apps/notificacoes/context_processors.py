from .models import Notificacao


def notificacoes(request):
    """Expõe as notificações não lidas do usuário logado para o header (todo template)."""
    if not request.user.is_authenticated:
        return {}
    try:
        nao_lidas = Notificacao.objects.filter(destinatario=request.user, lida=False)
        return {
            "notificacoes_nao_lidas": nao_lidas[:10],
            "notificacoes_total_nao_lidas": nao_lidas.count(),
        }
    except Exception:
        return {}
