import json
import re
from pathlib import Path

from django import forms
from apps.modelos.models import CategoriaModeloPeca, EstiloEscritorio, ModeloPeca, config_documento_padrao

TAMANHO_MAXIMO_BYTES = 10 * 1024 * 1024  # 10 MB
EXTENSOES_ACEITAS = {".pdf", ".docx"}
EXTENSOES_IMAGEM_ACEITAS = {".png", ".jpg", ".jpeg", ".svg"}

AREAS_DIREITO = [
    ("", "Selecione uma área"),
    ("civil", "Cível"),
    ("consumidor", "Consumidor"),
    ("trabalhista", "Trabalhista"),
    ("tributario", "Tributário"),
]


class ModeloPecaForm(forms.ModelForm):
    categoria = forms.ModelChoiceField(
        queryset=CategoriaModeloPeca.objects.all(),
        widget=forms.Select(attrs={"class": "select"}),
        label="Categoria",
        empty_label="Selecione uma categoria",
    )
    area_direito = forms.ChoiceField(
        choices=AREAS_DIREITO,
        widget=forms.Select(attrs={"class": "select"}),
        label="Área do direito",
    )

    class Meta:
        model = ModeloPeca
        fields = ["titulo", "categoria", "area_direito", "conteudo"]
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
        label="Categoria",
        empty_label="Selecione uma categoria",
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


class EstiloEscritorioForm(forms.ModelForm):
    class Meta:
        model = EstiloEscritorio
        fields = ["tom_voz", "instrucoes_gerais"]
        widgets = {
            "tom_voz": forms.Textarea(attrs={
                "class": "input h-32 resize-y",
                "placeholder": "Ex: Formal, direto, sem gírias.",
            }),
            "instrucoes_gerais": forms.Textarea(attrs={
                "class": "input h-32 resize-y",
                "placeholder": "Instruções gerais que a IA deve seguir ao redigir peças.",
            }),
        }
        labels = {
            "tom_voz": "Tom de voz",
            "instrucoes_gerais": "Instruções gerais",
        }


FONTES_PERMITIDAS = {"Times New Roman", "Arial", "Calibri", "Georgia"}
CORES_FOLHA_PERMITIDAS = {"#ffffff", "#faf6ee", "#f4f4f4", "#eef4ff"}
TAMANHOS_FONTE_GERAL_PERMITIDOS = {10, 11, 12, 14, 16}
ESPACAMENTOS_PERMITIDOS = {"1", "1.15", "1.5", "2"}
RECUOS_GERAIS_PERMITIDOS = {"0", "1.25", "2", "3"}
CAIXAS_PERMITIDAS = {"maiusculas", "capitalizado", "normal"}
ALINHAMENTOS_PERMITIDOS = {"left", "center", "right", "justify"}
RECUOS_TRECHO_PERMITIDOS = {"0", "20", "40", "60"}
MODOS_SLOT_PERMITIDOS = {"texto", "imagem"}
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
            "imagem_assinatura",
        ]
        widgets = {
            "arquivo_referencia": forms.ClearableFileInput(attrs={"accept": ".pdf,.docx"}),
            "imagem_cabecalho": forms.ClearableFileInput(attrs={"accept": "image/*"}),
            "imagem_rodape": forms.ClearableFileInput(attrs={"accept": "image/*"}),
            "imagem_marca_dagua": forms.ClearableFileInput(attrs={"accept": "image/*"}),
            "imagem_assinatura": forms.ClearableFileInput(attrs={"accept": "image/*"}),
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
        labels = {"nome": "Nome da categoria"}
