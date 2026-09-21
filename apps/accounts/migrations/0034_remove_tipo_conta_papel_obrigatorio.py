# Papel de acesso como único mecanismo (PDR-0030): remove `tipo_conta` de
# PermissaoPapel e HabilitacaoPapel e torna `papel` obrigatório. As linhas
# legadas já foram descartadas na 0033.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0033_papel_limitado_de_fabrica"),
    ]

    operations = [
        # ── PermissaoPapel ────────────────────────────────────────────────
        migrations.RemoveConstraint(
            model_name="permissaopapel",
            name="uniq_permissaopapel_tipo_modulo_legado",
        ),
        migrations.RemoveConstraint(
            model_name="permissaopapel",
            name="uniq_permissaopapel_papel_modulo",
        ),
        migrations.RemoveConstraint(
            model_name="permissaopapel",
            name="chk_permissaopapel_tipo_conta_legado_ou_nulo",
        ),
        migrations.RemoveConstraint(
            model_name="permissaopapel",
            name="chk_permissaopapel_tipo_ou_papel",
        ),
        migrations.RemoveField(
            model_name="permissaopapel",
            name="tipo_conta",
        ),
        migrations.AlterField(
            model_name="permissaopapel",
            name="papel",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="permissoes_modulo",
                to="accounts.papelacesso",
                verbose_name="Papel",
            ),
        ),
        migrations.AlterModelOptions(
            name="permissaopapel",
            options={
                "ordering": ["papel", "modulo"],
                "verbose_name": "Permissão por Papel",
                "verbose_name_plural": "Permissões por Papel",
            },
        ),
        migrations.AddConstraint(
            model_name="permissaopapel",
            constraint=models.UniqueConstraint(
                fields=("papel", "modulo"),
                name="uniq_permissaopapel_papel_modulo",
            ),
        ),
        # ── HabilitacaoPapel ──────────────────────────────────────────────
        migrations.RemoveConstraint(
            model_name="habilitacaopapel",
            name="uniq_habilitacaopapel_tipo_modulo_item_legado",
        ),
        migrations.RemoveConstraint(
            model_name="habilitacaopapel",
            name="uniq_habilitacaopapel_papel_modulo_item",
        ),
        migrations.RemoveConstraint(
            model_name="habilitacaopapel",
            name="chk_habilitacaopapel_tipo_conta_legado_ou_nulo",
        ),
        migrations.RemoveConstraint(
            model_name="habilitacaopapel",
            name="chk_habilitacaopapel_tipo_ou_papel",
        ),
        migrations.RemoveField(
            model_name="habilitacaopapel",
            name="tipo_conta",
        ),
        migrations.AlterField(
            model_name="habilitacaopapel",
            name="papel",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="habilitacoes",
                to="accounts.papelacesso",
                verbose_name="Papel",
            ),
        ),
        migrations.AlterModelOptions(
            name="habilitacaopapel",
            options={
                "ordering": ["papel", "modulo", "item"],
                "verbose_name": "Habilitação por Papel",
                "verbose_name_plural": "Habilitações por Papel",
            },
        ),
        migrations.AddConstraint(
            model_name="habilitacaopapel",
            constraint=models.UniqueConstraint(
                fields=("papel", "modulo", "item"),
                name="uniq_habilitacaopapel_papel_modulo_item",
            ),
        ),
    ]
