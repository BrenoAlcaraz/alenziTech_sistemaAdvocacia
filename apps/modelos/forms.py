import json
import re
from pathlib import Path

from django import forms
from django.forms import formset_factory

from apps.clientes.models import Cliente
from apps.modelos.models import (
    REPLICACAO_CHOICES,
    AssinaturaEstilo,
    CategoriaModeloPeca,
    EstiloEscritorio,
    ModeloPeca,
    config_documento_padrao,
)
from apps.processos.models import Processo

TAMANHO_MAXIMO_BYTES = 10 * 1024 * 1024  # 10 MB
EXTENSOES_ACEITAS = {".pdf", ".docx"}
EXTENSOES_IMAGEM_ACEITAS = {".png", ".jpg", ".jpeg", ".svg"}

# Mesmo catálogo de Processo.AREAS_CHOICES — sem lista própria divergente
# (spec area-direito-novas-areas).
AREAS_DIREITO = [("", "Selecione uma área")] + Processo.AREAS_CHOICES


class ModeloPecaForm(forms.ModelForm):
    categoria = forms.ModelChoiceField(
        queryset=CategoriaModeloPeca.objects.all(),
        widget=forms.Select(attrs={"class": "select"}),
        label="Tipo de peça",
        empty_label="Selecione um tipo de peça",
    )
    area_direito = forms.ChoiceField(
        choices=AREAS_DIREITO,
        widget=forms.Select(attrs={"class": "select"}),
        label="Área do direito",
    )
    # required=False + default "todas" no clean(): mantém o comportamento
    # de sempre para quem não mexe nesse campo (inclusive POST antigo,
    # sem essas duas chaves) — specs/modelos-estilo-simplificacao-imagens.md.
    cabecalho_replicacao = forms.ChoiceField(
        choices=REPLICACAO_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "select"}),
        label="Cabeçalho aparece em",
    )
    rodape_replicacao = forms.ChoiceField(
        choices=REPLICACAO_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "select"}),
        label="Rodapé aparece em",
    )

    class Meta:
        model = ModeloPeca
        fields = [
            "titulo", "categoria", "area_direito", "conteudo",
            "cabecalho_replicacao", "rodape_replicacao",
        ]
        widgets = {
            "titulo": forms.TextInput(attrs={
                "class": "input",
                "placeholder": "Ex: Petição inicial – Ação de cobrança",
            }),
            "conteudo": forms.Textarea(attrs={
                "class": "input h-64 resize-y font-mono text-xs",
                "placeholder": "EXCELENTÍSSIMO SENHOR DOUTOR JUIZ DE DIREITO...",
            }),
        }
        labels = {
            "titulo": "Título do modelo",
            "conteudo": "Conteúdo do modelo",
        }

    def clean_cabecalho_replicacao(self):
        return self.cleaned_data.get("cabecalho_replicacao") or "todas"

    def clean_rodape_replicacao(self):
        return self.cleaned_data.get("rodape_replicacao") or "todas"


class ImportarModeloPecaForm(forms.Form):
    arquivo = forms.FileField(
        label="Arquivo",
        help_text="Formatos aceitos: PDF ou DOCX, com até 10 MB.",
        widget=forms.ClearableFileInput(attrs={"class": "input", "accept": ".pdf,.docx"}),
    )
    titulo = forms.CharField(
        label="Título do modelo",
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "input",
            "placeholder": "Deixe em branco para usar o nome do arquivo",
        }),
    )
    categoria = forms.ModelChoiceField(
        queryset=CategoriaModeloPeca.objects.all(),
        widget=forms.Select(attrs={"class": "select"}),
        label="Tipo de peça",
        empty_label="Selecione um tipo de peça",
    )
    area_direito = forms.ChoiceField(
        choices=AREAS_DIREITO,
        widget=forms.Select(attrs={"class": "select"}),
        label="Área do direito",
    )

    def clean_arquivo(self):
        from pathlib import Path
        arquivo = self.cleaned_data.get("arquivo")
        if not arquivo:
            return arquivo

        extensao = Path(arquivo.name).suffix.lower()
        if extensao not in EXTENSOES_ACEITAS:
            raise forms.ValidationError("Envie um arquivo PDF ou DOCX.")

        if arquivo.size > TAMANHO_MAXIMO_BYTES:
            raise forms.ValidationError("O arquivo deve ter no máximo 10 MB.")

        return arquivo

    def clean_area_direito(self):
        valor = self.cleaned_data.get("area_direito", "")
        if not valor:
            raise forms.ValidationError("Selecione uma área do direito.")
        return valor


FONTES_PERMITIDAS = {"Times New Roman", "Arial", "Calibri", "Georgia"}
CORES_FOLHA_PERMITIDAS = {"#ffffff", "#faf6ee", "#f4f4f4", "#eef4ff"}
TAMANHOS_FONTE_GERAL_PERMITIDOS = {10, 11, 12, 14, 16}
ESPACAMENTOS_PERMITIDOS = {"1", "1.15", "1.5", "2"}
RECUOS_GERAIS_PERMITIDOS = {"0", "1.25", "2", "3"}
CAIXAS_PERMITIDAS = {"maiusculas", "capitalizado", "normal"}
ALINHAMENTOS_PERMITIDOS = {"left", "center", "right", "justify"}
RECUOS_TRECHO_PERMITIDOS = {"0", "20", "40", "60"}
MODOS_SLOT_PERMITIDOS = {"texto", "imagem"}
ALINHAMENTOS_IMAGEM_PERMITIDOS = {"left", "center", "right"}
REPLICACOES_PERMITIDAS = {"todas", "primeira", "ultima"}
_HEX_COR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


def _cor_valida(valor, permitir_transparent=False):
    if permitir_transparent and valor == "transparent":
        return True
    return isinstance(valor, str) and bool(_HEX_COR_RE.match(valor))


def _texto_seguro(valor, maximo):
    if not isinstance(valor, str):
        return ""
    return valor.strip()[:maximo]


def _inteiro_no_intervalo(valor, minimo, maximo, padrao):
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        return padrao
    return max(minimo, min(maximo, numero))


def _sanitizar_secao(entrada, padrao):
    """Mescla `entrada` (payload do editor) com `padrao`, aceitando só
    valores dentro dos conjuntos de opções que o editor oferece — o resto
    (tipo/chave desconhecida) é descartado silenciosamente."""
    if not isinstance(entrada, dict):
        return dict(padrao)

    resultado = dict(padrao)
    for chave, valor_padrao in padrao.items():
        if chave not in entrada:
            continue
        valor = entrada[chave]
        if isinstance(valor_padrao, bool):
            resultado[chave] = bool(valor)
        elif chave == "fonte":
            resultado[chave] = valor if valor in FONTES_PERMITIDAS else valor_padrao
        elif chave == "caixa":
            resultado[chave] = valor if valor in CAIXAS_PERMITIDAS else valor_padrao
        elif chave == "alinhamento":
            resultado[chave] = valor if valor in ALINHAMENTOS_PERMITIDOS else valor_padrao
        elif chave == "cor":
            resultado[chave] = valor if _cor_valida(valor) else valor_padrao
        elif chave == "marca_texto":
            resultado[chave] = valor if _cor_valida(valor, permitir_transparent=True) else valor_padrao
        elif chave == "recuo":
            resultado[chave] = valor if valor in RECUOS_TRECHO_PERMITIDOS else valor_padrao
        elif chave in ("distancia_linhas", "tamanho"):
            resultado[chave] = _inteiro_no_intervalo(valor, 0, 72, valor_padrao)
        else:
            resultado[chave] = valor_padrao
    return resultado


def sanitizar_config_documento(dados):
    """Valida o JSON enviado pelo editor de 'Meu Estilo' contra o formato
    de `config_documento_padrao()`, aceitando só as opções que a própria
    UI oferece — qualquer chave/valor fora disso cai no padrão."""
    padrao = config_documento_padrao()
    if not isinstance(dados, dict):
        return padrao

    geral_entrada = dados.get("geral") if isinstance(dados.get("geral"), dict) else {}
    geral_padrao = padrao["geral"]
    geral = dict(geral_padrao)
    if geral_entrada.get("cor_folha") in CORES_FOLHA_PERMITIDAS:
        geral["cor_folha"] = geral_entrada["cor_folha"]
    if geral_entrada.get("fonte") in FONTES_PERMITIDAS:
        geral["fonte"] = geral_entrada["fonte"]
    if geral_entrada.get("tamanho_fonte") in TAMANHOS_FONTE_GERAL_PERMITIDOS:
        geral["tamanho_fonte"] = geral_entrada["tamanho_fonte"]
    if geral_entrada.get("espacamento") in ESPACAMENTOS_PERMITIDOS:
        geral["espacamento"] = geral_entrada["espacamento"]
    if geral_entrada.get("recuo_texto") in RECUOS_GERAIS_PERMITIDOS:
        geral["recuo_texto"] = geral_entrada["recuo_texto"]
    if geral_entrada.get("recuo_paragrafo") in RECUOS_GERAIS_PERMITIDOS:
        geral["recuo_paragrafo"] = geral_entrada["recuo_paragrafo"]

    slots_entrada = dados.get("slots") if isinstance(dados.get("slots"), dict) else {}
    slots = {}
    for nome, slot_padrao in padrao["slots"].items():
        slot_entrada = slots_entrada.get(nome) if isinstance(slots_entrada.get(nome), dict) else {}
        slot = dict(slot_padrao)
        slot["ativo"] = bool(slot_entrada.get("ativo", slot_padrao["ativo"]))
        if slot_entrada.get("modo") in MODOS_SLOT_PERMITIDOS:
            slot["modo"] = slot_entrada["modo"]
        slot["texto"] = _texto_seguro(slot_entrada.get("texto", slot_padrao["texto"]), maximo=300)
        # Tamanho/posição só fazem sentido em modo imagem, mas ficam
        # sempre validados/salvos — evita perder o ajuste ao alternar
        # texto↔imagem (specs/modelos-estilo-simplificacao-imagens.md).
        slot["largura"] = _inteiro_no_intervalo(
            slot_entrada.get("largura", slot_padrao["largura"]), 10, 100, slot_padrao["largura"],
        )
        if slot_entrada.get("alinhamento") in ALINHAMENTOS_IMAGEM_PERMITIDOS:
            slot["alinhamento"] = slot_entrada["alinhamento"]
        if "replicacao" in slot_padrao:
            if slot_entrada.get("replicacao") in REPLICACOES_PERMITIDAS:
                slot["replicacao"] = slot_entrada["replicacao"]
        slots[nome] = slot

    secoes_entrada = dados.get("secoes") if isinstance(dados.get("secoes"), dict) else {}
    secoes = {
        nome: _sanitizar_secao(secoes_entrada.get(nome), secao_padrao)
        for nome, secao_padrao in padrao["secoes"].items()
    }

    return {"geral": geral, "slots": slots, "secoes": secoes}


class EstiloDocumentoForm(forms.ModelForm):
    """Formulário do editor visual de 'Meu Estilo' — os campos de arquivo
    são as únicas imagens/anexos reais; o resto da formatação (fonte, cor,
    recuos, estilo de cada seção) chega serializado em `config_documento`
    (JSON produzido pelo editor no cliente) e é validado em
    `clean_config_documento`."""

    config_documento = forms.CharField(widget=forms.HiddenInput, required=False)

    class Meta:
        model = EstiloEscritorio
        fields = [
            "modo_estilo",
            "arquivo_referencia",
            "imagem_cabecalho",
            "imagem_rodape",
            "imagem_marca_dagua",
        ]
        widgets = {
            "arquivo_referencia": forms.ClearableFileInput(attrs={"accept": ".pdf,.docx"}),
            "imagem_cabecalho": forms.ClearableFileInput(attrs={"accept": "image/*"}),
            "imagem_rodape": forms.ClearableFileInput(attrs={"accept": "image/*"}),
            "imagem_marca_dagua": forms.ClearableFileInput(attrs={"accept": "image/*"}),
        }

    def clean_config_documento(self):
        bruto = self.data.get("config_documento", "")
        try:
            dados = json.loads(bruto) if bruto else {}
        except (TypeError, ValueError):
            dados = {}
        return sanitizar_config_documento(dados)

    def _clean_arquivo(self, nome_campo, extensoes_aceitas, mensagem_extensao):
        arquivo = self.cleaned_data.get(nome_campo)
        if not arquivo or not hasattr(arquivo, "size"):
            return arquivo
        if arquivo.size > TAMANHO_MAXIMO_BYTES:
            raise forms.ValidationError("O arquivo deve ter no máximo 10 MB.")
        if Path(arquivo.name).suffix.lower() not in extensoes_aceitas:
            raise forms.ValidationError(mensagem_extensao)
        return arquivo

    def clean_arquivo_referencia(self):
        return self._clean_arquivo(
            "arquivo_referencia", EXTENSOES_ACEITAS, "Envie um arquivo PDF ou DOCX."
        )

    def clean_imagem_cabecalho(self):
        return self._clean_arquivo(
            "imagem_cabecalho", EXTENSOES_IMAGEM_ACEITAS, "Envie uma imagem PNG, JPG ou SVG."
        )

    def clean_imagem_rodape(self):
        return self._clean_arquivo(
            "imagem_rodape", EXTENSOES_IMAGEM_ACEITAS, "Envie uma imagem PNG, JPG ou SVG."
        )

    def clean_imagem_marca_dagua(self):
        return self._clean_arquivo(
            "imagem_marca_dagua", EXTENSOES_IMAGEM_ACEITAS, "Envie uma imagem PNG, JPG ou SVG."
        )

    def clean_imagem_assinatura(self):
        return self._clean_arquivo(
            "imagem_assinatura", EXTENSOES_IMAGEM_ACEITAS, "Envie uma imagem PNG, JPG ou SVG."
        )

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.config_documento = self.cleaned_data["config_documento"]
        if commit:
            instance.save()
        return instance


class AssinaturaEstiloForm(forms.ModelForm):
    """Um bloco de assinatura do padrão de Meu Estilo — texto ou imagem
    (specs/modelos-estilo-simplificacao-imagens.md)."""

    class Meta:
        model = AssinaturaEstilo
        fields = ["modo", "texto", "imagem", "largura", "alinhamento"]
        widgets = {
            "modo": forms.Select(attrs={"class": "select"}),
            "texto": forms.TextInput(attrs={
                "class": "input",
                "placeholder": "Ex: João Silva — OAB/SP 123.456",
            }),
            "imagem": forms.ClearableFileInput(attrs={"accept": "image/*"}),
            "largura": forms.NumberInput(attrs={"class": "input", "min": 10, "max": 100}),
            "alinhamento": forms.Select(attrs={"class": "select"}),
        }

    def clean_imagem(self):
        arquivo = self.cleaned_data.get("imagem")
        if not arquivo or not hasattr(arquivo, "size"):
            return arquivo
        if arquivo.size > TAMANHO_MAXIMO_BYTES:
            raise forms.ValidationError("O arquivo deve ter no máximo 10 MB.")
        if Path(arquivo.name).suffix.lower() not in EXTENSOES_IMAGEM_ACEITAS:
            raise forms.ValidationError("Envie uma imagem PNG, JPG ou SVG.")
        return arquivo

    def clean_largura(self):
        largura = self.cleaned_data.get("largura")
        if largura is None:
            return 30
        return max(10, min(100, largura))

    def clean(self):
        cleaned = super().clean()
        modo = cleaned.get("modo")
        if modo == AssinaturaEstilo.MODO_TEXTO and not cleaned.get("texto"):
            self.add_error("texto", "Informe o texto da assinatura.")
        if modo == AssinaturaEstilo.MODO_IMAGEM and not cleaned.get("imagem"):
            self.add_error("imagem", "Envie uma imagem para a assinatura.")
        return cleaned


class CategoriaModeloPecaForm(forms.ModelForm):
    class Meta:
        model = CategoriaModeloPeca
        fields = ["nome"]
        widgets = {
            "nome": forms.TextInput(attrs={
                "class": "input",
                "placeholder": "Ex: Petição inicial, Contestação, Recurso",
            }),
        }
        labels = {"nome": "Nome do tipo de peça"}


# ── Peças repetitivas (Fase 1, sem IA) ──────────────────────────────────────

MODO_BASE_ACERVO = "acervo"
MODO_BASE_ANEXAR = "anexar"
MODO_BASE_CHOICES = [
    (MODO_BASE_ACERVO, "Usar peça do acervo"),
    (MODO_BASE_ANEXAR, "Anexar peça nova como base"),
]


class PecaBaseRepetitivaForm(forms.Form):
    """Primeira parte do fluxo de peças repetitivas: escolhe a peça que
    serve de base para as N peças geradas — do acervo já existente, ou
    anexando um arquivo novo (usado só como base desta geração, sem virar
    um ModeloPeca próprio antes de gerar)."""

    modo_base = forms.ChoiceField(
        choices=MODO_BASE_CHOICES,
        widget=forms.Select(attrs={"class": "select", "data-toggle-select": "rep-base"}),
        initial=MODO_BASE_ACERVO,
        label="Peça base",
    )
    peca_base = forms.ModelChoiceField(
        queryset=ModeloPeca.objects.select_related("categoria"),
        required=False,
        widget=forms.Select(attrs={"class": "select"}),
        empty_label="Selecione uma peça do acervo...",
        label="Peça do acervo",
    )
    arquivo_base = forms.FileField(
        required=False,
        label="Arquivo",
        widget=forms.ClearableFileInput(attrs={"accept": ".pdf,.docx"}),
    )
    categoria = forms.ModelChoiceField(
        queryset=CategoriaModeloPeca.objects.all(),
        required=False,
        widget=forms.Select(attrs={"class": "select"}),
        empty_label="Selecione um tipo de peça",
        label="Tipo de peça",
    )
    area_direito = forms.ChoiceField(
        choices=AREAS_DIREITO,
        required=False,
        widget=forms.Select(attrs={"class": "select"}),
        label="Área do direito",
    )

    def clean(self):
        dados = super().clean()
        modo = dados.get("modo_base")

        if modo == MODO_BASE_ACERVO and not dados.get("peca_base"):
            self.add_error("peca_base", "Selecione uma peça do acervo.")

        if modo == MODO_BASE_ANEXAR:
            arquivo = dados.get("arquivo_base")
            if not arquivo:
                self.add_error("arquivo_base", "Anexe um arquivo PDF ou DOCX.")
            elif Path(arquivo.name).suffix.lower() not in EXTENSOES_ACEITAS:
                self.add_error("arquivo_base", "Envie um arquivo PDF ou DOCX.")
            elif arquivo.size > TAMANHO_MAXIMO_BYTES:
                self.add_error("arquivo_base", "O arquivo deve ter no máximo 10 MB.")
            if not dados.get("categoria"):
                self.add_error("categoria", "Selecione um tipo de peça.")
            if not dados.get("area_direito"):
                self.add_error("area_direito", "Selecione uma área do direito.")

        return dados


EXTENSOES_ANEXO_CASO = {".pdf", ".docx", ".png", ".jpg", ".jpeg"}
MAXIMO_ANEXOS_POR_CASO = 10


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    """FileField que aceita vários arquivos (padrão da documentação do Django)."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        limpar = super().clean
        if isinstance(data, (list, tuple)):
            return [limpar(arquivo, initial) for arquivo in data if arquivo]
        return [limpar(data, initial)] if data else []


class CasoRepetitivoForm(forms.Form):
    """Um caso da geração em lote: escolhe o Cliente (nome/CPF-CNPJ já
    preenchidos), anexa os documentos que embasam a nova peça e anota
    observações. A IA que ajusta a peça base a esses dados depende do
    PDR-0008 — por ora o conteúdo recebe o bloco de identificação e as
    observações, e os documentos ficam guardados na peça."""

    cliente = forms.ModelChoiceField(
        queryset=Cliente.objects.filter(ativo=True),
        required=False,
        widget=forms.Select(attrs={"class": "select"}),
        empty_label="Nenhum — preencher manualmente",
        label="Cliente já cadastrado",
    )
    documentos = MultipleFileField(
        required=False, label="Documentos que embasam a peça",
        widget=MultipleFileInput(attrs={"accept": ".pdf,.docx,.png,.jpg,.jpeg"}),
    )
    observacoes = forms.CharField(
        required=False, label="Observações",
        widget=forms.Textarea(attrs={"class": "input h-20 resize-y", "placeholder": "Anote o que a IA/quem revisar deve considerar neste caso"}),
    )

    def clean_documentos(self):
        documentos = self.cleaned_data.get("documentos") or []
        if len(documentos) > MAXIMO_ANEXOS_POR_CASO:
            raise forms.ValidationError(f"Anexe no máximo {MAXIMO_ANEXOS_POR_CASO} documentos por caso.")
        for documento in documentos:
            if Path(documento.name).suffix.lower() not in EXTENSOES_ANEXO_CASO:
                raise forms.ValidationError("Envie documentos PDF, DOCX, PNG ou JPG.")
            if documento.size > TAMANHO_MAXIMO_BYTES:
                raise forms.ValidationError("Cada documento deve ter no máximo 10 MB.")
        return documentos

    def tem_dados(self):
        """Formulário "vazio" (linha adicionada mas não preenchida, ou
        removida no navegador sem ajustar TOTAL_FORMS) não vira peça."""
        return bool(
            self.cleaned_data.get("cliente")
            or self.cleaned_data.get("documentos")
            or self.cleaned_data.get("observacoes")
        )


CasoRepetitivoFormSet = formset_factory(CasoRepetitivoForm, extra=1)
