"""
Acompanhamento automático de processos (PDR-0037): cada publicação do
DJEN de um processo acompanhado vira andamento "Intimação" sugerido, com
o prazo calculado a partir do texto quando possível; cada movimento
relevante do DataJud vira andamento sugerido sem prazo, e mudança de
vara/grau no tribunal atualiza o processo. Também cobra diariamente o
"prazo a definir", avisa publicação cancelada e guarda número CNJ citado
não cadastrado. Roda dentro do schema do escritório corrente (ver o
comando `acompanhar_processos`).
"""

import hashlib
import logging
import re
from datetime import datetime, time, timedelta, timezone as dt_timezone

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import PerfilUsuario
from apps.notificacoes.models import Notificacao

from .datajud import buscar_processo
from .dias_uteis import vencimento_intimacao_djen
from .djen import buscar_comunicacoes
from .extracao_prazo import extrair_prazo, texto_da_intimacao
from .models import (
    AcompanhamentoProcesso,
    ComunicacaoDjen,
    ExecucaoAcompanhamento,
    MovimentacaoProcessual,
    MovimentoDatajud,
    NumeroCnjCitado,
    Processo,
)
from .movimentos_tpu import classificar, normalizado
from .services import destinatarios_do_processo, recalcular_prazo_proximo

logger = logging.getLogger(__name__)

# Primeira consulta: publicações recentes viram só aviso, sem andamento.
DIAS_ANTERIORES_PRIMEIRA_CONSULTA = 15
# O cancelamento de uma publicação só é visto se ela ainda estiver na
# janela consultada; a consulta volta estes dias para enxergá-lo.
DIAS_VERIFICACAO_CANCELAMENTO = 30
# Hora limite da execução diária; depois dela, sem execução no dia = falha.
HORA_LIMITE_EXECUCAO = 7
AREA_PENAL = "CRIMINAL"
_TAMANHO_NOTIFICACAO = Notificacao._meta.get_field("mensagem").max_length


def digitos(texto):
    return re.sub(r"\D", "", texto or "")


def numero_cnj_valido(numero):
    """NNNNNNN-DD.AAAA.J.TR.OOOO com dígito verificador módulo 97
    (Resolução CNJ 65/2008)."""
    numero = digitos(numero)
    if len(numero) != 20:
        return False
    sequencial, verificador, resto = numero[:7], numero[7:9], numero[9:]
    return 98 - int(sequencial + resto + "00") % 97 == int(verificador)


_NUMERO_CNJ_NO_TEXTO = re.compile(r"(?<![\d.-])(\d{7}-?\d{2}\.?\d{4}\.?\d\.?\d{2}\.?\d{4})(?![\d-])")


def numeros_cnj_no_texto(texto):
    """Números CNJ válidos escritos no texto (com ou sem máscara), só
    dígitos, na ordem em que aparecem."""
    encontrados = (digitos(n) for n in _NUMERO_CNJ_NO_TEXTO.findall(texto_da_intimacao(texto)))
    return _unicos(n for n in encontrados if numero_cnj_valido(n))


def _numeros_cadastrados():
    return {digitos(n) for n in Processo.objects.exclude(numero="").values_list("numero", flat=True)}


def numeros_citados_nao_cadastrados(processo):
    """Sugestões da aba Apensos: citados que continuam sem cadastro."""
    citados = list(processo.numeros_cnj_citados.all())
    if not citados:
        return []
    cadastrados = _numeros_cadastrados()
    return [citado for citado in citados if citado.numero not in cadastrados]


def _registrar_numeros_citados(processo, texto):
    citados = [n for n in numeros_cnj_no_texto(texto) if n != digitos(processo.numero)]
    if not citados:
        return
    cadastrados = _numeros_cadastrados()
    NumeroCnjCitado.objects.bulk_create(
        [NumeroCnjCitado(processo=processo, numero=n) for n in citados if n not in cadastrados],
        ignore_conflicts=True,
    )


def processos_acompanhados():
    """Número CNJ válido, exceto arquivado e segredo de justiça."""
    candidatos = (
        Processo.objects.exclude(status="arquivado")
        .filter(segredo_justica=False)
        .exclude(numero="")
        .select_related("criado_por")
    )
    return [processo for processo in candidatos if numero_cnj_valido(processo.numero)]


def _oab(numero, uf):
    return digitos(numero).lstrip("0"), (uf or "").strip().upper()


def oabs_do_escritorio():
    return {
        _oab(numero, uf)
        for numero, uf in PerfilUsuario.objects.filter(user__is_active=True)
        .exclude(oab_numero="")
        .values_list("oab_numero", "oab_uf")
    }


def _chave_grupo(comunicacao):
    texto = texto_da_intimacao(comunicacao.texto)
    base = f"{comunicacao.data_disponibilizacao.isoformat()}|{texto}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def _unicos(valores):
    return list(dict.fromkeys(v for v in valores if v))


def _notificar(destinatario, mensagem):
    Notificacao.objects.create(destinatario=destinatario, mensagem=mensagem[:_TAMANHO_NOTIFICACAO])


def _notificar_processo(processo, mensagem):
    """Avisa todos os responsáveis do processo (ou quem criou, sem
    nenhum responsável ativo) — PDR-0039."""
    for destinatario in destinatarios_do_processo(processo):
        _notificar(destinatario, mensagem)


def _dono_do_prazo(advogados, oabs):
    """(prazo_de, sem_advogado). Sem advogado identificado: nosso cliente,
    com prazo a definir (padrão provisório J5)."""
    if not advogados:
        return MovimentacaoProcessual.PRAZO_DE_NOSSO_CLIENTE, True
    if any(_oab(a.oab, a.uf) in oabs for a in advogados):
        return MovimentacaoProcessual.PRAZO_DE_NOSSO_CLIENTE, False
    return MovimentacaoProcessual.PRAZO_DE_OUTRA_PARTE, False


def _destinatario_tem_prazo_em_dobro(processo, destinatarios):
    beneficiarias = {
        normalizado(nome)
        for nome in processo.partes.filter(prazo_em_dobro=True).values_list("nome", flat=True)
    }
    return any(normalizado(nome) in beneficiarias for nome in destinatarios)


def _descricao(comunicacao, texto):
    cabecalho = f"{comunicacao.tipo or 'Publicação'} disponibilizada no DJEN em {comunicacao.data_disponibilizacao:%d/%m/%Y}"
    if comunicacao.orgao:
        cabecalho += f" — {comunicacao.orgao}"
    return f"{cabecalho}\n\n{texto}"


def _criar_andamento_sugerido(processo, grupo, oabs, hoje):
    principal = grupo[0]
    destinatarios = _unicos(nome for c in grupo for nome in c.destinatarios)
    advogados = _unicos(a for c in grupo for a in c.advogados)
    prazo_de, sem_advogado = _dono_do_prazo(advogados, oabs)
    prazo = None
    if processo.area_direito != AREA_PENAL and not sem_advogado:
        prazo = extrair_prazo(principal.texto)
    dobrado = prazo is not None and _destinatario_tem_prazo_em_dobro(processo, destinatarios)
    data_prazo = None
    if prazo is not None:
        dias = prazo.dias * 2 if dobrado else prazo.dias
        data_prazo = vencimento_intimacao_djen(principal.data_disponibilizacao, dias, corridos=prazo.corridos)
    linhas_destinatarios = destinatarios + [
        f"Adv. {a.nome} (OAB {a.oab}/{a.uf})" for a in advogados
    ]
    return MovimentacaoProcessual.objects.create(
        processo=processo,
        tipo="intimacao",
        data=timezone.make_aware(datetime.combine(principal.data_disponibilizacao, time(12))),
        descricao=_descricao(principal, texto_da_intimacao(principal.texto)),
        data_prazo=data_prazo,
        sugerido=True,
        fonte=MovimentacaoProcessual.FONTE_DJEN,
        prazo_de=prazo_de,
        prazo_a_definir=prazo is None,
        # O aviso de andamento sugerido do dia já cobra o prazo a definir.
        prazo_a_definir_avisado_em=hoje if prazo is None else None,
        prazo_calculado=prazo is not None,
        prazo_dias=prazo.dias if prazo else None,
        prazo_dobrado=dobrado,
        link=principal.link,
        destinatarios="\n".join(linhas_destinatarios),
    )


def _registrar(processo, comunicacoes, chave, movimentacao=None, anterior=False):
    ComunicacaoDjen.objects.bulk_create([
        ComunicacaoDjen(
            processo=processo,
            hash=c.hash,
            comunicacao_id=c.id,
            chave_grupo=chave,
            data_disponibilizacao=c.data_disponibilizacao,
            link=c.link,
            movimentacao=movimentacao,
            anterior_ao_acompanhamento=anterior,
        )
        for c in comunicacoes
    ])


def _agrupar_novas(comunicacoes):
    """Comunicações ativas ainda não vistas, agrupadas por mesmo texto e
    mesma data de disponibilização (uma publicação por destinatário)."""
    vistas = set(
        ComunicacaoDjen.objects.filter(hash__in=[c.hash for c in comunicacoes]).values_list("hash", flat=True)
    )
    grupos = {}
    for comunicacao in sorted(comunicacoes, key=lambda c: (c.data_disponibilizacao, c.id)):
        if comunicacao.ativo and comunicacao.hash not in vistas:
            vistas.add(comunicacao.hash)
            grupos.setdefault(_chave_grupo(comunicacao), []).append(comunicacao)
    return grupos


def _avisar_cancelamentos(processo, comunicacoes, hoje):
    """Publicação já importada e depois cancelada no DJEN: nada é apagado,
    o responsável é avisado uma vez por publicação."""
    canceladas = [c.hash for c in comunicacoes if not c.ativo]
    if not canceladas:
        return
    novas = ComunicacaoDjen.objects.filter(processo=processo, hash__in=canceladas, cancelada_em__isnull=True)
    avisadas = {}
    for registro in novas:
        avisadas.setdefault(registro.chave_grupo, registro)
    novas.update(cancelada_em=hoje)
    for registro in avisadas.values():
        _notificar_processo(
            processo,
            f"Publicação de {registro.data_disponibilizacao:%d/%m/%Y} foi cancelada no DJEN no processo {processo} "
            "— nada foi apagado; confira o andamento",
        )


def _avisar_andamento_sugerido(processo, andamento):
    if andamento.prazo_a_definir:
        situacao = "prazo a definir"
    elif andamento.prazo_de == MovimentacaoProcessual.PRAZO_DE_OUTRA_PARTE:
        situacao = f"prazo da outra parte em {andamento.data_prazo:%d/%m}"
    else:
        situacao = f"prazo sugerido para {andamento.data_prazo:%d/%m}"
    _notificar_processo(processo, f"Intimação sugerida (DJEN) no processo {processo}: {situacao} — confira")


def _primeira_consulta(processo, hoje, buscar):
    inicio = hoje - timedelta(days=DIAS_ANTERIORES_PRIMEIRA_CONSULTA)
    grupos = _agrupar_novas(buscar(digitos(processo.numero), inicio, hoje))
    with transaction.atomic():
        for chave, grupo in grupos.items():
            _registrar(processo, grupo, chave, anterior=True)
        AcompanhamentoProcesso.objects.update_or_create(processo=processo, defaults={"djen_consultado_ate": hoje})
        if grupos:
            _notificar_processo(
                processo,
                f"Houve publicação no DJEN antes do acompanhamento do processo {processo} — confira na aba de andamentos",
            )


def sincronizar_djen(processo, hoje, *, oabs, buscar=buscar_comunicacoes):
    """Traz as publicações novas do processo como andamento sugerido.
    Retorna quantos andamentos foram criados."""
    acompanhamento = AcompanhamentoProcesso.objects.filter(processo=processo).first()
    if acompanhamento is None or acompanhamento.djen_consultado_ate is None:
        _primeira_consulta(processo, hoje, buscar)
        return 0
    # A janela de publicações novas reabre o último dia consultado:
    # publicação disponibilizada depois da consulta daquele dia ainda
    # chega; repetida é ignorada. Antes dela, só se procura cancelamento.
    consultado_ate = acompanhamento.djen_consultado_ate
    inicio = min(consultado_ate, hoje - timedelta(days=DIAS_VERIFICACAO_CANCELAMENTO))
    comunicacoes = buscar(digitos(processo.numero), inicio, hoje)
    grupos = _agrupar_novas([c for c in comunicacoes if c.data_disponibilizacao >= consultado_ate])
    criados = 0
    with transaction.atomic():
        _avisar_cancelamentos(processo, comunicacoes, hoje)
        for chave, grupo in grupos.items():
            existente = ComunicacaoDjen.objects.filter(processo=processo, chave_grupo=chave).first()
            if existente is not None:
                _registrar(processo, grupo, chave, movimentacao=existente.movimentacao)
                continue
            andamento = _criar_andamento_sugerido(processo, grupo, oabs, hoje)
            _registrar(processo, grupo, chave, movimentacao=andamento)
            _registrar_numeros_citados(processo, grupo[0].texto)
            _avisar_andamento_sugerido(processo, andamento)
            criados += 1
        if criados:
            processo.prazo_proximo = recalcular_prazo_proximo(processo)
            processo.save(update_fields=["prazo_proximo"])
        acompanhamento.djen_consultado_ate = hoje
        acompanhamento.save(update_fields=["djen_consultado_ate"])
    return criados


# Grau do DataJud → instância do cadastro; grau sem equivalente não
# altera a instância.
INSTANCIA_POR_GRAU = {"G1": "1ª Instância", "JE": "1ª Instância", "G2": "2ª Instância", "TR": "2ª Instância"}
_SEM_MOVIMENTO = datetime.min.replace(tzinfo=dt_timezone.utc)


def _registro_atual(registros):
    """Onde o processo tramita agora: o registro (grau/órgão) com o
    movimento mais recente."""
    return max(registros, key=lambda r: max((m.data_hora for m in r.movimentos), default=_SEM_MOVIMENTO))


def _importar_movimentos(processo, registros):
    vistas = set(processo.movimentos_datajud.values_list("chave", flat=True))
    movimentos = sorted(((m, r.grau) for r in registros for m in r.movimentos), key=lambda par: par[0].data_hora)
    criados = 0
    for movimento, grau in movimentos:
        if movimento.chave in vistas:
            continue
        vistas.add(movimento.chave)
        andamento = None
        classificacao = classificar(movimento, grau, processo)
        if classificacao is not None:
            tipo, descricao = classificacao
            andamento = MovimentacaoProcessual.objects.create(
                processo=processo, tipo=tipo, data=movimento.data_hora, descricao=descricao,
                sugerido=True, fonte=MovimentacaoProcessual.FONTE_DATAJUD,
            )
            criados += 1
        MovimentoDatajud.objects.create(processo=processo, chave=movimento.chave, movimentacao=andamento)
    return criados


def _atualizar_dados_do_processo(processo, acompanhamento, atual):
    """Mudança de vara/órgão julgador ou grau em relação ao último valor
    informado pelo DataJud atualiza o processo e avisa o responsável."""
    alterados, mudancas = [], []
    if atual.orgao_julgador and normalizado(atual.orgao_julgador) != normalizado(acompanhamento.datajud_orgao_julgador):
        acompanhamento.datajud_orgao_julgador = atual.orgao_julgador
        processo.vara = atual.orgao_julgador[:255]
        alterados.append("vara")
        mudancas.append(f"vara/órgão julgador: {processo.vara}")
    if atual.grau and atual.grau != acompanhamento.datajud_grau:
        acompanhamento.datajud_grau = atual.grau
        instancia = INSTANCIA_POR_GRAU.get(atual.grau)
        if instancia and instancia != processo.instancia:
            processo.instancia = instancia
            alterados.append("instancia")
            mudancas.append(f"instância: {instancia}")
    if alterados:
        processo.save(update_fields=alterados)
        _notificar_processo(
            processo,
            f"Dados do processo {processo} alterados no tribunal (DataJud) — {'; '.join(mudancas)} — confirme ou edite",
        )


def _ponto_de_partida_datajud(processo, acompanhamento, registros, atual):
    MovimentoDatajud.objects.bulk_create(
        [MovimentoDatajud(processo=processo, chave=m.chave) for r in registros for m in r.movimentos],
        ignore_conflicts=True,
    )
    acompanhamento.datajud_encontrado = True
    acompanhamento.datajud_orgao_julgador = atual.orgao_julgador
    acompanhamento.datajud_grau = atual.grau


def sincronizar_datajud(processo, *, buscar=buscar_processo):
    """Traz os movimentos relevantes novos do processo como andamento
    sugerido sem prazo. A primeira vez que o DataJud encontra o processo
    só registra o ponto de partida. Retorna quantos andamentos criou."""
    registros = buscar(digitos(processo.numero))
    if registros is None:
        return 0  # tribunal sem índice no DataJud
    criados = 0
    with transaction.atomic():
        acompanhamento, _ = AcompanhamentoProcesso.objects.get_or_create(processo=processo)
        acompanhamento.datajud_consultado_em = timezone.now()
        if registros:
            atual = _registro_atual(registros)
            if acompanhamento.datajud_encontrado:
                criados = _importar_movimentos(processo, registros)
                _atualizar_dados_do_processo(processo, acompanhamento, atual)
            else:
                _ponto_de_partida_datajud(processo, acompanhamento, registros, atual)
        acompanhamento.save()
        if criados:
            _notificar_processo(
                processo,
                f"{criados} andamento(s) sugerido(s) (DataJud) no processo {processo} — traga o documento e confira",
            )
    return criados


def _registrar_falha(execucao, processo, fonte, erro):
    logger.exception("Acompanhamento %s falhou no processo %s", fonte, processo.pk)
    execucao.falhas += 1
    execucao.erro = f"{execucao.erro}\nProcesso {processo.pk} ({fonte}): {erro}".strip()


def cobrar_prazos_a_definir(hoje):
    """Aviso diário ao responsável de cada "prazo a definir" ainda não
    resolvido (sem data informada e não rejeitado)."""
    pendentes = (
        MovimentacaoProcessual.objects.filter(prazo_a_definir=True)
        .exclude(processo__status="arquivado")
        .filter(Q(prazo_a_definir_avisado_em__isnull=True) | Q(prazo_a_definir_avisado_em__lt=hoje))
        .select_related("processo__criado_por")
    )
    for andamento in pendentes:
        with transaction.atomic():
            _notificar_processo(
                andamento.processo,
                f"Prazo a definir no processo {andamento.processo} (intimação de {timezone.localtime(andamento.data):%d/%m/%Y}) "
                "— informe a data do prazo",
            )
            andamento.prazo_a_definir_avisado_em = hoje
            andamento.save(update_fields=["prazo_a_definir_avisado_em"])


def executar_acompanhamento(hoje, *, buscar=buscar_comunicacoes, buscar_datajud=buscar_processo):
    """Execução do dia no escritório corrente. Falha num processo ou numa
    fonte não interrompe as demais; fica contada na execução."""
    execucao = ExecucaoAcompanhamento.objects.create()
    oabs = oabs_do_escritorio()
    for processo in processos_acompanhados():
        try:
            sincronizar_djen(processo, hoje, oabs=oabs, buscar=buscar)
        except Exception as erro:  # noqa: BLE001 — isolamento por processo e fonte
            _registrar_falha(execucao, processo, "DJEN", erro)
        try:
            sincronizar_datajud(processo, buscar=buscar_datajud)
        except Exception as erro:  # noqa: BLE001 — isolamento por processo e fonte
            _registrar_falha(execucao, processo, "DataJud", erro)
    try:
        cobrar_prazos_a_definir(hoje)
    except Exception as erro:  # noqa: BLE001 — a cobrança não invalida a sincronização
        logger.exception("Cobrança de prazo a definir falhou")
        execucao.falhas += 1
        execucao.erro = f"{execucao.erro}\nCobrança de prazo a definir: {erro}".strip()
    execucao.concluida_em = timezone.now()
    execucao.save(update_fields=["falhas", "erro", "concluida_em"])
    return execucao


def situacao_do_acompanhamento(agora=None):
    """Faixa "Última atualização" / "Falhou hoje". None antes da primeira
    execução no escritório."""
    ultima = ExecucaoAcompanhamento.objects.first()
    if ultima is None:
        return None
    agora = timezone.localtime(agora)
    concluida = ExecucaoAcompanhamento.objects.filter(concluida_em__isnull=False).first()
    rodou_hoje = timezone.localdate(ultima.iniciada_em) == agora.date()
    falhou_hoje = (rodou_hoje and ultima.falhou) or (not rodou_hoje and agora.hour >= HORA_LIMITE_EXECUCAO)
    return {
        "ultima_atualizacao": concluida.concluida_em if concluida else None,
        "falhou_hoje": falhou_hoje,
    }
