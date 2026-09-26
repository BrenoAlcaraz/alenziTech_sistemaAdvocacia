"""
Acompanhamento automático de processos pelo DJEN (PDR-0037): cada
publicação de um processo acompanhado vira andamento "Intimação"
sugerido, com o prazo calculado a partir do texto quando possível. Roda
dentro do schema do escritório corrente (ver o comando
`acompanhar_processos`).
"""

import hashlib
import logging
import re
import unicodedata
from datetime import datetime, time, timedelta

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import PerfilUsuario
from apps.notificacoes.models import Notificacao

from .dias_uteis import vencimento_intimacao_djen
from .djen import buscar_comunicacoes
from .extracao_prazo import extrair_prazo, texto_da_intimacao
from .models import (
    AcompanhamentoProcesso,
    ComunicacaoDjen,
    ExecucaoAcompanhamento,
    MovimentacaoProcessual,
    Processo,
)
from .services import recalcular_prazo_proximo

logger = logging.getLogger(__name__)

# Primeira consulta: publicações recentes viram só aviso, sem andamento.
DIAS_ANTERIORES_PRIMEIRA_CONSULTA = 15
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


def processos_acompanhados():
    """Número CNJ válido, exceto arquivado e segredo de justiça."""
    candidatos = (
        Processo.objects.exclude(status="arquivado")
        .filter(segredo_justica=False)
        .exclude(numero="")
        .select_related("responsavel")
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


def _nome_normalizado(nome):
    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    return " ".join(sem_acento.casefold().split())


def _chave_grupo(comunicacao):
    texto = texto_da_intimacao(comunicacao.texto)
    base = f"{comunicacao.data_disponibilizacao.isoformat()}|{texto}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def _unicos(valores):
    return list(dict.fromkeys(v for v in valores if v))


def _notificar(destinatario, mensagem):
    Notificacao.objects.create(destinatario=destinatario, mensagem=mensagem[:_TAMANHO_NOTIFICACAO])


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
        _nome_normalizado(nome)
        for nome in processo.partes.filter(prazo_em_dobro=True).values_list("nome", flat=True)
    }
    return any(_nome_normalizado(nome) in beneficiarias for nome in destinatarios)


def _descricao(comunicacao, texto):
    cabecalho = f"{comunicacao.tipo or 'Publicação'} disponibilizada no DJEN em {comunicacao.data_disponibilizacao:%d/%m/%Y}"
    if comunicacao.orgao:
        cabecalho += f" — {comunicacao.orgao}"
    return f"{cabecalho}\n\n{texto}"


def _criar_andamento_sugerido(processo, grupo, oabs):
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


def _avisar_andamento_sugerido(processo, andamento):
    if andamento.prazo_a_definir:
        situacao = "prazo a definir"
    elif andamento.prazo_de == MovimentacaoProcessual.PRAZO_DE_OUTRA_PARTE:
        situacao = f"prazo da outra parte em {andamento.data_prazo:%d/%m}"
    else:
        situacao = f"prazo sugerido para {andamento.data_prazo:%d/%m}"
    _notificar(processo.responsavel, f"Intimação sugerida (DJEN) no processo {processo}: {situacao} — confira")


def _primeira_consulta(processo, hoje, buscar):
    inicio = hoje - timedelta(days=DIAS_ANTERIORES_PRIMEIRA_CONSULTA)
    grupos = _agrupar_novas(buscar(digitos(processo.numero), inicio, hoje))
    with transaction.atomic():
        for chave, grupo in grupos.items():
            _registrar(processo, grupo, chave, anterior=True)
        AcompanhamentoProcesso.objects.create(processo=processo, djen_consultado_ate=hoje)
        if grupos:
            _notificar(
                processo.responsavel,
                f"Houve publicação no DJEN antes do acompanhamento do processo {processo} — confira na aba de andamentos",
            )


def sincronizar_djen(processo, hoje, *, oabs, buscar=buscar_comunicacoes):
    """Traz as publicações novas do processo como andamento sugerido.
    Retorna quantos andamentos foram criados."""
    acompanhamento = AcompanhamentoProcesso.objects.filter(processo=processo).first()
    if acompanhamento is None:
        _primeira_consulta(processo, hoje, buscar)
        return 0
    # A janela reabre o último dia consultado: publicação disponibilizada
    # depois da consulta daquele dia ainda chega; repetida é ignorada.
    grupos = _agrupar_novas(buscar(digitos(processo.numero), acompanhamento.djen_consultado_ate, hoje))
    criados = 0
    with transaction.atomic():
        for chave, grupo in grupos.items():
            existente = ComunicacaoDjen.objects.filter(processo=processo, chave_grupo=chave).first()
            if existente is not None:
                _registrar(processo, grupo, chave, movimentacao=existente.movimentacao)
                continue
            andamento = _criar_andamento_sugerido(processo, grupo, oabs)
            _registrar(processo, grupo, chave, movimentacao=andamento)
            _avisar_andamento_sugerido(processo, andamento)
            criados += 1
        if criados:
            processo.prazo_proximo = recalcular_prazo_proximo(processo)
            processo.save(update_fields=["prazo_proximo"])
        acompanhamento.djen_consultado_ate = hoje
        acompanhamento.save(update_fields=["djen_consultado_ate"])
    return criados


def executar_acompanhamento(hoje, *, buscar=buscar_comunicacoes):
    """Execução do dia no escritório corrente. Falha num processo não
    interrompe os demais; fica contada na execução."""
    execucao = ExecucaoAcompanhamento.objects.create()
    oabs = oabs_do_escritorio()
    for processo in processos_acompanhados():
        try:
            sincronizar_djen(processo, hoje, oabs=oabs, buscar=buscar)
        except Exception as erro:  # noqa: BLE001 — isolamento por processo
            logger.exception("Acompanhamento DJEN falhou no processo %s", processo.pk)
            execucao.falhas += 1
            execucao.erro = f"{execucao.erro}\nProcesso {processo.pk}: {erro}".strip()
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
