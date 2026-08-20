import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("clientes", "0006_cliente_responsavel_obrigatorio"),
        ("processos", "0006_responsavel_obrigatorio"),
    ]

    operations = [
        migrations.RenameField(
            model_name="parteprocesso",
            old_name="tipo",
            new_name="tipo_legado",
        ),
        migrations.AddField(
            model_name="parteprocesso",
            name="atuacao_ministerio_publico",
            field=models.CharField(
                blank=True,
                choices=[
                    ("parte", "Parte do processo"),
                    ("fiscal_ordem_juridica", "Fiscal da ordem jurídica"),
                ],
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name="parteprocesso",
            name="cliente",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="participacoes_processuais",
                to="clientes.cliente",
            ),
        ),
        migrations.AddField(
            model_name="parteprocesso",
            name="classificacao_pendente",
            field=models.BooleanField(default=False, editable=False),
        ),
        migrations.AddField(
            model_name="parteprocesso",
            name="posicao",
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
        migrations.AddField(
            model_name="parteprocesso",
            name="qualificacao",
            field=models.CharField(blank=True, max_length=40, null=True),
        ),
        migrations.AddField(
            model_name="parteprocesso",
            name="registro_legado",
            field=models.BooleanField(default=False, editable=False),
        ),
        migrations.AddField(
            model_name="parteprocesso",
            name="vinculo_escritorio",
            field=models.CharField(max_length=30, null=True),
        ),
        migrations.CreateModel(
            name="AutoridadeProcessual",
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
                (
                    "tipo",
                    models.CharField(
                        choices=[("juiz", "Juiz")],
                        default="juiz",
                        max_length=20,
                    ),
                ),
                ("nome", models.CharField(max_length=255)),
                ("vara_orgao", models.CharField(max_length=255)),
                ("observacao", models.TextField(blank=True)),
                (
                    "processo",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="autoridades",
                        to="processos.processo",
                    ),
                ),
            ],
            options={
                "verbose_name": "Autoridade processual",
                "verbose_name_plural": "Autoridades processuais",
            },
        ),
        migrations.CreateModel(
            name="RepresentanteParte",
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
                (
                    "tipo",
                    models.CharField(
                        choices=[
                            ("interno", "Advogado do escritório"),
                            ("externo", "Advogado externo"),
                        ],
                        max_length=10,
                    ),
                ),
                ("nome_externo", models.CharField(blank=True, max_length=255)),
                ("oab", models.CharField(blank=True, max_length=30)),
                ("uf_oab", models.CharField(blank=True, max_length=2)),
                ("telefone", models.CharField(blank=True, max_length=20)),
                ("email", models.EmailField(blank=True, max_length=254)),
                (
                    "fingerprint_externo",
                    models.CharField(blank=True, editable=False, max_length=64),
                ),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                (
                    "parte",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="representantes",
                        to="processos.parteprocesso",
                    ),
                ),
                (
                    "usuario",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="representacoes_processuais",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Representante da parte",
                "verbose_name_plural": "Representantes das partes",
            },
        ),
        migrations.AddConstraint(
            model_name="representanteparte",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(
                        ("email", ""),
                        ("fingerprint_externo", ""),
                        ("nome_externo", ""),
                        ("oab", ""),
                        ("telefone", ""),
                        ("tipo", "interno"),
                        ("uf_oab", ""),
                        ("usuario__isnull", False),
                    ),
                    models.Q(
                        ("tipo", "externo"),
                        ("usuario__isnull", True),
                        models.Q(("nome_externo", ""), _negated=True),
                        models.Q(("oab", ""), _negated=True),
                        models.Q(("uf_oab", ""), _negated=True),
                        models.Q(("fingerprint_externo", ""), _negated=True),
                    ),
                    _connector="OR",
                ),
                name="processos_representante_tipo_usuario_valido",
            ),
        ),
        migrations.AddConstraint(
            model_name="representanteparte",
            constraint=models.UniqueConstraint(
                condition=models.Q(("tipo", "interno")),
                fields=("parte", "usuario"),
                name="processos_representante_interno_unico",
            ),
        ),
        migrations.AddConstraint(
            model_name="representanteparte",
            constraint=models.UniqueConstraint(
                condition=models.Q(("tipo", "externo")),
                fields=("parte", "fingerprint_externo"),
                name="processos_representante_externo_unico",
            ),
        ),
        migrations.CreateModel(
            name="HistoricoClassificacaoParte",
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
                (
                    "posicao_anterior",
                    models.CharField(blank=True, max_length=30, null=True),
                ),
                (
                    "qualificacao_anterior",
                    models.CharField(blank=True, max_length=40, null=True),
                ),
                ("atuacao_mp_anterior", models.CharField(blank=True, max_length=30)),
                ("posicao_nova", models.CharField(max_length=30)),
                ("qualificacao_nova", models.CharField(max_length=40)),
                ("atuacao_mp_nova", models.CharField(blank=True, max_length=30)),
                ("alterado_em", models.DateTimeField(auto_now_add=True)),
                (
                    "parte",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="historico_classificacao",
                        to="processos.parteprocesso",
                    ),
                ),
                (
                    "usuario",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="alteracoes_classificacao_partes",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Histórico de classificação da parte",
                "verbose_name_plural": "Históricos de classificação das partes",
                "ordering": ["-alterado_em", "-pk"],
            },
        ),
    ]
