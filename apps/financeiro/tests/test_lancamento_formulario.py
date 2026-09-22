"""
Formulário de novo lançamento (revisão de 2026-09-20): categorias por
tipo, data de pagamento/comprovante só com
status Pago, parcelado e fontes de receita/despesa por categoria.
"""

import shutil
import tempfile
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PapelAcesso, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import (
    MODULO_FINANCEIRO,
    NIVEL_DADOS_PROPRIOS,
    NIVEL_DADOS_TODOS,
)
from apps.financeiro.forms import LancamentoFinanceiroForm
from apps.financeiro.models import LancamentoFinanceiro

_MEDIA_TMP = tempfile.mkdtemp(prefix="lawsystem_test_media_lancamento_form_")

CATEGORIAS_RECEITA = [
    "Honorários", "Honorários de sucumbência", "Reembolso", "Consultoria", "Comissão",
    "Auditoria", "Acordo", "Capacitação", "Outros",
]
CATEGORIAS_DESPESA = [
    "Aluguel", "Condomínio", "Água", "Luz", "Internet", "Salário", "Bonificação",
    "Impostos/taxas", "Cursos", "Equipamentos", "Material", "Software/assinatura", "Outros",
]


class LancamentoFormularioBase(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "fin_lancamento_formulario"

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_MEDIA_TMP, ignore_errors=True)

    def setUp(self):
        self._media_override = override_settings(MEDIA_ROOT=_MEDIA_TMP)
        self._media_override.enable()
        self.addCleanup(self._media_override.disable)
        super().setUp()
        from apps.saas_tenants.models import Dominio

        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"
        self.hoje = timezone.localdate()
        self.user = self._usuario("fin_form", NIVEL_DADOS_TODOS)
        self.client.force_login(self.user)

    def _usuario(self, username, nivel):
        usuario = User.objects.create_user(username=username, password="testpass")
        papel = PapelAcesso.objects.create(nome=f"Papel {username}", ativo=True)
        UsuarioPapel.objects.create(usuario=usuario, papel=papel, ativo=True)
        PermissaoPapel.objects.create(papel=papel, modulo=MODULO_FINANCEIRO, ativo=True, nivel=nivel)
        return usuario

    def _dados(self, **extra):
        dados = {
            "tipo": "receita", "descricao": "X", "valor": "10.00", "categoria": "honorario",
            "status": "pendente", "data_vencimento": self.hoje.isoformat(), "classificacao": "unica",
        }
        dados.update(extra)
        return dados

    def _form(self, **extra):
        return LancamentoFinanceiroForm(data=self._dados(**extra))

    def _lancamento(self, **kwargs):
        dados = {
            "tipo": "receita", "descricao": "Lanç", "valor": Decimal("100.00"),
            "data_vencimento": self.hoje, "status": "pendente", "categoria": "honorario",
        }
        dados.update(kwargs)
        return LancamentoFinanceiro.objects.create(**dados)


class TestCategoriasPorTipo(LancamentoFormularioBase):
    def _rotulos(self, tipo):
        return [rotulo for _, rotulo in LancamentoFinanceiroForm().categorias_por_tipo[tipo]]

    def test_dropdown_de_receita_tem_so_as_categorias_da_spec(self):
        self.assertEqual(self._rotulos("receita"), CATEGORIAS_RECEITA)

    def test_dropdown_de_despesa_tem_so_as_categorias_da_spec(self):
        self.assertEqual(self._rotulos("despesa"), CATEGORIAS_DESPESA)

    def test_categorias_internas_nao_aparecem_no_dropdown(self):
        opcoes = {v for lista in LancamentoFinanceiroForm().categorias_por_tipo.values() for v, _ in lista}
        for interna in ("custa_judicial", "solicitacao_pagamento", "exito", "diligencia", "pericia", "taxa"):
            self.assertNotIn(interna, opcoes)

    def test_backend_recusa_categoria_interna_em_lancamento_manual(self):
        for tipo, categoria in (("despesa", "custa_judicial"), ("despesa", "solicitacao_pagamento"),
                                ("despesa", "reembolso"), ("receita", "exito")):
            form = self._form(tipo=tipo, categoria=categoria)
            self.assertFalse(form.is_valid(), categoria)
            self.assertIn("categoria", form.errors)

    def test_backend_recusa_categoria_de_outro_tipo(self):
        self.assertIn("categoria", self._form(tipo="receita", categoria="luz").errors)
        self.assertIn("categoria", self._form(tipo="despesa", categoria="consultoria").errors)

    def test_toda_categoria_oferecida_e_aceita_no_seu_tipo(self):
        for tipo, categorias in LancamentoFinanceiro.CATEGORIAS_POR_TIPO.items():
            for categoria in categorias:
                extra = {"cliente": ""} if categoria != "reembolso" else {}
                if tipo == "receita" and categoria == "reembolso":
                    continue  # exige cliente — coberto em test_ajustes_revisao
                self.assertTrue(self._form(tipo=tipo, categoria=categoria, **extra).is_valid(), categoria)

    def test_lancamento_existente_com_categoria_interna_continua_editavel(self):
        gerado = self._lancamento(tipo="despesa", categoria="solicitacao_pagamento")
        form = LancamentoFinanceiroForm(
            data=self._dados(tipo="despesa", categoria="solicitacao_pagamento", descricao="Editada"),
            instance=gerado,
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIn("solicitacao_pagamento", [v for v, _ in form.categorias_por_tipo["despesa"]])

    def test_categoria_interna_do_lancamento_nao_vaza_para_o_outro_tipo(self):
        gerado = self._lancamento(tipo="despesa", categoria="solicitacao_pagamento")
        form = LancamentoFinanceiroForm(instance=gerado)
        self.assertNotIn("solicitacao_pagamento", [v for v, _ in form.categorias_por_tipo["receita"]])


class TestDataPagamentoEComprovante(LancamentoFormularioBase):
    def _arquivo(self):
        return SimpleUploadedFile("comprovante.pdf", b"x", content_type="application/pdf")

    def test_pago_exige_data_de_pagamento(self):
        self.assertIn("data_pagamento", self._form(status="pago").errors)

    def test_data_de_pagamento_e_descartada_se_nao_esta_pago(self):
        form = self._form(status="pendente", data_pagamento=self.hoje.isoformat())
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIsNone(form.cleaned_data["data_pagamento"])

    def test_boleto_e_aceito_independente_do_status(self):
        form = LancamentoFinanceiroForm(data=self._dados(), files={"anexo": self._arquivo()})
        self.assertTrue(form.is_valid(), form.errors)

    def test_comprovante_e_recusado_se_nao_esta_pago(self):
        form = LancamentoFinanceiroForm(data=self._dados(), files={"comprovante_pagamento": self._arquivo()})
        self.assertFalse(form.is_valid())
        self.assertIn("comprovante_pagamento", form.errors)

    def test_comprovante_e_aceito_com_status_pago(self):
        form = LancamentoFinanceiroForm(
            data=self._dados(status="pago", data_pagamento=self.hoje.isoformat()),
            files={"comprovante_pagamento": self._arquivo()},
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_comprovante_e_opcional_com_status_pago(self):
        self.assertTrue(self._form(status="pago", data_pagamento=self.hoje.isoformat()).is_valid())

    def test_view_grava_boleto_independente_do_status(self):
        r = self.client.post(
            "/financeiro/lancamentos/novo/",
            {**self._dados(), "anexo": self._arquivo()},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        self.assertTrue(LancamentoFinanceiro.objects.get(descricao="X").anexo)

    def test_view_grava_comprovante_do_lancamento_pago(self):
        r = self.client.post(
            "/financeiro/lancamentos/novo/",
            {**self._dados(status="pago", data_pagamento=self.hoje.isoformat()), "comprovante_pagamento": self._arquivo()},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        self.assertTrue(LancamentoFinanceiro.objects.get(descricao="X").comprovante_pagamento)

    def test_formulario_mostra_classificacao_antes_de_status_e_datas(self):
        r = self.client.get("/financeiro/lancamentos/novo/", HTTP_HOST=self.http_host)
        html = r.content.decode()
        posicoes = [html.index(f'id="{campo}"') for campo in (
            "id_valor", "id_categoria", "id_classificacao", "id_status", "id_data_vencimento", "id_data_pagamento",
        )]
        self.assertEqual(posicoes, sorted(posicoes))


class TestParcelado(LancamentoFormularioBase):
    def _criar(self, **extra):
        return self.client.post(
            "/financeiro/lancamentos/novo/",
            self._dados(tipo="despesa", categoria="aluguel", classificacao="parcelado",
                        numero_parcelas="3", data_vencimento="2026-01-31", **extra),
            HTTP_HOST=self.http_host,
        )

    def test_parcelas_no_mesmo_dia_sem_derivar_em_mes_curto(self):
        self.assertEqual(self._criar().status_code, 302)
        datas = list(
            LancamentoFinanceiro.objects.order_by("data_vencimento").values_list("data_vencimento", flat=True)
        )
        self.assertEqual(datas, [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31)])

    def test_valor_digitado_e_o_total_dividido_entre_as_parcelas(self):
        # 250,00 ÷ 3 não é exato: a última parcela absorve o resíduo do
        # arredondamento, para a soma bater com o total digitado.
        self._criar(valor="250.00")
        valores = list(LancamentoFinanceiro.objects.order_by("data_vencimento").values_list("valor", flat=True))
        self.assertEqual(valores, [Decimal("83.33"), Decimal("83.33"), Decimal("83.34")])
        self.assertEqual(sum(valores), Decimal("250.00"))

    def test_so_a_primeira_nasce_paga(self):
        self._criar(status="pago", data_pagamento="2026-01-31")
        lancamentos = list(LancamentoFinanceiro.objects.order_by("data_vencimento"))
        self.assertEqual([l.status for l in lancamentos], ["pago", "pendente", "pendente"])
        self.assertEqual([l.data_pagamento for l in lancamentos], [date(2026, 1, 31), None, None])

    def test_card_mostra_a_parcela_atual_sobre_o_total(self):
        self._criar()
        r_jan = self.client.get("/financeiro/?ano=2026&mes=1", HTTP_HOST=self.http_host)
        r_fev = self.client.get("/financeiro/?ano=2026&mes=2", HTTP_HOST=self.http_host)
        r_mar = self.client.get("/financeiro/?ano=2026&mes=3", HTTP_HOST=self.http_host)
        self.assertContains(r_jan, "PARCELA(S): (1/3)")
        self.assertContains(r_fev, "PARCELA(S): (2/3)")
        self.assertContains(r_mar, "PARCELA(S): (3/3)")

    def test_comprovante_fica_so_na_primeira_parcela(self):
        self.client.post(
            "/financeiro/lancamentos/novo/",
            {**self._dados(tipo="despesa", categoria="aluguel", classificacao="parcelado",
                           numero_parcelas="2", data_vencimento="2026-01-31", status="pago",
                           data_pagamento="2026-01-31"),
             "comprovante_pagamento": SimpleUploadedFile("c.pdf", b"x", content_type="application/pdf")},
            HTTP_HOST=self.http_host,
        )
        primeira, segunda = LancamentoFinanceiro.objects.order_by("data_vencimento")
        self.assertTrue(primeira.comprovante_pagamento)
        self.assertFalse(segunda.comprovante_pagamento)

    def test_boleto_tambem_fica_so_na_primeira_parcela(self):
        self.client.post(
            "/financeiro/lancamentos/novo/",
            {**self._dados(tipo="despesa", categoria="aluguel", classificacao="parcelado",
                           numero_parcelas="2", data_vencimento="2026-01-31"),
             "anexo": SimpleUploadedFile("boleto.pdf", b"x", content_type="application/pdf")},
            HTTP_HOST=self.http_host,
        )
        primeira, segunda = LancamentoFinanceiro.objects.order_by("data_vencimento")
        self.assertTrue(primeira.anexo)
        self.assertFalse(segunda.anexo)


class TestFontesPorCategoria(LancamentoFormularioBase):
    def _pago(self, **kw):
        return self._lancamento(status="pago", data_pagamento=self.hoje, **kw)

    def _fontes(self, chave, user=None, **params):
        if user:
            self.client.force_login(user)
        r = self.client.get("/financeiro/grafico/", params, HTTP_HOST=self.http_host)
        return {l["rotulo"]: l["valor"] for l in r.context["analise"][chave]["linhas"]}

    def test_soma_por_categoria_com_rotulo_novo(self):
        self._pago(categoria="honorario", valor=Decimal("100"))
        self._pago(categoria="honorario", valor=Decimal("50"))
        self._pago(categoria="consultoria", valor=Decimal("30"))
        self._pago(tipo="despesa", categoria="luz", valor=Decimal("20"))
        self._pago(tipo="despesa", categoria="luz", valor=Decimal("5"))
        self._pago(tipo="despesa", categoria="agua", valor=Decimal("7"))
        self.assertEqual(self._fontes("fontes_receita"), {"Honorários": Decimal("150"), "Consultoria": Decimal("30")})
        self.assertEqual(self._fontes("fontes_despesa"), {"Luz": Decimal("25"), "Água": Decimal("7")})

    def test_pendente_nao_entra_na_fonte(self):
        self._lancamento(categoria="acordo", valor=Decimal("999"))
        self.assertEqual(self._fontes("fontes_receita"), {})

    def test_dados_proprios_so_soma_os_lancamentos_do_usuario(self):
        proprio = self._usuario("fin_proprio", NIVEL_DADOS_PROPRIOS)
        self._pago(categoria="honorario", valor=Decimal("100"), responsavel=proprio)
        self._pago(categoria="honorario", valor=Decimal("900"), responsavel=self.user)
        self._pago(tipo="despesa", categoria="luz", valor=Decimal("10"), responsavel=proprio)
        self._pago(tipo="despesa", categoria="luz", valor=Decimal("90"), responsavel=self.user)
        self.assertEqual(self._fontes("fontes_receita", user=proprio), {"Honorários": Decimal("100")})
        self.assertEqual(self._fontes("fontes_despesa", user=proprio), {"Luz": Decimal("10")})

    def test_dados_todos_soma_os_lancamentos_de_todos(self):
        outro = self._usuario("fin_outro", NIVEL_DADOS_PROPRIOS)
        self._pago(categoria="honorario", valor=Decimal("100"), responsavel=outro)
        self._pago(categoria="honorario", valor=Decimal("900"), responsavel=self.user)
        self.assertEqual(self._fontes("fontes_receita"), {"Honorários": Decimal("1000")})
