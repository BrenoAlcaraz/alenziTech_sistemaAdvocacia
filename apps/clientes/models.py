from django.conf import settings
from django.db import models


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
    cpf_cnpj = models.CharField(max_length=18, blank=True)
    email = models.EmailField(blank=True)
    telefone = models.CharField(max_length=20, blank=True)

    # Brasileiro/Estrangeiro (reunião de 13/09) — documento, nacionalidade,
    # RG e a busca automática de endereço por CEP dependem deste flag.
    estrangeiro = models.BooleanField(default=False, verbose_name="Estrangeiro")
    nacionalidade = models.CharField(
        max_length=100, choices=NACIONALIDADE_CHOICES, default="Brasileira", blank=True,
    )
    estado_civil = models.CharField(max_length=20, choices=ESTADO_CIVIL_CHOICES, blank=True)
    profissao = models.CharField(max_length=100, blank=True)
    rg = models.CharField(max_length=20, blank=True, verbose_name="RG")

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

    def iniciais(self):
        partes = self.nome_razao_social.split()
        if len(partes) >= 2:
            return f"{partes[0][0]}{partes[1][0]}".upper()
        return self.nome_razao_social[:2].upper()
