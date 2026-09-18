"""
Testes de specs/modelos-estilo-simplificacao-imagens.md: remoção de
tom de voz/instruções gerais, tamanho/posição de imagem nos slots de
Meu Estilo, múltiplas assinaturas (texto ou imagem), réplica de
cabeçalho/rodapé por página (padrão do escritório + override por
modelo) e imagem inserida no conteúdo da peça (parser/exportação).

Reaproveita as fixtures de apps/modelos/tests/test_autorizacao.py.
"""

import base64
import json

from django.core.files.uploadedfile import SimpleUploadedFile

from apps.accounts.permissoes_constants import HAB_MODELOS_EDITAR_ESTILO, MODULO_MODELOS
from apps.modelos.forms import sanitizar_config_documento
from apps.modelos.models import AssinaturaEstilo, EstiloEscritorio, ModeloPeca, config_documento_padrao
from apps.modelos.services import extrair_paragrafos, gerar_docx_modelo, gerar_pdf_modelo
from apps.modelos.tests.test_autorizacao import ModelosAutorizacaoBase

_PIXEL_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)
_DATA_URL_PNG = "data:image/png;base64," + _PIXEL_PNG_BASE64


class TestTomDeVozRemovido(ModelosAutorizacaoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "estilo_simpl_tom_voz_removido"

    def test_estilo_escritorio_nao_tem_mais_esses_campos(self):
        self.assertFalse(hasattr(EstiloEscritorio(), "tom_voz"))
        self.assertFalse(hasattr(EstiloEscritorio(), "instrucoes_gerais"))

    def test_tela_de_estilo_nao_mostra_esses_campos(self):
        user = self._user("sem_tom_voz")
        papel = self._new_papel("Papel Sem Tom De Voz")
        self._assign_papel(user, papel)
        self._pp(papel, MODULO_MODELOS)
        self._hp(papel, MODULO_MODELOS, HAB_MODELOS_EDITAR_ESTILO)
        self.client.force_login(user)
        r = self.client.get("/modelos/?aba=estilo", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, "Tom de voz")
        self.assertNotContains(r, "Instruções gerais")


class TestSanitizarSlotsImagemEReplicacao(ModelosAutorizacaoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "estilo_simpl_sanitizar_slots"

    def test_largura_fora_do_intervalo_e_clampada(self):
        resultado = sanitizar_config_documento({"slots": {"cabecalho": {"largura": 500}}})
        self.assertEqual(resultado["slots"]["cabecalho"]["largura"], 100)
        resultado2 = sanitizar_config_documento({"slots": {"cabecalho": {"largura": 1}}})
        self.assertEqual(resultado2["slots"]["cabecalho"]["largura"], 10)

    def test_alinhamento_invalido_cai_no_padrao(self):
        resultado = sanitizar_config_documento({"slots": {"rodape": {"alinhamento": "diagonal"}}})
        self.assertEqual(resultado["slots"]["rodape"]["alinhamento"], "center")

    def test_alinhamento_valido_e_aceito(self):
        resultado = sanitizar_config_documento({"slots": {"rodape": {"alinhamento": "left"}}})
        self.assertEqual(resultado["slots"]["rodape"]["alinhamento"], "left")

    def test_replicacao_valida_e_aceita_em_cabecalho_e_rodape(self):
        resultado = sanitizar_config_documento({
            "slots": {"cabecalho": {"replicacao": "primeira"}, "rodape": {"replicacao": "ultima"}},
        })
        self.assertEqual(resultado["slots"]["cabecalho"]["replicacao"], "primeira")
        self.assertEqual(resultado["slots"]["rodape"]["replicacao"], "ultima")

    def test_replicacao_invalida_cai_no_padrao_todas(self):
        resultado = sanitizar_config_documento({"slots": {"cabecalho": {"replicacao": "so_as_pares"}}})
        self.assertEqual(resultado["slots"]["cabecalho"]["replicacao"], "todas")

    def test_marca_dagua_nao_tem_replicacao(self):
        padrao = config_documento_padrao()
        self.assertNotIn("replicacao", padrao["slots"]["marca_dagua"])
        resultado = sanitizar_config_documento({"slots": {"marca_dagua": {"replicacao": "primeira"}}})
        self.assertNotIn("replicacao", resultado["slots"]["marca_dagua"])

    def test_assinatura_nao_e_mais_um_slot(self):
        padrao = config_documento_padrao()
        self.assertNotIn("assinatura", padrao["slots"])


class TestGerenciarAssinaturasDoEstilo(ModelosAutorizacaoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "estilo_simpl_assinaturas"

    def setUp(self):
        super().setUp()
        self.user = self._user("gerencia_assinaturas")
        papel = self._new_papel("Papel Gerencia Assinaturas")
        self._assign_papel(self.user, papel)
        self._pp(papel, MODULO_MODELOS)
        self._hp(papel, MODULO_MODELOS, HAB_MODELOS_EDITAR_ESTILO)
        self.client.force_login(self.user)

    def test_adiciona_assinatura_de_texto(self):
        r = self.client.post(
            "/modelos/estilo/assinaturas/adicionar/",
            {"modo": "texto", "texto": "Fulano — OAB/SP 123.456", "largura": 30, "alinhamento": "center"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        estilo = EstiloEscritorio.objects.get(pk=1)
        self.assertEqual(estilo.assinaturas.count(), 1)
        self.assertEqual(estilo.assinaturas.first().texto, "Fulano — OAB/SP 123.456")

    def test_adiciona_assinatura_de_imagem(self):
        arquivo = SimpleUploadedFile("assinatura.png", b"conteudo-fake", content_type="image/png")
        r = self.client.post(
            "/modelos/estilo/assinaturas/adicionar/",
            {"modo": "imagem", "imagem": arquivo, "largura": 25, "alinhamento": "left"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        estilo = EstiloEscritorio.objects.get(pk=1)
        assinatura = estilo.assinaturas.first()
        self.assertEqual(assinatura.modo, "imagem")
        self.assertTrue(assinatura.imagem)

    def test_texto_vazio_em_modo_texto_e_rejeitado(self):
        r = self.client.post(
            "/modelos/estilo/assinaturas/adicionar/",
            {"modo": "texto", "texto": "", "largura": 30, "alinhamento": "center"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        estilo = EstiloEscritorio.objects.get(pk=1)
        self.assertEqual(estilo.assinaturas.count(), 0)

    def test_permite_mais_de_uma_assinatura(self):
        self.client.post(
            "/modelos/estilo/assinaturas/adicionar/",
            {"modo": "texto", "texto": "Sócio A", "largura": 30, "alinhamento": "center"},
            HTTP_HOST=self.http_host,
        )
        self.client.post(
            "/modelos/estilo/assinaturas/adicionar/",
            {"modo": "texto", "texto": "Sócio B", "largura": 30, "alinhamento": "center"},
            HTTP_HOST=self.http_host,
        )
        estilo = EstiloEscritorio.objects.get(pk=1)
        self.assertEqual(estilo.assinaturas.count(), 2)
        textos = set(estilo.assinaturas.values_list("texto", flat=True))
        self.assertEqual(textos, {"Sócio A", "Sócio B"})

    def test_remove_assinatura(self):
        estilo = EstiloEscritorio.objects.create(pk=1)
        assinatura = AssinaturaEstilo.objects.create(estilo=estilo, modo="texto", texto="Fulano")
        r = self.client.post(
            f"/modelos/estilo/assinaturas/{assinatura.pk}/remover/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 302)
        self.assertFalse(AssinaturaEstilo.objects.filter(pk=assinatura.pk).exists())

    def test_sem_habilitacao_e_negado(self):
        outro = self._user("sem_hab_assinatura")
        papel = self._new_papel("Papel Sem Hab Assinatura")
        self._assign_papel(outro, papel)
        self._pp(papel, MODULO_MODELOS)
        self.client.force_login(outro)
        r = self.client.post(
            "/modelos/estilo/assinaturas/adicionar/",
            {"modo": "texto", "texto": "Intruso", "largura": 30, "alinhamento": "center"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 403)


class TestReplicacaoPorPeca(ModelosAutorizacaoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "estilo_simpl_replicacao_peca"

    def setUp(self):
        super().setUp()
        self.user = self._user("cria_modelo_replicacao")
        papel = self._new_papel("Papel Cria Modelo Replicacao")
        self._assign_papel(self.user, papel)
        self._pp(papel, MODULO_MODELOS)
        from apps.accounts.permissoes_constants import HAB_MODELOS_CRIAR
        self._hp(papel, MODULO_MODELOS, HAB_MODELOS_CRIAR)
        self.client.force_login(self.user)
        self.categoria = self._categoria()

    def test_novo_modelo_herda_padrao_do_escritorio_no_get(self):
        estilo = EstiloEscritorio.objects.create(pk=1)
        estilo.config_documento["slots"]["cabecalho"]["replicacao"] = "primeira"
        estilo.save(update_fields=["config_documento"])

        r = self.client.get("/modelos/novo/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["form"].initial["cabecalho_replicacao"], "primeira")

    def test_modelo_criado_grava_a_propria_escolha(self):
        r = self.client.post(
            "/modelos/novo/",
            {
                "titulo": "Petição com réplica customizada",
                "categoria": self.categoria.pk,
                "area_direito": "CÍVEL",
                "conteudo": "<p>Texto.</p>",
                "cabecalho_replicacao": "primeira",
                "rodape_replicacao": "ultima",
            },
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        modelo = ModeloPeca.objects.get(titulo="Petição com réplica customizada")
        self.assertEqual(modelo.cabecalho_replicacao, "primeira")
        self.assertEqual(modelo.rodape_replicacao, "ultima")

    def test_post_sem_essas_chaves_usa_padrao_todas(self):
        r = self.client.post(
            "/modelos/novo/",
            {
                "titulo": "Petição sem réplica explícita",
                "categoria": self.categoria.pk,
                "area_direito": "CÍVEL",
                "conteudo": "<p>Texto.</p>",
            },
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        modelo = ModeloPeca.objects.get(titulo="Petição sem réplica explícita")
        self.assertEqual(modelo.cabecalho_replicacao, "todas")
        self.assertEqual(modelo.rodape_replicacao, "todas")

    def test_alterar_estilo_depois_nao_muda_modelo_ja_criado(self):
        self.client.post(
            "/modelos/novo/",
            {
                "titulo": "Petição fixa",
                "categoria": self.categoria.pk,
                "area_direito": "CÍVEL",
                "conteudo": "<p>Texto.</p>",
                "cabecalho_replicacao": "primeira",
            },
            HTTP_HOST=self.http_host,
        )
        estilo = EstiloEscritorio.objects.get(pk=1)
        estilo.config_documento["slots"]["cabecalho"]["replicacao"] = "ultima"
        estilo.save(update_fields=["config_documento"])

        modelo = ModeloPeca.objects.get(titulo="Petição fixa")
        self.assertEqual(modelo.cabecalho_replicacao, "primeira")


class TestExtrairParagrafosComImagem(ModelosAutorizacaoBase):
    """Parser de conteúdo reconhece <img> inserido pelo editor
    (_nova_peca_editor_js.html) como parágrafo próprio, não como texto."""

    @classmethod
    def get_test_schema_name(cls):
        return "estilo_simpl_parser_imagem"

    def test_imagem_vira_paragrafo_proprio(self):
        html = (
            '<p>Antes</p>'
            '<div style="text-align:right"><img src="' + _DATA_URL_PNG + '" style="width:40%;"></div>'
            '<p>Depois</p>'
        )
        paragrafos = extrair_paragrafos(html)
        tipos = [p.get("tipo") for p in paragrafos]
        self.assertIn("imagem", tipos)
        imagem = next(p for p in paragrafos if p.get("tipo") == "imagem")
        self.assertEqual(imagem["largura"], 40)
        self.assertEqual(imagem["alinhamento"], "right")
        self.assertEqual(imagem["src"], _DATA_URL_PNG)

    def test_imagem_sem_largura_usa_padrao(self):
        html = '<div><img src="' + _DATA_URL_PNG + '"></div>'
        paragrafos = extrair_paragrafos(html)
        imagem = next(p for p in paragrafos if p.get("tipo") == "imagem")
        self.assertEqual(imagem["largura"], 50)

    def test_src_que_nao_e_data_url_e_ignorado(self):
        html = '<p>Texto</p><div><img src="https://exemplo.com/x.png"></div>'
        paragrafos = extrair_paragrafos(html)
        self.assertFalse(any(p.get("tipo") == "imagem" for p in paragrafos))


class TestExportacaoComEstiloCompleto(ModelosAutorizacaoBase):
    """Gera PDF/DOCX de verdade com imagens de slot, múltiplas assinaturas,
    réplica primeira/última e imagem no conteúdo — só garante que a
    geração roda sem erro para cada combinação (não reabre o binário)."""

    @classmethod
    def get_test_schema_name(cls):
        return "estilo_simpl_exportacao"

    def setUp(self):
        super().setUp()
        self.categoria = self._categoria()
        self.estilo = EstiloEscritorio.objects.create(pk=1)
        self.estilo.imagem_cabecalho = SimpleUploadedFile(
            "cab.png", base64.b64decode(_PIXEL_PNG_BASE64), content_type="image/png",
        )
        self.estilo.config_documento["slots"]["cabecalho"]["modo"] = "imagem"
        self.estilo.config_documento["slots"]["cabecalho"]["replicacao"] = "primeira"
        self.estilo.config_documento["slots"]["rodape"]["replicacao"] = "ultima"
        self.estilo.save()
        AssinaturaEstilo.objects.create(estilo=self.estilo, modo="texto", texto="Sócio A", ordem=0)
        AssinaturaEstilo.objects.create(estilo=self.estilo, modo="texto", texto="Sócio B", ordem=1)

    def _modelo(self, conteudo="<p>Corpo da peça.</p>"):
        return ModeloPeca.objects.create(
            titulo="Modelo Exportação", categoria=self.categoria, area_direito="CÍVEL", conteudo=conteudo,
        )

    def test_gera_pdf_sem_erro_com_replicacao_primeira_e_ultima(self):
        buffer = gerar_pdf_modelo(self._modelo(), self.estilo)
        conteudo = buffer.read()
        self.assertTrue(conteudo.startswith(b"%PDF"))

    def test_gera_docx_sem_erro_com_replicacao_primeira_e_ultima(self):
        buffer = gerar_docx_modelo(self._modelo(), self.estilo)
        self.assertGreater(len(buffer.read()), 0)

    def test_gera_pdf_com_imagem_no_conteudo(self):
        conteudo = '<p>Antes</p><div style="text-align:center"><img src="' + _DATA_URL_PNG + '" style="width:40%;"></div><p>Depois</p>'
        buffer = gerar_pdf_modelo(self._modelo(conteudo), self.estilo)
        self.assertTrue(buffer.read().startswith(b"%PDF"))

    def test_gera_docx_com_imagem_no_conteudo(self):
        conteudo = '<p>Antes</p><div style="text-align:center"><img src="' + _DATA_URL_PNG + '" style="width:40%;"></div><p>Depois</p>'
        buffer = gerar_docx_modelo(self._modelo(conteudo), self.estilo)
        self.assertGreater(len(buffer.read()), 0)

    def test_gera_pdf_sem_nenhuma_assinatura(self):
        self.estilo.assinaturas.all().delete()
        buffer = gerar_pdf_modelo(self._modelo(), self.estilo)
        self.assertTrue(buffer.read().startswith(b"%PDF"))
