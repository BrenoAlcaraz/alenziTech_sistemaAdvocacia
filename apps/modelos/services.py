from io import BytesIO
from html.parser import HTMLParser
from pathlib import Path
from xml.sax.saxutils import escape as escapar_xml

from django.utils.html import escape as escapar_html


class ErroImportacaoDocumento(Exception):
    pass


def extrair_texto_documento(arquivo):
    """Extrai texto de um arquivo PDF ou DOCX e devolve string limpa."""
    nome = getattr(arquivo, "name", "") or ""
    extensao = Path(nome).suffix.lower()

    if extensao == ".pdf":
        return _extrair_pdf(arquivo)
    elif extensao == ".docx":
        return _extrair_docx(arquivo)
    else:
        raise ErroImportacaoDocumento("Envie um arquivo PDF ou DOCX.")


def _extrair_pdf(arquivo):
    try:
        from pypdf import PdfReader
        from pypdf.errors import PdfReadError
    except ImportError:
        raise ErroImportacaoDocumento("Biblioteca de leitura de PDF não disponível.")

    try:
        leitor = PdfReader(arquivo)
    except Exception:
        raise ErroImportacaoDocumento(
            "Não foi possível abrir o PDF. O arquivo pode estar corrompido ou protegido."
        )

    if leitor.is_encrypted:
        raise ErroImportacaoDocumento(
            "O PDF está protegido por senha e não pode ser importado."
        )

    textos = []
    for pagina in leitor.pages:
        try:
            texto = pagina.extract_text() or ""
        except Exception:
            texto = ""
        if texto.strip():
            textos.append(texto.strip())

    conteudo = "\n\n".join(textos).strip()

    if not conteudo:
        raise ErroImportacaoDocumento(
            "Não foi possível extrair texto deste PDF. "
            "Ele pode ser um documento escaneado."
        )

    return conteudo


def _extrair_docx(arquivo):
    try:
        from docx import Document
        from docx.opc.exceptions import PackageNotFoundError
    except ImportError:
        raise ErroImportacaoDocumento("Biblioteca de leitura de DOCX não disponível.")

    try:
        documento = Document(arquivo)
    except Exception:
        raise ErroImportacaoDocumento(
            "Não foi possível abrir o arquivo DOCX. "
            "O arquivo pode estar corrompido ou em formato inválido."
        )

    linhas = [p.text for p in documento.paragraphs if p.text.strip()]

    for tabela in documento.tables:
        for linha in tabela.rows:
            for celula in linha.cells:
                texto_celula = celula.text.strip()
                if texto_celula:
                    linhas.append(texto_celula)

    conteudo = "\n".join(linhas).strip()

    if not conteudo:
        raise ErroImportacaoDocumento(
            "Não foi possível encontrar texto reutilizável neste documento."
        )

    return conteudo


# ── Peças repetitivas (Fase 1, sem IA) ──────────────────────────────────────
# Sem pipeline de IA (PDR-0008) não há reconhecimento dos campos variáveis
# da peça base — os dados do caso entram como um bloco de identificação à
# frente do conteúdo original, nunca por substituição de marcador.

def montar_conteudo_caso_repetitivo(conteudo_base, *, cliente=None, valor="", endereco_caso="", particularidades=""):
    linhas = []
    if cliente is not None:
        documento = cliente.cpf_cnpj or "não informado"
        linhas.append(
            f"<p><b>Cliente:</b> {escapar_html(cliente.nome_razao_social)} "
            f"(CPF/CNPJ: {escapar_html(documento)})</p>"
        )
    if valor:
        linhas.append(f"<p><b>Valor:</b> {escapar_html(valor)}</p>")
    if endereco_caso:
        linhas.append(f"<p><b>Endereço do caso:</b> {escapar_html(endereco_caso)}</p>")
    if particularidades:
        linhas.append(f"<p><b>Particularidades:</b> {escapar_html(particularidades)}</p>")

    if not linhas:
        return conteudo_base or ""

    return "".join(linhas) + "<p>&nbsp;</p>" + (conteudo_base or "")


def titulo_peca_caso_repetitivo(titulo_base, cliente, indice):
    if cliente is not None:
        return f"{titulo_base} — {cliente.nome_razao_social}"[:255]
    return f"{titulo_base} — Caso {indice}"[:255]


# ── Exportação em PDF/DOCX ──────────────────────────────────────────────────
# `ModeloPeca.conteudo` vem tanto do editor visual (HTML só com <p>/<div>,
# <b>/<i>/<u> e `text-align` inline — ver `_nova_peca_editor_js.html`) quanto
# de texto puro (peça importada ou digitada na textarea de edição). O parser
# abaixo reduz os dois casos a uma lista de parágrafos com runs de
# formatação, formato intermediário único consumido pelos dois exportadores
# — não tenta reconhecer endereçamento/número de processo/jurisprudência/
# citação (isso depende do pipeline de IA do PDR-0008, ainda não existe).

_TAGS_BLOCO = {"p", "div"}
_TAGS_QUEBRA = {"br"}
_TAGS_NEGRITO = {"b", "strong"}
_TAGS_ITALICO = {"i", "em"}
_TAGS_SUBLINHADO = {"u"}
_ALINHAMENTOS_VALIDOS = {"left", "center", "right", "justify"}


class _ParserConteudoPeca(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.paragrafos = []
        self._runs_atuais = []
        self._alinhamento_atual = "left"
        self._negrito = 0
        self._italico = 0
        self._sublinhado = 0
        self._paragrafo_aberto = False

    def _abrir_paragrafo(self, alinhamento="left"):
        self._runs_atuais = []
        self._alinhamento_atual = alinhamento
        self._paragrafo_aberto = True

    def _fechar_paragrafo(self):
        if self._runs_atuais:
            self.paragrafos.append({
                "alinhamento": self._alinhamento_atual,
                "runs": self._runs_atuais,
            })
        self._runs_atuais = []
        self._paragrafo_aberto = False

    def _alinhamento_do_style(self, attrs):
        for nome, valor in attrs:
            if nome != "style" or not valor:
                continue
            for declaracao in valor.split(";"):
                chave, _, resto = declaracao.partition(":")
                resto = resto.strip()
                if chave.strip() == "text-align" and resto in _ALINHAMENTOS_VALIDOS:
                    return resto
        return "left"

    def handle_starttag(self, tag, attrs):
        if tag in _TAGS_BLOCO:
            if self._paragrafo_aberto:
                self._fechar_paragrafo()
            self._abrir_paragrafo(self._alinhamento_do_style(attrs))
        elif tag in _TAGS_NEGRITO:
            self._negrito += 1
        elif tag in _TAGS_ITALICO:
            self._italico += 1
        elif tag in _TAGS_SUBLINHADO:
            self._sublinhado += 1
        elif tag in _TAGS_QUEBRA:
            self._adicionar_texto("\n")

    def handle_endtag(self, tag):
        if tag in _TAGS_BLOCO:
            self._fechar_paragrafo()
        elif tag in _TAGS_NEGRITO:
            self._negrito = max(0, self._negrito - 1)
        elif tag in _TAGS_ITALICO:
            self._italico = max(0, self._italico - 1)
        elif tag in _TAGS_SUBLINHADO:
            self._sublinhado = max(0, self._sublinhado - 1)

    def _adicionar_texto(self, texto):
        if not self._paragrafo_aberto:
            self._abrir_paragrafo()
        self._runs_atuais.append({
            "texto": texto,
            "negrito": self._negrito > 0,
            "italico": self._italico > 0,
            "sublinhado": self._sublinhado > 0,
        })

    def handle_data(self, data):
        if data:
            self._adicionar_texto(data)

    def close(self):
        super().close()
        if self._paragrafo_aberto:
            self._fechar_paragrafo()


def _dividir_por_quebra_de_linha(paragrafos):
    """Conteúdo sem tags de bloco (peça importada/texto puro) chega como um
    único parágrafo com `\\n` cru dentro do texto — separa em parágrafos de
    verdade para não virar uma linha só no documento exportado."""
    resultado = []
    for paragrafo in paragrafos:
        atual = {"alinhamento": paragrafo["alinhamento"], "runs": []}
        for run in paragrafo["runs"]:
            partes = run["texto"].split("\n")
            for indice, parte in enumerate(partes):
                if indice > 0:
                    resultado.append(atual)
                    atual = {"alinhamento": paragrafo["alinhamento"], "runs": []}
                if parte:
                    atual["runs"].append({**run, "texto": parte})
        resultado.append(atual)
    return [p for p in resultado if p["runs"]]


def extrair_paragrafos(conteudo):
    """Converte `ModeloPeca.conteudo` numa lista de parágrafos
    (`{"alinhamento", "runs": [{"texto", "negrito", "italico",
    "sublinhado"}]}`) — formato intermediário comum entre
    `gerar_docx_modelo` e `gerar_pdf_modelo`."""
    parser = _ParserConteudoPeca()
    parser.feed(conteudo or "")
    parser.close()
    return _dividir_por_quebra_de_linha(parser.paragrafos)


def _cm(valor, padrao=0.0):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return padrao


def _bytes_do_arquivo(campo_arquivo):
    with campo_arquivo.open("rb") as arquivo:
        return BytesIO(arquivo.read())


def gerar_docx_modelo(modelo, estilo):
    """Gera um .docx a partir de `modelo.conteudo`, aplicando cabeçalho/
    rodapé/marca d'água/assinatura e fonte/espaçamento/recuo do
    `EstiloEscritorio` vigente (PRODUCT.md: cada peça nova segue o padrão
    automaticamente)."""
    from docx import Document as DocumentoDocx
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Cm, Pt, RGBColor

    alinhamento_docx = {
        "left": WD_ALIGN_PARAGRAPH.LEFT,
        "center": WD_ALIGN_PARAGRAPH.CENTER,
        "right": WD_ALIGN_PARAGRAPH.RIGHT,
        "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
    }
    espacamento_docx = {"1": 1.0, "1.15": 1.15, "1.5": 1.5, "2": 2.0}

    geral = estilo.config_documento.get("geral", {})
    slots = estilo.config_documento.get("slots", {})

    documento = DocumentoDocx()
    secao = documento.sections[0]
    margem = Cm(_cm(geral.get("recuo_texto")))
    secao.left_margin = margem
    secao.right_margin = margem

    fonte_normal = documento.styles["Normal"].font
    fonte_normal.name = geral.get("fonte", "Times New Roman")
    fonte_normal.size = Pt(geral.get("tamanho_fonte", 11))

    def _slot_texto_ou_imagem(paragrafo, slot, campo_imagem):
        if slot.get("modo") == "imagem":
            arquivo = getattr(estilo, campo_imagem)
            if arquivo:
                paragrafo.add_run().add_picture(_bytes_do_arquivo(arquivo), height=Cm(1.5))
        else:
            paragrafo.add_run(slot.get("texto", ""))

    slot_cabecalho = slots.get("cabecalho", {})
    if slot_cabecalho.get("ativo"):
        paragrafo = secao.header.paragraphs[0]
        paragrafo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _slot_texto_ou_imagem(paragrafo, slot_cabecalho, "imagem_cabecalho")

    slot_rodape = slots.get("rodape", {})
    if slot_rodape.get("ativo"):
        paragrafo = secao.footer.paragraphs[0]
        paragrafo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _slot_texto_ou_imagem(paragrafo, slot_rodape, "imagem_rodape")

    # Marca d'água rotacionada e atrás do texto exige injetar um shape VML
    # no XML do cabeçalho — desproporcional para o ganho aqui; aproxima com
    # texto grande cinza-claro (ou a imagem reduzida) no próprio cabeçalho.
    slot_marca_dagua = slots.get("marca_dagua", {})
    if slot_marca_dagua.get("ativo"):
        paragrafo = secao.header.add_paragraph()
        paragrafo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if slot_marca_dagua.get("modo") == "imagem":
            arquivo = getattr(estilo, "imagem_marca_dagua")
            if arquivo:
                paragrafo.add_run().add_picture(_bytes_do_arquivo(arquivo), height=Cm(1.2))
        else:
            run = paragrafo.add_run(slot_marca_dagua.get("texto", ""))
            run.font.size = Pt(28)
            run.font.bold = True
            run.font.color.rgb = RGBColor(0xD9, 0xD9, 0xD9)

    recuo_paragrafo = Cm(_cm(geral.get("recuo_paragrafo")))
    espacamento = espacamento_docx.get(geral.get("espacamento"), 1.15)
    for paragrafo_dado in extrair_paragrafos(modelo.conteudo):
        paragrafo = documento.add_paragraph()
        paragrafo.alignment = alinhamento_docx.get(paragrafo_dado["alinhamento"], WD_ALIGN_PARAGRAPH.JUSTIFY)
        paragrafo.paragraph_format.line_spacing = espacamento
        paragrafo.paragraph_format.first_line_indent = recuo_paragrafo
        for run_dado in paragrafo_dado["runs"]:
            run = paragrafo.add_run(run_dado["texto"])
            run.bold = run_dado["negrito"]
            run.italic = run_dado["italico"]
            run.underline = run_dado["sublinhado"]

    slot_assinatura = slots.get("assinatura", {})
    if slot_assinatura.get("ativo"):
        documento.add_paragraph()
        paragrafo = documento.add_paragraph("_" * 30)
        paragrafo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragrafo_texto = documento.add_paragraph()
        paragrafo_texto.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _slot_texto_ou_imagem(paragrafo_texto, slot_assinatura, "imagem_assinatura")

    buffer = BytesIO()
    documento.save(buffer)
    buffer.seek(0)
    return buffer


_FONTE_PDF_BASE = {
    "Times New Roman": "Times-Roman",
    "Georgia": "Times-Roman",
    "Arial": "Helvetica",
    "Calibri": "Helvetica",
}
_ESPACAMENTO_PDF = {"1": 1.0, "1.15": 1.15, "1.5": 1.5, "2": 2.0}


def _runs_para_markup_reportlab(runs):
    partes = []
    for run in runs:
        texto = escapar_xml(run["texto"])
        if run["negrito"]:
            texto = f"<b>{texto}</b>"
        if run["italico"]:
            texto = f"<i>{texto}</i>"
        if run["sublinhado"]:
            texto = f"<u>{texto}</u>"
        partes.append(texto)
    return "".join(partes) or "&nbsp;"


def gerar_pdf_modelo(modelo, estilo):
    """Gera um PDF a partir de `modelo.conteudo` com o mesmo padrão de
    `EstiloEscritorio` aplicado em `gerar_docx_modelo` — mesmas
    simplificações (sem seções de endereçamento/jurisprudência/citação,
    que dependem do pipeline de IA do PDR-0008)."""
    from reportlab.lib.colors import HexColor
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib.utils import ImageReader
    from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

    alinhamento_pdf = {"left": TA_LEFT, "center": TA_CENTER, "right": TA_RIGHT, "justify": TA_JUSTIFY}

    geral = estilo.config_documento.get("geral", {})
    slots = estilo.config_documento.get("slots", {})
    fonte_base = _FONTE_PDF_BASE.get(geral.get("fonte"), "Helvetica")
    tamanho_fonte = geral.get("tamanho_fonte", 11)
    margem_lateral = _cm(geral.get("recuo_texto")) * cm
    cor_folha = HexColor(geral.get("cor_folha", "#ffffff"))

    def _desenhar_slot(canvas, slot, campo_imagem, y, tamanho_fonte_slot, pagina_largura):
        if not slot.get("ativo"):
            return
        if slot.get("modo") == "imagem":
            arquivo = getattr(estilo, campo_imagem)
            if not arquivo:
                return
            try:
                imagem = ImageReader(_bytes_do_arquivo(arquivo))
                largura_original, altura_original = imagem.getSize()
                altura = 1.2 * cm
                largura = altura * largura_original / altura_original
                canvas.drawImage(
                    imagem, (pagina_largura - largura) / 2, y - altura,
                    width=largura, height=altura, mask="auto",
                )
            except Exception:
                pass
        else:
            canvas.setFont("Helvetica", tamanho_fonte_slot)
            canvas.setFillColor(HexColor("#555555"))
            canvas.drawCentredString(pagina_largura / 2, y, slot.get("texto", ""))

    def _desenhar_marca_dagua(canvas, pagina_largura, pagina_altura):
        slot = slots.get("marca_dagua", {})
        if not slot.get("ativo"):
            return
        canvas.saveState()
        canvas.translate(pagina_largura / 2, pagina_altura / 2)
        canvas.rotate(45)
        try:
            if slot.get("modo") == "imagem":
                arquivo = getattr(estilo, "imagem_marca_dagua")
                if arquivo:
                    canvas.setFillAlpha(0.12)
                    imagem = ImageReader(_bytes_do_arquivo(arquivo))
                    largura_original, altura_original = imagem.getSize()
                    largura = 8 * cm
                    altura = largura * altura_original / largura_original
                    canvas.drawImage(
                        imagem, -largura / 2, -altura / 2,
                        width=largura, height=altura, mask="auto",
                    )
            else:
                canvas.setFillColor(HexColor("#000000"))
                canvas.setFillAlpha(0.08)
                canvas.setFont("Helvetica-Bold", 60)
                canvas.drawCentredString(0, 0, slot.get("texto", ""))
        except Exception:
            pass
        canvas.restoreState()

    def _fundo_e_moldura(canvas, doc):
        pagina_largura, pagina_altura = A4
        canvas.saveState()
        canvas.setFillColor(cor_folha)
        canvas.rect(0, 0, pagina_largura, pagina_altura, fill=1, stroke=0)
        canvas.restoreState()
        _desenhar_slot(canvas, slots.get("cabecalho", {}), "imagem_cabecalho", pagina_altura - 1.5 * cm, 9, pagina_largura)
        _desenhar_slot(canvas, slots.get("rodape", {}), "imagem_rodape", 1.2 * cm, 8, pagina_largura)
        _desenhar_marca_dagua(canvas, pagina_largura, pagina_altura)

    buffer = BytesIO()
    documento = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=margem_lateral, rightMargin=margem_lateral,
        topMargin=2.5 * cm, bottomMargin=2.5 * cm,
    )

    estilo_base = ParagraphStyle(
        "corpo-peca",
        fontName=fonte_base,
        fontSize=tamanho_fonte,
        leading=tamanho_fonte * _ESPACAMENTO_PDF.get(geral.get("espacamento"), 1.15),
        firstLineIndent=_cm(geral.get("recuo_paragrafo")) * cm,
    )

    fluxo = []
    for paragrafo in extrair_paragrafos(modelo.conteudo):
        estilo_paragrafo = ParagraphStyle(
            "p", parent=estilo_base,
            alignment=alinhamento_pdf.get(paragrafo["alinhamento"], TA_JUSTIFY),
        )
        fluxo.append(Paragraph(_runs_para_markup_reportlab(paragrafo["runs"]), estilo_paragrafo))
        fluxo.append(Spacer(1, 6))

    slot_assinatura = slots.get("assinatura", {})
    if slot_assinatura.get("ativo"):
        fluxo.append(Spacer(1, 24))
        fluxo.append(HRFlowable(width="30%", thickness=1, color=HexColor("#333333"), hAlign="CENTER"))
        if slot_assinatura.get("modo") == "imagem":
            arquivo = getattr(estilo, "imagem_assinatura")
            if arquivo:
                from reportlab.platypus import Image as ImagemPdf
                try:
                    imagem = ImageReader(_bytes_do_arquivo(arquivo))
                    largura_original, altura_original = imagem.getSize()
                    altura = 1.5 * cm
                    largura = altura * largura_original / altura_original
                    fluxo.append(ImagemPdf(_bytes_do_arquivo(arquivo), width=largura, height=altura, hAlign="CENTER"))
                except Exception:
                    pass
        else:
            estilo_assinatura = ParagraphStyle("assinatura", alignment=TA_CENTER, fontName=fonte_base, fontSize=10)
            fluxo.append(Paragraph(escapar_xml(slot_assinatura.get("texto", "")), estilo_assinatura))

    documento.build(fluxo, onFirstPage=_fundo_e_moldura, onLaterPages=_fundo_e_moldura)
    buffer.seek(0)
    return buffer
