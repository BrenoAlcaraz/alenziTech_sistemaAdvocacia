from django.db import migrations


MODULO_PROCESSOS = "processos"
GRUPOS_TECNICOS = {"limitado", "financeiro"}


def _usuario_elegivel(
    usuario,
    PerfilUsuario,
    PermissaoUsuario,
    UsuarioPapel,
    PermissaoPapel,
):
    if not usuario.is_active:
        return False

    if PerfilUsuario.objects.filter(
        user_id=usuario.pk,
        is_admin_escritorio=True,
    ).exists():
        return True

    individual = PermissaoUsuario.objects.filter(
        usuario_id=usuario.pk,
        modulo=MODULO_PROCESSOS,
    ).first()
    if individual is not None:
        return individual.ativo

    atribuicoes = UsuarioPapel.objects.filter(usuario_id=usuario.pk)
    if atribuicoes.exists():
        papeis_ativos = atribuicoes.filter(
            ativo=True,
            papel__ativo=True,
        ).values_list("papel_id", flat=True)
        return PermissaoPapel.objects.filter(
            papel_id__in=papeis_ativos,
            modulo=MODULO_PROCESSOS,
            ativo=True,
        ).exists()

    grupos = set(
        usuario.groups.filter(name__in=GRUPOS_TECNICOS).values_list(
            "name", flat=True
        )
    )
    if len(grupos) != 1:
        return False
    return PermissaoPapel.objects.filter(
        tipo_conta=grupos.pop(),
        modulo=MODULO_PROCESSOS,
        ativo=True,
    ).exists()


def normalizar_responsaveis(apps, schema_editor):
    Processo = apps.get_model("processos", "Processo")
    User = apps.get_model("auth", "User")
    PerfilUsuario = apps.get_model("accounts", "PerfilUsuario")
    PermissaoUsuario = apps.get_model("accounts", "PermissaoUsuario")
    UsuarioPapel = apps.get_model("accounts", "UsuarioPapel")
    PermissaoPapel = apps.get_model("accounts", "PermissaoPapel")

    responsaveis = {
        usuario.pk: usuario
        for usuario in User.objects.filter(
            pk__in=Processo.objects.values_list("responsavel_id", flat=True)
        ).prefetch_related("groups")
    }
    ids_inelegiveis = {
        usuario_id
        for usuario_id, usuario in responsaveis.items()
        if not _usuario_elegivel(
            usuario,
            PerfilUsuario,
            PermissaoUsuario,
            UsuarioPapel,
            PermissaoPapel,
        )
    }

    processos_a_transferir = Processo.objects.filter(responsavel__isnull=True)
    if ids_inelegiveis:
        processos_a_transferir = Processo.objects.filter(
            responsavel__isnull=True
        ) | Processo.objects.filter(responsavel_id__in=ids_inelegiveis)

    ids_processos = list(
        processos_a_transferir.values_list("pk", flat=True).distinct()
    )
    if not ids_processos:
        return

    administradores = User.objects.filter(
        is_active=True,
        perfil__is_admin_escritorio=True,
    )
    if administradores.count() != 1:
        schema = getattr(schema_editor.connection, "schema_name", "desconhecido")
        raise RuntimeError(
            "Não foi possível normalizar Processo.responsavel no schema "
            f"'{schema}': é necessário exatamente um Administrador ativo."
        )

    Processo.objects.filter(pk__in=ids_processos).update(
        responsavel_id=administradores.get().pk
    )


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0012_adicionar_constraints_tipo_ou_papel"),
        ("processos", "0004_rename_departamento_equipe"),
    ]

    operations = [
        migrations.RunPython(normalizar_responsaveis, migrations.RunPython.noop),
    ]
