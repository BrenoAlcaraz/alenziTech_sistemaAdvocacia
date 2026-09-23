from django.db import migrations, models


class Migration(migrations.Migration):
    """Separada da 0002: ALTER TABLE logo após o UPDATE em massa na mesma
    transação pode falhar em PostgreSQL ("pending trigger events")."""

    dependencies = [
        ("clientes", "0002_numero_interno"),
    ]

    operations = [
        migrations.AlterField(
            model_name="cliente",
            name="numero_interno",
            field=models.PositiveIntegerField(editable=False, unique=True),
        ),
    ]
