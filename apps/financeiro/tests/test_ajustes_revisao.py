"""
Ajustes da revisão de 2026-09-19 no Financeiro: categoria por tipo,
Lançamentos ↔ Creditar (custas do cliente), reembolso de custa,
totais/saldo previsto, análise de dados, solicitações (pagas/pendentes,
filtros e campos por tipo).
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PapelAcesso, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import MODULO_FINANCEIRO, NIVEL_DADOS_TODOS
from apps.clientes.models import Cliente
from apps.financeiro.forms import LancamentoFinanceiroForm, SolicitacaoFinanceiraForm
from apps.financeiro.models import CustaJudicial, LancamentoFinanceiro, SolicitacaoFinanceira
from apps.financeiro.services import (
    analise_de_dados,
    registrar_credito_cliente,
    reembolsar_custa,
    totais_do_mes,
)
from apps.processos.models import Processo


class FinanceiroBase(TenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio

        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"
        self.user = User.objects.create_user(username="fin_ajustes", password="testpass")
        papel = PapelAcesso.objects.create(nome="Papel Fin Ajustes", ativo=True)
        UsuarioPapel.objects.create(usuario=self.user, papel=papel, ativo=True)
        PermissaoPapel.objects.create(
            papel=papel, modulo=MODULO_FINANCEIRO, ativo=True, nivel=NIVEL_DADOS_TODOS,
        )
        self.client.force_login(self.user)
        self.cliente = Cliente.objects.create(nome_razao_social="CLIENTE A", tipo="PF", responsavel=self.user)
        self.hoje = timezone.localdate()

    def _lancamento(self, **kwargs):
        dados = {
            "tipo": "receita", "descricao": "Lanç", "valor": Decimal("100.00"),
            "data_vencimento": self.hoje, "status": "pendente", "categoria": "honorario",
        }
        dados.update(kwargs)
        return LancamentoFinanceiro.objects.create(**dados)

    def _custa(self, **kwargs):
        dados = {
            "descricao": "Custa", "valor": Decimal("100.00"), "data": self.hoje,
            "tipo": "adiantamento", "cliente": self.cliente,
        }
        dados.update(kwargs)
        return CustaJudicial.objects.create(**dados)


class TestCategoriaPorTipo(FinanceiroBase):
    @classmethod
    def get_test_schema_name(cls):
        return "fin_ajustes_categoria"

    def _form(self, **kw):
        dados = {
            "tipo": "receita", "descricao": "X", "valor": "10", "categoria": "honorario",
            "status": "pendente", "data_vencimento": self.hoje.isoformat(),
        }
        dados.update(kw)
        return LancamentoFinanceiroForm(data=dados)

    def test_categoria_de_despesa_em_receita_e_recusada(self):
        form = self._form(categoria="aluguel")
        self.assertFalse(form.is_valid())
        self.assertIn("categoria", form.errors)

    def test_categoria_de_receita_em_despesa_e_recusada(self):
        form = self._form(tipo="despesa", categoria="honorario")
        self.assertFalse(form.is_valid())
        self.assertIn("categoria", form.errors)

    def test_categorias_coerentes_sao_aceitas(self):
        self.assertTrue(self._form().is_valid())
        self.assertTrue(self._form(tipo="despesa", categoria="aluguel").is_valid())

    def test_reembolso_de_cliente_exige_cliente(self):
        form = self._form(categoria="reembolso")
        self.assertFalse(form.is_valid())
        self.assertIn("cliente", form.errors)

    def test_formulario_expoe_categorias_por_tipo(self):
        form = self._form()
        self.assertNotIn("aluguel", [v for v, _ in form.categorias_por_tipo["receita"]])
        self.assertNotIn("honorario", [v for v, _ in form.categorias_por_tipo["despesa"]])


class TestLancamentoCreditaCustas(FinanceiroBase):
    @classmethod
    def get_test_schema_name(cls):
        return "fin_ajustes_credito"

    def _reembolso(self, **kw):
        return self._lancamento(categoria="reembolso", cliente=self.cliente, **kw)

    def test_receita_reembolso_paga_credita_nas_custas_do_cliente(self):
        lanc = self._reembolso(status="pago", data_pagamento=self.hoje)
        credito = CustaJudicial.objects.get(lancamento=lanc)
        self.assertEqual(credito.tipo, "deposito_cliente")
        self.assertEqual(credito.cliente, self.cliente)
        self.assertEqual(credito.valor, Decimal("100.00"))

    def test_reembolso_pendente_nao_credita_ate_ser_recebido(self):
        lanc = self._reembolso()
        self.assertFalse(CustaJudicial.objects.filter(lancamento=lanc).exists())
        lanc.status, lanc.data_pagamento = "pago", self.hoje
        lanc.save()
        self.assertTrue(CustaJudicial.objects.filter(lancamento=lanc).exists())

    def test_reabrir_ou_cancelar_remove_o_credito(self):
        lanc = self._reembolso(status="pago", data_pagamento=self.hoje)
        lanc.status = "pendente"
        lanc.save()
        self.assertFalse(CustaJudicial.objects.filter(lancamento=lanc).exists())

    def test_honorario_nao_credita_custas(self):
        self._lancamento(cliente=self.cliente, status="pago", data_pagamento=self.hoje)
        self.assertFalse(CustaJudicial.objects.exists())

    def test_despesa_reembolso_nao_credita_custas(self):
        self._lancamento(tipo="despesa", categoria="reembolso", cliente=self.cliente,
                         status="pago", data_pagamento=self.hoje)
        self.assertFalse(CustaJudicial.objects.exists())

    def test_excluir_lancamento_remove_o_credito(self):
        lanc = self._reembolso(status="pago", data_pagamento=self.hoje)
        lanc.delete()
        self.assertFalse(CustaJudicial.objects.exists())

    def test_creditar_gera_uma_receita_reembolso_e_um_credito(self):
        credito = registrar_credito_cliente(
            cliente=self.cliente, valor=Decimal("250.00"), data=self.hoje, descricao="Depósito",
            anexo=SimpleUploadedFile("c.txt", b"x"),
        )
        lanc = credito.lancamento
        self.assertEqual((lanc.tipo, lanc.categoria, lanc.status), ("receita", "reembolso", "pago"))
        self.assertEqual(CustaJudicial.objects.count(), 1)
        self.assertTrue(credito.anexo)

    def test_tela_creditar_usa_o_fluxo_integrado(self):
        r = self.client.post(
            f"/financeiro/custas/cliente/{self.cliente.pk}/creditar/",
            {"descricao": "Dep", "valor": "80.00", "data": self.hoje.isoformat()},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(LancamentoFinanceiro.objects.filter(categoria="reembolso").count(), 1)
        self.assertEqual(CustaJudicial.objects.filter(tipo="deposito_cliente").count(), 1)


class TestReembolsoDeCustaAdiantada(FinanceiroBase):
    @classmethod
    def get_test_schema_name(cls):
        return "fin_ajustes_reembolso_custa"

    def test_reembolso_baixa_saldo_devedor_e_marca_custa(self):
        custa = self._custa(valor=Decimal("300.00"))
        reembolsar_custa(custa, data=self.hoje, comprovante=SimpleUploadedFile("r.txt", b"x"))
        custa.refresh_from_db()
        self.assertTrue(custa.reembolsada)
        self.assertEqual(custa.reembolsada_por.valor, Decimal("300.00"))
        self.assertFalse(custa.pode_reembolsar)

    def test_so_adiantamento_ainda_nao_reembolsado_pode_ser_reembolsado(self):
        paga = self._custa(tipo="paga_pelo_cliente")
        with self.assertRaises(ValueError):
            reembolsar_custa(paga, data=self.hoje, comprovante=SimpleUploadedFile("r.txt", b"x"))

    def test_tela_exige_comprovante(self):
        custa = self._custa()
        r = self.client.post(
            f"/financeiro/custas/{custa.pk}/reembolsar/", {"data": self.hoje.isoformat()},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 200)
        custa.refresh_from_db()
        self.assertFalse(custa.reembolsada)

    def test_tela_reembolsa_com_comprovante(self):
        custa = self._custa()
        r = self.client.post(
            f"/financeiro/custas/{custa.pk}/reembolsar/",
            {"data": self.hoje.isoformat(), "comprovante": SimpleUploadedFile("r.txt", b"x")},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        custa.refresh_from_db()
        self.assertTrue(custa.reembolsada)

    def test_custa_ja_reembolsada_nao_abre_de_novo(self):
        custa = self._custa()
        reembolsar_custa(custa, data=self.hoje, comprovante=SimpleUploadedFile("r.txt", b"x"))
        r = self.client.get(f"/financeiro/custas/{custa.pk}/reembolsar/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 404)

    def test_extrato_filtra_por_processo_e_pago_por(self):
        p1 = Processo.objects.create(criado_por=self.user, titulo="Proc 1")
        p2 = Processo.objects.create(criado_por=self.user, titulo="Proc 2")
        p1.clientes.add(self.cliente)
        p2.clientes.add(self.cliente)
        self._custa(descricao="No P1", processo=p1)
        self._custa(descricao="No P2 pelo cliente", processo=p2, tipo="paga_pelo_cliente")
        url = f"/financeiro/custas/cliente/{self.cliente.pk}/"
        r = self.client.get(url, {"processo": p1.pk}, HTTP_HOST=self.http_host)
        self.assertEqual([c.descricao for c in r.context["lancamentos"]], ["No P1"])
        r = self.client.get(url, {"pago_por": "cliente"}, HTTP_HOST=self.http_host)
        self.assertEqual([c.descricao for c in r.context["lancamentos"]], ["No P2 pelo cliente"])
        r = self.client.get(url, {"pago_por": "escritorio"}, HTTP_HOST=self.http_host)
        self.assertEqual([c.descricao for c in r.context["lancamentos"]], ["No P1"])


class TestTotaisEAnalise(FinanceiroBase):
    @classmethod
    def get_test_schema_name(cls):
        return "fin_ajustes_totais"

    def _totais(self, incluir_custas=True):
        return totais_do_mes(
            LancamentoFinanceiro.objects.all(), self.hoje.year, self.hoje.month,
            incluir_custas=incluir_custas,
        )

    def test_saldo_previsto_soma_recebido_e_subtrai_pagos(self):
        self._lancamento(valor=Decimal("1000"))  # a receber
        self._lancamento(valor=Decimal("300"), status="pago", data_pagamento=self.hoje)  # recebido
        self._lancamento(tipo="despesa", categoria="aluguel", valor=Decimal("200"))  # a pagar
        self._lancamento(tipo="despesa", categoria="aluguel", valor=Decimal("50"),
                         status="pago", data_pagamento=self.hoje)  # pago
        r = self.client.get("/financeiro/", HTTP_HOST=self.http_host)
        # 1000 + 300 - 200 - 50
        self.assertEqual(r.context["resumo"]["saldo_previsto"], "R$ 1.050,00")

    def test_reembolso_de_cliente_nao_e_recebido(self):
        self._lancamento(categoria="reembolso", cliente=self.cliente, valor=Decimal("400"),
                         status="pago", data_pagamento=self.hoje)
        self.assertEqual(self._totais()["recebido"], Decimal("0"))

    def test_custa_adiantada_nao_reembolsada_entra_como_pago(self):
        self._custa(valor=Decimal("500"))
        self.assertEqual(self._totais()["pago"], Decimal("500"))

    def test_custa_reembolsada_deixa_de_ser_despesa(self):
        custa = self._custa(valor=Decimal("500"))
        reembolsar_custa(custa, data=self.hoje, comprovante=SimpleUploadedFile("r.txt", b"x"))
        totais = self._totais()
        self.assertEqual(totais["pago"], Decimal("0"))
        self.assertEqual(totais["recebido"], Decimal("0"))

    def test_custa_paga_pelo_cliente_nao_conta(self):
        self._custa(tipo="paga_pelo_cliente", valor=Decimal("500"))
        self.assertEqual(self._totais()["pago"], Decimal("0"))

    def test_lancamento_de_custa_do_cliente_nao_conta_em_dobro(self):
        # Solicitação paga gera lançamento (despesa) + custa adiantada: só a custa conta.
        self._lancamento(tipo="despesa", categoria="solicitacao_pagamento", cliente=self.cliente,
                         valor=Decimal("500"), status="pago", data_pagamento=self.hoje)
        self._custa(valor=Decimal("500"))
        self.assertEqual(self._totais()["pago"], Decimal("500"))

    def test_sem_acesso_a_todos_os_dados_custas_globais_nao_entram(self):
        self._custa(valor=Decimal("500"))
        self.assertEqual(self._totais(incluir_custas=False)["pago"], Decimal("0"))

    def test_analise_de_dados_fontes_area_e_cliente(self):
        processo = Processo.objects.create(criado_por=self.user, titulo="P", area_direito="TRABALHISTA")
        self._lancamento(valor=Decimal("700"), status="pago", data_pagamento=self.hoje,
                         cliente=self.cliente, processo=processo)
        outro = Cliente.objects.create(nome_razao_social="OUTRO", tipo="PF", responsavel=self.user)
        self._lancamento(categoria="reembolso", cliente=outro, valor=Decimal("999"),
                         status="pago", data_pagamento=self.hoje)
        self._lancamento(tipo="despesa", categoria="aluguel", valor=Decimal("120"),
                         status="pago", data_pagamento=self.hoje)
        self._custa(valor=Decimal("80"))
        analise = analise_de_dados(LancamentoFinanceiro.objects.all(), inicio=None, incluir_custas=True)
        receitas = {l["rotulo"]: l["valor"] for l in analise["fontes_receita"]["linhas"]}
        self.assertEqual(receitas, {"Honorários": Decimal("700")})
        despesas = {l["rotulo"]: l["valor"] for l in analise["fontes_despesa"]["linhas"]}
        self.assertEqual(despesas["Aluguel"], Decimal("120"))
        self.assertEqual(despesas["Custas adiantadas (a reembolsar)"], Decimal("80"))
        self.assertEqual(analise["receita_por_area"]["linhas"][0]["rotulo"], "Trabalhista")
        self.assertEqual(analise["receita_por_cliente"]["linhas"][0]["rotulo"], "CLIENTE A")

    def test_analise_respeita_a_janela(self):
        antigo = self.hoje - timedelta(days=800)
        self._lancamento(valor=Decimal("50"), status="pago", data_pagamento=antigo)
        self._lancamento(valor=Decimal("70"), status="pago", data_pagamento=self.hoje)
        r = self.client.get("/financeiro/grafico/", {"janela": "12meses"}, HTTP_HOST=self.http_host)
        self.assertEqual(r.context["analise"]["fontes_receita"]["total"], Decimal("70"))
        r = self.client.get("/financeiro/grafico/", {"janela": "sempre"}, HTTP_HOST=self.http_host)
        self.assertEqual(r.context["analise"]["fontes_receita"]["total"], Decimal("120"))

    def test_aba_renomeada_para_analise_de_dados(self):
        r = self.client.get("/financeiro/grafico/", HTTP_HOST=self.http_host)
        self.assertContains(r, "Análise de dados")


class TestSolicitacoes(FinanceiroBase):
    @classmethod
    def get_test_schema_name(cls):
        return "fin_ajustes_solicitacoes"

    def _dados(self, **kw):
        dados = {
            "tipo": "pagamento", "descricao": "Custa", "valor": "50", "cliente": self.cliente.pk,
            "vencimento": self.hoje.isoformat(),
        }
        dados.update(kw)
        return dados

    def _form(self, **kw):
        return SolicitacaoFinanceiraForm(
            data=self._dados(**kw), files={"anexo": SimpleUploadedFile("b.txt", b"x")},
        )

    def test_pagamento_nao_exige_processo(self):
        self.assertTrue(self._form().is_valid())

    def test_reembolso_nao_exige_processo_nem_vencimento(self):
        form = self._form(tipo="reembolso", vencimento="", data_gasto=self.hoje.isoformat())
        self.assertTrue(form.is_valid(), form.errors)

    def test_pagamento_descarta_data_do_gasto(self):
        form = self._form(data_gasto=self.hoje.isoformat())
        self.assertTrue(form.is_valid())
        self.assertIsNone(form.cleaned_data["data_gasto"])

    def test_reembolso_descarta_vencimento(self):
        form = self._form(tipo="reembolso", data_gasto=self.hoje.isoformat())
        self.assertTrue(form.is_valid())
        self.assertIsNone(form.cleaned_data["vencimento"])

    def test_pagamento_continua_exigindo_cliente_e_vencimento(self):
        form = self._form(cliente="", vencimento="")
        self.assertFalse(form.is_valid())
        self.assertIn("cliente", form.errors)
        self.assertIn("vencimento", form.errors)

    def _solicitacao(self, status="solicitada", **kw):
        dados = {
            "tipo": "reembolso", "descricao": "S", "valor": Decimal("10"), "status": status,
            "anexo": SimpleUploadedFile("a.txt", b"x"), "solicitante": self.user,
        }
        dados.update(kw)
        return SolicitacaoFinanceira.objects.create(**dados)

    def test_lista_separa_pendentes_pagas_e_rejeitadas(self):
        self._solicitacao("solicitada", descricao="pend")
        self._solicitacao("paga", descricao="paga")
        self._solicitacao("rejeitada", descricao="rej")
        nomes = lambda situacao: [  # noqa: E731
            s.descricao for s in self.client.get(
                "/financeiro/solicitacoes/", {"situacao": situacao}, HTTP_HOST=self.http_host,
            ).context["solicitacoes"]
        ]
        self.assertEqual(nomes("pendentes"), ["pend"])
        self.assertEqual(nomes("pagas"), ["paga"])
        self.assertEqual(nomes("rejeitadas"), ["rej"])
        self.assertEqual(nomes(""), ["pend"])

    def test_filtros_de_cliente_solicitante_e_data_de_pagamento(self):
        outro = User.objects.create_user(username="outro_fin", password="x")
        outro_cliente = Cliente.objects.create(nome_razao_social="B", tipo="PF", responsavel=self.user)
        self._solicitacao("paga", descricao="A", cliente=self.cliente, data_pagamento=self.hoje,
                              pagamento_realizado_por=self.user)
        self._solicitacao("paga", descricao="B", cliente=outro_cliente, solicitante=outro,
                          data_pagamento=self.hoje - timedelta(days=40), pagamento_realizado_por=outro)
        get = lambda **p: [  # noqa: E731
            s.descricao for s in self.client.get(
                "/financeiro/solicitacoes/", {"situacao": "pagas", **p}, HTTP_HOST=self.http_host,
            ).context["solicitacoes"]
        ]
        self.assertEqual(get(cliente=self.cliente.pk), ["A"])
        self.assertEqual(get(solicitante=outro.pk), ["B"])
        self.assertEqual(get(pago_por_usuario=self.user.pk), ["A"])
        self.assertEqual(get(pago_de=(self.hoje - timedelta(days=5)).isoformat()), ["A"])
        self.assertEqual(get(pago_ate=(self.hoje - timedelta(days=5)).isoformat()), ["B"])

    def test_pagar_registra_data_e_quem_pagou(self):
        s = self._solicitacao("aprovada")
        s.avancar_para("paga", usuario=self.user)
        s.refresh_from_db()
        self.assertEqual(s.data_pagamento, self.hoje)
        self.assertEqual(s.pagamento_realizado_por, self.user)
