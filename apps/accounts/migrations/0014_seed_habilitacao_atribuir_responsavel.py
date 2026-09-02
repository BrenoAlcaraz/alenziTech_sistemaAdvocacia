from django.db import migrations


HABILITACOES_DEFAULTS = [
    # (tipo_conta, modulo, item, ativo)
    ("limitado", "processos", "processos_atribuir_responsavel", False),
    ("financeiro", "processos", "processos_atribuir_responsavel", False),
]


def seed_habilitacao_atribuir_responsavel(apps, schema_editor):
    HabilitacaoPapel = apps.get_model("accounts", "HabilitacaoPapel")

    for tipo_conta, modulo, item, ativo in HABILITACOES_DEFAULTS:
        HabilitacaoPapel.objects.update_or_create(
            tipo_conta=tipo_conta,
            modulo=modulo,
            item=item,
            defaults={"ativo": ativo},
        )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0013_adicionar_habilitacao_atribuir_responsavel"),
    ]

    operations = [
        migrations.RunPython(
            seed_habilitacao_atribuir_responsavel,
            migrations.RunPython.noop,
        ),
    ]
