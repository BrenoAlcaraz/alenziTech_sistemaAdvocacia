"""`resposta_de_arquivo`: pré-visualização por padrão, download com
`?baixar=1`, e tipos que não são seguros para abrir no navegador sempre
baixados."""

from django.core.files.base import ContentFile
from django.test import RequestFactory, SimpleTestCase

from apps.saas_tenants.storage import resposta_de_arquivo


class _Campo:
    """Duplo mínimo de FieldFile: nome + open()."""

    def __init__(self, nome, conteudo=b"x"):
        self.name = f"tenants/t/protegido/{nome}"
        self._conteudo = conteudo

    def open(self, modo):
        return ContentFile(self._conteudo).open(modo)

    def __bool__(self):
        return True


class TestRespostaDeArquivo(SimpleTestCase):
    def _resposta(self, nome, query=""):
        request = RequestFactory().get(f"/x/{query}")
        return resposta_de_arquivo(request, _Campo(nome))

    def test_pdf_abre_no_navegador_por_padrao(self):
        r = self._resposta("a.pdf")
        self.assertTrue(r["Content-Disposition"].startswith("inline"))

    def test_baixar_forca_download(self):
        r = self._resposta("a.pdf", "?baixar=1")
        self.assertTrue(r["Content-Disposition"].startswith("attachment"))

    def test_imagem_abre_por_padrao(self):
        self.assertTrue(self._resposta("a.png")["Content-Disposition"].startswith("inline"))

    def test_html_e_svg_sempre_baixam(self):
        for nome in ("a.html", "a.svg", "a.docx", "a.exe"):
            with self.subTest(nome=nome):
                self.assertTrue(self._resposta(nome)["Content-Disposition"].startswith("attachment"))

    def test_nosniff(self):
        self.assertEqual(self._resposta("a.pdf")["X-Content-Type-Options"], "nosniff")
