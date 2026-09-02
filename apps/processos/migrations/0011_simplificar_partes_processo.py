from django.db import migrations, models


class Migration(migrations.Migration):
    """Simplifica ParteProcesso conforme PDR-0013.

    Substitui o modelo de três dimensões (PDR-0001/PDR-0011) — vínculo,
    posição, qualificação, MP, estado legado e classificação pendente,
    mais as entidades separadas AutoridadeProcessual, RepresentanteParte
    e HistoricoClassificacaoParte — por um único campo de papel
    processual e dois campos de texto livre para advogado, diretamente
    em ParteProcesso. Não há dado de produção a preservar (sistema ainda
    não está em produção); os dados de desenvolvimento existentes
    recebem "autor" como papel provisório, sujeito a reclassificação
    manual pela UI simplificada.
    """

    dependencies = [
        ("processos", "0010_vinculoprocessoapenso"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="parteprocesso",
            name="processos_parte_vinculo_cliente_valido",
        ),
        migrations.RemoveConstraint(
            model_name="parteprocesso",
            name="processos_parte_cliente_unico",
        ),
        migrations.RemoveConstraint(
            model_name="parteprocesso",
            name="processos_parte_pendente_valida",
        ),
        migrations.RemoveConstraint(
            model_name="parteprocesso",
            name="processos_parte_taxonomia_valida",
        ),
        migrations.RemoveConstraint(
            model_name="parteprocesso",
            name="processos_parte_atuacao_mp_valida",
        ),
        migrations.RemoveConstraint(
            model_name="parteprocesso",
            name="processos_parte_legado_valido",
        ),
        migrations.RemoveField(
            model_name="parteprocesso",
            name="cliente",
        ),
        migrations.RemoveField(
            model_name="parteprocesso",
            name="vinculo_escritorio",
        ),
        migrations.RemoveField(
            model_name="parteprocesso",
            name="posicao",
        ),
        migrations.RemoveField(
            model_name="parteprocesso",
            name="qualificacao",
        ),
        migrations.RemoveField(
            model_name="parteprocesso",
            name="atuacao_ministerio_publico",
        ),
        migrations.RemoveField(
            model_name="parteprocesso",
            name="tipo_legado",
        ),
        migrations.RemoveField(
            model_name="parteprocesso",
            name="registro_legado",
        ),
        migrations.RemoveField(
            model_name="parteprocesso",
            name="classificacao_pendente",
        ),
        migrations.AddField(
            model_name="parteprocesso",
            name="papel",
            field=models.CharField(
                choices=[
                    ("autor", "Autor"),
                    ("embargante", "Embargante"),
                    ("recorrente", "Recorrente"),
                    ("reu", "Réu"),
                    ("embargado", "Embargado"),
                    ("recorrido", "Recorrido"),
                    ("terceiro_interessado", "Terceiro Interessado"),
                    ("ministerio_publico", "Ministério Público"),
                    ("amicus_curiae", "Amicus Curiae"),
                    ("juiz", "Juiz"),
                ],
                default="autor",
                max_length=30,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="parteprocesso",
            name="advogado_nome",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="parteprocesso",
            name="advogado_oab",
            field=models.CharField(blank=True, max_length=30),
        ),
        migrations.AlterField(
            model_name="parteprocesso",
            name="nome",
            field=models.CharField(max_length=255),
        ),
        migrations.DeleteModel(
            name="HistoricoClassificacaoParte",
        ),
        migrations.DeleteModel(
            name="AutoridadeProcessual",
        ),
        migrations.DeleteModel(
            name="RepresentanteParte",
        ),
    ]
