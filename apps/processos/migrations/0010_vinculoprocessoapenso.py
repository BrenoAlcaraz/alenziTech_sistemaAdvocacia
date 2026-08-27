import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("processos", "0009_participantes_campos_obrigatorios"),
    ]

    operations = [
        migrations.CreateModel(
            name="VinculoProcessoApenso",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                (
                    "processo_maior",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="vinculos_apensos_como_maior",
                        to="processos.processo",
                    ),
                ),
                (
                    "processo_menor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="vinculos_apensos_como_menor",
                        to="processos.processo",
                    ),
                ),
            ],
            options={
                "verbose_name": "Vínculo de processo apenso",
                "verbose_name_plural": "Vínculos de processos apensos",
            },
        ),
        migrations.AddConstraint(
            model_name="vinculoprocessoapenso",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    processo_menor_id__lt=models.F("processo_maior_id")
                ),
                name="processos_apenso_ordem_valida",
            ),
        ),
        migrations.AddConstraint(
            model_name="vinculoprocessoapenso",
            constraint=models.UniqueConstraint(
                fields=("processo_menor", "processo_maior"),
                name="processos_apenso_par_unico",
            ),
        ),
    ]
