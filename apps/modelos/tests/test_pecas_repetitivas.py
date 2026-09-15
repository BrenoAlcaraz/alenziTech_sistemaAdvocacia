"""
Testes do fluxo de peças repetitivas Fase 1 (sem IA — Fase 2 depende do
PDR-0008): usuário escolhe uma peça base (do acervo ou anexando um
arquivo novo) e gera N peças, uma por caso, cada uma com o Cliente
selecionado (nome/CPF-CNPJ) já preenchido e valor/endereço do caso/
particularidades vindos de um editor manual.

Reaproveita as fixtures de apps/modelos/tests/test_autorizacao.py.
"""

from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile

from apps.accounts.permissoes_constants import HAB_MODELOS_CRIAR, MODULO_MODELOS
from apps.clientes.models import Cliente
from apps.modelos.models import ModeloPeca
from apps.modelos.tests.test_autorizacao import ModelosAutorizacaoBase


def _management_form(prefix, total):
    return {
        f"{prefix}-TOTAL_FORMS": str(total),
        f"{prefix}-INITIAL_FORMS": "0",
        f"{prefix}-MIN_NUM_FORMS": "0",
        f"{prefix}-MAX_NUM_FORMS": "1000",
    }


class RepetitivasBase(ModelosAutorizacaoBase):
    def setUp(self):
        super().setUp()
        self.user = self._user("gera_repetitivas")
        papel = self._new_papel("Papel Gera Repetitivas")
        self._assign_papel(self.user, papel)
        self._pp(papel, MODULO_MODELOS)
        self._hp(papel, MODULO_MODELOS, HAB_MODELOS_CRIAR)
        self.client.force_login(self.user)
        self.peca_base = self._modelo(
            criado_por=self.user,
            titulo="Petição Inicial — Ação de Cobrança",
            conteudo="<p>Corpo original da peça base.</p>",
        )

    def _cliente(self, **kwargs):
        defaults = {
            "nome_razao_social": "Fulano de Tal",
            "cpf_cnpj": "123.456.789-00",
            "tipo": "PF",
            "responsavel": self.user,
        }
        defaults.update(kwargs)
        return Cliente.objects.create(**defaults)


class TestRepetitivasAutorizacao(ModelosAutorizacaoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi_modelos_rep_autorizacao"

    def setUp(self):
        super().setUp()
        self.user = self._user("sem_criar_repetitivas")
        papel = self._new_papel("Papel Sem Criar Repetitivas")
        self._assign_papel(self.user, papel)
        self._pp(papel, MODULO_MODELOS)
        # Sem modelos_criar.
        self.client.force_login(self.user)

    def test_aba_repetitivas_nao_expoe_formularios_sem_habilitacao(self):
        r = self.client.get("/modelos/?aba=repetitivas", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        self.assertIsNone(r.context["peca_base_form"])
        self.assertFalse(r.context["pode_criar_modelo"])

    def test_gerar_negado_sem_habilitacao(self):
        r = self.client.post(
            "/modelos/repetitivas/gerar/",
            {"modo_base": "acervo"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 403)


class TestRepetitivasFluxoAcervo(RepetitivasBase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi_modelos_rep_acervo"

    def test_aba_repetitivas_expoe_formularios(self):
        r = self.client.get("/modelos/?aba=repetitivas", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        self.assertIsNotNone(r.context["peca_base_form"])
        self.assertIsNotNone(r.context["formset_casos"])

    def test_gera_peca_para_caso_com_cliente_selecionado(self):
        cliente = self._cliente()
        payload = {
            "modo_base": "acervo",
            "peca_base": self.peca_base.pk,
            **_management_form("casos", 1),
            "casos-0-cliente": cliente.pk,
            "casos-0-valor": "R$ 5.000,00",
            "casos-0-endereco_caso": "Rua Exemplo, 123",
            "casos-0-particularidades": "Caso com particularidade X",
        }
        r = self.client.post("/modelos/repetitivas/gerar/", payload, HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 302)

        gerada = ModeloPeca.objects.exclude(pk=self.peca_base.pk).get()
        self.assertIn(cliente.nome_razao_social, gerada.titulo)
        self.assertIn(cliente.nome_razao_social, gerada.conteudo)
        self.assertIn(cliente.cpf_cnpj, gerada.conteudo)
        self.assertIn("R$ 5.000,00", gerada.conteudo)
        self.assertIn("Rua Exemplo, 123", gerada.conteudo)
        self.assertIn("Caso com particularidade X", gerada.conteudo)
        self.assertIn("Corpo original da peça base.", gerada.conteudo)
        self.assertEqual(gerada.categoria_id, self.peca_base.categoria_id)
        self.assertEqual(gerada.area_direito, self.peca_base.area_direito)
        self.assertEqual(gerada.criado_por, self.user)
        # A peça base não é alterada pela geração.
        self.peca_base.refresh_from_db()
        self.assertEqual(self.peca_base.conteudo, "<p>Corpo original da peça base.</p>")

    def test_gera_multiplas_pecas_uma_por_caso(self):
        cliente_a = self._cliente(nome_razao_social="Cliente A")
        cliente_b = self._cliente(nome_razao_social="Cliente B")
        payload = {
            "modo_base": "acervo",
            "peca_base": self.peca_base.pk,
            **_management_form("casos", 2),
            "casos-0-cliente": cliente_a.pk,
            "casos-1-cliente": cliente_b.pk,
        }
        r = self.client.post("/modelos/repetitivas/gerar/", payload, HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 302)

        geradas = ModeloPeca.objects.exclude(pk=self.peca_base.pk)
        self.assertEqual(geradas.count(), 2)
        self.assertTrue(geradas.filter(titulo__contains="Cliente A").exists())
        self.assertTrue(geradas.filter(titulo__contains="Cliente B").exists())

    def test_caso_sem_cliente_usa_campos_manuais_e_titulo_generico(self):
        payload = {
            "modo_base": "acervo",
            "peca_base": self.peca_base.pk,
            **_management_form("casos", 1),
            "casos-0-valor": "R$ 1.000,00",
        }
        r = self.client.post("/modelos/repetitivas/gerar/", payload, HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 302)

        gerada = ModeloPeca.objects.exclude(pk=self.peca_base.pk).get()
        self.assertIn("Caso 1", gerada.titulo)
        self.assertIn("R$ 1.000,00", gerada.conteudo)

    def test_sem_nenhum_caso_preenchido_nao_gera_nada(self):
        payload = {
            "modo_base": "acervo",
            "peca_base": self.peca_base.pk,
            **_management_form("casos", 1),
        }
        r = self.client.post("/modelos/repetitivas/gerar/", payload, HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(ModeloPeca.objects.exclude(pk=self.peca_base.pk).exists())
        self.assertTrue(r.context["peca_base_form"].errors)

    def test_sem_peca_base_selecionada_reporta_erro(self):
        payload = {
            "modo_base": "acervo",
            **_management_form("casos", 1),
            "casos-0-valor": "R$ 1.000,00",
        }
        r = self.client.post("/modelos/repetitivas/gerar/", payload, HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(ModeloPeca.objects.exclude(pk=self.peca_base.pk).exists())
        self.assertIn("peca_base", r.context["peca_base_form"].errors)

    def test_pagina_mostra_pecas_recem_geradas(self):
        cliente = self._cliente()
        payload = {
            "modo_base": "acervo",
            "peca_base": self.peca_base.pk,
            **_management_form("casos", 1),
            "casos-0-cliente": cliente.pk,
        }
        r = self.client.post(
            "/modelos/repetitivas/gerar/", payload, HTTP_HOST=self.http_host, follow=True
        )
        gerada = ModeloPeca.objects.exclude(pk=self.peca_base.pk).get()
        self.assertContains(r, gerada.titulo)
        self.assertEqual(list(r.context["pecas_geradas"]), [gerada])


class TestRepetitivasFluxoAnexar(RepetitivasBase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi_modelos_rep_anexar"

    def test_gera_peca_a_partir_de_arquivo_anexado(self):
        arquivo = SimpleUploadedFile(
            "peca-base.docx",
            b"conteudo fake",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        payload = {
            "modo_base": "anexar",
            "categoria": self._categoria().pk,
            "area_direito": "civil",
            **_management_form("casos", 1),
            "casos-0-valor": "R$ 2.000,00",
        }
        with mock.patch("apps.modelos.views.extrair_texto_documento", return_value="Texto extraído do anexo."):
            r = self.client.post(
                "/modelos/repetitivas/gerar/",
                {**payload, "arquivo_base": arquivo},
                HTTP_HOST=self.http_host,
            )
        self.assertEqual(r.status_code, 302)
        gerada = ModeloPeca.objects.exclude(pk=self.peca_base.pk).get()
        self.assertIn("Texto extraído do anexo.", gerada.conteudo)
        self.assertIn("R$ 2.000,00", gerada.conteudo)
        self.assertEqual(gerada.area_direito, "civil")

    def test_sem_arquivo_nem_tipo_de_peca_reporta_erros(self):
        payload = {
            "modo_base": "anexar",
            **_management_form("casos", 1),
            "casos-0-valor": "R$ 2.000,00",
        }
        r = self.client.post("/modelos/repetitivas/gerar/", payload, HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        erros = r.context["peca_base_form"].errors
        self.assertIn("arquivo_base", erros)
        self.assertIn("categoria", erros)
        self.assertIn("area_direito", erros)
