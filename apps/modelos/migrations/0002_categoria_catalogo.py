import django.db.models.deletion
from django.db import migrations, models


def popular_categorias(apps, schema_editor):
    CategoriaModeloPeca = apps.get_model("modelos", "CategoriaModeloPeca")
    ModeloPeca = apps.get_model("modelos", "ModeloPeca")

    for modelo in ModeloPeca.objects.all():
        nome = (modelo.categoria or "").strip() or "Sem categoria"
        categoria, _ = CategoriaModeloPeca.objects.get_or_create(nome=nome)
        modelo.categoria_novo_id = categoria.id
        modelo.save(update_fields=["categoria_novo"])


def reverter_categorias(apps, schema_editor):
    ModeloPeca = apps.get_model("modelos", "ModeloPeca")

    for modelo in ModeloPeca.objects.select_related("categoria_novo").all():
        modelo.categoria = modelo.categoria_novo.nome if modelo.categoria_novo_id else ""
        modelo.save(update_fields=["categoria"])


class Migration(migrations.Migration):

    dependencies = [
        ("modelos", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="CategoriaModeloPeca",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=100, unique=True)),
            ],
            options={
                "verbose_name": "Categoria de Modelo de Peça",
                "verbose_name_plural": "Categorias de Modelo de Peça",
                "ordering": ["nome"],
            },
        ),
        migrations.AddField(
            model_name="modelopeca",
            name="categoria_novo",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="modelos",
                to="modelos.categoriamodelopeca",
            ),
        ),
        migrations.RunPython(popular_categorias, reverter_categorias),
        migrations.RemoveField(
            model_name="modelopeca",
            name="categoria",
        ),
        migrations.RenameField(
            model_name="modelopeca",
            old_name="categoria_novo",
            new_name="categoria",
        ),
        migrations.AlterField(
            model_name="modelopeca",
            name="categoria",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="modelos",
                to="modelos.categoriamodelopeca",
            ),
        ),
    ]
