"""
Testes de custas judiciais por grupo de clientes (specs/4-financeiro-custas-grupos.md):
saldo do grupo, entrada/saída de membros, busca e filtro de saldo, aviso de
saldo antes/depois do débito, autorização e isolamento entre tenants.

Segue o mesmo padrão de fixtures de
apps/financeiro/tests/test_extrato_custas_cliente.py.
"""

from decimal import Decimal

from django.contrib.auth.models import User
from django.db import connection
from django.test import TransactionTestCase
from django_tenants.test.cases import TenantTestCase
from django_tenants.utils import schema_context, tenant_context

from apps.accounts.models import PapelAcesso, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import (
    MODULO_FINANCEIRO,
    NIVEL_DADOS_PROPRIOS,
    NIVEL_DADOS_TODOS,
    NIVEL_SOLICITACOES,
)
from apps.clientes.models import Cliente
from apps.financeiro import services
from apps.financeiro.forms import CustaJudicialForm
from apps.financeiro.models import CustaJudicial, GrupoCustas, LancamentoFinanceiro, MembroGrupoCustas
from apps.processos.models import Processo
from apps.saas_tenants.models import Dominio, Escritorio


class GruposBase(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "financeiro_custas_grupos"

    def setUp(self):
        super().setUp()
        domain_obj = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = domain_obj.domain if domain_obj else "localhost"
        self.user = self._usuario("financeiro_grupos", NIVEL_DADOS_TODOS)
        self.client.force_login(self.user)
        self.holding = self._cliente("Holding X", "11.111.111/0001-11")
        self.filial_a = self._cliente("Filial Alfa", "22.222.222/0001-22")
        self.filial_b = self._cliente("Filial Beta", "33.333.333/0001-33")
        self.grupo = GrupoCustas.objects.create(nome="Grupo Holding X")
        services.adicionar_membro_ao_grupo(self.grupo, self.filial_a)
        services.adicionar_membro_ao_grupo(self.grupo, self.filial_b)

    def _usuario(self, username, nivel):
        user = User.objects.create_user(username=username, password="testpass")
        papel = PapelAcesso.objects.create(nome=f"Papel {username}", ativo=True)
        UsuarioPapel.objects.create(usuario=user, papel=papel, ativo=True)
        PermissaoPapel.objects.create(papel=papel, modulo=MODULO_FINANCEIRO, ativo=True, nivel=nivel)
        return user

    def _cliente(self, nome, documento=""):
        return Cliente.objects.create(
            nome_razao_social=nome, cpf_cnpj=documento, tipo="PJ", responsavel=self.user,
        )

    def _processo(self, cliente, titulo="Processo"):
        processo = Processo.objects.create(titulo=titulo, responsavel=self.user, status="ativo")
        processo.clientes.add(cliente)
        return processo

    def _custa(self, **kwargs):
        defaults = {
            "descricao": "Custa", "valor": "100.00", "data": "2026-09-01",
            "tipo": "adiantamento", "cliente": self.holding,
        }
        defaults.update(kwargs)
        return CustaJudicial.objects.create(**defaults)

    def _credito_grupo(self, valor="1000.00"):
        return services.registrar_credito_grupo(
            grupo=self.grupo, valor=Decimal(valor), data="2026-09-01", descricao="Aporte da holding",
        )

    def _get(self, url, **params):
        return self.client.get(url, params, HTTP_HOST=self.http_host)

    def _post(self, url, dados=None):
        return self.client.post(url, dados or {}, HTTP_HOST=self.http_host)

    def _linha_lista(self, resposta, *, grupo_id=None, cliente_id=None):
        return next(
            (s for s in resposta.context["saldo_clientes"]
             if (grupo_id and s["grupo_id"] == grupo_id) or (cliente_id and s["cliente_id"] == cliente_id)),
            None,
        )


class TestSaldoDoGrupo(GruposBase):
    def test_saldo_do_grupo_segue_a_formula_do_pdr_0005(self):
        self._credito_grupo("1000.00")
        self._custa(cliente=self.filial_a, grupo=self.grupo, valor="300.00")
        self._custa(cliente=self.filial_b, grupo=self.grupo, tipo="paga_pelo_cliente", valor="9999.00")

        self.assertEqual(services.saldo_do_grupo(self.grupo), Decimal("700.00"))

    def test_credito_e_debito_do_grupo_nao_alteram_saldo_individual_do_membro(self):
        self._credito_grupo("1000.00")
        self._custa(cliente=self.filial_a, grupo=self.grupo, valor="300.00")

        self.assertEqual(services.saldo_individual_do_cliente(self.filial_a), Decimal("0"))
        self.assertEqual(services.saldo_individual_do_cliente(self.filial_b), Decimal("0"))

    def test_lancamento_novo_de_membro_sem_grupo_cai_no_saldo_do_grupo(self):
        custa = self._custa(cliente=self.filial_a, valor="50.00")

        self.assertEqual(custa.grupo, self.grupo)
        self.assertEqual(services.saldo_do_grupo(self.grupo), Decimal("-50.00"))
        self.assertEqual(services.saldo_individual_do_cliente(self.filial_a), Decimal("0"))

    def test_credito_do_grupo_gera_receita_reembolso_sem_cliente(self):
        credito = self._credito_grupo("400.00")

        self.assertEqual(credito.grupo, self.grupo)
        self.assertIsNone(credito.cliente)
        self.assertEqual(credito.lancamento.categoria, "reembolso")
        self.assertEqual(credito.lancamento.tipo, "receita")

    def test_credito_do_grupo_sobrevive_a_novo_save_do_lancamento_e_acompanha_edicao(self):
        credito = self._credito_grupo("400.00")
        lancamento = credito.lancamento

        lancamento.valor = Decimal("450.00")
        lancamento.save()

        credito.refresh_from_db()
        self.assertEqual(credito.valor, Decimal("450.00"))
        self.assertEqual(credito.grupo, self.grupo)

        lancamento.status = "pendente"
        lancamento.save()
        self.assertFalse(CustaJudicial.objects.filter(pk=credito.pk).exists())

    def test_custa_do_grupo_nao_pode_ser_reembolsada_individualmente(self):
        custa = self._custa(cliente=self.filial_a, grupo=self.grupo)

        self.assertFalse(custa.pode_reembolsar)

    def test_custas_a_recuperar_conta_grupo_uma_vez_e_ignora_membro(self):
        self._custa(cliente=self.filial_a, grupo=self.grupo, valor="300.00")
        self._custa(cliente=self.filial_b, grupo=self.grupo, valor="200.00")
        avulsa = self._cliente("Avulso")
        self._custa(cliente=avulsa, valor="40.00")

        devedores = services.custas_a_recuperar()

        self.assertEqual(devedores, {
            ("grupo", self.grupo.pk): Decimal("500.00"),
            ("cliente", avulsa.pk): Decimal("40.00"),
        })
        self.assertEqual(services.total_custas_a_recuperar(), Decimal("540.00"))

    def test_credito_do_grupo_abate_custas_a_recuperar(self):
        self._credito_grupo("1000.00")
        self._custa(cliente=self.filial_a, grupo=self.grupo, valor="300.00")

        self.assertEqual(services.custas_a_recuperar(), {})


class TestMembros(GruposBase):
    def test_cliente_nao_entra_em_dois_grupos(self):
        outro = GrupoCustas.objects.create(nome="Outro grupo")

        with self.assertRaises(ValueError):
            services.adicionar_membro_ao_grupo(outro, self.filial_a)
        self.assertEqual(MembroGrupoCustas.objects.filter(cliente=self.filial_a).count(), 1)

    def test_cliente_com_saldo_individual_diferente_de_zero_nao_entra(self):
        devedor = self._cliente("Devedor")
        self._custa(cliente=devedor, valor="10.00")
        credor = self._cliente("Credor")
        self._custa(cliente=credor, tipo="deposito_cliente", valor="10.00")

        for cliente in (devedor, credor):
            with self.assertRaises(ValueError):
                services.adicionar_membro_ao_grupo(self.grupo, cliente)

    def test_cliente_com_saldo_individual_zerado_entra(self):
        novo = self._cliente("Zerado")
        self._custa(cliente=novo, valor="10.00")
        self._custa(cliente=novo, tipo="deposito_cliente", valor="10.00")

        services.adicionar_membro_ao_grupo(self.grupo, novo)

        self.assertTrue(MembroGrupoCustas.objects.filter(cliente=novo, grupo=self.grupo).exists())

    def test_remover_membro_bloqueado_com_lancamentos_no_grupo(self):
        self._custa(cliente=self.filial_a, grupo=self.grupo)
        membro = MembroGrupoCustas.objects.get(cliente=self.filial_a)

        with self.assertRaises(ValueError):
            services.remover_membro_do_grupo(membro)
        self.assertTrue(MembroGrupoCustas.objects.filter(pk=membro.pk).exists())

    def test_remover_membro_sem_lancamentos(self):
        membro = MembroGrupoCustas.objects.get(cliente=self.filial_b)

        services.remover_membro_do_grupo(membro)

        self.assertFalse(MembroGrupoCustas.objects.filter(cliente=self.filial_b).exists())

    def test_apagar_grupo_bloqueado_com_lancamentos_e_permitido_sem(self):
        self._credito_grupo()
        with self.assertRaises(ValueError):
            services.excluir_grupo(self.grupo)
        self.assertTrue(GrupoCustas.objects.filter(pk=self.grupo.pk).exists())

        vazio = GrupoCustas.objects.create(nome="Vazio")
        services.excluir_grupo(vazio)
        self.assertFalse(GrupoCustas.objects.filter(pk=vazio.pk).exists())

    def test_views_de_membros_e_grupo_mostram_bloqueio_sem_reescrever_historico(self):
        self._custa(cliente=self.filial_a, grupo=self.grupo)

        r = self._post(f"/financeiro/custas/grupo/{self.grupo.pk}/membros/{self.filial_a.pk}/remover/")
        self.assertEqual(r.status_code, 302)
        self.assertTrue(MembroGrupoCustas.objects.filter(cliente=self.filial_a).exists())

        r = self._post(f"/financeiro/custas/grupo/{self.grupo.pk}/apagar/")
        self.assertEqual(r.status_code, 302)
        self.assertTrue(GrupoCustas.objects.filter(pk=self.grupo.pk).exists())

    def test_view_adiciona_membro_apenas_de_cliente_sem_grupo(self):
        novo = self._cliente("Novo Membro")

        self._post(f"/financeiro/custas/grupo/{self.grupo.pk}/membros/adicionar/", {"cliente": novo.pk})
        self.assertTrue(MembroGrupoCustas.objects.filter(cliente=novo, grupo=self.grupo).exists())

        outro = GrupoCustas.objects.create(nome="Outro")
        self._post(f"/financeiro/custas/grupo/{outro.pk}/membros/adicionar/", {"cliente": self.filial_a.pk})
        self.assertFalse(MembroGrupoCustas.objects.filter(grupo=outro).exists())

    def test_criar_grupo_pela_view_e_nome_unico(self):
        r = self._post("/financeiro/custas/grupo/novo/", {"nome": "Grupo Y"})
        grupo = GrupoCustas.objects.get(nome="Grupo Y")
        self.assertRedirects(
            r, f"/financeiro/custas/grupo/{grupo.pk}/", fetch_redirect_response=False,
        )

        r = self._post("/financeiro/custas/grupo/novo/", {"nome": "Grupo Y"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(GrupoCustas.objects.filter(nome="Grupo Y").count(), 1)


class TestListaDeCustas(GruposBase):
    def test_membro_some_da_lista_individual_e_grupo_aparece_com_saldo_proprio(self):
        self._credito_grupo("1000.00")
        self._custa(cliente=self.filial_a, grupo=self.grupo, valor="300.00")

        r = self._get("/financeiro/custas/")

        self.assertIsNone(self._linha_lista(r, cliente_id=self.filial_a.pk))
        self.assertIsNone(self._linha_lista(r, cliente_id=self.filial_b.pk))
        self.assertIsNotNone(self._linha_lista(r, cliente_id=self.holding.pk))
        linha = self._linha_lista(r, grupo_id=self.grupo.pk)
        self.assertEqual(linha["saldo"], "Crédito: R$ 700,00")
        self.assertEqual(linha["url"], f"/financeiro/custas/grupo/{self.grupo.pk}/")

    def test_busca_por_nome_e_documento_do_cliente(self):
        r = self._get("/financeiro/custas/", busca="holding")
        self.assertIsNotNone(self._linha_lista(r, cliente_id=self.holding.pk))
        self.assertIsNotNone(self._linha_lista(r, grupo_id=self.grupo.pk))  # o nome do grupo também casa
        self.assertEqual(len(r.context["saldo_clientes"]), 2)

        r = self._get("/financeiro/custas/", busca="HOLDING X")
        self.assertEqual(len(r.context["saldo_clientes"]), 2)

        r = self._get("/financeiro/custas/", busca="11111111000111")
        self.assertEqual([s["cliente_id"] for s in r.context["saldo_clientes"]], [self.holding.pk])

        r = self._get("/financeiro/custas/", busca="11.111.111/0001-11")
        self.assertEqual([s["cliente_id"] for s in r.context["saldo_clientes"]], [self.holding.pk])

    def test_busca_pelo_nome_do_grupo_e_dos_membros_acha_o_grupo(self):
        for termo in ("grupo holding", "alfa"):
            r = self._get("/financeiro/custas/", busca=termo)
            self.assertEqual([s["grupo_id"] for s in r.context["saldo_clientes"]], [self.grupo.pk], termo)

    def test_busca_sem_resultado(self):
        r = self._get("/financeiro/custas/", busca="inexistente")
        self.assertEqual(r.context["saldo_clientes"], [])

    def test_filtro_de_saldo_para_clientes_e_grupos(self):
        credor = self._cliente("Credor")
        self._custa(cliente=credor, tipo="deposito_cliente", valor="10.00")
        devedor = self._cliente("Devedor")
        self._custa(cliente=devedor, valor="10.00")
        self._credito_grupo("1000.00")  # grupo com crédito

        def ids(filtro):
            r = self._get("/financeiro/custas/", saldo=filtro)
            return {(s["cliente_id"], s["grupo_id"]) for s in r.context["saldo_clientes"]}

        self.assertEqual(ids("com_credito"), {(credor.pk, None), (None, self.grupo.pk)})
        self.assertEqual(ids("em_debito"), {(devedor.pk, None)})
        self.assertEqual(ids("sem_saldo"), {(self.holding.pk, None)})

    def test_grupo_em_debito_entra_pelo_saldo_do_proprio_grupo(self):
        self._custa(cliente=self.filial_a, grupo=self.grupo, valor="10.00")

        r = self._get("/financeiro/custas/", saldo="em_debito")

        self.assertEqual([s["grupo_id"] for s in r.context["saldo_clientes"]], [self.grupo.pk])
        self.assertEqual(r.context["saldo_clientes"][0]["saldo"], "A cobrar: R$ 10,00")

    def test_filtro_invalido_e_ignorado(self):
        r = self._get("/financeiro/custas/", saldo="qualquer")
        self.assertEqual(r.context["filtro_saldo"], "")


class TestExtratos(GruposBase):
    def test_extrato_do_grupo_mostra_cliente_e_processo_de_cada_debito(self):
        processo = self._processo(self.filial_a, "Processo da Alfa")
        self._credito_grupo("1000.00")
        self._custa(cliente=self.filial_a, grupo=self.grupo, processo=processo, valor="300.00")

        r = self._get(f"/financeiro/custas/grupo/{self.grupo.pk}/")

        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["saldo"], "+ R$ 700,00")
        self.assertContains(r, f"Cliente: {self.filial_a}")
        self.assertContains(r, f"Processo: {processo}")
        self.assertEqual(len(r.context["lancamentos"]), 1)
        self.assertEqual(len(r.context["creditos"]), 1)
        self.assertEqual({m.cliente_id for m in r.context["membros"]}, {self.filial_a.pk, self.filial_b.pk})

    def test_ficha_do_membro_mostra_debito_do_grupo_sem_afetar_saldo_individual(self):
        self._custa(cliente=self.filial_a, grupo=self.grupo, valor="300.00", descricao="Custa pelo grupo")

        r = self._get(f"/financeiro/custas/cliente/{self.filial_a.pk}/")

        self.assertContains(r, "Pago pelo saldo do Grupo Grupo Holding X")
        self.assertEqual(r.context["saldo"], "+ R$ 0,00")
        self.assertEqual(r.context["grupo_do_cliente"], self.grupo)

    def test_extrato_de_cliente_sem_grupo_segue_igual(self):
        self._custa(cliente=self.holding, valor="100.00")

        r = self._get(f"/financeiro/custas/cliente/{self.holding.pk}/")

        self.assertEqual(r.context["saldo"], "− R$ 100,00")
        self.assertIsNone(r.context["grupo_do_cliente"])

    def test_creditar_grupo_altera_so_o_saldo_do_grupo(self):
        r = self._post(
            f"/financeiro/custas/grupo/{self.grupo.pk}/creditar/",
            {"descricao": "Aporte", "valor": "500.00", "data": "2026-09-10"},
        )

        self.assertRedirects(r, f"/financeiro/custas/grupo/{self.grupo.pk}/", fetch_redirect_response=False)
        self.assertEqual(services.saldo_do_grupo(self.grupo), Decimal("500.00"))
        self.assertEqual(services.saldo_individual_do_cliente(self.filial_a), Decimal("0"))
        self.assertEqual(
            LancamentoFinanceiro.objects.filter(categoria="reembolso", tipo="receita").count(), 1,
        )


class TestFormularioDeDebito(GruposBase):
    def _dados(self, **extra):
        dados = {
            "tipo": "adiantamento", "descricao": "Custa de citação", "valor": "80.00",
            "data": "2026-09-15", "cliente": self.filial_a.pk,
        }
        dados.update(extra)
        return dados

    def test_debito_no_grupo_exige_o_membro(self):
        r = self._post("/financeiro/custas/nova/", self._dados(grupo=self.grupo.pk, cliente=""))

        self.assertEqual(r.status_code, 200)
        self.assertIn("cliente", r.context["form"].errors)
        self.assertFalse(CustaJudicial.objects.exists())

    def test_debito_no_grupo_rejeita_cliente_que_nao_e_membro(self):
        r = self._post("/financeiro/custas/nova/", self._dados(grupo=self.grupo.pk, cliente=self.holding.pk))

        self.assertEqual(r.status_code, 200)
        self.assertIn("cliente", r.context["form"].errors)

    def test_debito_no_grupo_com_membro_debita_so_o_grupo(self):
        r = self._post("/financeiro/custas/nova/", self._dados(grupo=self.grupo.pk))

        self.assertRedirects(r, f"/financeiro/custas/grupo/{self.grupo.pk}/", fetch_redirect_response=False)
        custa = CustaJudicial.objects.get()
        self.assertEqual((custa.grupo, custa.cliente), (self.grupo, self.filial_a))
        self.assertEqual(services.saldo_do_grupo(self.grupo), Decimal("-80.00"))
        self.assertEqual(services.saldo_individual_do_cliente(self.filial_a), Decimal("0"))

    def test_processo_e_opcional_mas_so_de_membro(self):
        do_membro = self._processo(self.filial_a, "Da Alfa")
        de_fora = self._processo(self.holding, "Da Holding")

        r = self._post("/financeiro/custas/nova/", self._dados(grupo=self.grupo.pk, processo=de_fora.pk))
        self.assertEqual(r.status_code, 200)
        self.assertFalse(CustaJudicial.objects.exists())

        self._post("/financeiro/custas/nova/", self._dados(grupo=self.grupo.pk, processo=do_membro.pk))
        self.assertEqual(CustaJudicial.objects.get().processo, do_membro)

    def test_debito_de_membro_sem_escolher_grupo_cai_no_grupo(self):
        self._post("/financeiro/custas/nova/", self._dados())

        self.assertEqual(CustaJudicial.objects.get().grupo, self.grupo)

    def test_formulario_traz_grupo_pre_selecionado_pela_url(self):
        r = self._get("/financeiro/custas/nova/", grupo=self.grupo.pk)

        self.assertEqual(r.context["form"].initial["grupo"], str(self.grupo.pk))

    def test_formulario_de_grupo_nao_expoe_tipo_deposito(self):
        tipos = [valor for valor, _ in CustaJudicialForm().fields["tipo"].choices]
        self.assertNotIn("deposito_cliente", tipos)


class TestAvisoDeSaldo(GruposBase):
    URL = "/financeiro/custas/aviso-saldo/"

    def test_aviso_de_cliente_mostra_saldo_atual_e_depois(self):
        self._custa(cliente=self.holding, tipo="deposito_cliente", valor="500.00")

        dados = self._get(self.URL, cliente=self.holding.pk, valor="200.00").json()

        self.assertTrue(dados["visivel"])
        self.assertEqual(dados["origem"], "Holding X")
        self.assertEqual(dados["atual"], "+ R$ 500,00")
        self.assertEqual(dados["depois"], "+ R$ 300,00")
        self.assertFalse(dados["depois_negativo"])

    def test_aviso_mostra_saldo_negativo_apos_o_debito(self):
        self._custa(cliente=self.holding, tipo="deposito_cliente", valor="100.00")

        dados = self._get(self.URL, cliente=self.holding.pk, valor="250.50").json()

        self.assertEqual(dados["depois"], "− R$ 150,50")
        self.assertTrue(dados["depois_negativo"])
        self.assertFalse(dados["atual_negativo"])

    def test_aviso_de_grupo_usa_saldo_do_grupo(self):
        self._credito_grupo("1000.00")

        dados = self._get(self.URL, grupo=self.grupo.pk, cliente=self.filial_a.pk, valor="300").json()

        self.assertEqual(dados["origem"], "Grupo Grupo Holding X")
        self.assertEqual(dados["atual"], "+ R$ 1.000,00")
        self.assertEqual(dados["depois"], "+ R$ 700,00")

    def test_aviso_de_membro_sem_grupo_escolhido_usa_saldo_do_grupo(self):
        self._credito_grupo("1000.00")

        dados = self._get(self.URL, cliente=self.filial_b.pk, valor="100").json()

        self.assertEqual(dados["origem"], "Grupo Grupo Holding X")
        self.assertEqual(dados["depois"], "+ R$ 900,00")

    def test_aviso_sem_valor_mostra_so_saldo_atual(self):
        dados = self._get(self.URL, cliente=self.holding.pk).json()

        self.assertFalse(dados["valor_informado"])
        self.assertEqual(dados["atual"], dados["depois"])

    def test_aviso_sem_cliente_nem_grupo_nao_e_visivel(self):
        self.assertEqual(self._get(self.URL, valor="10").json(), {"visivel": False})

    def test_aviso_ignora_valor_invalido(self):
        for valor in ("abc", "-5", "Infinity", "NaN"):
            dados = self._get(self.URL, cliente=self.holding.pk, valor=valor).json()
            self.assertFalse(dados["valor_informado"], valor)

    def test_aviso_nao_muda_o_saldo(self):
        self._get(self.URL, cliente=self.holding.pk, valor="999")

        self.assertEqual(services.saldo_individual_do_cliente(self.holding), Decimal("0"))


class TestAutorizacaoDeGrupos(GruposBase):
    def _urls_get(self):
        return [
            "/financeiro/custas/aviso-saldo/",
            "/financeiro/custas/grupo/novo/",
            f"/financeiro/custas/grupo/{self.grupo.pk}/",
            f"/financeiro/custas/grupo/{self.grupo.pk}/creditar/",
        ]

    def _urls_post(self):
        return [
            f"/financeiro/custas/grupo/{self.grupo.pk}/membros/adicionar/",
            f"/financeiro/custas/grupo/{self.grupo.pk}/membros/{self.filial_a.pk}/remover/",
            f"/financeiro/custas/grupo/{self.grupo.pk}/apagar/",
            f"/financeiro/custas/grupo/{self.grupo.pk}/creditar/",
            "/financeiro/custas/grupo/novo/",
        ]

    def test_nivel_solicitacoes_nao_acessa_nenhuma_rota_de_grupo(self):
        solicitante = self._usuario("so_solicita", NIVEL_SOLICITACOES)
        self.client.force_login(solicitante)

        for url in self._urls_get():
            self.assertEqual(self._get(url).status_code, 403, url)
        for url in self._urls_post():
            self.assertEqual(self._post(url, {"nome": "X", "cliente": self.holding.pk}).status_code, 403, url)
        self.assertTrue(GrupoCustas.objects.filter(pk=self.grupo.pk).exists())
        self.assertEqual(GrupoCustas.objects.count(), 1)

    def test_usuario_sem_modulo_financeiro_nao_acessa(self):
        sem_modulo = User.objects.create_user(username="sem_modulo", password="testpass")
        self.client.force_login(sem_modulo)

        for url in self._urls_get():
            self.assertEqual(self._get(url).status_code, 403, url)

    def test_lista_de_custas_e_extrato_do_cliente_seguem_negados_ao_nivel_solicitacoes(self):
        solicitante = self._usuario("so_solicita_2", NIVEL_SOLICITACOES)
        self.client.force_login(solicitante)

        self.assertEqual(self._get("/financeiro/custas/").status_code, 403)
        self.assertEqual(self._get(f"/financeiro/custas/cliente/{self.filial_a.pk}/").status_code, 403)

    def test_acoes_de_alteracao_exigem_post(self):
        for url in (
            f"/financeiro/custas/grupo/{self.grupo.pk}/apagar/",
            f"/financeiro/custas/grupo/{self.grupo.pk}/membros/{self.filial_a.pk}/remover/",
            f"/financeiro/custas/grupo/{self.grupo.pk}/membros/adicionar/",
        ):
            self.assertEqual(self._get(url).status_code, 405, url)

    def test_visitante_anonimo_e_redirecionado_ao_login(self):
        self.client.logout()

        r = self._get(f"/financeiro/custas/grupo/{self.grupo.pk}/")

        self.assertEqual(r.status_code, 302)
        self.assertIn("login", r["Location"])


class TestRegressoesRelacionadas(GruposBase):
    def test_excluir_cliente_membro_preserva_saldo_e_historico_do_grupo(self):
        self._credito_grupo("1000.00")
        self._custa(cliente=self.filial_a, grupo=self.grupo, valor="300.00")

        self.filial_a.delete()

        self.assertEqual(services.saldo_do_grupo(self.grupo), Decimal("700.00"))
        self.assertFalse(MembroGrupoCustas.objects.filter(grupo=self.grupo, cliente_id=None).exists())
        r = self._get(f"/financeiro/custas/grupo/{self.grupo.pk}/")
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, "Cliente: None")

    def test_nivel_dados_proprios_acessa_como_nas_demais_rotas_de_custas(self):
        proprio = self._usuario("financeiro_proprio", NIVEL_DADOS_PROPRIOS)
        self.client.force_login(proprio)

        self.assertEqual(self._get("/financeiro/custas/").status_code, 200)
        self.assertEqual(self._get(f"/financeiro/custas/grupo/{self.grupo.pk}/").status_code, 200)


class TestIsolamentoDeGruposEntreTenants(GruposBase):
    @classmethod
    def _fixture_setup(cls):
        return TransactionTestCase._fixture_setup.__func__(cls)

    def _fixture_teardown(self):
        return TransactionTestCase._fixture_teardown(self)

    @classmethod
    def get_test_schema_name(cls):
        return "financeiro_grupos_iso_a"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Grupos Iso A"
        tenant.slug = "grupos-iso-a"

    def test_grupo_e_saldo_de_um_tenant_nao_aparecem_no_outro(self):
        self._credito_grupo("1000.00")
        tenant_b = Escritorio(
            schema_name="financeiro_grupos_iso_b", nome="Grupos Iso B", slug="grupos-iso-b",
        )
        with schema_context("public"):
            tenant_b.save()
            dominio_b = Dominio.objects.create(
                tenant=tenant_b, domain="grupos-iso-b.test.com", is_primary=True,
            )

        try:
            with tenant_context(tenant_b):
                usuario_b = self._usuario("financeiro_grupos_b", NIVEL_DADOS_TODOS)
                grupo_b = GrupoCustas.objects.create(nome="Grupo Holding X")
                self.assertEqual(services.saldo_do_grupo(grupo_b), Decimal("0"))
                self.client.force_login(usuario_b)

            r = self.client.get("/financeiro/custas/", HTTP_HOST=dominio_b.domain)
            self.assertEqual(r.status_code, 200)
            linha = next(s for s in r.context["saldo_clientes"] if s["grupo_id"] == grupo_b.pk)
            self.assertEqual(linha["saldo"], "Sem saldo pendente")
            self.assertEqual(len(r.context["saldo_clientes"]), 1)
            self.assertEqual(list(r.context["custas"]), [])

            r = self.client.get(
                f"/financeiro/custas/grupo/{grupo_b.pk}/", HTTP_HOST=dominio_b.domain,
            )
            self.assertEqual(r.context["saldo"], "+ R$ 0,00")
            with tenant_context(self.tenant):
                self.assertEqual(services.saldo_do_grupo(self.grupo), Decimal("1000.00"))
        finally:
            with schema_context("public"):
                tenant_b.delete(force_drop=True)
            connection.set_tenant(self.tenant)
