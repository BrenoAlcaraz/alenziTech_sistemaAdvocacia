from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db.models import F, Max, Q
from django.http import Http404
from apps.saas_tenants.storage import resposta_de_arquivo
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from apps.accounts.permissoes import tem_permissao_modulo
from apps.accounts.permissoes_constants import MODULO_CHAT
from apps.notificacoes.models import Notificacao

from .forms import NovaConversaGrupoForm, NovaConversaIndividualForm
from .mencoes import usernames_mencionados
from .models import Conversa, Mensagem
from .realtime import grupo_conversa, grupo_global, grupo_lista, grupo_usuario

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


def _mencionaveis(conversa, usuario):
    """Quem pode ser chamado com @ nesta conversa: os participantes; na
    sala global (sem lista), qualquer usuário ativo."""
    if conversa.tipo == Conversa.TIPO_GLOBAL:
        return _usuarios_disponiveis(usuario)
    return conversa.participantes.filter(is_active=True).exclude(pk=usuario.pk).order_by(
        "first_name", "username"
    )


def _notificar_nova_mensagem(mensagem):
    """Notifica cada participante da conversa, exceto o autor — quem foi
    chamado com @ recebe o aviso de menção no lugar do genérico. Sala
    global só notifica quem foi mencionado (compartilhada por todo o
    tenant, notificar tudo tornaria a notificação inútil)."""
    conversa = mensagem.conversa
    autor_nome = mensagem.autor.get_full_name() or f"@{mensagem.autor.username}"
    titulo = conversa.nome_para(mensagem.autor)

    mencionados = usernames_mencionados(mensagem.conteudo)
    destinatarios_mencao = {
        u.pk: u for u in _mencionaveis(conversa, mensagem.autor)
        if u.username.lower() in mencionados and tem_permissao_modulo(u, MODULO_CHAT)
    }
    for destinatario in destinatarios_mencao.values():
        Notificacao.objects.create(
            destinatario=destinatario,
            mensagem=f'{autor_nome} chamou você em "{titulo}"',
        )

    if conversa.tipo == Conversa.TIPO_GLOBAL:
        return
    if conversa.tipo == Conversa.TIPO_GRUPO:
        texto = f'Nova mensagem de {autor_nome} em "{titulo}"'
    else:
        texto = f"Nova mensagem de {autor_nome}"
    for destinatario in conversa.participantes.exclude(pk=mensagem.autor_id):
        if destinatario.pk in destinatarios_mencao:
            continue
        Notificacao.objects.create(destinatario=destinatario, mensagem=texto)


def _transmitir_mensagem_tempo_real(request, conversa, mensagem):
    """Publica a mensagem nova pelo channel layer para quem está com esta
    conversa aberta, mais um aviso de não lida para quem está na lista
    (`chat:lista`). Indisponibilidade do channel layer nunca interrompe o
    fluxo HTTP: só a atualização em tempo real fica de fora, o envio por
    HTTP já terminou antes desta chamada."""
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    enviar = async_to_sync(channel_layer.group_send)
    tenant = request.tenant

    if conversa.tipo == Conversa.TIPO_GLOBAL:
        enviar(grupo_global(tenant), {"type": "chat.mensagem", "mensagem_id": mensagem.pk})
        enviar(grupo_lista(tenant), {"type": "chat.nao_lida", "conversa_id": "global"})
    else:
        enviar(grupo_conversa(tenant, conversa.pk), {"type": "chat.mensagem", "mensagem_id": mensagem.pk})
        for participante_id in conversa.participantes.exclude(pk=mensagem.autor_id).values_list(
            "pk", flat=True
        ):
            enviar(
                grupo_usuario(tenant, participante_id),
                {"type": "chat.nao_lida", "conversa_id": str(conversa.pk)},
            )


def _visualizar_conversa(
    request, conversa, *, titulo, subtitulo, avatar_letra, post_url, voltar_url, ws_url,
    editar_url=None, avatar_usuario=None,
):
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
            _transmitir_mensagem_tempo_real(request, conversa, mensagem)
            return redirect(post_url)

    mensagens = list(
        conversa.mensagens
        .select_related("autor", "autor__perfil")
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
            "avatar_usuario": avatar_usuario,
            "mensagens": mensagens,
            "erro": erro,
            "conteudo_digitado": conteudo_digitado,
            "post_url": post_url,
            "voltar_url": voltar_url,
            "ws_url": ws_url,
            "editar_url": editar_url,
            "mencionaveis": [
                {"username": u.username, "nome": u.get_full_name()}
                for u in _mencionaveis(conversa, request.user)
            ],
            "item_ativo": "chat",
        },
    )


@login_required
def lista(request):
    if not tem_permissao_modulo(request.user, MODULO_CHAT):
        raise PermissionDenied

    sala_global = _sala_global()
    sala_global.tem_nao_lida = sala_global.tem_mensagem_nao_lida_para(request.user)

    conversas = list(
        _conversas_do_usuario(request.user).prefetch_related("participantes", "participantes__perfil")
    )
    for conversa in conversas:
        conversa.nome_exibicao = conversa.nome_para(request.user)
        conversa.outro = conversa.outro_participante(request.user)
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
        avatar_usuario = outro
        subtitulo = "Conversa individual"
    else:
        avatar_letra = None
        avatar_usuario = None
        subtitulo = "Grupo"

    # Grupo de equipe é gerido pela própria equipe (nome e membros).
    editavel = conversa.tipo == Conversa.TIPO_GRUPO and conversa.equipe_id is None
    return _visualizar_conversa(
        request,
        conversa,
        titulo=conversa.nome_para(request.user),
        subtitulo=subtitulo,
        avatar_letra=avatar_letra,
        avatar_usuario=avatar_usuario,
        post_url=reverse("chat:detalhe", args=[conversa.pk]),
        voltar_url=reverse("chat:lista"),
        ws_url=f"/ws/chat/{conversa.pk}/",
        editar_url=reverse("chat:editar_grupo", args=[conversa.pk]) if editavel else None,
    )


@login_required
def editar_grupo(request, pk):
    """Altera nome e integrantes de um grupo avulso de que o usuário
    participa. Grupo de equipe não é editável aqui — nome e membros vêm
    da Equipe. Quem edita sempre continua no grupo."""
    if not tem_permissao_modulo(request.user, MODULO_CHAT):
        raise PermissionDenied

    conversa = get_object_or_404(
        Conversa.objects.filter(
            participantes=request.user, tipo=Conversa.TIPO_GRUPO, equipe__isnull=True,
        ),
        pk=pk,
    )
    usuarios_qs = _usuarios_disponiveis(request.user)
    atuais = conversa.participantes.exclude(pk=request.user.pk)

    if request.method == "POST":
        form = NovaConversaGrupoForm(request.POST, usuarios_queryset=usuarios_qs)
        if form.is_valid():
            novos = form.cleaned_data["participantes"]
            adicionados = [u for u in novos if not atuais.filter(pk=u.pk).exists()]
            conversa.titulo = form.cleaned_data["titulo"]
            conversa.save(update_fields=["titulo"])
            conversa.participantes.set([*novos, request.user])
            nome = request.user.get_full_name() or f"@{request.user.username}"
            for usuario in adicionados:
                Notificacao.objects.create(
                    destinatario=usuario,
                    mensagem=f'{nome} adicionou você ao grupo "{conversa.titulo}"',
                )
            return redirect("chat:detalhe", pk=conversa.pk)
    else:
        form = NovaConversaGrupoForm(
            usuarios_queryset=usuarios_qs,
            initial={"titulo": conversa.titulo, "participantes": list(atuais.values_list("pk", flat=True))},
        )

    return render(
        request,
        "chat/nova_grupo.html",
        {"form": form, "conversa": conversa, "modo": "editar", "item_ativo": "chat"},
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
        ws_url="/ws/chat/global/",
    )


@login_required
def anexo_mensagem(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_CHAT):
        raise PermissionDenied

    mensagem = get_object_or_404(_mensagens_visiveis_para(request.user), pk=pk)
    if not mensagem.anexo:
        raise Http404

    return resposta_de_arquivo(request, mensagem.anexo, mensagem.nome_do_anexo())


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
