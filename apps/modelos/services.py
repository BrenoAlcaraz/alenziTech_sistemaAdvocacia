import base64
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


# ── Gerar procuração (specs/clientes-gerar-procuracao.md) ───────────────────
# Mesma lógica de Peças repetitivas: sem pipeline de IA (PDR-0008), os dados
# do cliente entram como bloco de identificação à frente do conteúdo do
# modelo de Procuração cadastrado pelo escritório — nunca substituição de
# marcador nem texto de poderes gerado do zero.

def _endereco_cliente(cliente):
    partes = [
        cliente.logradouro, cliente.numero, cliente.complemento,
        cliente.bairro, cliente.cidade, cliente.estado,
    ]
    endereco = ", ".join(parte for parte in partes if parte)
    if cliente.cep:
        endereco = f"{endereco} — CEP {cliente.cep}" if endereco else f"CEP {cliente.cep}"
    return endereco


def montar_conteudo_procuracao(conteudo_base, cliente):
    documento = cliente.cpf_cnpj or "não informado"
    linhas = [
        f"<p><b>Outorgante:</b> {escapar_html(cliente.nome_razao_social)} "
        f"(CPF/CNPJ: {escapar_html(documento)})</p>"
    ]
    endereco = _endereco_cliente(cliente)
    if endereco:
        linhas.append(f"<p><b>Endereço:</b> {escapar_html(endereco)}</p>")

    if cliente.tipo == "PJ" and cliente.representante_nome:
        cpf_representante = cliente.representante_cpf or "não informado"
        cargo = f", {escapar_html(cliente.representante_cargo)}" if cliente.representante_cargo else ""
        linhas.append(
            f"<p><b>Representante:</b> {escapar_html(cliente.representante_nome)} "
            f"(CPF: {escapar_html(cpf_representante)}{cargo})</p>"
        )

    return "".join(linhas) + "<p>&nbsp;</p>" + (conteudo_base or "")


def titulo_peca_procuracao(titulo_base, cliente):
    return f"{titulo_base} — {cliente.nome_razao_social}"[:255]


def gerar_peca_procuracao(modelo_base, cliente, autor):
    """Nova peça de Procuração do cliente a partir de um modelo-base, sem
    alterar o modelo; a peça fica vinculada ao cliente (nunca vira
    modelo-base). Único ponto de geração — reaproveitado por todo fluxo
    que gera procuração."""
    from .models import ModeloPeca

    return ModeloPeca.objects.create(
        titulo=titulo_peca_procuracao(modelo_base.titulo, cliente),
        categoria=modelo_base.categoria,
        area_direito=modelo_base.area_direito,
        conteudo=montar_conteudo_procuracao(modelo_base.conteudo, cliente),
        criado_por=autor,
        cliente=cliente,
    )


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
_TAGS_IMAGEM = {"img"}
_ALINHAMENTOS_VALIDOS = {"left", "center", "right", "justify"}
_LARGURA_IMAGEM_PADRAO = 50


def _atributo(attrs, nome):
    for chave, valor in attrs:
        if chave == nome:
            return valor
    return None


def _largura_do_style(attrs):
    style = _atributo(attrs, "style") or ""
    for declaracao in style.split(";"):
        chave, _, resto = declaracao.partition(":")
        if chave.strip() != "width":
            continue
        try:
            return max(10, min(100, int(float(resto.strip().rstrip("%")))))
        except ValueError:
            pass
    return _LARGURA_IMAGEM_PADRAO


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
        elif tag in _TAGS_IMAGEM:
            self._adicionar_imagem(attrs)
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

    def _adicionar_imagem(self, attrs):
        """Imagem inserida no conteúdo pelo editor (data-URL embutida,
        `_nova_peca_editor_js.html`) — vira parágrafo próprio, nunca um
        run de texto (specs/modelos-estilo-simplificacao-imagens.md)."""
        src = _atributo(attrs, "src") or ""
        if not src.startswith("data:image/"):
            return
        if self._paragrafo_aberto:
            self._fechar_paragrafo()
        self.paragrafos.append({
            "tipo": "imagem",
            "alinhamento": self._alinhamento_atual,
            "src": src,
            "largura": _largura_do_style(attrs),
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
        if paragrafo.get("tipo") == "imagem":
            resultado.append(paragrafo)
            continue
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
    return [p for p in resultado if p.get("tipo") == "imagem" or p["runs"]]


def extrair_paragrafos(conteudo):
    """Converte `ModeloPeca.conteudo` numa lista de parágrafos — texto
    (`{"alinhamento", "runs": [{"texto", "negrito", "italico",
    "sublinhado"}]}`) ou imagem inserida no conteúdo
    (`{"tipo": "imagem", "alinhamento", "src", "largura"}`) — formato
    intermediário comum entre `gerar_docx_modelo` e `gerar_pdf_modelo`."""
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


def _bytes_de_data_url(data_url):
    """Decodifica a imagem inserida no conteúdo (data-URL base64 — ver
    `_nova_peca_editor_js.html`); `None` se o valor não for uma data-URL
    de imagem válida."""
    try:
        _cabecalho, dados_b64 = data_url.split(",", 1)
        return BytesIO(base64.b64decode(dados_b64))
    except (ValueError, TypeError, base64.binascii.Error):
        return None


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
    largura_util = secao.page_width - secao.left_margin - secao.right_margin

    fonte_normal = documento.styles["Normal"].font
    fonte_normal.name = geral.get("fonte", "Times New Roman")
    fonte_normal.size = Pt(geral.get("tamanho_fonte", 11))

    def _slot_texto_ou_imagem(paragrafo, slot, campo_imagem):
        if slot.get("modo") == "imagem":
            arquivo = getattr(estilo, campo_imagem)
            if arquivo:
                largura_imagem = int(largura_util * (slot.get("largura", 30) / 100.0))
                paragrafo.add_run().add_picture(_bytes_do_arquivo(arquivo), width=largura_imagem)
        else:
            paragrafo.add_run(slot.get("texto", ""))

    def _alinhamento_do_slot(slot):
        if slot.get("modo") == "imagem":
            return alinhamento_docx.get(slot.get("alinhamento", "center"), WD_ALIGN_PARAGRAPH.CENTER)
        return WD_ALIGN_PARAGRAPH.CENTER

    # "ultima" página não é suportável em DOCX: o formato não conhece a
    # paginação no momento da geração (Word só calcula quebras de página
    # ao abrir o arquivo) — mesma classe de limitação já aceita para a
    # marca d'água rotacionada logo abaixo. Cabeçalho/rodapé com essa
    # escolha simplesmente não aparecem no .docx (aparecem normalmente
    # no PDF, que consegue calcular a página final).
    usar_primeira_pagina_distinta = any(
        slots.get(nome, {}).get("replicacao") == "primeira" for nome in ("cabecalho", "rodape")
    )
    if usar_primeira_pagina_distinta:
        secao.different_first_page_header_footer = True

    def _aplicar_cabecalho_ou_rodape(slot, campo_imagem, normal, primeira_pagina):
        if not slot.get("ativo") or slot.get("replicacao") == "ultima":
            return
        replicacao = slot.get("replicacao", "todas")
        if replicacao == "todas" or not usar_primeira_pagina_distinta:
            paragrafo = normal.paragraphs[0]
            paragrafo.alignment = _alinhamento_do_slot(slot)
            _slot_texto_ou_imagem(paragrafo, slot, campo_imagem)
        if replicacao in ("todas", "primeira") and usar_primeira_pagina_distinta:
            paragrafo = primeira_pagina.paragraphs[0]
            paragrafo.alignment = _alinhamento_do_slot(slot)
            _slot_texto_ou_imagem(paragrafo, slot, campo_imagem)

    _aplicar_cabecalho_ou_rodape(
        slots.get("cabecalho", {}), "imagem_cabecalho", secao.header, secao.first_page_header,
    )
    _aplicar_cabecalho_ou_rodape(
        slots.get("rodape", {}), "imagem_rodape", secao.footer, secao.first_page_footer,
    )

    # Marca d'água rotacionada e atrás do texto exige injetar um shape VML
    # no XML do cabeçalho — desproporcional para o ganho aqui; aproxima com
    # texto grande cinza-claro (ou a imagem reduzida) no próprio cabeçalho.
    slot_marca_dagua = slots.get("marca_dagua", {})
    if slot_marca_dagua.get("ativo"):
        paragrafo = secao.header.add_paragraph()
        paragrafo.alignment = _alinhamento_do_slot(slot_marca_dagua)
        if slot_marca_dagua.get("modo") == "imagem":
            arquivo = getattr(estilo, "imagem_marca_dagua")
            if arquivo:
                largura_imagem = int(largura_util * (slot_marca_dagua.get("largura", 30) / 100.0))
                paragrafo.add_run().add_picture(_bytes_do_arquivo(arquivo), width=largura_imagem)
        else:
            run = paragrafo.add_run(slot_marca_dagua.get("texto", ""))
            run.font.size = Pt(28)
            run.font.bold = True
            run.font.color.rgb = RGBColor(0xD9, 0xD9, 0xD9)

    recuo_paragrafo = Cm(_cm(geral.get("recuo_paragrafo")))
    espacamento = espacamento_docx.get(geral.get("espacamento"), 1.15)
    for paragrafo_dado in extrair_paragrafos(modelo.conteudo):
        if paragrafo_dado.get("tipo") == "imagem":
            dados = _bytes_de_data_url(paragrafo_dado["src"])
            if dados is None:
                continue
            paragrafo = documento.add_paragraph()
            paragrafo.alignment = alinhamento_docx.get(paragrafo_dado["alinhamento"], WD_ALIGN_PARAGRAPH.CENTER)
            largura_imagem = int(largura_util * (paragrafo_dado.get("largura", 50) / 100.0))
            paragrafo.add_run().add_picture(dados, width=largura_imagem)
            continue
        paragrafo = documento.add_paragraph()
        paragrafo.alignment = alinhamento_docx.get(paragrafo_dado["alinhamento"], WD_ALIGN_PARAGRAPH.JUSTIFY)
        paragrafo.paragraph_format.line_spacing = espacamento
        paragrafo.paragraph_format.first_line_indent = recuo_paragrafo
        for run_dado in paragrafo_dado["runs"]:
            run = paragrafo.add_run(run_dado["texto"])
            run.bold = run_dado["negrito"]
            run.italic = run_dado["italico"]
            run.underline = run_dado["sublinhado"]

    for assinatura in estilo.assinaturas.all():
        documento.add_paragraph()
        paragrafo = documento.add_paragraph("_" * 30)
        paragrafo.alignment = alinhamento_docx.get(assinatura.alinhamento, WD_ALIGN_PARAGRAPH.CENTER)
        paragrafo_conteudo = documento.add_paragraph()
        paragrafo_conteudo.alignment = alinhamento_docx.get(assinatura.alinhamento, WD_ALIGN_PARAGRAPH.CENTER)
        if assinatura.modo == "imagem" and assinatura.imagem:
            largura_imagem = int(largura_util * (assinatura.largura / 100.0))
            paragrafo_conteudo.add_run().add_picture(_bytes_do_arquivo(assinatura.imagem), width=largura_imagem)
        elif assinatura.texto:
            paragrafo_conteudo.add_run(assinatura.texto)

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


def _deve_mostrar_na_pagina(replicacao, numero_pagina, total_paginas):
    """"todas"/"primeira"/"última" (specs/modelos-estilo-simplificacao-
    imagens.md) — `total_paginas` só é conhecido (contagem em uma
    primeira passada de build) quando algum slot pede "ultima"."""
    if replicacao == "primeira":
        return numero_pagina == 1
    if replicacao == "ultima":
        return total_paginas is not None and numero_pagina == total_paginas
    return True


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
    from reportlab.platypus import HRFlowable, Image as ImagemPdf, Paragraph, SimpleDocTemplate, Spacer

    alinhamento_pdf = {"left": TA_LEFT, "center": TA_CENTER, "right": TA_RIGHT, "justify": TA_JUSTIFY}

    geral = estilo.config_documento.get("geral", {})
    slots = estilo.config_documento.get("slots", {})
    fonte_base = _FONTE_PDF_BASE.get(geral.get("fonte"), "Helvetica")
    tamanho_fonte = geral.get("tamanho_fonte", 11)
    margem_lateral = _cm(geral.get("recuo_texto")) * cm
    cor_folha = HexColor(geral.get("cor_folha", "#ffffff"))
    pagina_largura, pagina_altura = A4

    def _x_para_alinhamento(alinhamento, largura_elemento):
        if alinhamento == "left":
            return margem_lateral
        if alinhamento == "right":
            return pagina_largura - margem_lateral - largura_elemento
        return (pagina_largura - largura_elemento) / 2

    def _desenhar_slot(canvas, slot, campo_imagem, y, tamanho_fonte_slot):
        if not slot.get("ativo"):
            return
        if slot.get("modo") == "imagem":
            arquivo = getattr(estilo, campo_imagem)
            if not arquivo:
                return
            try:
                imagem = ImageReader(_bytes_do_arquivo(arquivo))
                largura_original, altura_original = imagem.getSize()
                largura = pagina_largura * (slot.get("largura", 30) / 100.0)
                altura = largura * altura_original / largura_original
                x = _x_para_alinhamento(slot.get("alinhamento", "center"), largura)
                canvas.drawImage(imagem, x, y - altura, width=largura, height=altura, mask="auto")
            except Exception:
                pass
        else:
            canvas.setFont("Helvetica", tamanho_fonte_slot)
            canvas.setFillColor(HexColor("#555555"))
            canvas.drawCentredString(pagina_largura / 2, y, slot.get("texto", ""))

    def _desenhar_marca_dagua(canvas):
        slot = slots.get("marca_dagua", {})
        if not slot.get("ativo"):
            return
        canvas.saveState()
        deslocamento_x = {"left": -pagina_largura * 0.2, "right": pagina_largura * 0.2}.get(
            slot.get("alinhamento", "center"), 0,
        )
        canvas.translate(pagina_largura / 2 + deslocamento_x, pagina_altura / 2)
        canvas.rotate(45)
        try:
            if slot.get("modo") == "imagem":
                arquivo = getattr(estilo, "imagem_marca_dagua")
                if arquivo:
                    canvas.setFillAlpha(0.12)
                    imagem = ImageReader(_bytes_do_arquivo(arquivo))
                    largura_original, altura_original = imagem.getSize()
                    largura = pagina_largura * (slot.get("largura", 30) / 100.0)
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

    def _fundo_e_moldura(total_paginas):
        def _desenhar(canvas, doc):
            numero_pagina = canvas.getPageNumber()
            canvas.saveState()
            canvas.setFillColor(cor_folha)
            canvas.rect(0, 0, pagina_largura, pagina_altura, fill=1, stroke=0)
            canvas.restoreState()
            slot_cabecalho = slots.get("cabecalho", {})
            if _deve_mostrar_na_pagina(slot_cabecalho.get("replicacao", "todas"), numero_pagina, total_paginas):
                _desenhar_slot(canvas, slot_cabecalho, "imagem_cabecalho", pagina_altura - 1.5 * cm, 9)
            slot_rodape = slots.get("rodape", {})
            if _deve_mostrar_na_pagina(slot_rodape.get("replicacao", "todas"), numero_pagina, total_paginas):
                _desenhar_slot(canvas, slot_rodape, "imagem_rodape", 1.2 * cm, 8)
            _desenhar_marca_dagua(canvas)
        return _desenhar

    estilo_base = ParagraphStyle(
        "corpo-peca",
        fontName=fonte_base,
        fontSize=tamanho_fonte,
        leading=tamanho_fonte * _ESPACAMENTO_PDF.get(geral.get("espacamento"), 1.15),
        firstLineIndent=_cm(geral.get("recuo_paragrafo")) * cm,
    )

    def _montar_fluxo():
        fluxo = []
        for paragrafo in extrair_paragrafos(modelo.conteudo):
            if paragrafo.get("tipo") == "imagem":
                dados = _bytes_de_data_url(paragrafo["src"])
                if dados is None:
                    continue
                try:
                    imagem = ImageReader(dados)
                    largura_original, altura_original = imagem.getSize()
                    largura_img = (pagina_largura - 2 * margem_lateral) * (paragrafo.get("largura", 50) / 100.0)
                    altura_img = largura_img * altura_original / largura_original
                    alinhamento_img = paragrafo.get("alinhamento", "center")
                    if alinhamento_img not in ("left", "center", "right"):
                        alinhamento_img = "center"
                    fluxo.append(ImagemPdf(
                        _bytes_de_data_url(paragrafo["src"]), width=largura_img, height=altura_img,
                        hAlign=alinhamento_img.upper(),
                    ))
                    fluxo.append(Spacer(1, 6))
                except Exception:
                    pass
                continue
            estilo_paragrafo = ParagraphStyle(
                "p", parent=estilo_base,
                alignment=alinhamento_pdf.get(paragrafo["alinhamento"], TA_JUSTIFY),
            )
            fluxo.append(Paragraph(_runs_para_markup_reportlab(paragrafo["runs"]), estilo_paragrafo))
            fluxo.append(Spacer(1, 6))

        for assinatura in estilo.assinaturas.all():
            fluxo.append(Spacer(1, 24))
            fluxo.append(HRFlowable(
                width="30%", thickness=1, color=HexColor("#333333"),
                hAlign=assinatura.alinhamento.upper(),
            ))
            if assinatura.modo == "imagem" and assinatura.imagem:
                try:
                    imagem = ImageReader(_bytes_do_arquivo(assinatura.imagem))
                    largura_original, altura_original = imagem.getSize()
                    largura_img = (pagina_largura - 2 * margem_lateral) * (assinatura.largura / 100.0)
                    altura_img = largura_img * altura_original / largura_original
                    fluxo.append(ImagemPdf(
                        _bytes_do_arquivo(assinatura.imagem), width=largura_img, height=altura_img,
                        hAlign=assinatura.alinhamento.upper(),
                    ))
                except Exception:
                    pass
            elif assinatura.texto:
                estilo_assinatura = ParagraphStyle(
                    "assinatura",
                    alignment=alinhamento_pdf.get(assinatura.alinhamento, TA_CENTER),
                    fontName=fonte_base, fontSize=10,
                )
                fluxo.append(Paragraph(escapar_xml(assinatura.texto), estilo_assinatura))
        return fluxo

    def _novo_documento(buffer_destino):
        return SimpleDocTemplate(
            buffer_destino, pagesize=A4,
            leftMargin=margem_lateral, rightMargin=margem_lateral,
            topMargin=2.5 * cm, bottomMargin=2.5 * cm,
        )

    # "ultima" página só é resolvível sabendo o total — uma passada extra
    # de contagem (descartada), só quando cabeçalho ou rodapé pedem isso.
    precisa_contar_paginas = any(
        slots.get(nome, {}).get("replicacao") == "ultima" for nome in ("cabecalho", "rodape")
    )
    total_paginas = None
    if precisa_contar_paginas:
        contador = {"n": 0}

        def _contar(canvas, doc):
            contador["n"] = canvas.getPageNumber()

        _novo_documento(BytesIO()).build(_montar_fluxo(), onFirstPage=_contar, onLaterPages=_contar)
        total_paginas = contador["n"]

    buffer = BytesIO()
    desenhar_pagina = _fundo_e_moldura(total_paginas)
    _novo_documento(buffer).build(_montar_fluxo(), onFirstPage=desenhar_pagina, onLaterPages=desenhar_pagina)
    buffer.seek(0)
    return buffer
