from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.saas_tenants.storage import (
    PROTEGIDO,
    CaminhoArquivoTenant,
    StorageProtegido,
    nome_do_arquivo,
)


UF_CHOICES = [
    ("AC", "Acre"), ("AL", "Alagoas"), ("AP", "Amapá"), ("AM", "Amazonas"),
    ("BA", "Bahia"), ("CE", "Ceará"), ("DF", "Distrito Federal"),
    ("ES", "Espírito Santo"), ("GO", "Goiás"), ("MA", "Maranhão"),
    ("MT", "Mato Grosso"), ("MS", "Mato Grosso do Sul"), ("MG", "Minas Gerais"),
    ("PA", "Pará"), ("PB", "Paraíba"), ("PR", "Paraná"), ("PE", "Pernambuco"),
    ("PI", "Piauí"), ("RJ", "Rio de Janeiro"), ("RN", "Rio Grande do Norte"),
    ("RS", "Rio Grande do Sul"), ("RO", "Rondônia"), ("RR", "Roraima"),
    ("SC", "Santa Catarina"), ("SP", "São Paulo"), ("SE", "Sergipe"),
    ("TO", "Tocantins"),
]

ESTADO_CIVIL_CHOICES = [
    ("solteiro", "Solteiro(a)"),
    ("casado", "Casado(a)"),
    ("uniao_estavel", "União Estável"),
    ("divorciado", "Divorciado(a)"),
    ("viuvo", "Viúvo(a)"),
    ("separado", "Separado(a) judicialmente"),
]

NACIONALIDADE_CHOICES = [
    ("Brasileira", "Brasileira"),
    ("Alemã", "Alemã"),
    ("Americana", "Americana"),
    ("Angolana", "Angolana"),
    ("Argentina", "Argentina"),
    ("Australiana", "Australiana"),
    ("Austríaca", "Austríaca"),
    ("Belga", "Belga"),
    ("Boliviana", "Boliviana"),
    ("Canadense", "Canadense"),
    ("Chilena", "Chilena"),
    ("Chinesa", "Chinesa"),
    ("Colombiana", "Colombiana"),
    ("Coreana", "Coreana"),
    ("Cubana", "Cubana"),
    ("Dinamarquesa", "Dinamarquesa"),
    ("Egípcia", "Egípcia"),
    ("Equatoriana", "Equatoriana"),
    ("Espanhola", "Espanhola"),
    ("Filipina", "Filipina"),
    ("Francesa", "Francesa"),
    ("Grega", "Grega"),
    ("Holandesa", "Holandesa"),
    ("Húngara", "Húngara"),
    ("Indiana", "Indiana"),
    ("Inglesa", "Inglesa"),
    ("Iraniana", "Iraniana"),
    ("Irlandesa", "Irlandesa"),
    ("Israelense", "Israelense"),
    ("Italiana", "Italiana"),
    ("Japonesa", "Japonesa"),
    ("Libanesa", "Libanesa"),
    ("Marroquina", "Marroquina"),
    ("Mexicana", "Mexicana"),
    ("Moçambicana", "Moçambicana"),
    ("Norueguesa", "Norueguesa"),
    ("Paraguaia", "Paraguaia"),
    ("Peruana", "Peruana"),
    ("Polonesa", "Polonesa"),
    ("Portuguesa", "Portuguesa"),
    ("Russa", "Russa"),
    ("Sueca", "Sueca"),
    ("Suíça", "Suíça"),
    ("Sul-africana", "Sul-africana"),
    ("Uruguaia", "Uruguaia"),
    ("Venezuelana", "Venezuelana"),
    ("Outra", "Outra"),
]


class Cliente(models.Model):
    TIPO_CHOICES = [
        ("PF", "Pessoa Física"),
        ("PJ", "Pessoa Jurídica"),
    ]

    tipo = models.CharField(max_length=2, choices=TIPO_CHOICES, default="PF")
    nome_razao_social = models.CharField(max_length=255)
    nome_fantasia = models.CharField(max_length=255, blank=True, verbose_name="Nome fantasia")
    cpf_cnpj = models.CharField(max_length=18, blank=True)
    email = models.EmailField(blank=True)
    telefone = models.CharField(max_length=20, blank=True)

    # Brasileiro/Estrangeiro (reunião de 13/09) — documento, nacionalidade,
    # RG e a busca automática de endereço por CEP dependem deste flag. Em
    # Pessoa Jurídica significa "empresa estrangeira" (documento livre, sem CNPJ).
    estrangeiro = models.BooleanField(default=False, verbose_name="Estrangeiro")
    nacionalidade = models.CharField(
        max_length=100, choices=NACIONALIDADE_CHOICES, default="Brasileira", blank=True,
    )
    estado_civil = models.CharField(max_length=20, choices=ESTADO_CIVIL_CHOICES, blank=True)
    profissao = models.CharField(max_length=100, blank=True)
    rg = models.CharField(max_length=20, blank=True, verbose_name="RG")
    data_nascimento = models.DateField(
        null=True, blank=True, verbose_name="Data de nascimento",
        help_text="Só para Pessoa Física — usada para calcular a idade, nunca digitada diretamente.",
    )

    # Representante da Pessoa Jurídica (spec
    # clientes-formulario-pf-pj-representante) — dados de quem assina/
    # representa a empresa, sem criar um segundo Cliente nem usuário do
    # sistema. Um representante principal por cliente PJ, nesta versão.
    representante_nome = models.CharField(max_length=255, blank=True, verbose_name="Nome do representante")
    representante_cpf = models.CharField(max_length=14, blank=True, verbose_name="CPF do representante")
    representante_cargo = models.CharField(
        max_length=100, blank=True, verbose_name="Cargo/qualificação do representante",
    )
    representante_telefone = models.CharField(
        max_length=20, blank=True, verbose_name="Telefone do representante",
    )
    representante_email = models.EmailField(blank=True, verbose_name="E-mail do representante")

    # Endereço estruturado — substitui o antigo campo único `endereco`.
    cep = models.CharField(max_length=9, blank=True, verbose_name="CEP")
    logradouro = models.CharField(max_length=255, blank=True)
    numero = models.CharField(max_length=20, blank=True, verbose_name="Número")
    complemento = models.CharField(max_length=100, blank=True)
    bairro = models.CharField(max_length=100, blank=True)
    cidade = models.CharField(max_length=100, blank=True)
    estado = models.CharField(max_length=2, choices=UF_CHOICES, blank=True)

    observacoes = models.TextField(blank=True)
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="clientes_responsaveis",
        verbose_name="Responsável",
    )
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ["nome_razao_social"]

    def __str__(self):
        return self.nome_razao_social

    @property
    def idade(self):
        """Idade calculada a partir de `data_nascimento` — só para Pessoa
        Física; `None` para PJ ou sem data de nascimento preenchida."""
        if self.tipo != "PF" or not self.data_nascimento:
            return None
        hoje = timezone.localdate()
        nascimento = self.data_nascimento
        anos = hoje.year - nascimento.year
        if (hoje.month, hoje.day) < (nascimento.month, nascimento.day):
            anos -= 1
        return anos

    @property
    def selo_prioridade(self):
        """"idoso"/"menor_idade" (Estatuto do Idoso, ECA) ou `None` — só
        indicativo/visual, sem efeito em ordenação de fila ou prazo."""
        idade = self.idade
        if idade is None:
            return None
        if idade >= 60:
            return "idoso"
        if idade < 18:
            return "menor_idade"
        return None

    def iniciais(self):
        partes = self.nome_razao_social.split()
        if len(partes) >= 2:
            return f"{partes[0][0]}{partes[1][0]}".upper()
        return self.nome_razao_social[:2].upper()


class Documento(models.Model):
    """Arquivo anexado a um Cliente (RG/CNH, comprovante de residência,
    contrato social etc.) — mesmo padrão de storage protegido por tenant
    de `apps.processos.models.Documento`."""

    TIPO_CHOICES = [
        ("identificacao", "Documento de identificação"),
        ("comprovante_residencia", "Comprovante de residência"),
        ("contrato_social", "Contrato social"),
        ("procuracao", "Procuração"),
        ("outro", "Outro"),
    ]

    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="documentos")
    arquivo = models.FileField(
        upload_to=CaminhoArquivoTenant(PROTEGIDO, "clientes/documentos"),
        storage=StorageProtegido(),
    )
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES, default="outro")
    descricao = models.CharField(max_length=255, blank=True)
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="documentos_cliente_autor",
    )
    enviado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Documento"
        verbose_name_plural = "Documentos"
        ordering = ["-enviado_em"]

    def __str__(self):
        return f"{self.get_tipo_display()} — {nome_do_arquivo(self.arquivo)}"

    def nome_do_documento(self):
        return nome_do_arquivo(self.arquivo)
