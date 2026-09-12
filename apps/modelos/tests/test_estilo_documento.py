"""
Testes do editor visual de "Meu Estilo" (`editar_estilo_documento`):
mesma autorização de `editar_estilo` (modelos_editar_estilo — Camada 2,
sobre MODULO_MODELOS na Camada 1), sanitização do JSON de configuração
enviado pelo editor e validação de extensão/tamanho dos arquivos.

Reaproveita as fixtures de apps/modelos/tests/test_autorizacao.py.
"""

import json
import os

from django.core.files.uploadedfile import SimpleUploadedFile

from apps.accounts.permissoes_constants import HAB_MODELOS_EDITAR_ESTILO, MODULO_MODELOS
from apps.modelos.forms import sanitizar_config_documento
from apps.modelos.models import EstiloEscritorio, config_documento_padrao
from apps.modelos.tests.test_autorizacao import ModelosAutorizacaoBase


class TestEstiloDocumentoSemHabilitacao(ModelosAutorizacaoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi_modelos_estilo_doc_sem_hab"

    def setUp(self):
        super().setUp()
        self.user = self._user("sem_editar_estilo_doc")
        papel = self._new_papel("Papel Sem Editar Estilo Documento")
        self._assign_papel(self.user, papel)
        self._pp(papel, MODULO_MODELOS)
        self.client.force_login(self.user)

    def test_get_negado(self):
        r = self.client.get("/modelos/estilo/documento/editar/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_post_negado(self):
        r = self.client.post(
            "/modelos/estilo/documento/editar/",
            {"modo_estilo": "construir", "config_documento": "{}"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 403)
        self.assertFalse(EstiloEscritorio.objects.exists())


class TestEstiloDocumentoComHabilitacao(ModelosAutorizacaoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi_modelos_estilo_doc_ok"

    def setUp(self):
        super().setUp()
        self.user = self._user("com_editar_estilo_doc")
        papel = self._new_papel("Papel Editar Estilo Documento")
        self._assign_papel(self.user, papel)
        self._pp(papel, MODULO_MODELOS)
        self._hp(papel, MODULO_MODELOS, HAB_MODELOS_EDITAR_ESTILO)
        self.client.force_login(self.user)

    def test_get_redireciona_para_aba(self):
        r = self.client.get("/modelos/estilo/documento/editar/", HTTP_HOST=self.http_host)
        self.assertRedirects(r, "/modelos/?aba=estilo", fetch_redirect_response=False)

    def test_post_salva_config_sanitizada(self):
        config = config_documento_padrao()
        config["geral"]["cor_folha"] = "#f4f4f4"
        config["slots"]["cabecalho"]["texto"] = "Meu Escritório Advocacia"
        config["secoes"]["numero_processo"]["distancia_linhas"] = 5

        r = self.client.post(
            "/modelos/estilo/documento/editar/",
            {"modo_estilo": "construir", "config_documento": json.dumps(config)},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)

        estilo = EstiloEscritorio.objects.get(pk=1)
        self.assertEqual(estilo.modo_estilo, "construir")
        self.assertEqual(estilo.config_documento["geral"]["cor_folha"], "#f4f4f4")
        self.assertEqual(estilo.config_documento["slots"]["cabecalho"]["texto"], "Meu Escritório Advocacia")
        self.assertEqual(estilo.config_documento["secoes"]["numero_processo"]["distancia_linhas"], 5)

    def test_post_config_invalida_cai_no_padrao(self):
        payload_malicioso = {
            "geral": {"cor_folha": "javascript:alert(1)", "fonte": "Comic Sans MS"},
            "secoes": {"jurisprudencia": {"cor": "not-a-color", "tamanho": 999}},
        }
        r = self.client.post(
            "/modelos/estilo/documento/editar/",
            {"modo_estilo": "construir", "config_documento": json.dumps(payload_malicioso)},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)

        estilo = EstiloEscritorio.objects.get(pk=1)
        padrao = config_documento_padrao()
        self.assertEqual(estilo.config_documento["geral"]["cor_folha"], padrao["geral"]["cor_folha"])
        self.assertEqual(estilo.config_documento["geral"]["fonte"], padrao["geral"]["fonte"])
        self.assertEqual(estilo.config_documento["secoes"]["jurisprudencia"]["cor"], padrao["secoes"]["jurisprudencia"]["cor"])
        self.assertEqual(estilo.config_documento["secoes"]["jurisprudencia"]["tamanho"], 72)  # clamp no teto

    def test_post_config_ausente_usa_padrao(self):
        r = self.client.post(
            "/modelos/estilo/documento/editar/",
            {"modo_estilo": "construir"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        estilo = EstiloEscritorio.objects.get(pk=1)
        self.assertEqual(estilo.config_documento, config_documento_padrao())

    def test_post_modo_anexar_com_arquivo_valido(self):
        arquivo = SimpleUploadedFile("peca.docx", b"conteudo fake", content_type="application/octet-stream")
        r = self.client.post(
            "/modelos/estilo/documento/editar/",
            {"modo_estilo": "anexar", "config_documento": "{}", "arquivo_referencia": arquivo},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        estilo = EstiloEscritorio.objects.get(pk=1)
        self.assertEqual(estilo.modo_estilo, "anexar")
        self.assertTrue(estilo.arquivo_referencia.name.endswith("peca.docx"))
        estilo.arquivo_referencia.delete(save=False)

    def test_post_arquivo_extensao_invalida_rejeitado(self):
        arquivo = SimpleUploadedFile("peca.exe", b"conteudo fake", content_type="application/octet-stream")
        r = self.client.post(
            "/modelos/estilo/documento/editar/",
            {"modo_estilo": "anexar", "config_documento": "{}", "arquivo_referencia": arquivo},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 200)  # form invalido -> re-renderiza a aba
        estilo = EstiloEscritorio.objects.get(pk=1)
        self.assertFalse(estilo.arquivo_referencia)

    def test_post_imagem_slot_extensao_invalida_rejeitada(self):
        arquivo = SimpleUploadedFile("logo.exe", b"conteudo fake", content_type="application/octet-stream")
        r = self.client.post(
            "/modelos/estilo/documento/editar/",
            {"modo_estilo": "construir", "config_documento": "{}", "imagem_cabecalho": arquivo},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 200)
        estilo = EstiloEscritorio.objects.get(pk=1)
        self.assertFalse(estilo.imagem_cabecalho)

    def test_substituir_imagem_remove_arquivo_anterior_do_storage(self):
        primeira = SimpleUploadedFile("logo1.png", b"a", content_type="image/png")
        self.client.post(
            "/modelos/estilo/documento/editar/",
            {"modo_estilo": "construir", "config_documento": "{}", "imagem_cabecalho": primeira},
            HTTP_HOST=self.http_host,
        )
        estilo = EstiloEscritorio.objects.get(pk=1)
        caminho_antigo = estilo.imagem_cabecalho.path
        self.assertTrue(os.path.exists(caminho_antigo))

        segunda = SimpleUploadedFile("logo2.png", b"b", content_type="image/png")
        self.client.post(
            "/modelos/estilo/documento/editar/",
            {"modo_estilo": "construir", "config_documento": "{}", "imagem_cabecalho": segunda},
            HTTP_HOST=self.http_host,
        )
        estilo.refresh_from_db()
        self.assertFalse(os.path.exists(caminho_antigo))
        self.assertTrue(os.path.exists(estilo.imagem_cabecalho.path))
        estilo.imagem_cabecalho.delete(save=False)


class TestSanitizarConfigDocumento(ModelosAutorizacaoBase):
    """Testes unitários da função pura de sanitização (sem HTTP)."""

    @classmethod
    def get_test_schema_name(cls):
        return "wi_modelos_estilo_sanitizar"

    def test_entrada_nao_dict_retorna_padrao(self):
        self.assertEqual(sanitizar_config_documento("string qualquer"), config_documento_padrao())
        self.assertEqual(sanitizar_config_documento(None), config_documento_padrao())
        self.assertEqual(sanitizar_config_documento([1, 2, 3]), config_documento_padrao())

    def test_chave_desconhecida_e_descartada(self):
        resultado = sanitizar_config_documento({"geral": {"campo_inventado": "x"}, "campo_de_fora": 1})
        self.assertNotIn("campo_de_fora", resultado)
        self.assertNotIn("campo_inventado", resultado["geral"])

    def test_marca_texto_aceita_transparent_e_hex(self):
        resultado = sanitizar_config_documento({"secoes": {"jurisprudencia": {"marca_texto": "transparent"}}})
        self.assertEqual(resultado["secoes"]["jurisprudencia"]["marca_texto"], "transparent")

        resultado2 = sanitizar_config_documento({"secoes": {"jurisprudencia": {"marca_texto": "#abc123"}}})
        self.assertEqual(resultado2["secoes"]["jurisprudencia"]["marca_texto"], "#abc123")

    def test_distancia_linhas_negativa_e_clampada_para_zero(self):
        resultado = sanitizar_config_documento({"secoes": {"numero_processo": {"distancia_linhas": -5}}})
        self.assertEqual(resultado["secoes"]["numero_processo"]["distancia_linhas"], 0)
