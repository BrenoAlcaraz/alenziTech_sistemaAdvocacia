from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.accounts.models import MembroEquipe
from apps.accounts.vinculo_equipe import sincronizar_membro_em_alvos
from apps.processos.models import Documento, Processo


@receiver(post_delete, sender=Documento)
def excluir_arquivo_do_documento(sender, instance, **kwargs):
    """Remove o arquivo do storage protegido ao excluir o registro —
    inclusive em cascata (Processo excluído) e via Django Admin, já que
    signal cobre qualquer caminho de exclusão, não só a view."""
    if instance.arquivo:
        instance.arquivo.delete(save=False)


def _sincronizar_integrantes_processo(instance, *, ativo):
    sincronizar_membro_em_alvos(
        Processo, instance.equipe, instance.usuario, ativo=ativo,
        aplicar_adicao=lambda processo, usuario: processo.integrantes_habilitados.add(usuario),
        aplicar_remocao=lambda processo, usuario: processo.integrantes_habilitados.remove(usuario),
    )


@receiver(post_save, sender=MembroEquipe)
def sincronizar_integrantes_processo_membro_salvo(sender, instance, **kwargs):
    """Equipe adicionada como integrante de um Processo
    (specs/grupo-integrante-participante-dinamico.md): membro que entra
    ou volta a ficar ativo na equipe passa a integrar automaticamente
    todo Processo onde ela foi adicionada."""
    _sincronizar_integrantes_processo(instance, ativo=instance.ativo)


@receiver(post_delete, sender=MembroEquipe)
def sincronizar_integrantes_processo_membro_removido(sender, instance, **kwargs):
    _sincronizar_integrantes_processo(instance, ativo=False)
