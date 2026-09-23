from django.db import migrations


TAREFAS = "tarefas"
AGENDA = "agenda"
HAB_TAREFAS = "tarefas_atribuir_outros"
HAB_AGENDA_ANTIGA = "agenda_criar_para_outros"
HAB_AGENDA = "agenda_atribuir_outros"
ORDEM_NIVEL = ["somente_seus", "todos"]


def _maior_nivel(niveis):
    return max(niveis, key=lambda n: ORDEM_NIVEL.index(n) if n in ORDEM_NIVEL else -1)


def _combinar(*permissoes):
    """União de acessos (ativo, nivel): acesso se algum tem; maior nível
    entre os que têm."""
    niveis = [nivel for ativo, nivel in permissoes if ativo]
    if niveis:
        return (True, _maior_nivel(niveis))
    return (False, None)


class _Estado:
    """Foto das permissões para reproduzir, sem o kernel de runtime, a
    resolução de `apps/accounts/permissoes.py` (override individual →
    união dos papéis ativos; habilitação só com o módulo aberto)."""

    def __init__(self, apps, papeis_por_usuario):
        PermissaoPapel = apps.get_model("accounts", "PermissaoPapel")
        PermissaoUsuario = apps.get_model("accounts", "PermissaoUsuario")
        HabilitacaoPapel = apps.get_model("accounts", "HabilitacaoPapel")
        HabilitacaoUsuario = apps.get_model("accounts", "HabilitacaoUsuario")
        self.papeis_por_usuario = papeis_por_usuario
        self.pp = {(p.papel_id, p.modulo): (p.ativo, p.nivel) for p in PermissaoPapel.objects.all()}
        self.pu = {(p.usuario_id, p.modulo): (p.ativo, p.nivel) for p in PermissaoUsuario.objects.all()}
        self.hp = {(h.papel_id, h.modulo, h.item): h.ativo for h in HabilitacaoPapel.objects.all()}
        self.hu = {(h.usuario_id, h.modulo, h.item): h.ativo for h in HabilitacaoUsuario.objects.all()}

    def permissao(self, usuario_id, modulo):
        if (usuario_id, modulo) in self.pu:
            ativo, nivel = self.pu[(usuario_id, modulo)]
            return (ativo, nivel) if ativo else (False, None)
        return _combinar(*[
            self.pp[(papel_id, modulo)]
            for papel_id in self.papeis_por_usuario.get(usuario_id, [])
            if (papel_id, modulo) in self.pp
        ])

    def habilitacao(self, usuario_id, modulo, item):
        if not self.permissao(usuario_id, modulo)[0]:
            return False
        if (usuario_id, modulo, item) in self.hu:
            return self.hu[(usuario_id, modulo, item)]
        return any(
            self.hp.get((papel_id, modulo, item), False)
            for papel_id in self.papeis_por_usuario.get(usuario_id, [])
        )


def _unificar_papeis(apps):
    PermissaoPapel = apps.get_model("accounts", "PermissaoPapel")
    HabilitacaoPapel = apps.get_model("accounts", "HabilitacaoPapel")

    for tarefas in PermissaoPapel.objects.filter(modulo=TAREFAS):
        agenda = PermissaoPapel.objects.filter(papel_id=tarefas.papel_id, modulo=AGENDA).first()
        if agenda is None:
            tarefas.modulo = AGENDA
            tarefas.save(update_fields=["modulo"])
            continue
        linhas = [(tarefas.ativo, tarefas.nivel), (agenda.ativo, agenda.nivel)]
        ativo, nivel = _combinar(*linhas)
        agenda.ativo = ativo
        agenda.nivel = nivel if ativo else min(
            (n for _, n in linhas), key=lambda n: ORDEM_NIVEL.index(n) if n in ORDEM_NIVEL else 99
        )
        agenda.save(update_fields=["ativo", "nivel"])
        tarefas.delete()

    antigas = HabilitacaoPapel.objects.filter(item__in=[HAB_TAREFAS, HAB_AGENDA_ANTIGA])
    for papel_id in set(antigas.values_list("papel_id", flat=True)):
        do_papel = list(antigas.filter(papel_id=papel_id))
        manter, excedentes = do_papel[0], do_papel[1:]
        manter.modulo = AGENDA
        manter.item = HAB_AGENDA
        manter.ativo = any(h.ativo for h in do_papel)
        manter.save(update_fields=["modulo", "item", "ativo"])
        for h in excedentes:
            h.delete()


def migrar_permissoes(apps, schema_editor):
    """Módulo `tarefas` some; `agenda` passa a dar a união dos dois
    acessos (maior nível e união das habilitações — PDR-0034). Papéis são
    unificados; override individual é gravado onde o usuário já tinha
    override ou onde o papel unificado não reproduz o acesso anterior."""
    User = apps.get_model("auth", "User")
    UsuarioPapel = apps.get_model("accounts", "UsuarioPapel")
    PermissaoUsuario = apps.get_model("accounts", "PermissaoUsuario")
    HabilitacaoUsuario = apps.get_model("accounts", "HabilitacaoUsuario")

    papeis_por_usuario = {}
    for up in UsuarioPapel.objects.filter(ativo=True, papel__ativo=True):
        papeis_por_usuario.setdefault(up.usuario_id, []).append(up.papel_id)

    usuarios = list(
        User.objects.exclude(perfil__is_admin_escritorio=True).values_list("pk", flat=True)
    )
    antes = _Estado(apps, papeis_por_usuario)
    desejado = {
        u: (
            _combinar(antes.permissao(u, TAREFAS), antes.permissao(u, AGENDA)),
            antes.habilitacao(u, TAREFAS, HAB_TAREFAS) or antes.habilitacao(u, AGENDA, HAB_AGENDA_ANTIGA),
        )
        for u in usuarios
    }
    com_override_perm = {u for (u, modulo) in antes.pu if modulo in (TAREFAS, AGENDA)}
    com_override_hab = {u for (u, _, item) in antes.hu if item in (HAB_TAREFAS, HAB_AGENDA_ANTIGA)}

    _unificar_papeis(apps)
    PermissaoUsuario.objects.filter(modulo__in=[TAREFAS, AGENDA]).delete()
    HabilitacaoUsuario.objects.filter(item__in=[HAB_TAREFAS, HAB_AGENDA_ANTIGA]).delete()

    depois = _Estado(apps, papeis_por_usuario)
    for u in usuarios:
        permissao, habilitacao = desejado[u]
        if u in com_override_perm or depois.permissao(u, AGENDA) != permissao:
            ativo, nivel = permissao
            PermissaoUsuario.objects.create(
                usuario_id=u, modulo=AGENDA, ativo=ativo, nivel=nivel or "somente_seus"
            )
            depois.pu[(u, AGENDA)] = (ativo, nivel or "somente_seus")
        if u in com_override_hab or depois.habilitacao(u, AGENDA, HAB_AGENDA) != habilitacao:
            HabilitacaoUsuario.objects.create(
                usuario_id=u, modulo=AGENDA, item=HAB_AGENDA, ativo=habilitacao
            )


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_modulo_agenda_unificado'),
    ]

    operations = [
        migrations.RunPython(migrar_permissoes, migrations.RunPython.noop),
    ]
