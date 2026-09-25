from django.db import migrations


def unificar_papeis(apps, schema_editor):
    """Quem tem mais de um papel ativo passa para o Limitado; ajustes
    individuais ficam intactos."""
    UsuarioPapel = apps.get_model("accounts", "UsuarioPapel")
    PapelAcesso = apps.get_model("accounts", "PapelAcesso")

    usuarios = {}
    for usuario_id in UsuarioPapel.objects.filter(ativo=True).values_list("usuario_id", flat=True):
        usuarios[usuario_id] = usuarios.get(usuario_id, 0) + 1
    afetados = [usuario_id for usuario_id, total in usuarios.items() if total > 1]
    if not afetados:
        return

    limitado = PapelAcesso.objects.get(codigo_preset="limitado")
    UsuarioPapel.objects.filter(usuario_id__in=afetados, ativo=True).update(ativo=False)
    for usuario_id in afetados:
        UsuarioPapel.objects.update_or_create(
            usuario_id=usuario_id, papel=limitado, defaults={"ativo": True}
        )

    # Serviço real (não o model histórico) de propósito: a troca de
    # responsável precisa disparar os signals da Agenda (prazos gerados).
    # Só roda em schema com usuários afetados, que já existem hoje.
    from apps.processos.services import transferir_processos_de_usuarios_sem_acesso

    transferir_processos_de_usuarios_sem_acesso(afetados)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0006_constraints_agenda_unificada"),
        ("processos", "0004_ente_publico_parte"),
        ("agenda", "0005_avisos_item_agenda"),
    ]

    operations = [
        migrations.RunPython(unificar_papeis, migrations.RunPython.noop),
    ]
