from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("processos", "0008_migrar_partes_legadas"),
    ]

    operations = [
        migrations.AlterField(
            model_name="parteprocesso",
            name="nome",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="parteprocesso",
            name="posicao",
            field=models.CharField(
                choices=[
                    ("polo_ativo", "Polo Ativo"),
                    ("polo_passivo", "Polo Passivo"),
                    ("terceiro", "Outros"),
                    ("ministerio_publico", "Outros"),
                    ("legado", "Outros — registro legado"),
                ],
                blank=True,
                max_length=30,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="parteprocesso",
            name="qualificacao",
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
                    ("advogado_contrario_legado", "Advogado Contrário — legado"),
                ],
                blank=True,
                max_length=40,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="parteprocesso",
            name="tipo_legado",
            field=models.CharField(blank=True, editable=False, max_length=30),
        ),
        migrations.AlterField(
            model_name="parteprocesso",
            name="vinculo_escritorio",
            field=models.CharField(
                choices=[
                    ("cliente", "Cliente representado"),
                    ("parte_contraria", "Parte contrária"),
                    ("outro", "Outro vínculo"),
                    ("legado", "Registro legado"),
                ],
                max_length=30,
            ),
        ),
        migrations.AddConstraint(
            model_name="parteprocesso",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(
                        ("cliente__isnull", False),
                        ("vinculo_escritorio", "cliente"),
                    )
                    | (
                        ~models.Q(("vinculo_escritorio", "cliente"))
                        & models.Q(("cliente__isnull", True))
                    )
                ),
                name="processos_parte_vinculo_cliente_valido",
            ),
        ),
        migrations.AddConstraint(
            model_name="parteprocesso",
            constraint=models.UniqueConstraint(
                condition=models.Q(("cliente__isnull", False)),
                fields=("processo", "cliente"),
                name="processos_parte_cliente_unico",
            ),
        ),
        migrations.AddConstraint(
            model_name="parteprocesso",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(
                        ("atuacao_ministerio_publico", ""),
                        ("classificacao_pendente", True),
                        ("cliente__isnull", False),
                        ("posicao__isnull", True),
                        ("qualificacao__isnull", True),
                        ("registro_legado", False),
                        ("tipo_legado", ""),
                        ("vinculo_escritorio", "cliente"),
                    )
                    | models.Q(("classificacao_pendente", False))
                ),
                name="processos_parte_pendente_valida",
            ),
        ),
        migrations.AddConstraint(
            model_name="parteprocesso",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(
                        ("classificacao_pendente", True),
                        ("posicao__isnull", True),
                        ("qualificacao__isnull", True),
                    )
                    | models.Q(("posicao", "polo_ativo"), ("qualificacao", "autor"))
                    | models.Q(("posicao", "polo_ativo"), ("qualificacao", "embargante"))
                    | models.Q(("posicao", "polo_ativo"), ("qualificacao", "recorrente"))
                    | models.Q(("posicao", "polo_passivo"), ("qualificacao", "reu"))
                    | models.Q(("posicao", "polo_passivo"), ("qualificacao", "embargado"))
                    | models.Q(("posicao", "polo_passivo"), ("qualificacao", "recorrido"))
                    | models.Q(("posicao", "terceiro"), ("qualificacao", "terceiro_interessado"))
                    | models.Q(("posicao", "terceiro"), ("qualificacao", "amicus_curiae"))
                    | models.Q(
                        ("posicao", "ministerio_publico"),
                        ("qualificacao", "ministerio_publico"),
                    )
                    | models.Q(
                        ("posicao", "legado"),
                        ("qualificacao", "advogado_contrario_legado"),
                    )
                ),
                name="processos_parte_taxonomia_valida",
            ),
        ),
        migrations.AddConstraint(
            model_name="parteprocesso",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(
                        ("atuacao_ministerio_publico__in", ["parte", "fiscal_ordem_juridica"]),
                        ("qualificacao", "ministerio_publico"),
                    )
                    | models.Q(
                        ("atuacao_ministerio_publico", ""),
                        ("qualificacao__isnull", True),
                    )
                    | models.Q(
                        ("atuacao_ministerio_publico", ""),
                        (
                            "qualificacao__in",
                            [
                                "autor",
                                "embargante",
                                "recorrente",
                                "reu",
                                "embargado",
                                "recorrido",
                                "terceiro_interessado",
                                "amicus_curiae",
                                "advogado_contrario_legado",
                            ],
                        ),
                    )
                ),
                name="processos_parte_atuacao_mp_valida",
            ),
        ),
        migrations.AddConstraint(
            model_name="parteprocesso",
            constraint=models.CheckConstraint(
                condition=(
                    (
                        models.Q(
                            ("classificacao_pendente", False),
                            ("cliente__isnull", True),
                            ("posicao", "legado"),
                            ("qualificacao", "advogado_contrario_legado"),
                            ("registro_legado", True),
                            ("vinculo_escritorio", "legado"),
                        )
                        & ~models.Q(("tipo_legado", ""))
                    )
                    | models.Q(
                        ("registro_legado", False),
                        (
                            "vinculo_escritorio__in",
                            ["cliente", "parte_contraria", "outro"],
                        ),
                    )
                    & ~models.Q(("posicao", "legado"))
                    & ~models.Q(
                        ("qualificacao", "advogado_contrario_legado")
                    )
                ),
                name="processos_parte_legado_valido",
            ),
        ),
        migrations.AlterField(
            model_name="historicoclassificacaoparte",
            name="posicao_anterior",
            field=models.CharField(
                blank=True,
                choices=[
                    ("polo_ativo", "Polo Ativo"),
                    ("polo_passivo", "Polo Passivo"),
                    ("terceiro", "Outros"),
                    ("ministerio_publico", "Outros"),
                    ("legado", "Outros — registro legado"),
                ],
                max_length=30,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="historicoclassificacaoparte",
            name="posicao_nova",
            field=models.CharField(
                choices=[
                    ("polo_ativo", "Polo Ativo"),
                    ("polo_passivo", "Polo Passivo"),
                    ("terceiro", "Outros"),
                    ("ministerio_publico", "Outros"),
                    ("legado", "Outros — registro legado"),
                ],
                max_length=30,
            ),
        ),
        migrations.AlterField(
            model_name="historicoclassificacaoparte",
            name="qualificacao_anterior",
            field=models.CharField(
                blank=True,
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
                    ("advogado_contrario_legado", "Advogado Contrário — legado"),
                ],
                max_length=40,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="historicoclassificacaoparte",
            name="qualificacao_nova",
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
                    ("advogado_contrario_legado", "Advogado Contrário — legado"),
                ],
                max_length=40,
            ),
        ),
        migrations.AlterField(
            model_name="historicoclassificacaoparte",
            name="atuacao_mp_anterior",
            field=models.CharField(
                blank=True,
                choices=[
                    ("parte", "Parte do processo"),
                    ("fiscal_ordem_juridica", "Fiscal da ordem jurídica"),
                ],
                max_length=30,
            ),
        ),
        migrations.AlterField(
            model_name="historicoclassificacaoparte",
            name="atuacao_mp_nova",
            field=models.CharField(
                blank=True,
                choices=[
                    ("parte", "Parte do processo"),
                    ("fiscal_ordem_juridica", "Fiscal da ordem jurídica"),
                ],
                max_length=30,
            ),
        ),
    ]
