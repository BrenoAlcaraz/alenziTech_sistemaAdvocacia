from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.accounts.models import MembroEquipe
from apps.accounts.vinculo_equipe import sincronizar_membro_em_alvos
from apps.tarefas.models import Tarefa


def _adicionar_participante(tarefa, usuario):
    if usuario.pk == tarefa.responsavel_id:
        return
    tarefa.participantes.add(usuario)


def _remover_participante(tarefa, usuario):
    tarefa.participantes.remove(usuario)


def _sincronizar_participantes_tarefa(instance, *, ativo):
    sincronizar_membro_em_alvos(
        Tarefa, instance.equipe, instance.usuario, ativo=ativo,
        aplicar_adicao=_adicionar_participante,
        aplicar_remocao=_remover_participante,
    )


@receiver(post_save, sender=MembroEquipe)
def sincronizar_participantes_tarefa_membro_salvo(sender, instance, **kwargs):
    """Equipe adicionada como participante de uma Tarefa
    (specs/grupo-integrante-participante-dinamico.md,
    specs/tarefas-multiplos-participantes.md)."""
    _sincronizar_participantes_tarefa(instance, ativo=instance.ativo)


@receiver(post_delete, sender=MembroEquipe)
def sincronizar_participantes_tarefa_membro_removido(sender, instance, **kwargs):
    _sincronizar_participantes_tarefa(instance, ativo=False)
