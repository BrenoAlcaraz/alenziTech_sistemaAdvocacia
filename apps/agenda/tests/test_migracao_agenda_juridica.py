"""
Migrações de dados da Agenda Jurídica (PDR-0034), exercitadas contra o
schema de teste chamando as funções das migrations:

- tarefas → itens tipo Tarefa (participantes, convite, histórico);
- andamentos existentes com prazo → itens Prazo, sem duplicar;
- permissões de `tarefas` → `agenda`, preservando o acesso efetivo.

As tabelas `tarefas_*` e os valores antigos de módulo/habilitação já não
existem no schema novo; cada teste os recria dentro da própria
transação (desfeita ao final).
"""

import importlib
from datetime import date, datetime, timezone as dt_timezone
from types import SimpleNamespace

from django.apps import apps as django_apps
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import (
    ConviteDelegacao,
    HabilitacaoPapel,
    HabilitacaoUsuario,
    PapelAcesso,
    PermissaoPapel,
    PermissaoUsuario,
    UsuarioPapel,
)
from apps.accounts.permissoes import permissao_efetiva, tem_habilitacao
from apps.accounts.permissoes_constants import HAB_AGENDA_ATRIBUIR_OUTROS, MODULO_AGENDA
from apps.agenda.models import ItemAgenda
from apps.processos.models import MovimentacaoProcessual, Processo

migracao_agenda = importlib.import_module("apps.agenda.migrations.0003_dados_item_agenda")
migracao_permissoes = importlib.import_module(
    "apps.accounts.migrations.0005_migrar_permissoes_tarefas_para_agenda"
)

_TABELAS_TAREFAS = """
CREATE TABLE tarefas_tarefa (
    id serial PRIMARY KEY, titulo varchar(255), descricao text, status varchar(20),
    prioridade varchar(10), responsavel_id integer, criador_id integer, atribuidor_id integer,
    atribuido_em timestamptz, processo_id bigint, cliente_id bigint, prazo date,
    criado_em timestamptz, convite_delegacao_id bigint
);
CREATE TABLE tarefas_tarefa_participantes (id serial PRIMARY KEY, tarefa_id integer, user_id integer);
CREATE TABLE tarefas_reatribuicaotarefa (
    id serial PRIMARY KEY, tarefa_id integer, responsavel_anterior_id integer,
    responsavel_novo_id integer, autor_id integer, criado_em timestamptz
);
"""


class TestImportacaoDeTarefasEPrazos(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "agenda_migracao_tarefas"

    def setUp(self):
        super().setUp()
        self.dono = User.objects.create_user("dono_tarefa", password="x")
        self.colega = User.objects.create_user("colega_tarefa", password="x")
        self.delegante = User.objects.create_user("delegante_tarefa", password="x")

    def _importar(self):
        migracao_agenda.importar_tarefas(django_apps, SimpleNamespace(connection=connection))

    def test_tarefas_viram_itens_tipo_tarefa_com_vinculos(self):
        criado_em = datetime(2026, 9, 1, 12, 0, tzinfo=dt_timezone.utc)
        ct_tarefa = ContentType.objects.create(app_label="tarefas", model="tarefa")
        with connection.cursor() as cursor:
            cursor.execute(_TABELAS_TAREFAS)
            cursor.execute(
                "INSERT INTO tarefas_tarefa (id, titulo, descricao, status, prioridade, responsavel_id, "
                "criador_id, atribuidor_id, prazo, criado_em) VALUES "
                "(7, 'Petição', 'd', 'concluida', 'alta', %s, %s, %s, '2026-10-05', %s), "
                "(8, 'Delegada', '', 'cancelada', 'media', %s, %s, %s, NULL, %s)",
                [self.dono.pk, self.delegante.pk, self.delegante.pk, criado_em,
                 self.colega.pk, self.delegante.pk, self.delegante.pk, criado_em],
            )
            cursor.execute(
                "INSERT INTO tarefas_tarefa_participantes (tarefa_id, user_id) VALUES (7, %s), (7, %s)",
                [self.colega.pk, self.dono.pk],
            )
            cursor.execute(
                "INSERT INTO tarefas_reatribuicaotarefa (tarefa_id, responsavel_anterior_id, "
                "responsavel_novo_id, autor_id, criado_em) VALUES (7, %s, %s, %s, %s)",
                [self.colega.pk, self.dono.pk, self.delegante.pk, criado_em],
            )
        convite = ConviteDelegacao.objects.create(
            delegante=self.delegante, destinatario=self.colega,
            content_type=ct_tarefa, object_id=8,
        )
        with connection.cursor() as cursor:
            cursor.execute("UPDATE tarefas_tarefa SET convite_delegacao_id = %s WHERE id = 8", [convite.pk])

        self._importar()

        peticao = ItemAgenda.objects.get(titulo="Petição")
        self.assertEqual(peticao.tipo, "tarefa")
        self.assertEqual(peticao.status, "concluido")
        self.assertEqual(peticao.prioridade, "alta")
        self.assertEqual(peticao.data_fatal, date(2026, 10, 5))
        self.assertEqual(peticao.responsavel, self.dono)
        self.assertEqual(peticao.criado_por, self.delegante)
        self.assertEqual(peticao.criado_em, criado_em)
        # Responsável não vira participante de si mesmo.
        self.assertEqual(list(peticao.participantes.all()), [self.colega])
        historico = peticao.reatribuicoes.get()
        self.assertEqual(historico.responsavel_anterior, self.colega)
        self.assertEqual(historico.autor, self.delegante)

        delegada = ItemAgenda.objects.get(titulo="Delegada")
        self.assertEqual(delegada.status, "cancelado")
        self.assertIsNotNone(delegada.cancelado_em)
        self.assertEqual(delegada.convite_delegacao, convite)
        convite.refresh_from_db()
        self.assertEqual(convite.content_type, ContentType.objects.get_for_model(ItemAgenda))
        self.assertEqual(convite.object_id, delegada.pk)
        self.assertTrue(delegada.oculta_por_convite)

    def test_schema_sem_tabela_de_tarefas_nao_faz_nada(self):
        self._importar()
        self.assertFalse(ItemAgenda.objects.exists())

    def test_andamentos_existentes_com_prazo_geram_prazo_uma_vez(self):
        processo = Processo.objects.create(responsavel=self.dono, titulo="Processo Migração")
        andamento = MovimentacaoProcessual.objects.create(
            processo=processo, descricao="Prazo antigo", tipo="despacho", data_prazo=date(2026, 11, 3),
        )
        MovimentacaoProcessual.objects.create(processo=processo, descricao="Sem prazo", tipo="despacho")
        # Simula o andamento anterior à Agenda Jurídica (sem item gerado).
        ItemAgenda.objects.filter(movimentacao_origem=andamento).delete()

        migracao_agenda.gerar_prazos_dos_andamentos(django_apps)
        migracao_agenda.gerar_prazos_dos_andamentos(django_apps)

        item = ItemAgenda.objects.get()
        self.assertEqual(item.movimentacao_origem, andamento)
        self.assertEqual(item.tipo, "prazo")
        self.assertEqual(item.responsavel, self.dono)
        self.assertEqual(item.data_fatal, date(2026, 11, 3))
        self.assertEqual(item.data_para_fazer, date(2026, 11, 1))


class TestMigracaoDePermissoes(TenantTestCase):
    """Quem tinha acesso a `tarefas` mantém acesso equivalente em `agenda`
    (maior nível, união das habilitações), sem ganhar o que não tinha."""

    @classmethod
    def get_test_schema_name(cls):
        return "agenda_migracao_permissoes"

    def setUp(self):
        super().setUp()
        with connection.cursor() as cursor:
            for tabela, constraint in [
                ("accounts_permissaopapel", "chk_permissaopapel_nivel"),
                ("accounts_permissaousuario", "chk_permissaousuario_nivel"),
                ("accounts_habilitacaopapel", "chk_habilitacaopapel_modulo_item"),
                ("accounts_habilitacaousuario", "chk_habilitacaousuario_modulo_item"),
            ]:
                cursor.execute(f"ALTER TABLE {tabela} DROP CONSTRAINT {constraint}")

    def _usuario_com_papel(self, username, permissoes, habilitacoes=()):
        user = User.objects.create_user(username, password="x")
        papel = PapelAcesso.objects.create(nome=f"Papel {username}")
        UsuarioPapel.objects.create(usuario=user, papel=papel)
        for modulo, nivel in permissoes.items():
            PermissaoPapel.objects.create(papel=papel, modulo=modulo, ativo=True, nivel=nivel)
        for modulo, item in habilitacoes:
            HabilitacaoPapel.objects.create(papel=papel, modulo=modulo, item=item, ativo=True)
        return user, papel

    def _migrar(self):
        migracao_permissoes.migrar_permissoes(django_apps, None)

    def _agenda(self, user):
        efetiva = permissao_efetiva(User.objects.get(pk=user.pk), MODULO_AGENDA)
        return efetiva["tem_acesso"], efetiva["nivel"] if efetiva["tem_acesso"] else None

    def _pode_atribuir(self, user):
        return tem_habilitacao(User.objects.get(pk=user.pk), MODULO_AGENDA, HAB_AGENDA_ATRIBUIR_OUTROS)

    def test_papel_unifica_maior_nivel_e_habilitacoes(self):
        user, papel = self._usuario_com_papel(
            "papel_uniao",
            {"tarefas": "todos", "agenda": "somente_seus"},
            [("tarefas", "tarefas_atribuir_outros")],
        )

        self._migrar()

        self.assertFalse(PermissaoPapel.objects.filter(modulo="tarefas").exists())
        self.assertFalse(HabilitacaoPapel.objects.filter(modulo="tarefas").exists())
        self.assertEqual(PermissaoPapel.objects.get(papel=papel, modulo="agenda").nivel, "todos")
        self.assertTrue(
            HabilitacaoPapel.objects.get(papel=papel, modulo="agenda", item=HAB_AGENDA_ATRIBUIR_OUTROS).ativo
        )
        self.assertEqual(self._agenda(user), (True, "todos"))
        self.assertTrue(self._pode_atribuir(user))
        self.assertFalse(PermissaoUsuario.objects.filter(usuario=user).exists())

    def test_papel_so_com_tarefas_passa_a_dar_agenda(self):
        user, _ = self._usuario_com_papel("so_tarefas", {"tarefas": "somente_seus"})
        self._migrar()
        self.assertEqual(self._agenda(user), (True, "somente_seus"))

    def test_override_que_bloqueava_agenda_nao_tira_acesso_de_quem_tinha_tarefas(self):
        user, _ = self._usuario_com_papel("bloqueio_agenda", {"tarefas": "todos"})
        PermissaoUsuario.objects.create(usuario=user, modulo="agenda", ativo=False, nivel="somente_seus")
        self._migrar()
        self.assertEqual(self._agenda(user), (True, "todos"))
        self.assertFalse(PermissaoUsuario.objects.filter(modulo="tarefas").exists())

    def test_override_que_bloqueava_tarefas_nao_tira_a_agenda_do_papel(self):
        user, _ = self._usuario_com_papel("bloqueio_tarefas", {"tarefas": "todos", "agenda": "somente_seus"})
        PermissaoUsuario.objects.create(usuario=user, modulo="tarefas", ativo=False, nivel="todos")
        self._migrar()
        self.assertEqual(self._agenda(user), (True, "somente_seus"))

    def test_habilitacao_de_tarefas_sem_o_modulo_nao_vira_ganho_na_agenda(self):
        user, papel = self._usuario_com_papel(
            "hab_sem_modulo", {"agenda": "somente_seus"}, [("tarefas", "tarefas_atribuir_outros")],
        )
        PermissaoPapel.objects.create(papel=papel, modulo="tarefas", ativo=False, nivel="somente_seus")
        self._migrar()
        self.assertEqual(self._agenda(user), (True, "somente_seus"))
        self.assertFalse(self._pode_atribuir(user))

    def test_habilitacao_individual_de_tarefas_e_preservada(self):
        user, _ = self._usuario_com_papel("hab_individual", {"tarefas": "todos"})
        HabilitacaoUsuario.objects.create(
            usuario=user, modulo="tarefas", item="tarefas_atribuir_outros", ativo=True
        )
        self._migrar()
        self.assertTrue(self._pode_atribuir(user))
        self.assertFalse(HabilitacaoUsuario.objects.filter(modulo="tarefas").exists())
