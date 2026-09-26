import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


def responsavel_atual_vira_responsavel_atribuido(apps, schema_editor):
    # O responsável principal de hoje continua responsável (nada muda para
    # quem já usa) e fica também como `criado_por`: quem criou de fato não
    # era registrado no processo.
    Processo = apps.get_model("processos", "Processo")
    ResponsavelProcesso = apps.get_model("processos", "ResponsavelProcesso")
    ResponsavelProcesso.objects.bulk_create([
        ResponsavelProcesso(processo_id=pk, usuario_id=criado_por_id, atribuido_em=criado_em)
        for pk, criado_por_id, criado_em in Processo.objects.values_list("pk", "criado_por_id", "criado_em")
    ])


class Migration(migrations.Migration):

    dependencies = [
        ("processos", "0009_partes_gratuidade_representante"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RenameField(model_name="processo", old_name="responsavel", new_name="criado_por"),
        migrations.AlterField(
            model_name="processo",
            name="criado_por",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="processos_criados",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.CreateModel(
            name="ResponsavelProcesso",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("atribuido_em", models.DateTimeField(default=django.utils.timezone.now)),
                ("atribuido_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("processo", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="atribuicoes_responsavel", to="processos.processo")),
                ("usuario", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="atribuicoes_responsavel", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Responsável do processo",
                "verbose_name_plural": "Responsáveis do processo",
                "ordering": ["atribuido_em", "pk"],
                "constraints": [models.UniqueConstraint(fields=("processo", "usuario"), name="processos_responsavel_unico")],
            },
        ),
        migrations.AddField(
            model_name="processo",
            name="responsaveis",
            field=models.ManyToManyField(
                blank=True,
                related_name="processos_responsavel",
                through="processos.ResponsavelProcesso",
                through_fields=("processo", "usuario"),
                to=settings.AUTH_USER_MODEL,
                verbose_name="Responsáveis",
            ),
        ),
        migrations.RunPython(responsavel_atual_vira_responsavel_atribuido, migrations.RunPython.noop),
    ]
