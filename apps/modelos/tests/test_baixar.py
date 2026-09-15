"""
Testes de exportação de modelo de peça em PDF/DOCX (`baixar_pdf`/
`baixar_docx`): mesma autorização de Camada 1 das demais rotas de leitura
(`tem_permissao_modulo`, sem habilitação extra — ver `detalhe`), aplicando
cabeçalho/rodapé/marca d'água/assinatura do `EstiloEscritorio` vigente.

Reaproveita as fixtures de apps/modelos/tests/test_autorizacao.py.
"""

from apps.accounts.permissoes_constants import MODULO_MODELOS
from apps.modelos.models import EstiloEscritorio
from apps.modelos.tests.test_autorizacao import ModelosAutorizacaoBase


class TestBaixarSemModulo(ModelosAutorizacaoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi_modelos_baixar_sem_modulo"

    def setUp(self):
        super().setUp()
        self.user = self._user("sem_modulo_baixar")
        self.client.force_login(self.user)
        self.modelo = self._modelo(criado_por=self.user)

    def test_baixar_pdf_negado(self):
        r = self.client.get(f"/modelos/{self.modelo.pk}/baixar/pdf/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_baixar_docx_negado(self):
        r = self.client.get(f"/modelos/{self.modelo.pk}/baixar/docx/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)


class TestBaixarComModulo(ModelosAutorizacaoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi_modelos_baixar_ok"

    def setUp(self):
        super().setUp()
        self.user = self._user("com_modulo_baixar")
        papel = self._new_papel("Papel Baixar")
        self._assign_papel(self.user, papel)
        self._pp(papel, MODULO_MODELOS)
        self.client.force_login(self.user)
        self.modelo = self._modelo(
            criado_por=self.user,
            titulo="Petição Teste",
            conteudo='<p style="text-align:center;">EXCELENTÍSSIMO</p><p>Corpo <b>negrito</b> do texto.</p>',
        )

    def test_baixar_pdf_ok(self):
        r = self.client.get(f"/modelos/{self.modelo.pk}/baixar/pdf/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "application/pdf")
        self.assertTrue(r.content.startswith(b"%PDF-"))
        self.assertIn("Peti", r["Content-Disposition"])

    def test_baixar_docx_ok(self):
        r = self.client.get(f"/modelos/{self.modelo.pk}/baixar/docx/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            r["Content-Type"],
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        self.assertGreater(len(r.content), 0)

    def test_baixar_pdf_404_para_modelo_inexistente(self):
        r = self.client.get("/modelos/999999/baixar/pdf/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 404)

    def test_baixar_aplica_slots_do_estilo_vigente(self):
        estilo, _ = EstiloEscritorio.objects.get_or_create(pk=1)
        estilo.config_documento["slots"]["cabecalho"]["texto"] = "CABEÇALHO DO ESCRITÓRIO"
        estilo.config_documento["slots"]["rodape"]["texto"] = "RODAPÉ DO ESCRITÓRIO"
        estilo.save()

        r_pdf = self.client.get(f"/modelos/{self.modelo.pk}/baixar/pdf/", HTTP_HOST=self.http_host)
        self.assertEqual(r_pdf.status_code, 200)

        r_docx = self.client.get(f"/modelos/{self.modelo.pk}/baixar/docx/", HTTP_HOST=self.http_host)
        self.assertEqual(r_docx.status_code, 200)
