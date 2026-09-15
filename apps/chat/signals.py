from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.accounts.models import Equipe, MembroEquipe
from apps.chat.models import Conversa, Mensagem


@receiver(post_delete, sender=Mensagem)
def excluir_anexo_da_mensagem(sender, instance, **kwargs):
    """Remove o arquivo do storage protegido ao excluir o registro —
    inclusive em cascata (Conversa excluída) e via Django Admin, já que
    signal cobre qualquer caminho de exclusão, não só uma view."""
    if instance.anexo:
        instance.anexo.delete(save=False)


@receiver(post_save, sender=Equipe)
def sincronizar_grupo_da_equipe(sender, instance, **kwargs):
    """Toda Equipe tem um grupo de Chat correspondente (specs/chat-grupo-
    automatico-por-equipe.md) — cria na primeira gravação e mantém o
    título alinhado ao nome da equipe nas seguintes."""
    conversa, criada = Conversa.objects.get_or_create(
        equipe=instance,
        defaults={"tipo": Conversa.TIPO_GRUPO, "titulo": instance.nome},
    )
    if not criada and conversa.titulo != instance.nome:
        conversa.titulo = instance.nome
        conversa.save(update_fields=["titulo"])


@receiver(post_save, sender=MembroEquipe)
def adicionar_membro_ao_grupo(sender, instance, **kwargs):
    """Membro efetivo (ativo=True) da equipe entra automaticamente no
    grupo de chat correspondente; a saída não é sincronizada no sentido
    contrário (sair do grupo manualmente não remove da equipe)."""
    conversa, _ = Conversa.objects.get_or_create(
        equipe=instance.equipe,
        defaults={"tipo": Conversa.TIPO_GRUPO, "titulo": instance.equipe.nome},
    )
    if instance.ativo:
        conversa.participantes.add(instance.usuario)
    else:
        conversa.participantes.remove(instance.usuario)


@receiver(post_delete, sender=MembroEquipe)
def remover_membro_do_grupo(sender, instance, **kwargs):
    """Remover o membro da equipe remove do grupo de chat correspondente,
    automaticamente."""
    conversa = getattr(instance.equipe, "conversa_grupo", None)
    if conversa is not None:
        conversa.participantes.remove(instance.usuario)
