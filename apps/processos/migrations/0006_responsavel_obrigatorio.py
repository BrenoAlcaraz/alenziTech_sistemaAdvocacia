import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("processos", "0005_normalizar_responsavel"),
    ]

    operations = [
        migrations.AlterField(
            model_name="processo",
            name="responsavel",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="processos",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
