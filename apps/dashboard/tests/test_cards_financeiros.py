"""
Cards financeiros da Visão geral por nível de acesso —
specs/painel-cards-financeiros.md.
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.utils import timezone
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PapelAcesso, PerfilUsuario, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import (
    MODULO_FINANCEIRO,
    MODULO_PAINEL,
    NIVEL_DADOS_TODOS,
    NIVEL_SOLICITACOES,
    NIVEL_TODOS,
)
from apps.clientes.models import Cliente
from apps.financeiro.models import (
    CustaJudicial, GrupoCustas, Honorario, LancamentoFinanceiro, SolicitacaoFinanceira,
)
from apps.financeiro.services import gerar_lancamentos_do_honorario


class CardsFinanceirosBase(TenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio

        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"
        self.hoje = timezone.localdate()

    def _usuario(self, username, nivel):
        usuario = User.objects.create_user(username, password="testpass")
        papel = PapelAcesso.objects.create(nome=f"Papel {username}", ativo=True)
        UsuarioPapel.objects.create(usuario=usuario, papel=papel, ativo=True)
        PermissaoPapel.objects.create(papel=papel, modulo=MODULO_FINANCEIRO, ativo=True, nivel=nivel)
        PermissaoPapel.objects.create(papel=papel, modulo=MODULO_PAINEL, ativo=True, nivel=NIVEL_TODOS)
        return usuario

    def _cards(self, usuario):
        self.client.force_login(usuario)
        resposta = self.client.get("/", HTTP_HOST=self.http_host)
        self.assertEqual(resposta.status_code, 200)
        return resposta.context["cards_financeiros"]

    def _solicitacao(self, solicitante, **kwargs):
        dados = {"tipo": "reembolso", "descricao": "Solicitação", "valor": "100.00", "solicitante": solicitante}
        dados.update(kwargs)
        return SolicitacaoFinanceira.objects.create(**dados)

    def _lancamento(self, **kwargs):
        dados = {"descricao": "Lançamento", "status": "pendente", "data_vencimento": self.hoje}
        dados.update(kwargs)
        return LancamentoFinanceiro.objects.create(**dados)


class TestCardsNivelSolicitacoes(CardsFinanceirosBase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi_painel_cards_solicitante"

    def test_pendentes_e_pagas_na_janela_de_7_dias_so_das_proprias(self):
        usuario = self._usuario("solicitante_cards", NIVEL_SOLICITACOES)
        outro = self._usuario("outro_cards", NIVEL_SOLICITACOES)
        self._solicitacao(usuario, status="solicitada", valor="100.00")
        self._solicitacao(
            usuario, tipo="pagamento", status="aprovada", valor="50.00",
            vencimento=self.hoje - timedelta(days=1),
        )
        self._solicitacao(usuario, status="rejeitada")
        self._solicitacao(outro, status="solicitada")
        self._solicitacao(usuario, status="paga", valor="30.00", data_pagamento=self.hoje - timedelta(days=6))
        self._solicitacao(usuario, status="paga", data_pagamento=self.hoje - timedelta(days=7))
        self._solicitacao(outro, status="paga", data_pagamento=self.hoje)

        cards = self._cards(usuario)

        self.assertNotIn("pendencias", cards)
        pendentes = cards["solicitante"]["pendentes"]
        self.assertEqual(pendentes["quantidade"], 2)
        self.assertEqual(pendentes["total"], "R$ 150,00")
        self.assertEqual(pendentes["vencidas"], 1)
        pagas = cards["solicitante"]["pagas"]
        self.assertEqual(pagas["quantidade"], 1)
        self.assertEqual(pagas["total"], "R$ 30,00")

        destino = self.client.get(
            f"/financeiro/solicitacoes/?{pagas['query']}", HTTP_HOST=self.http_host,
        )
        self.assertEqual(len(destino.context["solicitacoes"]), 1)


class TestCardsNivelDadosEAdmin(CardsFinanceirosBase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi_painel_cards_dados_admin"

    def setUp(self):
        super().setUp()
        self.usuario = self._usuario("dados_cards", NIVEL_DADOS_TODOS)
        self.admin = self._usuario("admin_cards", NIVEL_DADOS_TODOS)
        PerfilUsuario.objects.filter(user=self.admin).update(is_admin_escritorio=True)
        self.mes_anterior = self.hoje.replace(day=1) - timedelta(days=1)

    def test_pendencias_de_hoje_separadas_dos_atrasados_de_qualquer_mes(self):
        self._lancamento(tipo="despesa", valor="200.00")
        self._lancamento(tipo="despesa", valor="999.00", status="cancelado")
        self._lancamento(tipo="despesa", valor="70.00", data_vencimento=self.mes_anterior)
        self._lancamento(tipo="receita", valor="500.00")
        self._lancamento(tipo="receita", valor="40.00", status="pago", data_pagamento=self.hoje)

        cards = self._cards(self.usuario)

        self.assertNotIn("admin", cards)
        pagar = cards["pendencias"]["a_pagar"]
        self.assertEqual(pagar["hoje"], {"total": "R$ 200,00", "quantidade": 1})
        self.assertEqual(pagar["atrasados"], {"total": "R$ 70,00", "quantidade": 1})
        receber = cards["pendencias"]["a_receber"]
        self.assertEqual(receber["hoje"], {"total": "R$ 500,00", "quantidade": 1})
        self.assertEqual(receber["atrasados"]["quantidade"], 0)

        destino = self.client.get("/financeiro/?filtro=apagar_atrasados", HTTP_HOST=self.http_host)
        self.assertEqual([l.valor for l in destino.context["lancamentos"]], [Decimal("70.00")])

    def test_fila_de_solicitacoes_pela_etapa_que_falta(self):
        self._solicitacao(self.admin, status="solicitada")
        self._solicitacao(self.usuario, status="em_analise", tipo="pagamento", vencimento=self.hoje)
        self._solicitacao(
            self.usuario, status="aprovada", tipo="pagamento", vencimento=self.hoje - timedelta(days=2),
        )
        self._solicitacao(self.usuario, status="paga")

        fila = self._cards(self.usuario)["fila_solicitacoes"]

        self.assertEqual(fila["quantidade"], 3)
        self.assertEqual(fila["aguardando_analise"], 2)
        self.assertEqual(fila["aguardando_pagamento"], 1)
        self.assertEqual(fila["vencidas"], 1)
        self.assertEqual(fila["vencem_hoje"], 1)

    def test_admin_ve_saldo_previsto_igual_ao_do_financeiro(self):
        self._lancamento(tipo="receita", valor="1000.00")
        self._lancamento(tipo="receita", valor="300.00", status="pago", data_pagamento=self.hoje)
        self._lancamento(tipo="despesa", valor="1500.00")
        self._lancamento(tipo="despesa", valor="80.00", data_vencimento=self.mes_anterior)

        admin = self._cards(self.admin)["admin"]
        financeiro = self.client.get("/financeiro/", HTTP_HOST=self.http_host).context["resumo"]

        self.assertTrue(admin["saldo_previsto_negativo"])
        self.assertEqual(admin["saldo_previsto"], "R$ 200,00")
        self.assertEqual(financeiro["saldo_previsto"], "R$ -200,00")
        self.assertEqual(admin["realizado"], "R$ 300,00")

    def test_admin_honorarios_do_mes_sem_dupla_contagem(self):
        parcelado = Honorario.objects.create(
            tipo="contratual", modalidade="valor", classificacao="parcelado", numero_parcelas=2,
            valor_estimado="600.00", data_prevista=self.hoje,
        )
        gerar_lancamentos_do_honorario(parcelado)
        Honorario.objects.create(
            tipo="contratual", modalidade="valor", valor_estimado="2000.00",
            valor_recebido="500.00", data_prevista=self.hoje,
        )
        self._lancamento(
            tipo="receita", categoria="honorario", valor="500.00", status="pago", data_pagamento=self.hoje,
        )
        Honorario.objects.create(tipo="contratual", modalidade="exito", valor_estimado="0", data_prevista=self.hoje)
        Honorario.objects.create(
            tipo="contratual", modalidade="valor", valor_estimado="700.00",
            status="cancelado", data_prevista=self.hoje,
        )
        Honorario.objects.create(tipo="sucumbencial", valor_estimado="900.00", data_prevista=self.hoje)

        admin = self._cards(self.admin)["admin"]

        # 1ª parcela (300) + único pendente (1500) + recebido do único (500)
        self.assertEqual(admin["honorarios_previsto"], "R$ 2.300,00")
        self.assertEqual(admin["honorarios_recebido"], "R$ 500,00")

    def test_admin_custas_a_cobrar_iguais_ao_filtro_em_debito(self):
        devedor = Cliente.objects.create(nome_razao_social="Devedor", tipo="PJ", responsavel=self.admin)
        inativo = Cliente.objects.create(
            nome_razao_social="Inativo", tipo="PJ", responsavel=self.admin, ativo=False,
        )
        grupo = GrupoCustas.objects.create(nome="Grupo devedor")
        CustaJudicial.objects.create(
            descricao="Custa", valor="120.00", data=self.hoje, tipo="adiantamento", cliente=devedor,
        )
        CustaJudicial.objects.create(
            descricao="Custa", valor="40.00", data=self.hoje, tipo="adiantamento", cliente=inativo,
        )
        CustaJudicial.objects.create(
            descricao="Custa", valor="30.00", data=self.hoje, tipo="adiantamento", grupo=grupo, cliente=devedor,
        )

        admin = self._cards(self.admin)["admin"]
        destino = self.client.get("/financeiro/custas/?saldo=em_debito", HTTP_HOST=self.http_host)

        self.assertEqual(admin["custas_a_cobrar"], {"total": "R$ 150,00", "quantidade": 2})
        self.assertEqual(len(destino.context["saldo_clientes"]), 2)
