from datetime import datetime
from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import ProtectedError, Q
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
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
from apps.clientes.views import resolver_cliente_para_procuracao
from apps.modelos.forms import (
    AREAS_DIREITO,
    MODO_BASE_ACERVO,
    AssinaturaEstiloForm,
    CasoRepetitivoFormSet,
    CategoriaModeloPecaForm,
    EstiloDocumentoForm,
    ImportarModeloPecaForm,
    ModeloPecaForm,
    PecaBaseRepetitivaForm,
)
from apps.modelos.models import (
    AnexoPecaGerada,
    AssinaturaEstilo,
    CategoriaModeloPeca,
    EstiloEscritorio,
    ModeloPeca,
    VersaoModeloPeca,
)
from apps.modelos.services import (
    gerar_peca_procuracao,
    ErroImportacaoDocumento,
    extrair_texto_documento,
    gerar_docx_modelo,
    gerar_pdf_modelo,
    montar_conteudo_caso_repetitivo,
    titulo_peca_caso_repetitivo,
)
from apps.notificacoes.models import Notificacao
from apps.saas_tenants.storage import resposta_de_arquivo


def _obter_estilo_escritorio():
    estilo, _ = EstiloEscritorio.objects.get_or_create(pk=1)
    return estilo


def _pode_editar_estilo(user):
    return tem_habilitacao(user, MODULO_MODELOS, HAB_MODELOS_EDITAR_ESTILO)


CAMPOS_ARQUIVO_ESTILO_DOCUMENTO = [
    "arquivo_referencia",
    "imagem_cabecalho",
    "imagem_rodape",
    "imagem_marca_dagua",
]


def _arquivos_estilo_documento_atuais(estilo):
    """Captura os FieldFile atuais antes de vincular o form: `is_valid()`
    já sobrescreve os atributos de arquivo de `estilo` em memória com os
    dados novos (via `construct_instance` em `_post_clean`), antes do
    save — sem este snapshot, `_substituir_arquivos_estilo_documento`
    apagaria o arquivo recém-enviado em vez do anterior."""
    return {campo: getattr(estilo, campo) for campo in CAMPOS_ARQUIVO_ESTILO_DOCUMENTO}


def _substituir_arquivos_estilo_documento(arquivos_antigos, request):
    """Remove do storage o arquivo anterior de cada campo para o qual um
    novo arquivo foi enviado nesta requisição — evita acumular arquivo
    órfão a cada substituição de imagem/anexo de referência.

    Usa `storage.delete(name)` direto, não `FieldFile.delete()`: este
    último também faz `setattr(self.instance, campo, None)` — como
    `arquivo_antigo.instance` é o mesmo objeto `estilo` que o form já
    mutou para o arquivo novo (via `construct_instance` em
    `_post_clean`, antes de `is_valid()` retornar), chamar `.delete()`
    nele apagaria o valor novo já atribuído à instância."""
    for campo, arquivo_antigo in arquivos_antigos.items():
        if campo in request.FILES and arquivo_antigo:
            arquivo_antigo.storage.delete(arquivo_antigo.name)


CAMPOS_IMAGEM_SLOT_ESTILO = {
    "cabecalho": "imagem_cabecalho",
    "rodape": "imagem_rodape",
    "marca_dagua": "imagem_marca_dagua",
}


def _imagens_estilo_urls(estilo):
    return {
        slot: reverse("modelos:imagem_estilo_documento", args=[slot]) if getattr(estilo, campo) else None
        for slot, campo in CAMPOS_IMAGEM_SLOT_ESTILO.items()
    }


def _pode_gerir_categorias(user):
    return tem_habilitacao(user, MODULO_MODELOS, HAB_MODELOS_GERIR_CATEGORIAS)


def _pode_criar_modelo(user):
    return tem_habilitacao(user, MODULO_MODELOS, HAB_MODELOS_CRIAR)


def _listar_modelos(busca, categoria_id=None, area_direito=None, criado_por_id=None, data=None):
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

    if area_direito:
        modelos = modelos.filter(area_direito=area_direito)

    if criado_por_id:
        modelos = modelos.filter(criado_por_id=criado_por_id)

    if data:
        modelos = modelos.filter(criado_em__date=data)

    return modelos


def _autores_com_modelo():
    ids = ModeloPeca.objects.exclude(criado_por__isnull=True).values_list(
        "criado_por_id", flat=True
    ).distinct()
    return User.objects.filter(pk__in=ids).order_by("username")


@login_required
def lista(request):
    if not tem_permissao_modulo(request.user, MODULO_MODELOS):
        raise PermissionDenied

    aba_ativa = request.GET.get("aba", "modelos")
    busca = request.GET.get("q", "").strip()
    categoria_id = request.GET.get("categoria", "").strip()
    if not categoria_id.isdigit():
        categoria_id = ""
    area_direito = request.GET.get("area_direito", "").strip()
    if area_direito not in dict(AREAS_DIREITO):
        area_direito = ""
    responsavel_id = request.GET.get("responsavel", "").strip()
    if not responsavel_id.isdigit():
        responsavel_id = ""
    data_criacao = request.GET.get("data", "").strip()
    try:
        datetime.strptime(data_criacao, "%Y-%m-%d")
    except ValueError:
        data_criacao = ""

    modelos = list(_listar_modelos(
        busca, categoria_id or None, area_direito or None,
        responsavel_id or None, data_criacao or None,
    ))
    area_labels = dict(AREAS_DIREITO)
    for modelo in modelos:
        modelo.area_direito_label = area_labels.get(modelo.area_direito, modelo.area_direito)

    pode_editar_estilo = False
    estilo = None
    form_estilo_documento = None
    config_documento = None
    imagens_estilo_urls = None
    assinaturas_estilo = None
    form_assinatura_estilo = None
    if aba_ativa == "estilo":
        pode_editar_estilo = _pode_editar_estilo(request.user)
        estilo = _obter_estilo_escritorio()
        config_documento = estilo.config_documento
        imagens_estilo_urls = _imagens_estilo_urls(estilo)
        assinaturas_estilo = list(estilo.assinaturas.all())
        if pode_editar_estilo:
            form_estilo_documento = EstiloDocumentoForm(instance=estilo)
            form_assinatura_estilo = AssinaturaEstiloForm()

    pode_criar_modelo = _pode_criar_modelo(request.user)
    peca_base_form = None
    formset_casos = None
    pecas_geradas = None
    if aba_ativa == "repetitivas" and pode_criar_modelo:
        peca_base_form = PecaBaseRepetitivaForm()
        formset_casos = CasoRepetitivoFormSet(prefix="casos")
        geradas_ids = [pk for pk in request.GET.get("geradas", "").split(",") if pk.isdigit()]
        if geradas_ids:
            pecas_geradas = ModeloPeca.objects.filter(pk__in=geradas_ids).select_related("categoria")

    return render(request, "modelos/lista.html", {
        "modelos": modelos,
        "aba_ativa": aba_ativa,
        "busca": busca,
        "categorias": CategoriaModeloPeca.objects.all(),
        "categoria_selecionada": categoria_id,
        "areas_direito": AREAS_DIREITO,
        "area_direito_selecionada": area_direito,
        "autores": _autores_com_modelo(),
        "responsavel_selecionado": responsavel_id,
        "data_selecionada": data_criacao,
        "item_ativo": "modelos",
        "pode_criar_modelo": pode_criar_modelo,
        "peca_base_form": peca_base_form,
        "formset_casos": formset_casos,
        "pecas_geradas": pecas_geradas,
        "estilo": estilo,
        "pode_editar_estilo": pode_editar_estilo,
        "pode_gerir_categorias": _pode_gerir_categorias(request.user),
        "form_estilo_documento": form_estilo_documento,
        "config_documento": config_documento,
        "imagens_estilo_urls": imagens_estilo_urls,
        "assinaturas_estilo": assinaturas_estilo,
        "form_assinatura_estilo": form_assinatura_estilo,
    })


@login_required
def novo(request):
    if not tem_permissao_modulo(request.user, MODULO_MODELOS):
        raise PermissionDenied
    if not tem_habilitacao(request.user, MODULO_MODELOS, HAB_MODELOS_CRIAR):
        raise PermissionDenied

    estilo = _obter_estilo_escritorio()
    # Fluxo "Criar modelo de Procuração" (vindo de Clientes): só ativo com
    # cliente válido no escopo E categoria Procuração existente.
    categoria_procuracao = CategoriaModeloPeca.objects.filter(nome="Procuração").first()
    cliente_origem = resolver_cliente_para_procuracao(request) if categoria_procuracao else None

    if request.method == "POST":
        form = ModeloPecaForm(request.POST, initial=_initial_fluxo_procuracao(cliente_origem, categoria_procuracao))
        if cliente_origem:
            # `disabled` faz o Django ignorar o valor postado e usar o initial.
            form.fields["categoria"].disabled = True
        if form.is_valid():
            criar_procuracao = cliente_origem is not None and "criar_procuracao" in request.POST
            with transaction.atomic():
                modelo = form.save(commit=False)
                modelo.criado_por = request.user
                modelo.save()
                if criar_procuracao:
                    gerar_peca_procuracao(modelo, cliente_origem, request.user)
            if criar_procuracao:
                messages.success(request, "Procuração criada")
                return redirect(f"{reverse('clientes:detalhe', args=[cliente_origem.pk])}?aba=documentos")
            return redirect("modelos:detalhe", pk=modelo.pk)
    else:
        # Moldura de contexto no momento da criação (mesma lógica do
        # resto do padrão de Meu Estilo): valor inicial vem do padrão do
        # escritório, mas o modelo guarda sua própria escolha daí em
        # diante (specs/modelos-estilo-simplificacao-imagens.md).
        slots = estilo.config_documento.get("slots", {})
        form = ModeloPecaForm(initial={
            "cabecalho_replicacao": slots.get("cabecalho", {}).get("replicacao", "todas"),
            "rodape_replicacao": slots.get("rodape", {}).get("replicacao", "todas"),
            **_initial_fluxo_procuracao(cliente_origem, categoria_procuracao),
        })
        if cliente_origem:
            form.fields["categoria"].disabled = True

    return render(request, "modelos/form.html", {
        "form": form,
        "modo": "novo",
        "modelo": None,
        "item_ativo": "modelos",
        "config_documento": estilo.config_documento,
        "imagens_estilo_urls": _imagens_estilo_urls(estilo),
        "assinaturas_estilo": list(estilo.assinaturas.all()),
        "cliente_origem": cliente_origem,
    })


def _initial_fluxo_procuracao(cliente_origem, categoria_procuracao):
    return {"categoria": categoria_procuracao.pk} if cliente_origem else {}


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
        "anexos": modelo.anexos.all(),
        "pode_editar": eh_dono or _pode_editar_alheio(request.user),
        "pode_excluir": eh_dono or _pode_excluir_alheio(request.user),
    })


@login_required
def anexo_peca(request, pk, anexo_pk):
    """Documento anexado a uma peça gerada — mesmo acesso da peça (banco
    compartilhado do módulo). `?baixar=1` baixa; sem, pré-visualiza."""
    if not tem_permissao_modulo(request.user, MODULO_MODELOS):
        raise PermissionDenied

    anexo = get_object_or_404(AnexoPecaGerada, pk=anexo_pk, modelo_id=pk)
    return resposta_de_arquivo(request, anexo.arquivo)


def _nome_arquivo_download(modelo, extensao):
    nome = "".join(c if c.isalnum() or c in " -_" else "_" for c in modelo.titulo).strip() or "modelo"
    return f"{nome}.{extensao}"


@login_required
def baixar_pdf(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_MODELOS):
        raise PermissionDenied

    modelo = get_object_or_404(ModeloPeca, pk=pk)
    estilo = _obter_estilo_escritorio()
    buffer = gerar_pdf_modelo(modelo, estilo)
    resposta = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    resposta["Content-Disposition"] = f'attachment; filename="{_nome_arquivo_download(modelo, "pdf")}"'
    return resposta


@login_required
def baixar_docx(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_MODELOS):
        raise PermissionDenied

    modelo = get_object_or_404(ModeloPeca, pk=pk)
    estilo = _obter_estilo_escritorio()
    buffer = gerar_docx_modelo(modelo, estilo)
    resposta = HttpResponse(
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    resposta["Content-Disposition"] = f'attachment; filename="{_nome_arquivo_download(modelo, "docx")}"'
    return resposta


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
def editar_estilo_documento(request):
    if not tem_permissao_modulo(request.user, MODULO_MODELOS):
        raise PermissionDenied
    if not _pode_editar_estilo(request.user):
        raise PermissionDenied

    destino = f"{reverse('modelos:lista')}?aba=estilo"

    if request.method != "POST":
        return redirect(destino)

    estilo = _obter_estilo_escritorio()
    arquivos_antigos = _arquivos_estilo_documento_atuais(estilo)
    form = EstiloDocumentoForm(request.POST, request.FILES, instance=estilo)
    if form.is_valid():
        _substituir_arquivos_estilo_documento(arquivos_antigos, request)
        form.save()
        return redirect(destino)

    config_documento_atual = form.cleaned_data.get("config_documento", estilo.config_documento)
    return render(request, "modelos/lista.html", {
        "modelos": _listar_modelos(""),
        "aba_ativa": "estilo",
        "busca": "",
        "item_ativo": "modelos",
        "estilo": estilo,
        "pode_editar_estilo": True,
        "form_estilo_documento": form,
        "config_documento": config_documento_atual,
        "imagens_estilo_urls": _imagens_estilo_urls(estilo),
        "assinaturas_estilo": list(estilo.assinaturas.all()),
        "form_assinatura_estilo": AssinaturaEstiloForm(),
    })


@login_required
def imagem_estilo_documento(request, slot):
    if not tem_permissao_modulo(request.user, MODULO_MODELOS):
        raise PermissionDenied

    campo = CAMPOS_IMAGEM_SLOT_ESTILO.get(slot)
    if campo is None:
        raise Http404

    estilo = _obter_estilo_escritorio()
    arquivo = getattr(estilo, campo)
    if not arquivo:
        raise Http404

    return FileResponse(arquivo.open("rb"), as_attachment=False)


@login_required
def adicionar_assinatura_estilo(request):
    """Mais de um bloco de assinatura no padrão de Meu Estilo
    (specs/modelos-estilo-simplificacao-imagens.md) — texto ou imagem,
    independente dos demais."""
    if not tem_permissao_modulo(request.user, MODULO_MODELOS):
        raise PermissionDenied
    if not _pode_editar_estilo(request.user):
        raise PermissionDenied

    destino = f"{reverse('modelos:lista')}?aba=estilo"
    if request.method != "POST":
        return redirect(destino)

    estilo = _obter_estilo_escritorio()
    form = AssinaturaEstiloForm(request.POST, request.FILES)
    if form.is_valid():
        assinatura = form.save(commit=False)
        assinatura.estilo = estilo
        proxima_ordem = estilo.assinaturas.count()
        assinatura.ordem = proxima_ordem
        assinatura.save()
    return redirect(destino)


@login_required
def ajustar_assinatura_estilo(request, pk):
    """Tamanho e posição da imagem da assinatura, ajustados arrastando na
    própria folha do editor (salvo ao soltar)."""
    if not tem_permissao_modulo(request.user, MODULO_MODELOS):
        raise PermissionDenied
    if not _pode_editar_estilo(request.user):
        raise PermissionDenied
    if request.method != "POST":
        raise Http404

    assinatura = get_object_or_404(_obter_estilo_escritorio().assinaturas, pk=pk)
    try:
        largura = int(request.POST.get("largura", ""))
    except ValueError:
        return JsonResponse({"erro": "largura inválida"}, status=400)
    alinhamento = request.POST.get("alinhamento", "")
    if alinhamento not in dict(AssinaturaEstilo.ALINHAMENTO_CHOICES):
        return JsonResponse({"erro": "alinhamento inválido"}, status=400)
    assinatura.largura = max(10, min(100, largura))
    assinatura.alinhamento = alinhamento
    assinatura.save(update_fields=["largura", "alinhamento"])
    return JsonResponse({"largura": assinatura.largura, "alinhamento": assinatura.alinhamento})


@login_required
def remover_assinatura_estilo(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_MODELOS):
        raise PermissionDenied
    if not _pode_editar_estilo(request.user):
        raise PermissionDenied

    destino = f"{reverse('modelos:lista')}?aba=estilo"
    if request.method == "POST":
        estilo = _obter_estilo_escritorio()
        assinatura = get_object_or_404(estilo.assinaturas, pk=pk)
        if assinatura.imagem:
            assinatura.imagem.storage.delete(assinatura.imagem.name)
        assinatura.delete()
    return redirect(destino)


@login_required
def imagem_assinatura_estilo(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_MODELOS):
        raise PermissionDenied

    estilo = _obter_estilo_escritorio()
    assinatura = get_object_or_404(estilo.assinaturas, pk=pk)
    if not assinatura.imagem:
        raise Http404
    return FileResponse(assinatura.imagem.open("rb"), as_attachment=False)


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


def _conteudo_e_metadados_peca_base(peca_base_form):
    """Resolve conteúdo/título/tipo de peça/área a partir do modo escolhido
    em PecaBaseRepetitivaForm — do acervo (ModeloPeca já existente) ou de um
    arquivo anexado só para esta geração (nunca vira ModeloPeca próprio
    antes de gerar). Retorna None em caso de erro de extração (já registrado
    em peca_base_form)."""
    dados = peca_base_form.cleaned_data
    if dados["modo_base"] == MODO_BASE_ACERVO:
        peca_base = dados["peca_base"]
        return {
            "conteudo": peca_base.conteudo,
            "titulo": peca_base.titulo,
            "categoria": peca_base.categoria,
            "area_direito": peca_base.area_direito,
        }

    try:
        conteudo = extrair_texto_documento(dados["arquivo_base"])
    except ErroImportacaoDocumento as erro:
        peca_base_form.add_error("arquivo_base", str(erro))
        return None

    return {
        "conteudo": conteudo,
        "titulo": Path(dados["arquivo_base"].name).stem.strip() or "Peça base",
        "categoria": dados["categoria"],
        "area_direito": dados["area_direito"],
    }


@login_required
def gerar_pecas_repetitivas(request):
    if not tem_permissao_modulo(request.user, MODULO_MODELOS):
        raise PermissionDenied
    if not tem_habilitacao(request.user, MODULO_MODELOS, HAB_MODELOS_CRIAR):
        raise PermissionDenied

    destino = f"{reverse('modelos:lista')}?aba=repetitivas"

    if request.method != "POST":
        return redirect(destino)

    peca_base_form = PecaBaseRepetitivaForm(request.POST, request.FILES)
    formset_casos = CasoRepetitivoFormSet(request.POST, request.FILES, prefix="casos")

    if peca_base_form.is_valid() and formset_casos.is_valid():
        casos_preenchidos = [caso for caso in formset_casos.forms if caso.tem_dados()]
        if not casos_preenchidos:
            peca_base_form.add_error(None, "Adicione ao menos um caso com dados preenchidos.")
        else:
            base = _conteudo_e_metadados_peca_base(peca_base_form)
            if base is not None:
                pecas_criadas = []
                for indice, caso_form in enumerate(casos_preenchidos, start=1):
                    dados_caso = caso_form.cleaned_data
                    documentos = dados_caso.get("documentos") or []
                    modelo = ModeloPeca.objects.create(
                        titulo=titulo_peca_caso_repetitivo(base["titulo"], dados_caso.get("cliente"), indice),
                        categoria=base["categoria"],
                        area_direito=base["area_direito"],
                        conteudo=montar_conteudo_caso_repetitivo(
                            base["conteudo"],
                            cliente=dados_caso.get("cliente"),
                            observacoes=dados_caso.get("observacoes", ""),
                            nomes_documentos=[documento.name for documento in documentos],
                        ),
                        criado_por=request.user,
                    )
                    for documento in documentos:
                        AnexoPecaGerada.objects.create(modelo=modelo, arquivo=documento)
                    pecas_criadas.append(modelo.pk)
                ids = ",".join(str(pk) for pk in pecas_criadas)
                return redirect(f"{destino}&geradas={ids}")

    return render(request, "modelos/lista.html", {
        "modelos": _listar_modelos(""),
        "aba_ativa": "repetitivas",
        "busca": "",
        "item_ativo": "modelos",
        "pode_criar_modelo": True,
        "peca_base_form": peca_base_form,
        "formset_casos": formset_casos,
        "pecas_geradas": None,
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
