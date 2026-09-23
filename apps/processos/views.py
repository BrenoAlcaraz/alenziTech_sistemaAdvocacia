from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import Http404
from django.urls import reverse
from django.views.decorators.http import require_POST
from apps.accounts.equipe_atalho import SelecionarMembrosEquipeForm, dados_para_js
from apps.accounts.escopo import equipe_padrao_para_usuario
from apps.accounts.decorators import usuario_admin_escritorio
from apps.accounts.models import Equipe
from apps.accounts.permissoes import nivel_acesso_modulo, tem_habilitacao, tem_permissao_modulo
from apps.accounts.permissoes_constants import (
    HAB_GERIR_HABILITAR_USUARIO_PROCESSOS,
    HAB_PROCESSOS_ANDAMENTO_ADICIONAR,
    HAB_PROCESSOS_ATRIBUIR_RESPONSAVEL,
    HAB_PROCESSOS_CRIAR,
    HAB_PROCESSOS_DOCUMENTO_ADICIONAR,
    HAB_PROCESSOS_DOCUMENTO_EXCLUIR,
    HAB_PROCESSOS_EDITAR,
    HAB_PROCESSOS_EXCLUIR,
    HAB_PROCESSOS_USAR_LABORATORIO,
    MODULO_FINANCEIRO,
    MODULO_GERIR,
    MODULO_PROCESSOS,
    NIVEL_SOMENTE_SEUS,
    NIVEL_TODOS,
)
from apps.agenda.services import agenda_do_vinculo, anexar_urls, itens_visiveis_para
from apps.atividade.services import registrar_atividade
from apps.clientes.models import Cliente
from apps.financeiro.models import SolicitacaoFinanceira
from apps.saas_tenants.storage import resposta_de_arquivo
from .models import Documento, Intimacao, ParteProcesso, Processo
from .forms import (
    AdicionarApensoForm,
    AdicionarIntegranteForm,
    DocumentoForm,
    IntimacaoForm,
    MovimentacaoProcessualForm,
    ParteProcessoForm,
    ProcessoForm,
    ProcessoResponsavelForm,
)
from .services import (
    faixa_status_do_processo,
    filtrar_processos_por_busca,
    ids_processos_apensos_do,
    nome_exibicao_usuario,
    parte_contraria_do_processo,
    recalcular_prazo_proximo,
    responsaveis_elegiveis,
    vincular_processos_apensos,
    vinculos_apensos_do,
)


User = get_user_model()

_ESCOPOS_VALIDOS = {NIVEL_SOMENTE_SEUS, NIVEL_TODOS}


def _pode_atribuir_responsavel(user):
    # tem_habilitacao já concede automaticamente ao Administrador do
    # escritório (bypass interno do kernel), independentemente desta
    # habilitação — ver apps/accounts/permissoes.py.
    return tem_habilitacao(user, MODULO_PROCESSOS, HAB_PROCESSOS_ATRIBUIR_RESPONSAVEL)


def _pode_gerenciar_integrantes(user):
    return tem_habilitacao(user, MODULO_GERIR, HAB_GERIR_HABILITAR_USUARIO_PROCESSOS)


def _pode_adicionar_documento(user):
    return tem_habilitacao(user, MODULO_PROCESSOS, HAB_PROCESSOS_DOCUMENTO_ADICIONAR)


def _pode_excluir_documento(user):
    return tem_habilitacao(user, MODULO_PROCESSOS, HAB_PROCESSOS_DOCUMENTO_EXCLUIR)


def _pode_excluir_processo(user):
    return tem_habilitacao(user, MODULO_PROCESSOS, HAB_PROCESSOS_EXCLUIR)


def _resolver_escopo(request):
    nivel_maximo = nivel_acesso_modulo(request.user, MODULO_PROCESSOS)
    if nivel_maximo not in _ESCOPOS_VALIDOS:
        nivel_maximo = NIVEL_SOMENTE_SEUS

    solicitado = request.GET.get("escopo")
    if solicitado is None:
        return nivel_maximo, nivel_maximo
    if solicitado not in _ESCOPOS_VALIDOS:
        raise PermissionDenied
    if solicitado == NIVEL_TODOS and nivel_maximo != NIVEL_TODOS:
        raise PermissionDenied
    return solicitado, nivel_maximo


def _processos_no_escopo(request, escopo):
    qs = Processo.objects.select_related("responsavel").prefetch_related("clientes")
    if escopo == NIVEL_SOMENTE_SEUS:
        qs = qs.filter(responsavel=request.user)
    return qs


def _processos_mutaveis(request):
    qs = Processo.objects.all()
    if not usuario_admin_escritorio(request.user):
        qs = qs.filter(responsavel=request.user)
    return qs


@login_required
def lista(request):
    if not tem_permissao_modulo(request.user, MODULO_PROCESSOS):
        raise PermissionDenied
    pode_usar_laboratorio = tem_habilitacao(
        request.user, MODULO_PROCESSOS, HAB_PROCESSOS_USAR_LABORATORIO
    )
    if request.GET.get("aba") == "laboratorio":
        if not pode_usar_laboratorio:
            raise PermissionDenied
        return render(request, "processos/lista.html", {
            "item_ativo": "processos",
            "aba_ativa": "laboratorio",
            "pode_usar_laboratorio": True,
        })

    escopo, escopo_maximo = _resolver_escopo(request)
    processos = _processos_no_escopo(request, escopo).exclude(status="arquivado")

    busca = (request.GET.get("busca") or "").strip()
    if busca:
        processos = filtrar_processos_por_busca(processos, busca)
    materia = request.GET.get("materia") or ""
    if materia:
        processos = processos.filter(area_direito=materia)
    status = request.GET.get("status") or ""
    if status:
        processos = processos.filter(status=status)
    cliente_id = request.GET.get("cliente") or ""
    if cliente_id:
        processos = processos.filter(clientes__id=cliente_id)
    equipe_id = request.GET.get("equipe") or ""
    if equipe_id == "nenhuma":
        processos = processos.filter(equipe__isnull=True)
    elif equipe_id:
        processos = processos.filter(equipe_id=equipe_id)

    return render(request, "processos/lista.html", {
        "processos": processos,
        "item_ativo": "processos",
        "aba_ativa": "processos",
        "pode_usar_laboratorio": pode_usar_laboratorio,
        "novo_url": reverse("processos:novo"),
        "escopo_atual": escopo,
        "escopo_maximo": escopo_maximo,
        "filtro_busca": busca,
        "filtro_materia": materia,
        "filtro_status": status,
        "filtro_cliente": cliente_id,
        "filtro_equipe": equipe_id,
        "areas_choices": Processo.AREAS_CHOICES,
        "status_choices": Processo.STATUS_CHOICES,
        "clientes_filtro": Cliente.objects.filter(ativo=True).order_by("nome_razao_social"),
        "equipes_filtro": Equipe.objects.filter(ativo=True).order_by("nome"),
    })


def _anexar_item_do_prazo(user, prazos):
    """`mov.item_prazo`: o Prazo da Agenda Jurídica gerado pelo andamento,
    só quando o usuário o enxerga na agenda."""
    itens = anexar_urls(list(
        itens_visiveis_para(user).filter(movimentacao_origem__in=[mov.pk for mov in prazos])
    ), user)
    por_andamento = {item.movimentacao_origem_id: item for item in itens}
    for mov in prazos:
        mov.item_prazo = por_andamento.get(mov.pk)


@login_required
def detalhe(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_PROCESSOS):
        raise PermissionDenied
    escopo, _ = _resolver_escopo(request)
    processo = get_object_or_404(
        _processos_no_escopo(request, escopo).prefetch_related(
            "partes",
            "movimentacoes",
            "integrantes_habilitados",
        ),
        pk=pk,
    )
    pode_modificar = (
        usuario_admin_escritorio(request.user)
        or processo.responsavel_id == request.user.pk
    )
    pode_gerenciar_integrantes = _pode_gerenciar_integrantes(request.user)
    pode_adicionar_documento = pode_modificar and _pode_adicionar_documento(request.user)
    pode_excluir_documento = pode_modificar and _pode_excluir_documento(request.user)
    pode_excluir_processo = pode_modificar and _pode_excluir_processo(request.user)
    partes = list(processo.partes.all())
    for parte in partes:
        if pode_modificar:
            parte.form_editar = ParteProcessoForm(instance=parte, processo=processo)
    vinculos_apensos = list(
        vinculos_apensos_do(
            processo,
            processos_visiveis=_processos_no_escopo(request, escopo),
        ).select_related(
            "processo_menor__responsavel",
            "processo_maior__responsavel",
        ).prefetch_related(
            "processo_menor__clientes",
            "processo_maior__clientes",
        )
    )
    processos_apensos = [
        vinculo.outro_processo(processo) for vinculo in vinculos_apensos
    ]
    ids_mutaveis = set(
        _processos_mutaveis(request)
        .filter(pk__in=[apenso.pk for apenso in processos_apensos])
        .values_list("pk", flat=True)
    )
    apensos = [
        {
            "vinculo": vinculo,
            "processo": apenso,
            "pode_remover": pode_modificar and apenso.pk in ids_mutaveis,
        }
        for vinculo, apenso in zip(vinculos_apensos, processos_apensos)
    ]
    candidatos_apenso = Processo.objects.none()
    if pode_modificar:
        candidatos_apenso = (
            _processos_mutaveis(request)
            .exclude(pk=processo.pk)
            .exclude(pk__in=ids_processos_apensos_do(processo))
            .order_by("numero", "titulo", "pk")
        )
    form_apenso = AdicionarApensoForm(
        processo_origem=processo,
        processos_queryset=candidatos_apenso,
    )
    integrantes = list(processo.integrantes_habilitados.all())
    candidatos_integrante = User.objects.none()
    equipe_atalho = None
    if pode_gerenciar_integrantes:
        candidatos_integrante = responsaveis_elegiveis().exclude(
            pk__in=[integrante.pk for integrante in integrantes]
        )
        equipe_atalho = dados_para_js(
            responsaveis_elegiveis(), presentes=[integrante.pk for integrante in integrantes]
        )
    form_integrante = AdicionarIntegranteForm(usuarios_queryset=candidatos_integrante)
    documentos = list(processo.documentos.select_related("autor"))
    movimentacoes = list(processo.movimentacoes.select_related("origem_prazo").order_by("-data"))
    prazos = sorted(
        (mov for mov in movimentacoes if mov.data_prazo),
        key=lambda mov: mov.data_prazo,
    )
    agenda_do_processo = agenda_do_vinculo(request.user, processo=processo)
    _anexar_item_do_prazo(request.user, prazos)
    custas_financeiras = list(
        SolicitacaoFinanceira.objects.filter(processo=processo)
        .select_related("solicitante")
        .order_by("-criado_em")
    )
    return render(request, "processos/detalhe.html", {
        "processo": processo,
        "movimentacoes": movimentacoes,
        "prazos": prazos,
        "parte_contraria": parte_contraria_do_processo(processo, partes=partes),
        "faixa_status": faixa_status_do_processo(processo, movimentacoes=movimentacoes),
        "agenda_do_processo": agenda_do_processo,
        "custas_financeiras": custas_financeiras,
        "custas_total": len(custas_financeiras),
        "pode_criar_solicitacao_financeira": tem_permissao_modulo(request.user, MODULO_FINANCEIRO),
        "documentos": documentos,
        "documentos_total": len(documentos),
        "form_documento": DocumentoForm(),
        "pode_adicionar_documento": pode_adicionar_documento,
        "pode_excluir_documento": pode_excluir_documento,
        "pode_excluir_processo": pode_excluir_processo,
        "partes": partes,
        "partes_polo_ativo": [p for p in partes if p.grupo_visual == "polo_ativo"],
        "partes_polo_passivo": [p for p in partes if p.grupo_visual == "polo_passivo"],
        "partes_outros": [p for p in partes if p.grupo_visual == "outros"],
        "participantes_total": len(partes),
        "apensos": apensos,
        "apensos_total": len(apensos),
        "form_apenso": form_apenso,
        "tem_candidatos_apenso": candidatos_apenso.exists(),
        "integrantes": integrantes,
        "integrantes_total": len(integrantes),
        "form_integrante": form_integrante,
        "tem_candidatos_integrante": candidatos_integrante.exists(),
        "pode_gerenciar_integrantes": pode_gerenciar_integrantes,
        "equipe_atalho": equipe_atalho,
        "form_parte": ParteProcessoForm(processo=processo),
        "form_parte_contraparte": ParteProcessoForm(processo=processo, auto_id="id_contraparte_%s"),
        "papel_contraparte": ParteProcesso.PAPEL_CONTRAPARTE,
        "papeis_cadastrados": [parte.papel for parte in partes],
        "form_movimentacao": MovimentacaoProcessualForm(processo=processo),
        "aba_ativa": request.GET.get("aba", "andamentos"),
        "item_ativo": "processos",
        "pode_modificar": pode_modificar,
    })


@login_required
@require_POST
def adicionar_apenso(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_PROCESSOS):
        raise PermissionDenied
    _resolver_escopo(request)
    with transaction.atomic():
        mutaveis = _processos_mutaveis(request).select_for_update()
        processo = get_object_or_404(mutaveis, pk=pk)
        formulario = AdicionarApensoForm(
            request.POST,
            processo_origem=processo,
            processos_queryset=mutaveis.exclude(pk=processo.pk),
        )
        if not formulario.is_valid():
            raise Http404
        processo_apenso = get_object_or_404(
            mutaveis,
            pk=formulario.cleaned_data["processo_apenso"].pk,
        )
        vincular_processos_apensos(processo, processo_apenso)
    registrar_atividade(
        request.user, "processo_apenso_adicionado",
        f"Vinculou o processo {processo_apenso} como apenso de {processo}",
        processo=processo,
    )
    return redirect(f"{reverse('processos:detalhe', args=[pk])}?aba=apensos")


@login_required
@require_POST
def remover_apenso(request, pk, vinculo_pk):
    if not tem_permissao_modulo(request.user, MODULO_PROCESSOS):
        raise PermissionDenied
    _resolver_escopo(request)
    with transaction.atomic():
        mutaveis = _processos_mutaveis(request).select_for_update()
        processo = get_object_or_404(mutaveis, pk=pk)
        vinculo = get_object_or_404(
            vinculos_apensos_do(processo).select_for_update(),
            pk=vinculo_pk,
        )
        processo_apenso = vinculo.outro_processo(processo)
        get_object_or_404(mutaveis, pk=processo_apenso.pk)
        vinculo.delete()
    registrar_atividade(
        request.user, "processo_apenso_removido",
        f"Removeu o vínculo de apenso entre {processo} e {processo_apenso}",
        processo=processo,
    )
    return redirect(f"{reverse('processos:detalhe', args=[pk])}?aba=apensos")


@login_required
@require_POST
def adicionar_integrante(request, pk):
    if not _pode_gerenciar_integrantes(request.user):
        raise PermissionDenied
    processo = get_object_or_404(Processo, pk=pk)
    formulario = AdicionarIntegranteForm(
        request.POST,
        usuarios_queryset=responsaveis_elegiveis().exclude(
            pk__in=processo.integrantes_habilitados.values("pk")
        ),
    )
    if not formulario.is_valid():
        raise Http404
    usuario_integrante = formulario.cleaned_data["usuario"]
    processo.integrantes_habilitados.add(usuario_integrante)
    registrar_atividade(
        request.user, "processo_integrante_adicionado",
        f"Habilitou {nome_exibicao_usuario(usuario_integrante)} no processo {processo}",
        processo=processo,
    )
    return redirect("processos:detalhe", pk=pk)


@login_required
@require_POST
def remover_integrante(request, pk, usuario_pk):
    if not _pode_gerenciar_integrantes(request.user):
        raise PermissionDenied
    processo = get_object_or_404(Processo, pk=pk)
    usuario = get_object_or_404(processo.integrantes_habilitados, pk=usuario_pk)
    processo.integrantes_habilitados.remove(usuario)
    registrar_atividade(
        request.user, "processo_integrante_removido",
        f"Removeu a habilitação de {nome_exibicao_usuario(usuario)} no processo {processo}",
        processo=processo,
    )
    return redirect("processos:detalhe", pk=pk)


@login_required
@require_POST
def adicionar_equipe_integrante(request, pk):
    """Equipe como atalho de seleção (PDR-0028): a lista de conferência
    envia só pessoas; nada da equipe é gravado. Não afeta o responsável
    principal, mesma habilitação de sempre."""
    if not _pode_gerenciar_integrantes(request.user):
        raise PermissionDenied
    processo = get_object_or_404(Processo, pk=pk)
    formulario = SelecionarMembrosEquipeForm(
        request.POST, usuarios_elegiveis=responsaveis_elegiveis()
    )
    if not formulario.is_valid():
        raise Http404
    ja_integrantes = set(processo.integrantes_habilitados.values_list("pk", flat=True))
    for usuario in formulario.cleaned_data["usuarios"]:
        if usuario.pk in ja_integrantes:
            continue
        processo.integrantes_habilitados.add(usuario)
        registrar_atividade(
            request.user, "processo_integrante_adicionado",
            f"Habilitou {nome_exibicao_usuario(usuario)} no processo {processo}",
            processo=processo,
        )
    return redirect("processos:detalhe", pk=pk)


@login_required
def novo(request):
    if not tem_permissao_modulo(request.user, MODULO_PROCESSOS):
        raise PermissionDenied
    if not tem_habilitacao(request.user, MODULO_PROCESSOS, HAB_PROCESSOS_CRIAR):
        raise PermissionDenied
    pode_atribuir_responsavel = _pode_atribuir_responsavel(request.user)
    FormClass = ProcessoResponsavelForm if pode_atribuir_responsavel else ProcessoForm
    form_kwargs = (
        {"responsaveis_queryset": responsaveis_elegiveis()}
        if pode_atribuir_responsavel else {}
    )
    if request.method == "POST":
        form = FormClass(request.POST, **form_kwargs)
        if form.is_valid():
            processo = form.save(commit=False)
            if not pode_atribuir_responsavel:
                processo.responsavel = request.user
            processo.status = "ativo"
            if not processo.equipe:
                processo.equipe = equipe_padrao_para_usuario(request.user)
            processo.save()
            form.save_m2m()
            registrar_atividade(
                request.user, "processo_criado",
                f"Criou o processo {processo}",
                processo=processo,
            )
            return redirect("processos:detalhe", pk=processo.pk)
    else:
        initial = {"responsavel": request.user.pk} if pode_atribuir_responsavel else {}
        cliente_id = request.GET.get("cliente")
        if cliente_id and Cliente.objects.filter(pk=cliente_id, ativo=True).exists():
            # Criação cruzada a partir da aba Processos do Cliente
            # (specs/cliente-processo-criacao-cruzada.md) — mesmo padrão de
            # pré-preenchimento por querystring já usado em Custas Judiciais.
            initial["clientes"] = [cliente_id]
        form = FormClass(initial=initial, **form_kwargs)
    return render(request, "processos/form.html", {
        "modo": "novo",
        "form": form,
        "item_ativo": "processos",
        "pode_atribuir_responsavel": pode_atribuir_responsavel,
        "responsavel_exibido": request.user,
    })


@login_required
def editar(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_PROCESSOS):
        raise PermissionDenied
    if not tem_habilitacao(request.user, MODULO_PROCESSOS, HAB_PROCESSOS_EDITAR):
        raise PermissionDenied
    _resolver_escopo(request)
    processo = get_object_or_404(_processos_mutaveis(request), pk=pk)
    pode_atribuir_responsavel = _pode_atribuir_responsavel(request.user)
    FormClass = ProcessoResponsavelForm if pode_atribuir_responsavel else ProcessoForm
    form_kwargs = (
        {"responsaveis_queryset": responsaveis_elegiveis()}
        if pode_atribuir_responsavel else {}
    )
    if request.method == "POST":
        form = FormClass(request.POST, instance=processo, **form_kwargs)
        if form.is_valid():
            form.save()
            registrar_atividade(
                request.user, "processo_editado",
                f"Editou o processo {processo}",
                processo=processo,
            )
            return redirect("processos:detalhe", pk=processo.pk)
    else:
        form = FormClass(instance=processo, **form_kwargs)
    return render(request, "processos/form.html", {
        "modo": "editar",
        "form": form,
        "item_ativo": "processos",
        "pode_atribuir_responsavel": pode_atribuir_responsavel,
        "responsavel_exibido": processo.responsavel,
    })


@login_required
def arquivados(request):
    if not tem_permissao_modulo(request.user, MODULO_PROCESSOS):
        raise PermissionDenied
    escopo, escopo_maximo = _resolver_escopo(request)
    processos = _processos_no_escopo(request, escopo).filter(status="arquivado")
    return render(request, "processos/arquivados.html", {
        "processos": processos,
        "item_ativo": "processos",
        "escopo_atual": escopo,
        "escopo_maximo": escopo_maximo,
        "usuario_e_admin": usuario_admin_escritorio(request.user),
    })


@login_required
def arquivar(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_PROCESSOS):
        raise PermissionDenied
    _resolver_escopo(request)
    processo = get_object_or_404(_processos_mutaveis(request), pk=pk)
    if request.method == "POST":
        processo.status = "arquivado"
        processo.save()
        registrar_atividade(
            request.user, "processo_arquivado",
            f"Arquivou o processo {processo}",
            processo=processo,
        )
    return redirect("processos:detalhe", pk=pk)


@login_required
def reabrir(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_PROCESSOS):
        raise PermissionDenied
    _resolver_escopo(request)
    processo = get_object_or_404(_processos_mutaveis(request), pk=pk)
    if request.method == "POST":
        processo.status = "ativo"
        processo.save()
        registrar_atividade(
            request.user, "processo_reaberto",
            f"Reabriu o processo {processo}",
            processo=processo,
        )
    return redirect("processos:detalhe", pk=pk)


@login_required
@require_POST
def excluir(request, pk):
    """Exclusão definitiva — distinta de arquivar. Remove o Processo e
    tudo que é intrínseco a ele (Documentos, Partes, Andamentos, Apensos,
    Intimações já cascateiam pelo modelo; os Prazos da agenda gerados
    pelos andamentos saem junto com eles). Registros de outros módulos
    (lançamentos financeiros, demais itens da agenda) não são apagados —
    a FK deles já é SET_NULL, então só perdem a referência."""
    if not tem_permissao_modulo(request.user, MODULO_PROCESSOS):
        raise PermissionDenied
    if not _pode_excluir_processo(request.user):
        raise PermissionDenied
    _resolver_escopo(request)
    processo = get_object_or_404(_processos_mutaveis(request), pk=pk)
    titulo = str(processo)
    registrar_atividade(
        request.user, "processo_excluido",
        f"Excluiu definitivamente o processo {titulo}",
    )
    processo.delete()
    return redirect("processos:lista")


@login_required
def adicionar_movimentacao(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_PROCESSOS):
        raise PermissionDenied
    if not tem_habilitacao(request.user, MODULO_PROCESSOS, HAB_PROCESSOS_ANDAMENTO_ADICIONAR):
        raise PermissionDenied
    _resolver_escopo(request)
    processo = get_object_or_404(_processos_mutaveis(request), pk=pk)
    if request.method == "POST":
        form = MovimentacaoProcessualForm(request.POST, processo=processo)
        if form.is_valid():
            movimentacao = form.save(commit=False)
            movimentacao.processo = processo
            movimentacao.autor = request.user
            movimentacao.save()
            campos_processo_atualizados = []
            novo_prazo_proximo = recalcular_prazo_proximo(processo)
            if novo_prazo_proximo != processo.prazo_proximo:
                processo.prazo_proximo = novo_prazo_proximo
                campos_processo_atualizados.append("prazo_proximo")
            novo_resultado = form.cleaned_data.get("atualizar_resultado_sentenca")
            if novo_resultado:
                processo.resultado_sentenca = novo_resultado
                campos_processo_atualizados.append("resultado_sentenca")
            nova_fase_andamento = form.cleaned_data.get("atualizar_fase_andamento")
            if nova_fase_andamento:
                processo.fase_andamento_atual = nova_fase_andamento
                campos_processo_atualizados.append("fase_andamento_atual")
            nova_situacao = form.cleaned_data.get("atualizar_situacao")
            if nova_situacao and processo.status != "arquivado":
                processo.status = nova_situacao
                campos_processo_atualizados.append("status")
            if campos_processo_atualizados:
                processo.save(update_fields=campos_processo_atualizados)
            registrar_atividade(
                request.user, "processo_andamento_adicionado",
                f"Adicionou andamento ({movimentacao.get_tipo_display()}) no processo {processo}",
                processo=processo,
            )
    return redirect(f"{reverse('processos:detalhe', args=[pk])}?aba=andamentos")


@login_required
def adicionar_parte(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_PROCESSOS):
        raise PermissionDenied
    _resolver_escopo(request)
    processo = get_object_or_404(_processos_mutaveis(request), pk=pk)
    if request.method == "POST":
        form = ParteProcessoForm(request.POST, processo=processo)
        if form.is_valid():
            parte = form.save(commit=False)
            parte.processo = processo
            parte.save()
            registrar_atividade(
                request.user, "processo_parte_adicionada",
                f"Adicionou parte ({parte.get_papel_display()}) no processo {processo}",
                processo=processo,
            )
    return redirect(f"{reverse('processos:detalhe', args=[pk])}?aba=partes")


@login_required
def editar_parte(request, pk, parte_pk):
    if not tem_permissao_modulo(request.user, MODULO_PROCESSOS):
        raise PermissionDenied
    _resolver_escopo(request)
    processo = get_object_or_404(_processos_mutaveis(request), pk=pk)
    parte = get_object_or_404(processo.partes, pk=parte_pk)
    if request.method == "POST":
        form = ParteProcessoForm(request.POST, instance=parte, processo=processo)
        if form.is_valid():
            form.save()
            registrar_atividade(
                request.user, "processo_parte_editada",
                f"Editou parte ({parte.get_papel_display()}) no processo {processo}",
                processo=processo,
            )
    return redirect(f"{reverse('processos:detalhe', args=[pk])}?aba=partes")


@login_required
@require_POST
def adicionar_documento(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_PROCESSOS):
        raise PermissionDenied
    if not _pode_adicionar_documento(request.user):
        raise PermissionDenied
    _resolver_escopo(request)
    processo = get_object_or_404(_processos_mutaveis(request), pk=pk)
    form = DocumentoForm(request.POST, request.FILES)
    if form.is_valid():
        documento = form.save(commit=False)
        documento.processo = processo
        documento.autor = request.user
        documento.save()
        registrar_atividade(
            request.user, "processo_documento_adicionado",
            f"Adicionou documento ({documento.get_tipo_display()}) no processo {processo}",
            processo=processo,
        )
    return redirect(f"{reverse('processos:detalhe', args=[pk])}?aba=documentos")


@login_required
@require_POST
def excluir_documento(request, pk, documento_pk):
    if not tem_permissao_modulo(request.user, MODULO_PROCESSOS):
        raise PermissionDenied
    if not _pode_excluir_documento(request.user):
        raise PermissionDenied
    _resolver_escopo(request)
    processo = get_object_or_404(_processos_mutaveis(request), pk=pk)
    documento = get_object_or_404(processo.documentos, pk=documento_pk)
    descricao_tipo = documento.get_tipo_display()
    documento.delete()
    registrar_atividade(
        request.user, "processo_documento_excluido",
        f"Excluiu documento ({descricao_tipo}) do processo {processo}",
        processo=processo,
    )
    return redirect(f"{reverse('processos:detalhe', args=[pk])}?aba=documentos")


@login_required
def baixar_documento(request, documento_pk):
    if not tem_permissao_modulo(request.user, MODULO_PROCESSOS):
        raise PermissionDenied
    escopo, _ = _resolver_escopo(request)
    documento = get_object_or_404(
        Documento.objects.filter(processo__in=_processos_no_escopo(request, escopo)),
        pk=documento_pk,
    )
    if not documento.arquivo:
        raise Http404
    return resposta_de_arquivo(request, documento.arquivo, documento.nome_do_documento())


@login_required
def baixar_comprovante_custa(request, solicitacao_pk):
    """Comprovante de pagamento de uma custa judicial (Financeiro), aberto
    a partir da aba Custas Judiciais do processo — mesma visibilidade da
    aba (qualquer usuário que veja o processo, sem exigir o módulo
    Financeiro nem o escopo dados_próprios/dados_todos que protege o
    mesmo arquivo dentro de Financeiro)."""
    if not tem_permissao_modulo(request.user, MODULO_PROCESSOS):
        raise PermissionDenied
    escopo, _ = _resolver_escopo(request)
    solicitacao = get_object_or_404(
        SolicitacaoFinanceira.objects.filter(processo__in=_processos_no_escopo(request, escopo)),
        pk=solicitacao_pk,
    )
    if not solicitacao.comprovante_pagamento:
        raise Http404
    return resposta_de_arquivo(request, solicitacao.comprovante_pagamento)


# ── Intimações (specs/dashboard-intimacoes.md) ──────────────────────────────

@login_required
def nova_intimacao(request):
    """Criação manual — sem e-mail nesta versão. Processo limitado ao
    escopo de mutação de quem cria, mesma regra dos demais formulários
    de Processo."""
    if not tem_permissao_modulo(request.user, MODULO_PROCESSOS):
        raise PermissionDenied
    processos_queryset = _processos_mutaveis(request).exclude(status="arquivado")
    if request.method == "POST":
        form = IntimacaoForm(request.POST, processos_queryset=processos_queryset)
        if form.is_valid():
            intimacao = form.save(commit=False)
            intimacao.criado_por = request.user
            intimacao.origem = "manual"
            intimacao.save()
            return redirect("dashboard:painel")
    else:
        form = IntimacaoForm(processos_queryset=processos_queryset)
    return render(request, "processos/form_intimacao.html", {
        "form": form,
        "item_ativo": "painel",
    })


@login_required
@require_POST
def manifestar_intimacao(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_PROCESSOS):
        raise PermissionDenied
    intimacao = get_object_or_404(
        Intimacao.objects.filter(processo__in=_processos_mutaveis(request)), pk=pk
    )
    intimacao.status = "manifestada"
    intimacao.save()
    return redirect("dashboard:painel")
