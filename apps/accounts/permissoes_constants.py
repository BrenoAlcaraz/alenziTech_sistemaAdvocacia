# Constantes de permissões e habilitações por tipo de conta.
#
# Este arquivo não importa models Django nem qualquer módulo que importe models.
# Pode ser importado com segurança de models.py sem risco de importação circular.

# ── Tipos de conta ─────────────────────────────────────────────────────────────

TIPO_CONTA_ADMINISTRADOR = "administrador_escritorio"
TIPO_CONTA_LIMITADO = "limitado"
TIPO_CONTA_FINANCEIRO = "financeiro"

# Administrador não aparece aqui — não possui registros editáveis de permissão.
TIPOS_CONTA_CONFIGURAVEIS = [
    TIPO_CONTA_LIMITADO,
    TIPO_CONTA_FINANCEIRO,
]

TIPOS_CONTA_CHOICES = [
    (TIPO_CONTA_LIMITADO, "Limitado"),
    (TIPO_CONTA_FINANCEIRO, "Financeiro"),
]

# ── Módulos ────────────────────────────────────────────────────────────────────

MODULO_PROCESSOS = "processos"
MODULO_CLIENTES = "clientes"
MODULO_FINANCEIRO = "financeiro"
MODULO_TAREFAS = "tarefas"
MODULO_MODELOS = "modelos"
MODULO_CHAT = "chat"
MODULO_PAINEL = "painel"
MODULO_AGENDA = "agenda"
MODULO_GERIR = "gerir"

MODULO_CHOICES = [
    (MODULO_PROCESSOS, "Processos"),
    (MODULO_CLIENTES, "Clientes"),
    (MODULO_FINANCEIRO, "Financeiro"),
    (MODULO_TAREFAS, "Tarefas"),
    (MODULO_MODELOS, "Modelos de peças"),
    (MODULO_CHAT, "Chat"),
    (MODULO_PAINEL, "Painel"),
    (MODULO_AGENDA, "Agenda"),
    (MODULO_GERIR, "Gerir"),
]

# Módulos que possuem itens de habilitação nesta versão.
# Financeiro, Chat e Painel foram deliberadamente avaliados e não têm itens.
MODULO_HABILITACAO_CHOICES = [
    (MODULO_PROCESSOS, "Processos"),
    (MODULO_CLIENTES, "Clientes"),
    (MODULO_TAREFAS, "Tarefas"),
    (MODULO_MODELOS, "Modelos de peças"),
    (MODULO_AGENDA, "Agenda"),
    (MODULO_GERIR, "Gerir"),
]

# ── Níveis ─────────────────────────────────────────────────────────────────────

NIVEL_SOMENTE_SEUS = "somente_seus"
NIVEL_TODOS = "todos"
NIVEL_SOLICITACOES = "solicitacoes"
NIVEL_DADOS = "dados"

NIVEL_CHOICES = [
    (NIVEL_SOMENTE_SEUS, "Somente os seus"),
    (NIVEL_TODOS, "Todos"),
    (NIVEL_SOLICITACOES, "Apenas solicitações"),
    (NIVEL_DADOS, "Acesso a dados"),
]

# nivel vazio ("") é válido para chat e gerir — não incluso em NIVEL_CHOICES
# porque CharField com blank=True já permite string vazia sem aparecer nas choices.

NIVEIS_POR_MODULO = {
    MODULO_PROCESSOS: [NIVEL_SOMENTE_SEUS, NIVEL_TODOS],
    MODULO_CLIENTES: [NIVEL_SOMENTE_SEUS, NIVEL_TODOS],
    MODULO_TAREFAS: [NIVEL_SOMENTE_SEUS, NIVEL_TODOS],
    MODULO_MODELOS: [NIVEL_SOMENTE_SEUS, NIVEL_TODOS],
    MODULO_PAINEL: [NIVEL_SOMENTE_SEUS, NIVEL_TODOS],
    MODULO_AGENDA: [NIVEL_SOMENTE_SEUS, NIVEL_TODOS],
    MODULO_FINANCEIRO: [NIVEL_SOLICITACOES, NIVEL_DADOS],
    MODULO_CHAT: [""],
    MODULO_GERIR: [""],
}

# ── Habilitações — slugs ───────────────────────────────────────────────────────

HAB_PROCESSOS_CRIAR = "processos_criar"
HAB_PROCESSOS_EDITAR = "processos_editar"
HAB_PROCESSOS_ANDAMENTO_ADICIONAR = "processos_andamento_adicionar"
HAB_PROCESSOS_USAR_IA = "processos_usar_ia"
HAB_PROCESSOS_USAR_LABORATORIO = "processos_usar_laboratorio"

HAB_CLIENTES_CRIAR = "clientes_criar"
HAB_CLIENTES_EDITAR = "clientes_editar"

HAB_TAREFAS_ATRIBUIR_OUTROS = "tarefas_atribuir_outros"

HAB_MODELOS_CRIAR = "modelos_criar"
HAB_MODELOS_EDITAR_ESTILO = "modelos_editar_estilo"

HAB_AGENDA_CRIAR_PARA_OUTROS = "agenda_criar_para_outros"

HAB_GERIR_CRIAR_USUARIO = "gerir_criar_usuario"
HAB_GERIR_HABILITAR_USUARIO_PROCESSOS = "gerir_habilitar_usuario_processos"
HAB_GERIR_CRIAR_EQUIPE = "gerir_criar_equipe"
HAB_GERIR_HABILITAR_TERCEIROS = "gerir_habilitar_terceiros"

ITEM_CHOICES = [
    (HAB_PROCESSOS_CRIAR, "Criar processo"),
    (HAB_PROCESSOS_EDITAR, "Editar processo"),
    (HAB_PROCESSOS_ANDAMENTO_ADICIONAR, "Adicionar andamento"),
    (HAB_PROCESSOS_USAR_IA, "Usar assistência de IA"),
    (HAB_PROCESSOS_USAR_LABORATORIO, "Usar Laboratório Jurídico"),
    (HAB_CLIENTES_CRIAR, "Criar cliente"),
    (HAB_CLIENTES_EDITAR, "Editar cliente"),
    (HAB_TAREFAS_ATRIBUIR_OUTROS, "Atribuir tarefa a outros usuários"),
    (HAB_MODELOS_CRIAR, "Criar modelo de peça"),
    (HAB_MODELOS_EDITAR_ESTILO, "Editar estilo de peças"),
    (HAB_AGENDA_CRIAR_PARA_OUTROS, "Criar compromisso para outros usuários"),
    (HAB_GERIR_CRIAR_USUARIO, "Criar usuário"),
    (HAB_GERIR_HABILITAR_USUARIO_PROCESSOS, "Habilitar usuário em processos"),
    (HAB_GERIR_CRIAR_EQUIPE, "Criar equipe"),
    (HAB_GERIR_HABILITAR_TERCEIROS, "Habilitar terceiros"),
]

ITENS_POR_MODULO = {
    MODULO_PROCESSOS: [
        HAB_PROCESSOS_CRIAR,
        HAB_PROCESSOS_EDITAR,
        HAB_PROCESSOS_ANDAMENTO_ADICIONAR,
        HAB_PROCESSOS_USAR_IA,
        HAB_PROCESSOS_USAR_LABORATORIO,
    ],
    MODULO_CLIENTES: [
        HAB_CLIENTES_CRIAR,
        HAB_CLIENTES_EDITAR,
    ],
    MODULO_TAREFAS: [
        HAB_TAREFAS_ATRIBUIR_OUTROS,
    ],
    MODULO_MODELOS: [
        HAB_MODELOS_CRIAR,
        HAB_MODELOS_EDITAR_ESTILO,
    ],
    MODULO_AGENDA: [
        HAB_AGENDA_CRIAR_PARA_OUTROS,
    ],
    MODULO_GERIR: [
        HAB_GERIR_CRIAR_USUARIO,
        HAB_GERIR_HABILITAR_USUARIO_PROCESSOS,
        HAB_GERIR_CRIAR_EQUIPE,
        HAB_GERIR_HABILITAR_TERCEIROS,
    ],
    # sem habilitações nesta versão
    MODULO_FINANCEIRO: [],
    MODULO_CHAT: [],
    MODULO_PAINEL: [],
}

# ── Nomes legíveis — uso futuro em telas e helpers ────────────────────────────

NOMES_MODULOS = {
    MODULO_PROCESSOS: "Processos",
    MODULO_CLIENTES: "Clientes",
    MODULO_FINANCEIRO: "Financeiro",
    MODULO_TAREFAS: "Tarefas",
    MODULO_MODELOS: "Modelos de peças",
    MODULO_CHAT: "Chat",
    MODULO_PAINEL: "Painel",
    MODULO_AGENDA: "Agenda",
    MODULO_GERIR: "Gerir",
}

NOMES_NIVEIS = {
    NIVEL_SOMENTE_SEUS: "Somente os seus",
    NIVEL_TODOS: "Todos",
    NIVEL_SOLICITACOES: "Apenas solicitações",
    NIVEL_DADOS: "Acesso a dados",
}

NOMES_ITENS = {
    HAB_PROCESSOS_CRIAR: "Criar processo",
    HAB_PROCESSOS_EDITAR: "Editar processo",
    HAB_PROCESSOS_ANDAMENTO_ADICIONAR: "Adicionar andamento",
    HAB_PROCESSOS_USAR_IA: "Usar assistência de IA",
    HAB_PROCESSOS_USAR_LABORATORIO: "Usar Laboratório Jurídico",
    HAB_CLIENTES_CRIAR: "Criar cliente",
    HAB_CLIENTES_EDITAR: "Editar cliente",
    HAB_TAREFAS_ATRIBUIR_OUTROS: "Atribuir tarefa a outros usuários",
    HAB_MODELOS_CRIAR: "Criar modelo de peça",
    HAB_MODELOS_EDITAR_ESTILO: "Editar estilo de peças",
    HAB_AGENDA_CRIAR_PARA_OUTROS: "Criar compromisso para outros usuários",
    HAB_GERIR_CRIAR_USUARIO: "Criar usuário",
    HAB_GERIR_HABILITAR_USUARIO_PROCESSOS: "Habilitar usuário em processos",
    HAB_GERIR_CRIAR_EQUIPE: "Criar equipe",
    HAB_GERIR_HABILITAR_TERCEIROS: "Habilitar terceiros",
}
