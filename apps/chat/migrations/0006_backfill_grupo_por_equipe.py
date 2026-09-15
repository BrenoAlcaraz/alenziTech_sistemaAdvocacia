from django.db import migrations


def criar_grupos_das_equipes_existentes(apps, schema_editor):
    Equipe = apps.get_model("accounts", "Equipe")
    MembroEquipe = apps.get_model("accounts", "MembroEquipe")
    Conversa = apps.get_model("chat", "Conversa")

    for equipe in Equipe.objects.all():
        conversa, _ = Conversa.objects.get_or_create(
            equipe=equipe,
            defaults={"tipo": "grupo", "titulo": equipe.nome},
        )
        ids_membros_ativos = MembroEquipe.objects.filter(
            equipe=equipe, ativo=True
        ).values_list("usuario_id", flat=True)
        conversa.participantes.set(ids_membros_ativos)


def reverter(apps, schema_editor):
    Conversa = apps.get_model("chat", "Conversa")
    Conversa.objects.filter(equipe__isnull=False).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0028_remove_habilitacaopapel_chk_habilitacaopapel_modulo_item_and_more"),
        ("chat", "0005_conversa_equipe"),
    ]

    operations = [
        migrations.RunPython(criar_grupos_das_equipes_existentes, reverter),
    ]
