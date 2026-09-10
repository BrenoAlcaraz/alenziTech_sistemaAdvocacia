from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import ProtectedError, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.accounts.permissoes import tem_habilitacao, tem_permissao_modulo
from apps.accounts.permissoes_constants import (
    HAB_MODELOS_CRIAR,
    HAB_MODELOS_EDITAR_ALHEIO,
    HAB_MODELOS_EDITAR_ESTILO,
    HAB_MODELOS_EXCLUIR_ALHEIO,
    HAB_MODELOS_GERIR_CATEGORIAS,
    MODULO_MODELOS,
)
from apps.modelos.forms import (
    CategoriaModeloPecaForm,
    EstiloEscritorioForm,
    ImportarModeloPecaForm,
    ModeloPecaForm,
)
from apps.modelos.models import (
    CategoriaModeloPeca,
    EstiloEscritorio,
    ModeloPeca,
    VersaoModeloPeca,
)
from apps.modelos.services import ErroImportacaoDocumento, extrair_texto_documento
from apps.notificacoes.models import Notificacao


def _obter_estilo_escritorio():
    estilo, _ = EstiloEscritorio.objects.get_or_create(pk=1)
    return estilo


def _pode_editar_estilo(user):
    return tem_habilitacao(user, MODULO_MODELOS, HAB_MODELOS_EDITAR_ESTILO)


def _pode_gerir_categorias(user):
    return tem_habilitacao(user, MODULO_MODELOS, HAB_MODELOS_GERIR_CATEGORIAS)


def _listar_modelos(busca, categoria_id=None):
    modelos = ModeloPeca.objects.select_related("criado_por", "categoria").order_by(
        "-criado_em", "-pk"
    )

    if busca:
        modelos = modelos.filter(
            Q(titulo__icontains=busca)
            | Q(categoria__nome__icontains=busca)
            | Q(area_direito__icontains=busca)
            | Q(conteudo__icontains=busca)
        )

    if categoria_id:
        modelos = modelos.filter(categoria_id=categoria_id)

    return modelos


@login_required
def lista(request):
    if not tem_permissao_modulo(request.user, MODULO_MODELOS):
        raise PermissionDenied

    aba_ativa = request.GET.get("aba", "modelos")
    busca = request.GET.get("q", "").strip()
    categoria_id = request.GET.get("categoria", "").strip()
    if not categoria_id.isdigit():
        categoria_id = ""

    modelos = _listar_modelos(busca, categoria_id or None)

    pode_editar_estilo = False
    estilo = None
    form_estilo = None
    if aba_ativa != "modelos":
        pode_editar_estilo = _pode_editar_estilo(request.user)
        estilo = _obter_estilo_escritorio()
        form_estilo = EstiloEscritorioForm(instance=estilo) if pode_editar_estilo else None

    return render(request, "modelos/lista.html", {
        "modelos": modelos,
        "aba_ativa": aba_ativa,
        "busca": busca,
        "categorias": CategoriaModeloPeca.objects.all(),
        "categoria_selecionada": categoria_id,
        "item_ativo": "modelos",
        "estilo": estilo,
        "pode_editar_estilo": pode_editar_estilo,
        "pode_gerir_categorias": _pode_gerir_categorias(request.user),
        "form_estilo": form_estilo,
    })


@login_required
def novo(request):
    if not tem_permissao_modulo(request.user, MODULO_MODELOS):
        raise PermissionDenied
    if not tem_habilitacao(request.user, MODULO_MODELOS, HAB_MODELOS_CRIAR):
        raise PermissionDenied

    if request.method == "POST":
        form = ModeloPecaForm(request.POST)
        if form.is_valid():
            modelo = form.save(commit=False)
            modelo.criado_por = request.user
            modelo.save()
            return redirect("modelos:detalhe", pk=modelo.pk)
    else:
        form = ModeloPecaForm()

    return render(request, "modelos/form.html", {
        "form": form,
        "modo": "novo",
        "modelo": None,
        "item_ativo": "modelos",
    })


# `editar`/`excluir` repetem "dono OU habilitação alheia" (2 ocorrências,
# cada uma com sua própria habilitação — PDR-0018). Deliberadamente não
# extraído: só vale abstrair se uma 3ª view precisar do mesmo padrão.
def _eh_dono(user, modelo):
    return modelo.criado_por_id == user.id


def _pode_editar_alheio(user):
    return tem_habilitacao(user, MODULO_MODELOS, HAB_MODELOS_EDITAR_ALHEIO)


def _pode_excluir_alheio(user):
    return tem_habilitacao(user, MODULO_MODELOS, HAB_MODELOS_EXCLUIR_ALHEIO)


CAMPOS_VERSIONADOS = ["titulo", "categoria_id", "area_direito", "conteudo"]


def _valores(origem):
    """Extrai os campos versionados de um ModeloPeca ou VersaoModeloPeca."""
    return {campo: getattr(origem, campo) for campo in CAMPOS_VERSIONADOS}


def _registrar_versao(modelo, valores, editado_por):
    return VersaoModeloPeca.objects.create(modelo=modelo, editado_por=editado_por, **valores)


def _aplicar_valores(modelo, valores):
    for campo, valor in valores.items():
        setattr(modelo, campo, valor)


@login_required
def detalhe(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_MODELOS):
        raise PermissionDenied

    modelo = get_object_or_404(ModeloPeca, pk=pk)
    eh_dono = _eh_dono(request.user, modelo)
    return render(request, "modelos/detalhe.html", {
        "modelo": modelo,
        "item_ativo": "modelos",
        "versoes": modelo.versoes.select_related("categoria", "editado_por"),
        "pode_editar": eh_dono or _pode_editar_alheio(request.user),
        "pode_excluir": eh_dono or _pode_excluir_alheio(request.user),
    })


@login_required
def editar(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_MODELOS):
        raise PermissionDenied

    modelo = get_object_or_404(ModeloPeca, pk=pk)
    eh_dono = _eh_dono(request.user, modelo)
    if not eh_dono and not _pode_editar_alheio(request.user):
        raise PermissionDenied

    if request.method == "POST":
        # Captura o snapshot antes de vincular o form: `is_valid()` já
        # sobrescreve os atributos de `modelo` em memória com os dados
        # novos (via `construct_instance` em `_post_clean`), antes do save.
        valores_anteriores = _valores(modelo)
        form = ModeloPecaForm(request.POST, instance=modelo)
        if form.is_valid():
            _registrar_versao(modelo, valores_anteriores, editado_por=request.user)
            form.save()
            if not eh_dono and modelo.criado_por_id:
                Notificacao.objects.create(
                    destinatario=modelo.criado_por,
                    mensagem=f'Seu modelo de peça foi editado: "{modelo.titulo}"',
                )
            return redirect("modelos:detalhe", pk=modelo.pk)
    else:
        form = ModeloPecaForm(instance=modelo)

    return render(request, "modelos/form.html", {
        "form": form,
        "modo": "editar",
        "modelo": modelo,
        "item_ativo": "modelos",
    })


@login_required
def reverter(request, pk, versao_pk):
    if not tem_permissao_modulo(request.user, MODULO_MODELOS):
        raise PermissionDenied

    modelo = get_object_or_404(ModeloPeca, pk=pk)
    eh_dono = _eh_dono(request.user, modelo)
    if not eh_dono and not _pode_editar_alheio(request.user):
        raise PermissionDenied

    versao = get_object_or_404(VersaoModeloPeca, pk=versao_pk, modelo=modelo)

    if request.method == "POST":
        _registrar_versao(modelo, _valores(modelo), editado_por=request.user)
        _aplicar_valores(modelo, _valores(versao))
        modelo.save()
        if not eh_dono and modelo.criado_por_id:
            Notificacao.objects.create(
                destinatario=modelo.criado_por,
                mensagem=f'Seu modelo de peça foi editado: "{modelo.titulo}"',
            )

    return redirect("modelos:detalhe", pk=modelo.pk)


@login_required
def excluir(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_MODELOS):
        raise PermissionDenied

    modelo = get_object_or_404(ModeloPeca, pk=pk)
    eh_dono = _eh_dono(request.user, modelo)
    if not eh_dono and not _pode_excluir_alheio(request.user):
        raise PermissionDenied

    if request.method == "POST":
        titulo = modelo.titulo
        autor = modelo.criado_por
        modelo.delete()
        if not eh_dono and autor is not None:
            Notificacao.objects.create(
                destinatario=autor,
                mensagem=f'Seu modelo de peça foi excluído: "{titulo}"',
            )
        return redirect("modelos:lista")

    return redirect("modelos:detalhe", pk=modelo.pk)


@login_required
def editar_estilo(request):
    if not tem_permissao_modulo(request.user, MODULO_MODELOS):
        raise PermissionDenied
    if not _pode_editar_estilo(request.user):
        raise PermissionDenied

    destino = f"{reverse('modelos:lista')}?aba=estilo"

    if request.method != "POST":
        return redirect(destino)

    estilo = _obter_estilo_escritorio()
    form = EstiloEscritorioForm(request.POST, instance=estilo)
    if form.is_valid():
        form.save()
        return redirect(destino)

    return render(request, "modelos/lista.html", {
        "modelos": _listar_modelos(""),
        "aba_ativa": "estilo",
        "busca": "",
        "item_ativo": "modelos",
        "estilo": estilo,
        "pode_editar_estilo": True,
        "form_estilo": form,
    })


@login_required
def importar(request):
    if not tem_permissao_modulo(request.user, MODULO_MODELOS):
        raise PermissionDenied
    if not tem_habilitacao(request.user, MODULO_MODELOS, HAB_MODELOS_CRIAR):
        raise PermissionDenied

    if request.method == "POST":
        form = ImportarModeloPecaForm(request.POST, request.FILES)
        if form.is_valid():
            arquivo = form.cleaned_data["arquivo"]
            try:
                conteudo = extrair_texto_documento(arquivo)
            except ErroImportacaoDocumento as erro:
                form.add_error("arquivo", str(erro))
            else:
                titulo = form.cleaned_data["titulo"].strip()
                if not titulo:
                    titulo = Path(arquivo.name).stem.strip()
                titulo = titulo[:255] or "Modelo importado"

                modelo = ModeloPeca.objects.create(
                    titulo=titulo,
                    categoria=form.cleaned_data["categoria"],
                    area_direito=form.cleaned_data["area_direito"],
                    conteudo=conteudo,
                    criado_por=request.user,
                )
                return redirect("modelos:detalhe", pk=modelo.pk)
    else:
        form = ImportarModeloPecaForm()

    return render(request, "modelos/importar.html", {
        "form": form,
        "item_ativo": "modelos",
    })


@login_required
def categorias(request):
    if not tem_permissao_modulo(request.user, MODULO_MODELOS):
        raise PermissionDenied
    if not _pode_gerir_categorias(request.user):
        raise PermissionDenied

    if request.method == "POST":
        form = CategoriaModeloPecaForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("modelos:categorias")
    else:
        form = CategoriaModeloPecaForm()

    return render(request, "modelos/categorias.html", {
        "categorias": CategoriaModeloPeca.objects.all(),
        "form": form,
        "item_ativo": "modelos",
    })


@login_required
def categoria_editar(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_MODELOS):
        raise PermissionDenied
    if not _pode_gerir_categorias(request.user):
        raise PermissionDenied

    categoria = get_object_or_404(CategoriaModeloPeca, pk=pk)

    if request.method == "POST":
        form = CategoriaModeloPecaForm(request.POST, instance=categoria)
        if form.is_valid():
            form.save()
            return redirect("modelos:categorias")
    else:
        form = CategoriaModeloPecaForm(instance=categoria)

    return render(request, "modelos/categoria_editar.html", {
        "form": form,
        "categoria": categoria,
        "item_ativo": "modelos",
    })


@login_required
def categoria_excluir(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_MODELOS):
        raise PermissionDenied
    if not _pode_gerir_categorias(request.user):
        raise PermissionDenied

    categoria = get_object_or_404(CategoriaModeloPeca, pk=pk)

    if request.method == "POST":
        try:
            categoria.delete()
        except ProtectedError:
            messages.error(
                request,
                f'Categoria "{categoria.nome}" está em uso por algum modelo de peça '
                "(atual ou no histórico de versões) e não pode ser excluída.",
            )

    return redirect("modelos:categorias")
