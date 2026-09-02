from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django_tenants.test.cases import TenantTestCase


PROCESSOS_ANTES = ("processos", "0006_responsavel_obrigatorio")
PROCESSOS_SCHEMA = ("processos", "0007_participantes_representantes_schema")
PROCESSOS_DADOS = ("processos", "0008_migrar_partes_legadas")
PROCESSOS_DEPOIS = ("processos", "0009_participantes_campos_obrigatorios")


class TestMigrationParticipantesProcesso(TenantTestCase):
    @classmethod
    def _fixture_setup(cls):
        return TransactionTestCase._fixture_setup.__func__(cls)

    def _fixture_teardown(self):
        return TransactionTestCase._fixture_teardown(self)

    def tearDown(self):
        # Recoloca o schema no HEAD de todas as apps antes do flush da
        # TransactionTestCase — o teste move deliberadamente "processos"
        # para um estado de migration anterior ao HEAD, e o flush usa o
        # registry de models em Python (HEAD), não o estado físico do
        # schema; sem isso, tabelas removidas do HEAD mas ainda presentes
        # no estado testado quebram o TRUNCATE por FK pendente.
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    @classmethod
    def get_test_schema_name(cls):
        return "wi0006_processos_migrations"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "WI-0006 Migration Participantes"
        tenant.slug = "wi0006-migration-participantes"

    def _targets(self, executor, target):
        return [
            *[
                node
                for node in executor.loader.graph.leaf_nodes()
                if node[0] != "processos"
            ],
            target,
        ]

    def _migrar(self, target):
        executor = MigrationExecutor(connection)
        targets = self._targets(executor, target)
        executor.migrate(targets)
        executor = MigrationExecutor(connection)
        targets = self._targets(executor, target)
        return executor.loader.project_state(targets).apps

    def _usuario(self, apps, username):
        User = apps.get_model("auth", "User")
        return User.objects.create(username=username, password="!", is_active=True)

    def test_mapeamento_rollback_reaplicacao_e_preservacao_integral(self):
        self.assertEqual(connection.vendor, "postgresql")
        self.assertEqual(connection.schema_name, self.get_test_schema_name())

        apps_antes = self._migrar(PROCESSOS_ANTES)
        Cliente = apps_antes.get_model("clientes", "Cliente")
        Processo = apps_antes.get_model("processos", "Processo")
        Parte = apps_antes.get_model("processos", "ParteProcesso")

        responsavel = self._usuario(apps_antes, "responsavel_wi0006_migration")
        cliente = Cliente.objects.create(
            nome_razao_social="Cliente histórico",
            tipo="PF",
            cpf_cnpj="123.456.789-00",
            responsavel_id=responsavel.pk,
        )
        processo = Processo.objects.create(
            titulo="Processo histórico WI-0006",
            cliente_id=cliente.pk,
            responsavel_id=responsavel.pk,
        )
        cliente_sem_documento = Cliente.objects.create(
            nome_razao_social="Cliente histórico sem documento",
            tipo="PF",
            cpf_cnpj="",
            responsavel_id=responsavel.pk,
        )
        processo_sem_parte = Processo.objects.create(
            titulo="Processo histórico sem parte",
            cliente_id=cliente_sem_documento.pk,
            responsavel_id=responsavel.pk,
        )
        cliente_ambiguo = Cliente.objects.create(
            nome_razao_social="Cliente histórico ambíguo",
            tipo="PJ",
            cpf_cnpj="11.222.333/0001-44",
            responsavel_id=responsavel.pk,
        )
        processo_ambiguo = Processo.objects.create(
            titulo="Processo histórico com documento ambíguo",
            cliente_id=cliente_ambiguo.pk,
            responsavel_id=responsavel.pk,
        )
        partes = {
            tipo: Parte.objects.create(
                processo_id=processo.pk,
                nome=f"Parte {tipo}",
                tipo=tipo,
                cpf_cnpj="12345678900" if tipo == "autor" else "",
            )
            for tipo in ("autor", "reu", "terceiro", "advogado_contrario")
        }
        ids = {parte.pk for parte in partes.values()}
        partes_ambiguas = [
            Parte.objects.create(
                processo_id=processo_ambiguo.pk,
                nome=f"Candidata ambígua {tipo}",
                tipo=tipo,
                cpf_cnpj=documento,
            )
            for tipo, documento in (
                ("autor", "11.222.333/0001-44"),
                ("reu", "11222333000144"),
            )
        ]
        ids_ambiguos = {parte.pk for parte in partes_ambiguas}

        apps_depois = self._migrar(PROCESSOS_DEPOIS)
        ParteDepois = apps_depois.get_model("processos", "ParteProcesso")
        Representante = apps_depois.get_model("processos", "RepresentanteParte")
        mapeamento = {
            parte.tipo_legado: (
                parte.posicao,
                parte.qualificacao,
                parte.vinculo_escritorio,
                parte.registro_legado,
            )
            for parte in ParteDepois.objects.filter(pk__in=ids)
        }
        self.assertEqual(set(ParteDepois.objects.filter(pk__in=ids).values_list("pk", flat=True)), ids)
        self.assertEqual(mapeamento["autor"], ("polo_ativo", "autor", "cliente", False))
        autor_preservado = ParteDepois.objects.get(
            processo_id=processo.pk,
            tipo_legado="autor",
        )
        self.assertEqual(autor_preservado.nome, "Parte autor")
        self.assertEqual(autor_preservado.cpf_cnpj, "12345678900")
        self.assertEqual(mapeamento["reu"], ("polo_passivo", "reu", "parte_contraria", False))
        self.assertEqual(
            mapeamento["terceiro"],
            ("terceiro", "terceiro_interessado", "outro", False),
        )
        self.assertEqual(
            mapeamento["advogado_contrario"],
            ("legado", "advogado_contrario_legado", "legado", True),
        )
        legado = ParteDepois.objects.get(tipo_legado="advogado_contrario")
        self.assertEqual(Representante.objects.filter(parte_id=legado.pk).count(), 0)

        autor = ParteDepois.objects.get(
            processo_id=processo.pk,
            tipo_legado="autor",
        )
        self.assertEqual(
            Representante.objects.filter(
                parte_id=autor.pk,
                tipo="interno",
                usuario_id=responsavel.pk,
            ).count(),
            1,
        )
        automatico_pendente = ParteDepois.objects.get(
            processo_id=processo_sem_parte.pk,
            cliente_id=cliente_sem_documento.pk,
        )
        self.assertTrue(automatico_pendente.classificacao_pendente)
        self.assertIsNone(automatico_pendente.posicao)
        self.assertIsNone(automatico_pendente.qualificacao)
        self.assertEqual(automatico_pendente.nome, "")
        self.assertEqual(automatico_pendente.cpf_cnpj, "")
        self.assertEqual(
            Representante.objects.filter(
                parte_id=automatico_pendente.pk,
                tipo="interno",
                usuario_id=responsavel.pk,
            ).count(),
            1,
        )

        candidatas_ambiguas = ParteDepois.objects.filter(pk__in=ids_ambiguos)
        self.assertEqual(
            set(candidatas_ambiguas.values_list("pk", flat=True)),
            ids_ambiguos,
        )
        self.assertFalse(candidatas_ambiguas.filter(cliente_id__isnull=False).exists())
        self.assertFalse(
            candidatas_ambiguas.filter(vinculo_escritorio="cliente").exists()
        )
        automatico_ambiguo = ParteDepois.objects.get(
            processo_id=processo_ambiguo.pk,
            cliente_id=cliente_ambiguo.pk,
        )
        self.assertNotIn(automatico_ambiguo.pk, ids_ambiguos)
        self.assertTrue(automatico_ambiguo.classificacao_pendente)
        self.assertEqual(
            ParteDepois.objects.filter(
                processo_id=processo_ambiguo.pk,
                cliente_id=cliente_ambiguo.pk,
            ).count(),
            1,
        )
        self.assertEqual(
            ParteDepois.objects.filter(processo_id=processo_ambiguo.pk).count(),
            3,
        )
        self.assertEqual(
            Representante.objects.filter(
                parte_id=automatico_ambiguo.pk,
                tipo="interno",
                usuario_id=responsavel.pk,
            ).count(),
            1,
        )
        Representante.objects.create(
            parte_id=autor.pk,
            tipo="externo",
            nome_externo="Advogada externa",
            oab="12345",
            uf_oab="SP",
            fingerprint_externo="a" * 64,
        )
        self.assertEqual(Representante.objects.filter(parte_id=autor.pk).count(), 2)

        apps_rollback = self._migrar(PROCESSOS_ANTES)
        ParteRollback = apps_rollback.get_model("processos", "ParteProcesso")
        self.assertEqual(
            set(ParteRollback.objects.filter(pk__in=ids).values_list("tipo", flat=True)),
            {"autor", "reu", "terceiro", "advogado_contrario"},
        )
        self.assertEqual(ParteRollback.objects.filter(pk__in=ids).count(), 4)
        self.assertEqual(
            ParteRollback.objects.filter(processo_id=processo_sem_parte.pk).count(),
            0,
        )
        self.assertEqual(
            set(
                ParteRollback.objects.filter(pk__in=ids_ambiguos).values_list(
                    "pk", flat=True
                )
            ),
            ids_ambiguos,
        )
        self.assertEqual(
            ParteRollback.objects.filter(processo_id=processo_ambiguo.pk).count(),
            2,
        )

        apps_reaplicado = self._migrar(PROCESSOS_DEPOIS)
        ParteReaplicada = apps_reaplicado.get_model("processos", "ParteProcesso")
        self.assertEqual(ParteReaplicada.objects.filter(pk__in=ids).count(), 4)
        self.assertTrue(
            ParteReaplicada.objects.get(
                tipo_legado="advogado_contrario"
            ).registro_legado
        )
        automatico_reaplicado = ParteReaplicada.objects.get(
            processo_id=processo_sem_parte.pk,
            cliente_id=cliente_sem_documento.pk,
        )
        self.assertTrue(automatico_reaplicado.classificacao_pendente)
        candidatas_reaplicadas = ParteReaplicada.objects.filter(pk__in=ids_ambiguos)
        self.assertEqual(
            set(candidatas_reaplicadas.values_list("pk", flat=True)),
            ids_ambiguos,
        )
        self.assertFalse(
            candidatas_reaplicadas.filter(cliente_id__isnull=False).exists()
        )
        automatico_ambiguo_reaplicado = ParteReaplicada.objects.get(
            processo_id=processo_ambiguo.pk,
            cliente_id=cliente_ambiguo.pk,
        )
        self.assertNotIn(automatico_ambiguo_reaplicado.pk, ids_ambiguos)
        self.assertTrue(automatico_ambiguo_reaplicado.classificacao_pendente)
        self.assertEqual(
            ParteReaplicada.objects.filter(
                processo_id=processo_ambiguo.pk,
                cliente_id=cliente_ambiguo.pk,
            ).count(),
            1,
        )
