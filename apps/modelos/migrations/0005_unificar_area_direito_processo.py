from django.db import migrations

# Modelo de Peças tinha catálogo de área do direito próprio (chaves em
# minúsculo, só 4 opções). A partir da spec area-direito-novas-areas ele
# passou a reusar Processo.AREAS_CHOICES — esta migration converte os
# valores já gravados para as novas chaves, sem perder dado existente.
MAPA_AREAS = {
    "civil": "CÍVEL",
    "consumidor": "CONSUMIDOR",
    "trabalhista": "TRABALHISTA",
    "tributario": "TRIBUTÁRIO",
}
MAPA_AREAS_REVERSO = {novo: antigo for antigo, novo in MAPA_AREAS.items()}


def migrar_valores(apps, schema_editor, mapa):
    ModeloPeca = apps.get_model("modelos", "ModeloPeca")
    VersaoModeloPeca = apps.get_model("modelos", "VersaoModeloPeca")
    for valor_antigo, valor_novo in mapa.items():
        ModeloPeca.objects.filter(area_direito=valor_antigo).update(area_direito=valor_novo)
        VersaoModeloPeca.objects.filter(area_direito=valor_antigo).update(area_direito=valor_novo)


def aplicar(apps, schema_editor):
    migrar_valores(apps, schema_editor, MAPA_AREAS)


def reverter(apps, schema_editor):
    migrar_valores(apps, schema_editor, MAPA_AREAS_REVERSO)


class Migration(migrations.Migration):

    dependencies = [
        ("modelos", "0004_estiloescritorio_arquivo_referencia_and_more"),
    ]

    operations = [
        migrations.RunPython(aplicar, reverter),
    ]
