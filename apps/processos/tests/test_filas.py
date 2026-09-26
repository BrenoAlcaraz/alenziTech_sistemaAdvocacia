"""Filas automáticas da lista de Processos: Parados, Prazo em 7 dias e
Sem responsável ativo (docs/modules/processos.md)."""

from datetime import datetime, time, timedelta

from django.utils import timezone

from apps.accounts.models import PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import MODULO_PAINEL, NIVEL_SOMENTE_SEUS, NIVEL_TODOS
from apps.processos.models import MovimentacaoProcessual, Processo

from .test_escopo import ProcessosEscopoBase


class TestFilasProcessos(ProcessosEscopoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "ui06_filas_processos"

    def setUp(self):
        super().setUp()
        self.hoje = timezone.localdate()
        self.user = self._user("filas_somente_seus")
        self.outro = self._user("filas_alheio")
        self._autorizar(self.user, NIVEL_SOMENTE_SEUS)

    def _processo(self, titulo, responsavel=None, **campos):
        processo = Processo.objects.create(titulo=titulo, criado_por=responsavel or self.user)
        processo.responsaveis.add(responsavel or self.user)
        # update() evita o recálculo de prazo_proximo feito no save/andamento.
        if campos:
            Processo.objects.filter(pk=processo.pk).update(**campos)
        return processo

    def _andamento_ha(self, processo, dias):
        dia = self.hoje - timedelta(days=dias)
        MovimentacaoProcessual.objects.create(
            processo=processo, data=timezone.make_aware(datetime.combine(dia, time(12))),
        )

    def _fila(self, fila, query=""):
        resposta = self.client.get(f"/processos/?fila={fila}{query}", HTTP_HOST=self.http_host)
        self.assertEqual(resposta.status_code, 200)
        titulos = sorted(p.titulo for p in resposta.context["processos"])
        contagem = {aba["chave"]: aba["total"] for aba in resposta.context["filas"]}
        return titulos, contagem

    def test_parados_pelo_ultimo_andamento_ou_distribuicao_acima_de_30_dias(self):
        self._andamento_ha(self._processo("Andamento há 31 dias"), 31)
        self._processo("Distribuído há 31 dias", data_distribuicao=self.hoje - timedelta(days=31))
        self._processo("Distribuído há 30 dias", data_distribuicao=self.hoje - timedelta(days=30))
        recente = self._processo("Andamento recente", data_distribuicao=self.hoje - timedelta(days=200))
        self._andamento_ha(recente, 5)
        self._processo("Sem data nenhuma")
        self._processo("Arquivado parado", status="arquivado", data_distribuicao=self.hoje - timedelta(days=90))
        self.client.force_login(self.user)

        titulos, contagem = self._fila("parados")

        self.assertEqual(titulos, ["Andamento há 31 dias", "Distribuído há 31 dias"])
        self.assertEqual(contagem["parados"], len(titulos))

    def test_prazo_nos_proximos_7_dias(self):
        self._processo("Prazo hoje", prazo_proximo=self.hoje)
        self._processo("Prazo em 7 dias", prazo_proximo=self.hoje + timedelta(days=7))
        self._processo("Prazo em 8 dias", prazo_proximo=self.hoje + timedelta(days=8))
        self._processo("Prazo vencido", prazo_proximo=self.hoje - timedelta(days=1))
        self.client.force_login(self.user)

        titulos, contagem = self._fila("prazo_7dias")

        self.assertEqual(titulos, ["Prazo em 7 dias", "Prazo hoje"])
        self.assertEqual(contagem["prazo_7dias"], 2)

    def test_sem_responsavel_ativo(self):
        admin = self._admin()
        inativo = self._user("filas_inativo", is_active=False)
        self._processo("De usuário inativo", responsavel=inativo)
        self._processo("De usuário ativo", responsavel=admin)
        self._processo("Sem responsável", responsavel=admin).responsaveis.clear()
        self.client.force_login(admin)

        titulos, contagem = self._fila("sem_responsavel")

        self.assertEqual(titulos, ["De usuário inativo", "Sem responsável"])
        self.assertEqual(contagem["sem_responsavel"], 2)

    def test_somente_seus_ve_so_os_proprios_em_cada_fila(self):
        self._processo("Meu parado", data_distribuicao=self.hoje - timedelta(days=60))
        self._processo("Alheio parado", responsavel=self.outro, data_distribuicao=self.hoje - timedelta(days=60))
        self._processo("Meu prazo", prazo_proximo=self.hoje)
        self._processo("Alheio prazo", responsavel=self.outro, prazo_proximo=self.hoje)
        self.client.force_login(self.user)

        parados, contagem = self._fila("parados")
        prazos, _ = self._fila("prazo_7dias")

        self.assertEqual(parados, ["Meu parado"])
        self.assertEqual(prazos, ["Meu prazo"])
        self.assertEqual(contagem, {"": None, "parados": 1, "prazo_7dias": 1, "sem_responsavel": 0})

    def test_fila_combina_com_busca_e_contagem_acompanha(self):
        self._processo("Trabalhista parado", data_distribuicao=self.hoje - timedelta(days=60))
        self._processo("Cível parado", data_distribuicao=self.hoje - timedelta(days=60))
        self.client.force_login(self.user)

        titulos, contagem = self._fila("parados", "&busca=Trabalhista")

        self.assertEqual(titulos, ["Trabalhista parado"])
        self.assertEqual(contagem["parados"], 1)

    def test_fila_desconhecida_mostra_todos(self):
        self._processo("Qualquer")
        self.client.force_login(self.user)

        titulos, _ = self._fila("inexistente")

        self.assertEqual(titulos, ["Qualquer"])

    def test_parados_tem_o_mesmo_numero_do_painel(self):
        # Um papel por usuário: Painel entra no papel que o usuário já tem.
        papel = UsuarioPapel.objects.get(usuario=self.user, ativo=True).papel
        PermissaoPapel.objects.create(papel=papel, modulo=MODULO_PAINEL, ativo=True, nivel=NIVEL_TODOS)
        for dias in (31, 45, 120, 400):
            self._andamento_ha(self._processo(f"Andamento há {dias}"), dias)
        self._processo("Distribuído há 40", data_distribuicao=self.hoje - timedelta(days=40))
        self._andamento_ha(self._processo("Recente"), 2)
        self._processo("Alheio", responsavel=self.outro, data_distribuicao=self.hoje - timedelta(days=90))
        self.client.force_login(self.user)

        painel = self.client.get("/", HTTP_HOST=self.http_host)
        titulos, contagem = self._fila("parados")

        self.assertEqual(painel.context["paralisados"]["1mes"]["total"], 5)
        self.assertEqual(contagem["parados"], 5)
        self.assertEqual(len(titulos), 5)
        self.assertContains(painel, "/processos/?fila=parados")
