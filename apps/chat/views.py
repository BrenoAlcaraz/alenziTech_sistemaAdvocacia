from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db.models import F, Max, Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from apps.accounts.permissoes import tem_permissao_modulo
from apps.accounts.permissoes_constants import MODULO_CHAT
from apps.notificacoes.models import Notificacao

from .forms import NovaConversaGrupoForm, NovaConversaIndividualForm
from .models import Conversa, Mensagem

TAMANHO_MAXIMO_ANEXO_BYTES = 10 * 1024 * 1024  # 10 MB — mesmo limite de apps/modelos/forms.py


def _usuarios_disponiveis(user):
    """Universo de usuários que podem ser convidados para uma conversa
    individual/grupo — mesmo padrão de
    `apps/agenda/views.py::_usuarios_elegiveis_para_participante`."""
    return (
        User.objects.filter(is_active=True)
        .exclude(pk=user.pk)
        .order_by("first_name", "username")
    )


def _sala_global():
    sala, _ = Conversa.objects.get_or_create(
        tipo=Conversa.TIPO_GLOBAL,
        defaults={"titulo": "Sala Geral"},
    )
    return sala


def _conversas_do_usuario(user):
    """Conversas individuais/grupo de que `user` participa, mais recente
    primeiro (pela última mensagem; sem mensagem ainda, pela criação)."""
    return (
        Conversa.objects.filter(participantes=user)
        .exclude(tipo=Conversa.TIPO_GLOBAL)
        .annotate(ultima_mensagem_em=Max("mensagens__enviada_em"))
        .order_by(F("ultima_mensagem_em").desc(nulls_last=True), "-criada_em")
    )


def _mensagens_visiveis_para(usuario):
    """Mensagens de conversas em que `usuario` participa, mais as da
    sala global (aberta a todo o módulo, sem lista de participantes) —
    mesmo padrão de escopo de
    `apps/financeiro/views.py::_solicitacoes_no_escopo`."""
    return Mensagem.objects.filter(
        Q(conversa__tipo=Conversa.TIPO_GLOBAL) | Q(conversa__participantes=usuario)
    )


def _notificar_nova_mensagem(mensagem):
    """Notifica cada participante da conversa, exceto o autor — sala
    global não notifica (compartilhada por todo o tenant, volume alto
    tornaria a notificação inútil)."""
    conversa = mensagem.conversa
    if conversa.tipo == Conversa.TIPO_GLOBAL:
        return
    autor_nome = mensagem.autor.get_full_name() or f"@{mensagem.autor.username}"
    if conversa.tipo == Conversa.TIPO_GRUPO:
        texto = f'Nova mensagem de {autor_nome} em "{conversa.nome_para(mensagem.autor)}"'
    else:
        texto = f"Nova mensagem de {autor_nome}"
    for destinatario in conversa.participantes.exclude(pk=mensagem.autor_id):
        Notificacao.objects.create(destinatario=destinatario, mensagem=texto)


def _visualizar_conversa(request, conversa, *, titulo, subtitulo, avatar_letra, post_url, voltar_url):
    """Lista mensagens e processa envio — reaproveitado pela sala global
    e pela conversa individual/grupo (mesmo fluxo POST + redirect)."""
    erro = None
    conteudo_digitado = ""

    if request.method == "POST":
        conteudo_digitado = request.POST.get("conteudo", "")
        conteudo = conteudo_digitado.strip()
        anexo = request.FILES.get("anexo")

        if not conteudo and not anexo:
            erro = "Digite uma mensagem ou anexe um arquivo antes de enviar."
        elif anexo and anexo.size > TAMANHO_MAXIMO_ANEXO_BYTES:
            erro = "O arquivo deve ter no máximo 10 MB."
        else:
            mensagem = Mensagem.objects.create(
                conversa=conversa,
                autor=request.user,
                conteudo=conteudo,
                anexo=anexo or "",
            )
            _notificar_nova_mensagem(mensagem)
            return redirect(post_url)

    mensagens = list(
        conversa.mensagens
        .select_related("autor")
        .order_by("-enviada_em", "-pk")[:100]
    )
    mensagens.reverse()

    conversa.marcar_lida_para(request.user)

    return render(
        request,
        "chat/conversa.html",
        {
            "titulo": titulo,
            "subtitulo": subtitulo,
            "avatar_letra": avatar_letra,
            "mensagens": mensagens,
            "erro": erro,
            "conteudo_digitado": conteudo_digitado,
            "post_url": post_url,
            "voltar_url": voltar_url,
            "item_ativo": "chat",
        },
    )


@login_required
def lista(request):
    if not tem_permissao_modulo(request.user, MODULO_CHAT):
        raise PermissionDenied

    sala_global = _sala_global()
    sala_global.tem_nao_lida = sala_global.tem_mensagem_nao_lida_para(request.user)

    conversas = list(_conversas_do_usuario(request.user).prefetch_related("participantes"))
    for conversa in conversas:
        conversa.nome_exibicao = conversa.nome_para(request.user)
        conversa.tem_nao_lida = conversa.tem_mensagem_nao_lida_para(request.user)

    return render(
        request,
        "chat/lista.html",
        {
            "sala_global": sala_global,
            "conversas": conversas,
            "item_ativo": "chat",
        },
    )


@login_required
def detalhe(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_CHAT):
        raise PermissionDenied

    conversa = get_object_or_404(
        Conversa.objects.filter(participantes=request.user).exclude(tipo=Conversa.TIPO_GLOBAL),
        pk=pk,
    )

    if conversa.tipo == Conversa.TIPO_INDIVIDUAL:
        outro = conversa.outro_participante(request.user)
        avatar_letra = outro.username[0].upper() if outro else "?"
        subtitulo = "Conversa individual"
    else:
        avatar_letra = None
        subtitulo = "Grupo"

    return _visualizar_conversa(
        request,
        conversa,
        titulo=conversa.nome_para(request.user),
        subtitulo=subtitulo,
        avatar_letra=avatar_letra,
        post_url=reverse("chat:detalhe", args=[conversa.pk]),
        voltar_url=reverse("chat:lista"),
    )


@login_required
@require_http_methods(["GET", "POST"])
def global_sala(request):
    if not tem_permissao_modulo(request.user, MODULO_CHAT):
        raise PermissionDenied

    return _visualizar_conversa(
        request,
        _sala_global(),
        titulo="Sala Geral",
        subtitulo="Todos do escritório",
        avatar_letra=None,
        post_url=reverse("chat:global"),
        voltar_url=reverse("chat:lista"),
    )


@login_required
def anexo_mensagem(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_CHAT):
        raise PermissionDenied

    mensagem = get_object_or_404(_mensagens_visiveis_para(request.user), pk=pk)
    if not mensagem.anexo:
        raise Http404

    return FileResponse(mensagem.anexo.open("rb"), filename=mensagem.nome_do_anexo())


@login_required
def nova_individual(request):
    if not tem_permissao_modulo(request.user, MODULO_CHAT):
        raise PermissionDenied

    usuarios_qs = _usuarios_disponiveis(request.user)

    if request.method == "POST":
        form = NovaConversaIndividualForm(request.POST, usuarios_queryset=usuarios_qs)
        if form.is_valid():
            outro = form.cleaned_data["usuario"]
            conversa = (
                Conversa.objects.filter(tipo=Conversa.TIPO_INDIVIDUAL)
                .filter(participantes=request.user)
                .filter(participantes=outro)
                .first()
            )
            if conversa is None:
                conversa = Conversa.objects.create(tipo=Conversa.TIPO_INDIVIDUAL)
                conversa.participantes.set([request.user, outro])
            return redirect("chat:detalhe", pk=conversa.pk)
    else:
        form = NovaConversaIndividualForm(usuarios_queryset=usuarios_qs)

    return render(
        request,
        "chat/nova_individual.html",
        {"form": form, "item_ativo": "chat"},
    )


@login_required
def nova_grupo(request):
    if not tem_permissao_modulo(request.user, MODULO_CHAT):
        raise PermissionDenied

    usuarios_qs = _usuarios_disponiveis(request.user)

    if request.method == "POST":
        form = NovaConversaGrupoForm(request.POST, usuarios_queryset=usuarios_qs)
        if form.is_valid():
            conversa = Conversa.objects.create(
                tipo=Conversa.TIPO_GRUPO,
                titulo=form.cleaned_data["titulo"],
            )
            participantes = list(form.cleaned_data["participantes"]) + [request.user]
            conversa.participantes.set(participantes)
            return redirect("chat:detalhe", pk=conversa.pk)
    else:
        form = NovaConversaGrupoForm(usuarios_queryset=usuarios_qs)

    return render(
        request,
        "chat/nova_grupo.html",
        {"form": form, "item_ativo": "chat"},
    )
