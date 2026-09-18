"""
Vínculo dinâmico de Equipe como integrante/participante/atribuído
(specs/grupo-integrante-participante-dinamico.md).

Motor único, reaproveitado por Processos e Agenda (e, quando
implementada, Tarefas) — cada módulo só fornece os dois callbacks que
sabem conceder/revogar o acesso de fato no seu próprio modelo
(`aplicar_adicao`/`aplicar_remocao`); toda a contabilidade de "por que
esse usuário está aqui" (individual vs. uma ou mais equipes) fica só
aqui, em `EquipeVinculada`/`VinculoIntegrante`.

Mesmo padrão de sincronização do grupo de chat automático por equipe
(PDR-0026, `apps/chat/signals.py`): reage a `MembroEquipe` entrando/
saindo. Cada app consumidor conecta esse reator ao próprio signal de
`MembroEquipe` (ver `apps/processos/signals.py`,
`apps/agenda/signals.py`) — feito por app, não aqui, porque só o app
consumidor sabe quais dos seus próprios objetos (`EquipeVinculada`)
existem e como aplicar adição/remoção.
"""

from django.contrib.contenttypes.models import ContentType

from .models import Equipe, EquipeVinculada, VinculoIntegrante


def membros_ativos(equipe):
    """Usuários atualmente efetivos (MembroEquipe.ativo=True) da equipe."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.filter(membros_equipe__equipe=equipe, membros_equipe__ativo=True)


def equipes_vinculadas(alvo):
    """Equipes hoje adicionadas como integrante/participante/atribuído
    de `alvo` — para listar na tela e oferecer "remover"."""
    ct = ContentType.objects.get_for_model(alvo)
    return Equipe.objects.filter(
        vinculos__content_type=ct, vinculos__object_id=alvo.pk
    ).distinct()


def _materializar(ct, object_id, equipe, usuario, aplicar_adicao, alvo):
    _, criado = VinculoIntegrante.objects.get_or_create(
        content_type=ct, object_id=object_id, equipe=equipe, usuario=usuario,
    )
    if criado:
        aplicar_adicao(alvo, usuario)


def _revogar_se_sem_justificativa(ct, object_id, usuario, aplicar_remocao, alvo):
    ainda_justificado = VinculoIntegrante.objects.filter(
        content_type=ct, object_id=object_id, usuario=usuario,
    ).exists()
    if not ainda_justificado:
        aplicar_remocao(alvo, usuario)


def vincular_equipe(alvo, equipe, *, aplicar_adicao):
    """Adiciona `equipe` como integrante/participante/atribuído de
    `alvo` — materializa todos os membros efetivos atuais. Idempotente:
    equipe já vinculada não duplica nem remateralializa."""
    ct = ContentType.objects.get_for_model(alvo)
    _, criado = EquipeVinculada.objects.get_or_create(
        content_type=ct, object_id=alvo.pk, equipe=equipe,
    )
    if not criado:
        return
    for usuario in membros_ativos(equipe):
        _materializar(ct, alvo.pk, equipe, usuario, aplicar_adicao, alvo)


def desvincular_equipe(alvo, equipe, *, aplicar_remocao):
    """Remove o vínculo da equipe (não de uma pessoa individual) com
    `alvo` — desfaz o acesso de cada membro que só estava ali por causa
    dela; quem também tem vínculo individual ou de outra equipe
    permanece."""
    ct = ContentType.objects.get_for_model(alvo)
    EquipeVinculada.objects.filter(content_type=ct, object_id=alvo.pk, equipe=equipe).delete()
    linhas = list(
        VinculoIntegrante.objects.filter(content_type=ct, object_id=alvo.pk, equipe=equipe)
    )
    VinculoIntegrante.objects.filter(pk__in=[linha.pk for linha in linhas]).delete()
    for linha in linhas:
        _revogar_se_sem_justificativa(ct, alvo.pk, linha.usuario, aplicar_remocao, alvo)


def registrar_vinculo_individual(alvo, usuario):
    """Marca que `usuario` foi adicionado individualmente a `alvo` — sem
    isso, não haveria como distinguir depois "só estava aqui por causa
    da equipe" de "foi adicionado à parte", ao desvincular uma equipe."""
    ct = ContentType.objects.get_for_model(alvo)
    VinculoIntegrante.objects.get_or_create(
        content_type=ct, object_id=alvo.pk, usuario=usuario, equipe=None,
    )


def remover_vinculo_individual(alvo, usuario):
    """Desfaz só o vínculo individual — nunca mexe nas materializações
    por equipe do mesmo usuário no mesmo alvo."""
    ct = ContentType.objects.get_for_model(alvo)
    VinculoIntegrante.objects.filter(
        content_type=ct, object_id=alvo.pk, usuario=usuario, equipe=None,
    ).delete()


def remover_pessoa(alvo, usuario):
    """Remove `usuario` de `alvo` por completo — ação explícita sobre
    uma pessoa específica (botão "remover" na lista), não sobre uma
    equipe. Limpa tanto o vínculo individual quanto qualquer
    materialização por equipe, para não deixar contabilidade órfã
    (usuário volta a aparecer se reentrar numa equipe vinculada depois)."""
    ct = ContentType.objects.get_for_model(alvo)
    VinculoIntegrante.objects.filter(
        content_type=ct, object_id=alvo.pk, usuario=usuario,
    ).delete()


def sincronizar_membro_em_alvos(modelo_alvo, equipe, usuario, *, ativo, aplicar_adicao, aplicar_remocao):
    """Reage a uma mudança de `MembroEquipe` (entrou/saiu ou virou
    ativo/inativo): para todo `alvo` de `modelo_alvo` onde `equipe` foi
    adicionada, materializa ou desfaz o vínculo desse usuário."""
    ct = ContentType.objects.get_for_model(modelo_alvo)
    alvo_ids = list(
        EquipeVinculada.objects.filter(content_type=ct, equipe=equipe).values_list("object_id", flat=True)
    )
    if not alvo_ids:
        return
    for alvo in modelo_alvo.objects.filter(pk__in=alvo_ids):
        if ativo:
            _materializar(ct, alvo.pk, equipe, usuario, aplicar_adicao, alvo)
        else:
            VinculoIntegrante.objects.filter(
                content_type=ct, object_id=alvo.pk, equipe=equipe, usuario=usuario,
            ).delete()
            _revogar_se_sem_justificativa(ct, alvo.pk, usuario, aplicar_remocao, alvo)
