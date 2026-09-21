# Papel de acesso como único mecanismo (PDR-0030): o Tipo de conta sai e os
# cinco presets de fábrica deixam de existir; de fábrica sobra só o papel
# "Limitado", com tudo desligado (sem linhas de PermissaoPapel/HabilitacaoPapel).
#
# Sistema fora de produção — sem migração de dados fina: as linhas legadas
# por tipo_conta e os presets antigos são apenas descartados. Usuários que
# estavam em um preset antigo passam ao Limitado para não ficarem sem papel.
# A remoção das colunas fica na migration seguinte (0034): DELETE e ALTER
# TABLE na mesma migration podem falhar com "pending trigger events".
#
# Rollback: RunPython.noop — não recria os presets nem as linhas legadas.

from django.db import migrations

CODIGOS_PRESETS_ANTIGOS = [
    "socio_gestor_nucleo",
    "advogado_associado",
    "estagiario_paralegal",
    "gestor_financeiro",
    "secretaria_recepcao",
]


def criar_limitado_e_remover_presets(apps, schema_editor):
    PapelAcesso = apps.get_model("accounts", "PapelAcesso")
    PermissaoPapel = apps.get_model("accounts", "PermissaoPapel")
    HabilitacaoPapel = apps.get_model("accounts", "HabilitacaoPapel")
    UsuarioPapel = apps.get_model("accounts", "UsuarioPapel")

    PermissaoPapel.objects.filter(tipo_conta__isnull=False).delete()
    HabilitacaoPapel.objects.filter(tipo_conta__isnull=False).delete()

    limitado = PapelAcesso.objects.filter(codigo_preset="limitado").first()
    if limitado is None:
        # Um papel personalizado com o mesmo nome é adotado, não duplicado.
        limitado = PapelAcesso.objects.filter(nome="Limitado").first()
    if limitado is None:
        limitado = PapelAcesso(
            nome="Limitado",
            descricao="Papel padrão de fábrica: nenhum módulo nem habilitação liberados.",
        )
    limitado.codigo_preset = "limitado"
    limitado.protegido_sistema = True
    limitado.ativo = True
    limitado.save()

    antigos = PapelAcesso.objects.filter(codigo_preset__in=CODIGOS_PRESETS_ANTIGOS)
    for vinculo in UsuarioPapel.objects.filter(papel__in=antigos, ativo=True):
        UsuarioPapel.objects.get_or_create(
            usuario_id=vinculo.usuario_id,
            papel=limitado,
            defaults={"ativo": True},
        )
    UsuarioPapel.objects.filter(papel__in=antigos).delete()
    PermissaoPapel.objects.filter(papel__in=antigos).delete()
    HabilitacaoPapel.objects.filter(papel__in=antigos).delete()
    antigos.delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0032_remove_equipe_vinculada_vinculo_integrante"),
    ]

    operations = [
        migrations.RunPython(
            criar_limitado_e_remover_presets,
            migrations.RunPython.noop,
        ),
    ]
