from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction

from apps.accounts.decorators import (
    requer_admin_escritorio,
    usuario_admin_escritorio,
)
from apps.accounts.forms import (
    AlterarSenhaForm,
    AtribuirPapelForm,
    CriarUsuarioEscritorioForm,
    EquipeForm,
    MembroEquipeForm,
    PapelAcessoForm,
    PerfilUsuarioForm,
)
from apps.accounts.models import (
    Equipe,
    HabilitacaoPapel,
    HabilitacaoUsuario,
    MembroEquipe,
    PapelAcesso,
    PerfilUsuario,
    PermissaoPapel,
    PermissaoUsuario,
    UsuarioPapel,
)
from apps.accounts.permissoes import nomes_papeis_usuario, tem_habilitacao
from apps.accounts.permissoes_constants import (
    HAB_GERIR_CRIAR_EQUIPE,
    HAB_GERIR_CRIAR_USUARIO,
    HAB_GERIR_HABILITAR_TERCEIROS,
    HAB_GERIR_HABILITAR_USUARIO_PROCESSOS,
    ITENS_POR_MODULO,
    MODULO_GERIR,
    NOMES_ITENS,
)
from apps.atividade.services import registrar_atividade
from apps.clientes.models import Cliente
from apps.processos.models import Processo
from apps.processos.services import (
    AdministradorResponsavelIndisponivel,
    transferir_processos_de_usuarios_sem_acesso,
    usuarios_com_acesso_processos,
)
from apps.saas_tenants.storage import nome_do_arquivo
from apps.saas_tenants.cores import cores_predominantes
from apps.saas_tenants.models import ConfiguracaoVisual
from .models import ConfiguracaoEscritorio
from .forms import ConfiguracaoEscritorioForm, IdentidadeVisualForm


def _obter_configuracao_escritorio():
    configuracao, _ = ConfiguracaoEscritorio.objects.get_or_create(pk=1)
    return configuracao


def _pode_criar_usuario(user):
    return tem_habilitacao(user, MODULO_GERIR, HAB_GERIR_CRIAR_USUARIO)


def _pode_gerenciar_equipes(user):
    return tem_habilitacao(user, MODULO_GERIR, HAB_GERIR_CRIAR_EQUIPE)


def _pode_gerenciar_permissoes(user):
    return tem_habilitacao(user, MODULO_GERIR, HAB_GERIR_HABILITAR_TERCEIROS)


def _pode_habilitar_usuario_processos(user):
    return tem_habilitacao(user, MODULO_GERIR, HAB_GERIR_HABILITAR_USUARIO_PROCESSOS)


@login_required
def index(request):
    perfil_usuario = getattr(request.user, 'perfil', None)

    usuarios = (
        User.objects.filter(is_active=True)
        .select_related("perfil")
        .prefetch_related(
            "atribuicoes_papel__papel",
            "membros_equipe",
            "membros_equipe__equipe",
        )
        .order_by("first_name", "last_name", "username")
    )
    usuarios_ativos = usuarios.count()

    usuarios_contexto = []
    for usuario in usuarios:
        membros_equipe = [
            membro
            for membro in usuario.membros_equipe.all()
            if membro.ativo and membro.equipe.ativo
        ]
        usuarios_contexto.append({
            "usuario": usuario,
            "papel_nome": nomes_papeis_usuario(usuario),
            "membros_equipe": membros_equipe,
            "e_admin": usuario_admin_escritorio(usuario),
        })

    configuracao_escritorio = _obter_configuracao_escritorio()
    usuario_e_admin_escritorio = usuario_admin_escritorio(request.user)
    assinatura = getattr(request.tenant, "assinatura", None)
    plano_nome = assinatura.plano.nome if assinatura else None

    return render(request, "configuracoes/index.html", {
        "perfil_usuario": perfil_usuario,
        "usuarios_contexto": usuarios_contexto,
        "plano_nome": plano_nome,
        "usuarios_ativos": usuarios_ativos,
        "limite_usuarios": 10,
        "configuracao_escritorio": configuracao_escritorio,
        "usuario_e_admin_escritorio": usuario_e_admin_escritorio,
        "pode_criar_usuario": _pode_criar_usuario(request.user),
        "pode_gerenciar_equipes": _pode_gerenciar_equipes(request.user),
        "pode_gerenciar_permissoes": _pode_gerenciar_permissoes(request.user),
        "item_ativo": "configuracoes",
    })


@login_required
def editar_perfil(request):
    perfil, _ = PerfilUsuario.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = PerfilUsuarioForm(request.POST, request.FILES, instance=perfil)
        if form.is_valid():
            form.save()
            return redirect("configuracoes:index")
    else:
        form = PerfilUsuarioForm(instance=perfil)

    return render(
        request,
        "configuracoes/editar_perfil.html",
        {
            "form": form,
            "perfil": perfil,
            "item_ativo": "configuracoes",
        },
    )


@login_required
def foto_perfil(request):
    """Serve o avatar do próprio usuário logado — `PerfilUsuario.avatar`
    usa storage protegido (sem URL pública), por isso a entrega passa
    por uma view autenticada, mesmo padrão de `chat.anexo_mensagem`."""
    perfil, _ = PerfilUsuario.objects.get_or_create(user=request.user)
    if not perfil.avatar:
        raise Http404

    return FileResponse(perfil.avatar.open("rb"), filename=nome_do_arquivo(perfil.avatar))


@login_required
def foto_usuario(request, user_pk):
    """Avatar de qualquer usuário ativo do escritório — a foto aparece
    para os colegas (chat, listas), então a entrega é aberta a qualquer
    usuário autenticado do tenant; sem foto, 404 (a tela mostra iniciais)."""
    perfil = get_object_or_404(
        PerfilUsuario.objects.select_related("user"), user_id=user_pk, user__is_active=True,
    )
    if not perfil.avatar:
        raise Http404

    return FileResponse(perfil.avatar.open("rb"), filename=nome_do_arquivo(perfil.avatar))


@login_required
def alterar_senha(request):
    if request.method == "POST":
        form = AlterarSenhaForm(request.user, request.POST)
        if form.is_valid():
            usuario = form.save()
            update_session_auth_hash(request, usuario)
            messages.success(request, "Senha alterada com sucesso.")
            return redirect("configuracoes:index")
    else:
        form = AlterarSenhaForm(request.user)

    return render(
        request,
        "configuracoes/alterar_senha.html",
        {
            "form": form,
            "item_ativo": "configuracoes",
        },
    )


@login_required
def novo_usuario(request):
    if not _pode_criar_usuario(request.user):
        raise PermissionDenied

    if request.method == "POST":
        form = CriarUsuarioEscritorioForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            registrar_atividade(
                request.user, "usuario_criado",
                f"Criou o usuário {usuario.get_full_name() or usuario.username}",
            )
            return redirect("configuracoes:index")
    else:
        form = CriarUsuarioEscritorioForm()

    return render(
        request,
        "configuracoes/novo_usuario.html",
        {
            "form": form,
            "item_ativo": "configuracoes",
        },
    )


@login_required
def equipes(request):
    if not _pode_gerenciar_equipes(request.user):
        raise PermissionDenied

    deps = (
        Equipe.objects
        .prefetch_related("membros", "membros__usuario")
        .order_by("nome")
    )

    equipes_contexto = []
    for dep in deps:
        membros_list = list(dep.membros.all())
        equipes_contexto.append({
            "equipe": dep,
            "total_membros": len(membros_list),
            "total_gerentes": sum(1 for m in membros_list if m.eh_gerente),
        })

    return render(
        request,
        "configuracoes/equipes.html",
        {
            "equipes_contexto": equipes_contexto,
            "item_ativo": "configuracoes",
        },
    )


@login_required
def nova_equipe(request):
    if not _pode_gerenciar_equipes(request.user):
        raise PermissionDenied

    if request.method == "POST":
        form = EquipeForm(request.POST)
        if form.is_valid():
            equipe = form.save()
            registrar_atividade(request.user, "equipe_criada", f"Criou a equipe {equipe.nome}")
            return redirect("configuracoes:equipes")
    else:
        form = EquipeForm()

    return render(
        request,
        "configuracoes/equipe_form.html",
        {
            "form": form,
            "modo": "novo",
            "titulo": "Nova equipe",
            "item_ativo": "configuracoes",
        },
    )


@login_required
def editar_equipe(request, pk):
    if not _pode_gerenciar_equipes(request.user):
        raise PermissionDenied

    equipe = get_object_or_404(Equipe, pk=pk)

    if request.method == "POST":
        form = EquipeForm(request.POST, instance=equipe)
        if form.is_valid():
            equipe = form.save()
            registrar_atividade(request.user, "equipe_editada", f"Editou a equipe {equipe.nome}")
            return redirect("configuracoes:equipes")
    else:
        form = EquipeForm(instance=equipe)

    return render(
        request,
        "configuracoes/equipe_form.html",
        {
            "form": form,
            "equipe": equipe,
            "modo": "editar",
            "titulo": "Editar equipe",
            "item_ativo": "configuracoes",
        },
    )


@login_required
def equipe_membros(request, pk):
    if not _pode_gerenciar_equipes(request.user):
        raise PermissionDenied

    equipe = get_object_or_404(Equipe, pk=pk)

    if request.method == "POST":
        form = MembroEquipeForm(request.POST, equipe=equipe)
        if form.is_valid():
            membro = form.save(commit=False)
            membro.equipe = equipe
            membro.ativo = True
            membro.save()
            registrar_atividade(
                request.user, "equipe_membro_adicionado",
                f"Adicionou {membro.usuario.get_full_name() or membro.usuario.username} "
                f"à equipe {equipe.nome}",
            )
            return redirect("configuracoes:equipe_membros", pk=equipe.pk)
    else:
        form = MembroEquipeForm(equipe=equipe)

    membros = (
        MembroEquipe.objects
        .filter(equipe=equipe)
        .select_related("usuario", "usuario__perfil")
        .order_by("-eh_gerente", "usuario__username")
    )

    return render(
        request,
        "configuracoes/equipe_membros.html",
        {
            "equipe": equipe,
            "form": form,
            "membros": membros,
            "item_ativo": "configuracoes",
        },
    )


@login_required
def remover_membro_equipe(request, pk, membro_pk):
    if not _pode_gerenciar_equipes(request.user):
        raise PermissionDenied

    equipe = get_object_or_404(Equipe, pk=pk)
    membro = get_object_or_404(
        MembroEquipe,
        pk=membro_pk,
        equipe=equipe,
    )

    if request.method == "POST":
        usuario = membro.usuario
        membro.delete()
        registrar_atividade(
            request.user, "equipe_membro_removido",
            f"Removeu {usuario.get_full_name() or usuario.username} da equipe {equipe.nome}",
        )

    return redirect("configuracoes:equipe_membros", pk=equipe.pk)


@login_required
def alternar_gerente_equipe(request, pk, membro_pk):
    if not _pode_gerenciar_equipes(request.user):
        raise PermissionDenied

    equipe = get_object_or_404(Equipe, pk=pk)
    membro = get_object_or_404(
        MembroEquipe,
        pk=membro_pk,
        equipe=equipe,
    )

    if request.method == "POST":
        membro.eh_gerente = not membro.eh_gerente
        membro.save(update_fields=["eh_gerente"])
        nome = membro.usuario.get_full_name() or membro.usuario.username
        acao = "Definiu" if membro.eh_gerente else "Removeu"
        registrar_atividade(
            request.user, "equipe_gerente_alterado",
            f"{acao} {nome} como gerente da equipe {equipe.nome}",
        )

    return redirect("configuracoes:equipe_membros", pk=equipe.pk)


@login_required
def papeis(request):
    if not _pode_gerenciar_permissoes(request.user):
        raise PermissionDenied

    papeis_qs = PapelAcesso.objects.order_by("nome").prefetch_related("atribuicoes_usuario")

    papeis_contexto = []
    for papel in papeis_qs:
        papeis_contexto.append({
            "papel": papel,
            "total_usuarios": sum(1 for up in papel.atribuicoes_usuario.all() if up.ativo),
        })

    return render(
        request,
        "configuracoes/papeis.html",
        {
            "papeis_contexto": papeis_contexto,
            "item_ativo": "configuracoes",
        },
    )


@login_required
def novo_papel(request):
    if not _pode_gerenciar_permissoes(request.user):
        raise PermissionDenied

    if request.method == "POST":
        form = PapelAcessoForm(request.POST)
        if form.is_valid():
            papel = form.save()
            registrar_atividade(request.user, "papel_criado", f"Criou o papel de acesso {papel.nome}")
            return redirect("configuracoes:papeis")
    else:
        form = PapelAcessoForm()

    return render(
        request,
        "configuracoes/papel_form.html",
        {
            "form": form,
            "modo": "novo",
            "titulo": "Novo papel",
            "item_ativo": "configuracoes",
        },
    )


@login_required
def editar_papel(request, pk):
    if not _pode_gerenciar_permissoes(request.user):
        raise PermissionDenied

    papel = get_object_or_404(PapelAcesso, pk=pk)

    if request.method == "POST":
        form = PapelAcessoForm(request.POST, instance=papel)
        if form.is_valid():
            papel = form.save()
            registrar_atividade(request.user, "papel_editado", f"Editou o papel de acesso {papel.nome}")
            return redirect("configuracoes:papeis")
    else:
        form = PapelAcessoForm(instance=papel)

    return render(
        request,
        "configuracoes/papel_form.html",
        {
            "form": form,
            "papel": papel,
            "modo": "editar",
            "titulo": "Editar papel",
            "item_ativo": "configuracoes",
        },
    )


@login_required
def papel_usuarios(request, pk):
    if not _pode_gerenciar_permissoes(request.user):
        raise PermissionDenied

    papel = get_object_or_404(PapelAcesso, pk=pk)

    if request.method == "POST":
        form = AtribuirPapelForm(request.POST, papel=papel)
        if form.is_valid():
            usuario = form.cleaned_data["usuario"]
            UsuarioPapel.objects.update_or_create(
                usuario=usuario,
                papel=papel,
                defaults={"ativo": True, "atribuido_por": request.user},
            )
            registrar_atividade(
                request.user, "papel_usuario_atribuido",
                f"Atribuiu {usuario.get_full_name() or usuario.username} ao papel {papel.nome}",
            )
            return redirect("configuracoes:papel_usuarios", pk=papel.pk)
    else:
        form = AtribuirPapelForm(papel=papel)

    vinculos = (
        UsuarioPapel.objects
        .filter(papel=papel, ativo=True)
        .select_related("usuario", "usuario__perfil")
        .order_by("usuario__username")
    )

    return render(
        request,
        "configuracoes/papel_usuarios.html",
        {
            "papel": papel,
            "form": form,
            "vinculos": vinculos,
            "item_ativo": "configuracoes",
        },
    )


@login_required
def remover_usuario_papel(request, pk, usuario_papel_pk):
    if not _pode_gerenciar_permissoes(request.user):
        raise PermissionDenied

    papel = get_object_or_404(PapelAcesso, pk=pk)
    vinculo = get_object_or_404(
        UsuarioPapel,
        pk=usuario_papel_pk,
        papel=papel,
    )

    if request.method == "POST":
        vinculo.ativo = False
        vinculo.save(update_fields=["ativo"])
        registrar_atividade(
            request.user, "papel_usuario_removido",
            f"Removeu {vinculo.usuario.get_full_name() or vinculo.usuario.username} "
            f"do papel {papel.nome}",
        )

    return redirect("configuracoes:papel_usuarios", pk=papel.pk)


_MODULOS_CONFIG = [
    ("processos",  "Processos",       [("somente_seus", "Somente os seus"), ("todos", "Todos")]),
    ("clientes",   "Clientes",        [("somente_seus", "Somente os seus"), ("todos", "Todos")]),
    ("financeiro", "Financeiro",      [("solicitacoes", "Apenas solicitações"), ("dados_proprios", "Dados — só os meus lançamentos"), ("dados_todos", "Dados — todos os lançamentos")]),
    ("tarefas",    "Tarefas",         [("somente_seus", "Somente os seus"), ("todos", "Todos")]),
    ("modelos",    "Modelos de peças",[("somente_seus", "Somente os seus"), ("todos", "Todos")]),
    ("chat",       "Chat",            []),
    ("painel",     "Painel",          [("somente_seus", "Somente os seus"), ("todos", "Todos")]),
    ("agenda",     "Agenda",          [("somente_seus", "Somente os seus"), ("todos", "Todos")]),
    ("gerir",      "Gerir",           []),
]


def _build_modulos_permissao(papel):
    """Monta a lista de módulos (nível + habilitações granulares) de um papel."""
    registros = {p.modulo: p for p in PermissaoPapel.objects.filter(papel=papel)}
    habilitacoes = {(h.modulo, h.item): h for h in HabilitacaoPapel.objects.filter(papel=papel)}

    result = []
    for slug, label, niveis in _MODULOS_CONFIG:
        reg = registros.get(slug)
        itens = []
        for item_slug in ITENS_POR_MODULO.get(slug, []):
            hab = habilitacoes.get((slug, item_slug))
            itens.append({
                "slug": item_slug,
                "label": NOMES_ITENS.get(item_slug, item_slug),
                "ativo": hab.ativo if hab else False,
            })
        result.append({
            "slug": slug,
            "label": label,
            "niveis": [{"valor": v, "label": lbl} for v, lbl in niveis],
            "ativo": reg.ativo if reg else False,
            "nivel_atual": reg.nivel if reg else (niveis[0][0] if niveis else ""),
            "itens": itens,
        })
    return result


def _salvar_permissoes(request, papel):
    """Persiste módulo/nível e habilitações granulares de um papel."""
    with transaction.atomic():
        usuarios_antes = usuarios_com_acesso_processos()
        for slug, _, niveis in _MODULOS_CONFIG:
            ativo = request.POST.get(f"ativo_{slug}") == "on"
            if niveis:
                nivel = request.POST.get(f"nivel_{slug}", niveis[0][0])
                if nivel not in [n[0] for n in niveis]:
                    nivel = niveis[0][0]
            else:
                nivel = ""
            PermissaoPapel.objects.update_or_create(
                papel=papel,
                modulo=slug,
                defaults={"ativo": ativo, "nivel": nivel},
            )
            for item_slug in ITENS_POR_MODULO.get(slug, []):
                habilitado = request.POST.get(f"hab_{slug}_{item_slug}") == "on"
                HabilitacaoPapel.objects.update_or_create(
                    papel=papel,
                    modulo=slug,
                    item=item_slug,
                    defaults={"ativo": habilitado},
                )
        transferir_processos_de_usuarios_sem_acesso(usuarios_antes)


@login_required
def permissoes(request):
    if not _pode_gerenciar_permissoes(request.user):
        raise PermissionDenied

    papeis_ativos = list(PapelAcesso.objects.filter(ativo=True).order_by("nome"))
    tabs_papeis = {f"papel_{p.pk}" for p in papeis_ativos}

    mensagem = None
    erro = None
    limitado = next((p for p in papeis_ativos if p.eh_limitado), None)
    tab_padrao = f"papel_{limitado.pk}" if limitado else "administrador"
    tab_ativa = request.GET.get("tab", tab_padrao)
    if tab_ativa not in ({"administrador"} | tabs_papeis):
        tab_ativa = tab_padrao

    if request.method == "POST":
        papel_id = request.POST.get("papel_id", "")
        papel_alvo = next((p for p in papeis_ativos if str(p.pk) == papel_id), None)
        if papel_alvo is None:
            erro = "Papel inválido ou inativo."
        else:
            _salvar_permissoes(request, papel_alvo)
            registrar_atividade(
                request.user, "permissao_papel_editada",
                f"Editou as permissões do papel {papel_alvo.nome}",
            )
            tab_ativa = f"papel_{papel_alvo.pk}"
            mensagem = f"Permissões de '{papel_alvo.nome}' atualizadas com sucesso."

    papeis_contexto = [
        {
            "papel": papel,
            "modulos": _build_modulos_permissao(papel),
            "titulo": f"Módulos — {papel.nome}",
            "botao_label": f"Salvar permissões de '{papel.nome}'",
        }
        for papel in papeis_ativos
    ]

    return render(request, "configuracoes/permissoes.html", {
        "tab_ativa": tab_ativa,
        "modulos_admin": [label for _, label, _ in _MODULOS_CONFIG],
        "papeis_contexto": papeis_contexto,
        "mensagem": mensagem,
        "erro": erro,
        "item_ativo": "configuracoes",
    })


def _papeis_ativos_usuario(usuario):
    return [
        up.papel
        for up in UsuarioPapel.objects.filter(usuario=usuario, ativo=True).select_related("papel")
        if up.papel.ativo
    ]


def _herdado_modulo(papeis_ativos, slug, niveis):
    """Valor que o usuário teria para o módulo via papéis, ignorando
    qualquer override individual."""
    if not papeis_ativos:
        return {"ativo": False, "nivel": ""}
    linhas = list(PermissaoPapel.objects.filter(papel__in=papeis_ativos, modulo=slug))
    ativas = [l for l in linhas if l.ativo]
    if not ativas:
        return {"ativo": False, "nivel": ""}
    ordem = [v for v, _ in niveis]
    nivel = max(
        (l.nivel for l in ativas),
        key=lambda n: ordem.index(n) if n in ordem else -1,
        default="",
    )
    return {"ativo": True, "nivel": nivel}


def _herdado_item(papeis_ativos, slug, item_slug):
    if not papeis_ativos:
        return False
    return HabilitacaoPapel.objects.filter(
        papel__in=papeis_ativos, modulo=slug, item=item_slug, ativo=True
    ).exists()


def _modulos_efetivos_usuario(usuario_alvo, papeis_ativos):
    """Estado efetivo — já herdado dos papéis, com
    override individual por cima quando existir — de cada módulo e
    habilitação granular. A tela não expõe mais herdado/override como
    conceitos separados (specs/configuracoes-perfil-e-habilitacoes.md);
    o mecanismo de override continua existindo tecnicamente por baixo."""
    overrides_modulo = {po.modulo: po for po in PermissaoUsuario.objects.filter(usuario=usuario_alvo)}
    overrides_item = {
        (hu.modulo, hu.item): hu
        for hu in HabilitacaoUsuario.objects.filter(usuario=usuario_alvo)
    }

    modulos_contexto = []
    for slug, label, niveis in _MODULOS_CONFIG:
        herdado = _herdado_modulo(papeis_ativos, slug, niveis)
        override = overrides_modulo.get(slug)

        itens = []
        for item_slug in ITENS_POR_MODULO.get(slug, []):
            override_item = overrides_item.get((slug, item_slug))
            herdado_item = _herdado_item(papeis_ativos, slug, item_slug)
            itens.append({
                "slug": item_slug,
                "label": NOMES_ITENS.get(item_slug, item_slug),
                "ativo": override_item.ativo if override_item else herdado_item,
            })

        ativo = override.ativo if override else herdado["ativo"]
        nivel_atual = (override.nivel if override else herdado["nivel"]) or (niveis[0][0] if niveis else "")
        modulos_contexto.append({
            "slug": slug,
            "label": label,
            "niveis": [{"valor": v, "label": lbl} for v, lbl in niveis],
            "ativo": ativo,
            "nivel_atual": nivel_atual,
            "itens": itens,
        })
    return modulos_contexto


def _salvar_overrides_usuario(request, usuario_alvo):
    """Grava, para cada módulo/habilitação da tela, um override
    individual explícito com o estado efetivo submetido — substitui o
    valor herdado sem exigir uma ação separada de "desligar herança"."""
    with transaction.atomic():
        for slug, _, niveis in _MODULOS_CONFIG:
            ativo = request.POST.get(f"ativo_{slug}") == "on"
            if niveis:
                nivel = request.POST.get(f"nivel_{slug}", niveis[0][0])
                if nivel not in [n[0] for n in niveis]:
                    nivel = niveis[0][0]
            else:
                nivel = ""
            PermissaoUsuario.objects.update_or_create(
                usuario=usuario_alvo,
                modulo=slug,
                defaults={"ativo": ativo, "nivel": nivel},
            )
            for item_slug in ITENS_POR_MODULO.get(slug, []):
                habilitado = request.POST.get(f"hab_{slug}_{item_slug}") == "on"
                HabilitacaoUsuario.objects.update_or_create(
                    usuario=usuario_alvo,
                    modulo=slug,
                    item=item_slug,
                    defaults={"ativo": habilitado},
                )
        transferir_processos_de_usuarios_sem_acesso([usuario_alvo.pk])


@login_required
def usuario_overrides(request, user_pk):
    if not _pode_gerenciar_permissoes(request.user):
        raise PermissionDenied

    usuario_alvo = get_object_or_404(User, pk=user_pk)
    is_admin_alvo = usuario_admin_escritorio(usuario_alvo)

    if request.method == "POST" and not is_admin_alvo:
        _salvar_overrides_usuario(request, usuario_alvo)
        registrar_atividade(
            request.user, "permissao_usuario_editada",
            f"Editou as permissões individuais de "
            f"{usuario_alvo.get_full_name() or usuario_alvo.username}",
        )
        return redirect("configuracoes:usuario_overrides", user_pk=usuario_alvo.pk)

    papeis_ativos = _papeis_ativos_usuario(usuario_alvo)
    modulos_contexto = _modulos_efetivos_usuario(usuario_alvo, papeis_ativos)

    return render(
        request,
        "configuracoes/usuario_overrides.html",
        {
            "usuario_alvo": usuario_alvo,
            "is_admin_alvo": is_admin_alvo,
            "modulos_contexto": modulos_contexto,
            "item_ativo": "configuracoes",
        },
    )


@login_required
def usuario_equipes(request, user_pk):
    """Equipes de um usuário específico — atalho "Grupos" do Painel do
    gestor (specs/dashboard-painel-do-gestor.md). Mesma autorização e
    mesmo modelo (MembroEquipe) já usados em `equipe_membros`, só que
    pela perspectiva do usuário em vez da equipe."""
    if not _pode_gerenciar_equipes(request.user):
        raise PermissionDenied

    usuario_alvo = get_object_or_404(User, pk=user_pk)

    if request.method == "POST":
        equipe = get_object_or_404(Equipe, pk=request.POST.get("equipe_id"))
        nome_alvo = usuario_alvo.get_full_name() or usuario_alvo.username
        if request.POST.get("acao") == "remover":
            MembroEquipe.objects.filter(usuario=usuario_alvo, equipe=equipe).delete()
            registrar_atividade(
                request.user, "equipe_membro_removido",
                f"Removeu {nome_alvo} da equipe {equipe.nome}",
            )
        else:
            MembroEquipe.objects.update_or_create(
                usuario=usuario_alvo, equipe=equipe, defaults={"ativo": True},
            )
            registrar_atividade(
                request.user, "equipe_membro_adicionado",
                f"Adicionou {nome_alvo} à equipe {equipe.nome}",
            )
        return redirect("configuracoes:usuario_equipes", user_pk=usuario_alvo.pk)

    ids_membro = set(
        MembroEquipe.objects.filter(usuario=usuario_alvo, ativo=True)
        .values_list("equipe_id", flat=True)
    )
    equipes_contexto = [
        {"equipe": equipe, "membro": equipe.pk in ids_membro}
        for equipe in Equipe.objects.filter(ativo=True).order_by("nome")
    ]

    return render(
        request,
        "configuracoes/usuario_equipes.html",
        {
            "usuario_alvo": usuario_alvo,
            "equipes_contexto": equipes_contexto,
            "item_ativo": "configuracoes",
        },
    )


@login_required
def usuario_processos_habilitados(request, user_pk):
    """Habilitar um usuário específico em processos — atalho "Habilitar
    em processos" do Painel do gestor
    (specs/dashboard-painel-do-gestor.md). Cada linha grava na hora
    (toggle), sem checklist com "Salvar" ao final — assim trocar o
    filtro nunca perde uma seleção ainda não salva."""
    if not _pode_habilitar_usuario_processos(request.user):
        raise PermissionDenied

    usuario_alvo = get_object_or_404(User, pk=user_pk)

    if request.method == "POST":
        processo = get_object_or_404(Processo, pk=request.POST.get("processo_id"))
        if request.POST.get("acao") == "remover":
            processo.integrantes_habilitados.remove(usuario_alvo)
            registrar_atividade(
                request.user, "processo_integrante_removido",
                f"Removeu a habilitação de {usuario_alvo.get_full_name() or usuario_alvo.username} no processo {processo.titulo}",
                processo=processo,
            )
        else:
            processo.integrantes_habilitados.add(usuario_alvo)
            registrar_atividade(
                request.user, "processo_integrante_adicionado",
                f"Habilitou {usuario_alvo.get_full_name() or usuario_alvo.username} no processo {processo.titulo}",
                processo=processo,
            )
        querystring = request.GET.urlencode()
        url = reverse("configuracoes:usuario_processos_habilitados", args=[usuario_alvo.pk])
        return redirect(f"{url}?{querystring}" if querystring else url)

    cliente_id = request.GET.get("cliente") or ""
    materia = request.GET.get("materia") or ""
    data = request.GET.get("data") or ""
    busca = request.GET.get("busca") or ""

    processos = Processo.objects.exclude(status="arquivado").prefetch_related("clientes")
    if cliente_id:
        processos = processos.filter(clientes__id=cliente_id)
    if materia:
        processos = processos.filter(area_direito=materia)
    if data:
        processos = processos.filter(data_distribuicao=data)
    if busca:
        processos = processos.filter(Q(titulo__icontains=busca) | Q(numero__icontains=busca))
    processos = processos.order_by("titulo")

    ids_habilitados = set(
        usuario_alvo.processos_integrante_habilitado.values_list("pk", flat=True)
    )

    return render(
        request,
        "configuracoes/usuario_processos_habilitados.html",
        {
            "usuario_alvo": usuario_alvo,
            "processos": processos,
            "ids_habilitados": ids_habilitados,
            "clientes_opcoes": Cliente.objects.filter(ativo=True).order_by("nome_razao_social"),
            "materias_opcoes": Processo.AREAS_CHOICES,
            "cliente_id": cliente_id,
            "materia": materia,
            "data": data,
            "busca": busca,
            "item_ativo": "configuracoes",
        },
    )


@requer_admin_escritorio
def editar_escritorio(request):
    configuracao = _obter_configuracao_escritorio()

    if request.method == "POST":
        form = ConfiguracaoEscritorioForm(request.POST, instance=configuracao)
        if form.is_valid():
            form.save()
            registrar_atividade(request.user, "escritorio_editado", "Editou os dados do escritório")
            return redirect("configuracoes:index")
    else:
        form = ConfiguracaoEscritorioForm(instance=configuracao)

    return render(
        request,
        "configuracoes/editar_escritorio.html",
        {
            "form": form,
            "configuracao": configuracao,
            "item_ativo": "configuracoes",
        },
    )


@requer_admin_escritorio
def identidade_visual(request):
    """Logo e cores do escritório (white label) — o logo é aplicado na
    barra lateral e as cores predominantes dele tingem o sistema."""
    config, _ = ConfiguracaoVisual.objects.get_or_create(escritorio=request.tenant)

    if request.method == "POST":
        form = IdentidadeVisualForm(request.POST, request.FILES)
        if form.is_valid():
            dados = form.cleaned_data
            logo = dados.get("logo")
            if logo:
                cores = [] if dados["manter_cores"] else cores_predominantes(logo)
                logo.seek(0)
                if config.logo:
                    config.logo.delete(save=False)
                config.logo = logo
                if cores:
                    config.cor_primaria = cores[0]
                    if len(cores) > 1:
                        config.cor_secundaria = cores[1]
            elif dados["remover_logo"] and config.logo:
                config.logo.delete(save=False)
                config.logo = None
            if not logo:
                config.cor_primaria = dados["cor_primaria"] or config.cor_primaria
                config.cor_secundaria = dados["cor_secundaria"] or config.cor_secundaria
            config.save()
            registrar_atividade(
                request.user, "escritorio_identidade_visual_editada",
                "Editou a identidade visual do escritório",
            )
            messages.success(request, "Identidade visual atualizada.")
            return redirect("configuracoes:identidade_visual")
    else:
        form = IdentidadeVisualForm(initial={
            "cor_primaria": config.cor_primaria, "cor_secundaria": config.cor_secundaria,
        })

    return render(request, "configuracoes/identidade_visual.html", {
        "form": form,
        "config": config,
        "item_ativo": "configuracoes",
    })


@requer_admin_escritorio
def excluir_usuario(request, user_pk):
    """Exclui o usuário do escritório: a conta é inativada (não há como
    apagar o registro — processos, clientes e tarefas o referenciam) e os
    processos sob a responsabilidade dele passam ao Administrador
    (PDR-0010). Não vale para si mesmo nem para o Administrador. Exige a
    senha de quem está logado (PDR-0030)."""
    if request.method != "POST":
        raise Http404
    alvo = get_object_or_404(User, pk=user_pk, is_active=True)
    if not request.user.check_password(request.POST.get("senha", "")):
        messages.error(request, "Senha incorreta. Nenhum usuário foi excluído.")
        return redirect("configuracoes:index")
    if alvo.pk == request.user.pk:
        messages.error(request, "Você não pode excluir a própria conta.")
        return redirect("configuracoes:index")
    if usuario_admin_escritorio(alvo):
        messages.error(request, "O Administrador do escritório não pode ser excluído.")
        return redirect("configuracoes:index")

    nome = alvo.get_full_name() or alvo.username
    try:
        with transaction.atomic():
            alvo.is_active = False
            alvo.save(update_fields=["is_active"])
            MembroEquipe.objects.filter(usuario=alvo).delete()
            transferir_processos_de_usuarios_sem_acesso([alvo.pk])
    except AdministradorResponsavelIndisponivel as exc:
        messages.error(request, str(exc))
        return redirect("configuracoes:index")

    registrar_atividade(request.user, "usuario_excluido", f"Excluiu o usuário {nome}")
    messages.success(request, f"Usuário {nome} excluído.")
    return redirect("configuracoes:index")
