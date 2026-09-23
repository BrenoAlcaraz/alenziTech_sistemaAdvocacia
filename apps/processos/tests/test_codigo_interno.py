"""
Código interno P de Processo (specs/codigos-internos-processo-cliente-usuario.md).
"""

from apps.processos.models import Processo
from apps.processos.services import rotulo_processo
from apps.processos.tests.test_escopo import ProcessosEscopoBase


class TestCodigoInternoProcesso(ProcessosEscopoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "codigo_interno_processo"

    def setUp(self):
        super().setUp()
        self.user = self._user("dono_codigo_processo")

    def _processos(self, quantidade):
        return [self._processo(self.user, None, f"Processo {i}") for i in range(1, quantidade + 1)]

    def test_criacao_atribui_codigos_sequenciais(self):
        primeiro, segundo = self._processos(2)
        self.assertEqual(primeiro.codigo, "P1")
        self.assertEqual(segundo.codigo, "P2")

    def test_numero_excluido_nunca_e_reutilizado(self):
        _, ultimo = self._processos(2)
        ultimo.delete()
        novo = self._processo(self.user, None, "Depois da exclusão")
        self.assertEqual(novo.codigo, "P3")

    def test_edicao_mantem_codigo(self):
        processo = self._processo(self.user, None, "Original")
        processo.titulo = "Alterado"
        processo.save()
        processo.refresh_from_db()
        self.assertEqual(processo.codigo, "P1")

    def test_rotulo_e_texto_padrao_incluem_codigo(self):
        processo = self._processo(self.user, None, "Ação de Cobrança")
        self.assertEqual(str(processo), "P1 · Ação de Cobrança")
        Processo.objects.filter(pk=processo.pk).update(numero="0000001-00.2026.8.00.0001")
        processo.refresh_from_db()
        self.assertEqual(rotulo_processo(processo), "P1 · Ação de Cobrança — 0000001-00.2026.8.00.0001")

    def test_busca_por_codigo_e_exata(self):
        self._autorizar(self.user)
        processos = self._processos(10)
        self.client.force_login(self.user)

        for termo in ("P1", "p1", " P1 "):
            with self.subTest(termo=termo):
                resposta = self.client.get("/processos/", {"busca": termo}, HTTP_HOST=self.http_host)
                self.assertEqual(list(resposta.context["processos"]), [processos[0]])

    def test_numero_sem_prefixo_nao_e_codigo(self):
        self._autorizar(self.user)
        self._processo(self.user, None, "Sem dígito no título")
        self.client.force_login(self.user)
        resposta = self.client.get("/processos/", {"busca": "1"}, HTTP_HOST=self.http_host)
        self.assertEqual(list(resposta.context["processos"]), [])

    def test_migration_numera_existentes_por_ordem_de_criacao(self):
        from importlib import import_module

        from django.apps import apps

        from apps.accounts.models import SequenciaCodigoInterno

        migration = import_module("apps.processos.migrations.0002_numero_interno")
        primeiro, meio, ultimo = self._processos(3)
        meio.delete()

        migration.numerar_existentes(apps, None)

        primeiro.refresh_from_db()
        ultimo.refresh_from_db()
        self.assertEqual((primeiro.codigo, ultimo.codigo), ("P1", "P2"))
        self.assertEqual(
            SequenciaCodigoInterno.objects.get(entidade=SequenciaCodigoInterno.PROCESSO).ultimo_numero, 2
        )
