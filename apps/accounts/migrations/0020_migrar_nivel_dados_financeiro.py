# Passo 2/3 — ver 0019_ampliar_nivel_financeiro_dados.py.
#
# Todo usuário/papel hoje configurado com acesso total ao caixa geral
# do Financeiro ("dados") passa para "dados_todos" — preserva
# exatamente o acesso já concedido; ninguém perde visibilidade sobre
# lançamentos que já podia ver/editar.

from django.db import migrations


def migrar_dados_para_dados_todos(apps, schema_editor):
    PermissaoPapel = apps.get_model("accounts", "PermissaoPapel")
    PermissaoUsuario = apps.get_model("accounts", "PermissaoUsuario")

    PermissaoPapel.objects.filter(modulo="financeiro", nivel="dados").update(nivel="dados_todos")
    PermissaoUsuario.objects.filter(modulo="financeiro", nivel="dados").update(nivel="dados_todos")


def reverter_dados_todos_para_dados(apps, schema_editor):
    PermissaoPapel = apps.get_model("accounts", "PermissaoPapel")
    PermissaoUsuario = apps.get_model("accounts", "PermissaoUsuario")

    PermissaoPapel.objects.filter(modulo="financeiro", nivel="dados_todos").update(nivel="dados")
    PermissaoUsuario.objects.filter(modulo="financeiro", nivel="dados_todos").update(nivel="dados")


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0019_ampliar_nivel_financeiro_dados"),
    ]

    operations = [
        migrations.RunPython(
            migrar_dados_para_dados_todos,
            reverter_dados_todos_para_dados,
        ),
    ]
