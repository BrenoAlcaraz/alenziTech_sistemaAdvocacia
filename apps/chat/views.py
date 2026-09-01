from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.accounts.permissoes import tem_permissao_modulo
from apps.accounts.permissoes_constants import MODULO_CHAT
from apps.chat.models import Conversa, Mensagem


@login_required
def lista(request):
    if not tem_permissao_modulo(request.user, MODULO_CHAT):
        raise PermissionDenied
    return redirect("chat:global")


@login_required
def detalhe(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_CHAT):
        raise PermissionDenied
    return redirect("chat:global")


@login_required
@require_http_methods(["GET", "POST"])
def global_sala(request):
    if not tem_permissao_modulo(request.user, MODULO_CHAT):
        raise PermissionDenied

    sala, _ = Conversa.objects.get_or_create(
        tipo=Conversa.TIPO_GLOBAL,
        defaults={"titulo": "Sala Geral"},
    )

    erro = None
    conteudo_digitado = ""

    if request.method == "POST":
        conteudo_digitado = request.POST.get("conteudo", "")
        conteudo = conteudo_digitado.strip()

        if not conteudo:
            erro = "Digite uma mensagem antes de enviar."
        else:
            Mensagem.objects.create(
                conversa=sala,
                autor=request.user,
                conteudo=conteudo,
            )
            return redirect("chat:global")

    mensagens = list(
        sala.mensagens
        .select_related("autor")
        .order_by("-enviada_em", "-pk")[:100]
    )
    mensagens.reverse()

    return render(
        request,
        "chat/global.html",
        {
            "sala": sala,
            "mensagens": mensagens,
            "erro": erro,
            "conteudo_digitado": conteudo_digitado,
            "item_ativo": "chat",
        },
    )
