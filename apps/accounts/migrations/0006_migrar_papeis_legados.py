from django.db import migrations


def migrar_papeis_legados(apps, schema_editor):
    """
    Move usuários dos grupos legados (advogado, gerente) para o grupo limitado.

    Regras:
    - Apenas usuários não-administradores são migrados.
    - Administrador = is_superuser OU PerfilUsuario.is_admin_escritorio OU grupo administrador_escritorio.
    - Os objetos Group legados NÃO são excluídos — apenas as associações de usuário são removidas.
    - MembroEquipe.eh_gerente NÃO é alterado.
    """
    Group = apps.get_model("auth", "Group")
    User = apps.get_model("auth", "User")
    PerfilUsuario = apps.get_model("accounts", "PerfilUsuario")

    grupo_limitado, _ = Group.objects.get_or_create(name="limitado")
    grupo_admin = Group.objects.filter(name="administrador_escritorio").first()

    # Coleta ids de todos os administradores (os três caminhos)
    ids_admin = set()
    ids_admin.update(User.objects.filter(is_superuser=True).values_list("id", flat=True))
    ids_admin.update(
        PerfilUsuario.objects.filter(is_admin_escritorio=True).values_list("user_id", flat=True)
    )
    if grupo_admin:
        ids_admin.update(grupo_admin.user_set.values_list("id", flat=True))

    for nome_legado in ("advogado", "gerente"):
        grupo_legado = Group.objects.filter(name=nome_legado).first()
        if not grupo_legado:
            continue
        for usuario in grupo_legado.user_set.exclude(id__in=ids_admin):
            usuario.groups.add(grupo_limitado)
            usuario.groups.remove(grupo_legado)


class Migration(migrations.Migration):
    """
    Reverse: noop deliberado.

    A migração não é reversível semanticamente: após a execução, não há registro
    de qual grupo legado (advogado ou gerente) o usuário pertencia originalmente.
    Reverter criaria associações incorretas. O noop mantém o estado atual em caso
    de rollback de migration, exigindo intervenção manual se necessário.
    """

    dependencies = [
        ("accounts", "0005_criar_grupo_limitado"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(migrar_papeis_legados, migrations.RunPython.noop),
    ]
