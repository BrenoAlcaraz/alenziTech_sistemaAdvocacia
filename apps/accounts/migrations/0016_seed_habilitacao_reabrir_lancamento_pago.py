from django.db import migrations


HABILITACOES_DEFAULTS = [
    # (tipo_conta, modulo, item, ativo)
    ("limitado", "financeiro", "financeiro_reabrir_lancamento_pago", False),
    ("financeiro", "financeiro", "financeiro_reabrir_lancamento_pago", False),
]


def seed_habilitacao_reabrir_lancamento_pago(apps, schema_editor):
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
        ("accounts", "0015_adicionar_habilitacao_reabrir_lancamento_pago"),
    ]

    operations = [
        migrations.RunPython(
            seed_habilitacao_reabrir_lancamento_pago,
            migrations.RunPython.noop,
        ),
    ]
