from django import forms
from apps.modelos.models import ModeloPeca

TAMANHO_MAXIMO_BYTES = 10 * 1024 * 1024  # 10 MB
EXTENSOES_ACEITAS = {".pdf", ".docx"}

AREAS_DIREITO = [
    ("", "Selecione uma área"),
    ("civil", "Cível"),
    ("consumidor", "Consumidor"),
    ("trabalhista", "Trabalhista"),
    ("tributario", "Tributário"),
]


class ModeloPecaForm(forms.ModelForm):
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
            "categoria": forms.TextInput(attrs={
                "class": "input",
                "placeholder": "Ex: Petição inicial, Contestação",
            }),
            "conteudo": forms.Textarea(attrs={
                "class": "input h-64 resize-y font-mono text-xs",
                "placeholder": "EXCELENTÍSSIMO SENHOR DOUTOR JUIZ DE DIREITO...",
            }),
        }
        labels = {
            "titulo": "Título do modelo",
            "categoria": "Categoria",
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
    categoria = forms.CharField(
        label="Categoria",
        max_length=100,
        widget=forms.TextInput(attrs={
            "class": "input",
            "placeholder": "Ex: Petição inicial, Contestação",
        }),
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
