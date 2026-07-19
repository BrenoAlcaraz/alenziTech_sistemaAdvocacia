from django.db import migrations


PERMISSOES_DEFAULTS = [
    # (tipo_conta, modulo, ativo, nivel)

    # ── Limitado ───────────────────────────────────────────────────────────────
    ("limitado", "processos", True,  "somente_seus"),
    ("limitado", "clientes",  True,  "somente_seus"),
    ("limitado", "financeiro", False, "solicitacoes"),
    ("limitado", "tarefas",   True,  "somente_seus"),
    ("limitado", "modelos",   True,  "somente_seus"),
    ("limitado", "chat",      True,  ""),
    ("limitado", "painel",    True,  "somente_seus"),
    ("limitado", "agenda",    True,  "somente_seus"),
    ("limitado", "gerir",     False, ""),

    # ── Financeiro ─────────────────────────────────────────────────────────────
    ("financeiro", "processos",  False, "somente_seus"),
    ("financeiro", "clientes",   True,  "todos"),
    ("financeiro", "financeiro", True,  "dados"),
    ("financeiro", "tarefas",    True,  "somente_seus"),
    ("financeiro", "modelos",    False, "somente_seus"),
    ("financeiro", "chat",       True,  ""),
    ("financeiro", "painel",     True,  "todos"),
    ("financeiro", "agenda",     True,  "somente_seus"),
    ("financeiro", "gerir",      False, ""),
]


HABILITACOES_DEFAULTS = [
    # (tipo_conta, modulo, item, ativo)

    # ── Limitado — Processos ───────────────────────────────────────────────────
    ("limitado", "processos", "processos_criar",               True),
    ("limitado", "processos", "processos_editar",              True),
    ("limitado", "processos", "processos_andamento_adicionar", True),
    ("limitado", "processos", "processos_usar_ia",             True),
    ("limitado", "processos", "processos_usar_laboratorio",    True),

    # ── Limitado — Clientes ────────────────────────────────────────────────────
    ("limitado", "clientes", "clientes_criar",  True),
    ("limitado", "clientes", "clientes_editar", True),

    # ── Limitado — Tarefas ─────────────────────────────────────────────────────
    ("limitado", "tarefas", "tarefas_atribuir_outros", False),

    # ── Limitado — Modelos ─────────────────────────────────────────────────────
    ("limitado", "modelos", "modelos_criar",        False),
    ("limitado", "modelos", "modelos_editar_estilo", True),

    # ── Limitado — Agenda ──────────────────────────────────────────────────────
    ("limitado", "agenda", "agenda_criar_para_outros", False),

    # ── Limitado — Gerir ───────────────────────────────────────────────────────
    ("limitado", "gerir", "gerir_criar_usuario",              False),
    ("limitado", "gerir", "gerir_habilitar_usuario_processos", False),
    ("limitado", "gerir", "gerir_criar_equipe",               False),
    ("limitado", "gerir", "gerir_habilitar_terceiros",        False),

    # ── Financeiro — Processos ─────────────────────────────────────────────────
    ("financeiro", "processos", "processos_criar",               False),
    ("financeiro", "processos", "processos_editar",              False),
    ("financeiro", "processos", "processos_andamento_adicionar", False),
    ("financeiro", "processos", "processos_usar_ia",             False),
    ("financeiro", "processos", "processos_usar_laboratorio",    False),

    # ── Financeiro — Clientes ──────────────────────────────────────────────────
    ("financeiro", "clientes", "clientes_criar",  False),
    ("financeiro", "clientes", "clientes_editar", False),

    # ── Financeiro — Tarefas ───────────────────────────────────────────────────
    ("financeiro", "tarefas", "tarefas_atribuir_outros", False),

    # ── Financeiro — Modelos ───────────────────────────────────────────────────
    ("financeiro", "modelos", "modelos_criar",        False),
    ("financeiro", "modelos", "modelos_editar_estilo", False),

    # ── Financeiro — Agenda ────────────────────────────────────────────────────
    ("financeiro", "agenda", "agenda_criar_para_outros", False),

    # ── Financeiro — Gerir ─────────────────────────────────────────────────────
    ("financeiro", "gerir", "gerir_criar_usuario",              False),
    ("financeiro", "gerir", "gerir_habilitar_usuario_processos", False),
    ("financeiro", "gerir", "gerir_criar_equipe",               False),
    ("financeiro", "gerir", "gerir_habilitar_terceiros",        False),
]


def seed_permissoes_habilitacoes(apps, schema_editor):
    PermissaoPapel = apps.get_model("accounts", "PermissaoPapel")
    HabilitacaoPapel = apps.get_model("accounts", "HabilitacaoPapel")

    for tipo_conta, modulo, ativo, nivel in PERMISSOES_DEFAULTS:
        PermissaoPapel.objects.update_or_create(
            tipo_conta=tipo_conta,
            modulo=modulo,
            defaults={"ativo": ativo, "nivel": nivel},
        )

    for tipo_conta, modulo, item, ativo in HABILITACOES_DEFAULTS:
        HabilitacaoPapel.objects.update_or_create(
            tipo_conta=tipo_conta,
            modulo=modulo,
            item=item,
            defaults={"ativo": ativo},
        )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0007_permissoes_habilitacoes"),
    ]

    operations = [
        migrations.RunPython(
            seed_permissoes_habilitacoes,
            migrations.RunPython.noop,
        ),
    ]
