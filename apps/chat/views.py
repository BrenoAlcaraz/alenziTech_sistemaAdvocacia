from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.chat.models import Conversa, Mensagem


@login_required
def lista(request):
    return redirect("chat:global")


@login_required
def detalhe(request, pk):
    return redirect("chat:global")


@login_required
@require_http_methods(["GET", "POST"])
def global_sala(request):
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
