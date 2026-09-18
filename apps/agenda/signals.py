from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.accounts.models import MembroEquipe
from apps.accounts.vinculo_equipe import sincronizar_membro_em_alvos
from apps.agenda.models import Compromisso, ParticipanteCompromisso


def _adicionar_participante(compromisso, usuario):
    if usuario.pk == compromisso.responsavel_id:
        # Mesma regra de `_usuarios_elegiveis_para_participante`: o
        # responsável não é convidado como participante à parte.
        return
    ParticipanteCompromisso.objects.get_or_create(compromisso=compromisso, usuario=usuario)


def _remover_participante(compromisso, usuario):
    ParticipanteCompromisso.objects.filter(compromisso=compromisso, usuario=usuario).delete()


def _sincronizar_participantes_compromisso(instance, *, ativo):
    sincronizar_membro_em_alvos(
        Compromisso, instance.equipe, instance.usuario, ativo=ativo,
        aplicar_adicao=_adicionar_participante,
        aplicar_remocao=_remover_participante,
    )


@receiver(post_save, sender=MembroEquipe)
def sincronizar_participantes_compromisso_membro_salvo(sender, instance, **kwargs):
    """Equipe adicionada como participante de um Compromisso
    (specs/grupo-integrante-participante-dinamico.md): cada membro
    entra como ParticipanteCompromisso individual e passa pelo mesmo
    fluxo de confirmação de presença de sempre (PDR-0020) — a equipe
    não pula a confirmação, só evita adicionar pessoa por pessoa."""
    _sincronizar_participantes_compromisso(instance, ativo=instance.ativo)


@receiver(post_delete, sender=MembroEquipe)
def sincronizar_participantes_compromisso_membro_removido(sender, instance, **kwargs):
    _sincronizar_participantes_compromisso(instance, ativo=False)
