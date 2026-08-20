import re

from django.db import migrations


def _documento(valor):
    return re.sub(r"\D", "", valor or "")


def migrar_partes_legadas(apps, schema_editor):
    ParteProcesso = apps.get_model("processos", "ParteProcesso")
    Processo = apps.get_model("processos", "Processo")
    RepresentanteParte = apps.get_model("processos", "RepresentanteParte")

    processos = {
        processo.pk: processo
        for processo in Processo.objects.select_related("cliente", "responsavel")
    }
    candidatas_por_processo = {processo_id: [] for processo_id in processos}
    for parte in ParteProcesso.objects.only(
        "pk",
        "processo_id",
        "cpf_cnpj",
    ):
        processo = processos.get(parte.processo_id)
        if processo is None or not processo.cliente_id:
            continue
        documento_cliente = _documento(processo.cliente.cpf_cnpj)
        documento_parte = _documento(parte.cpf_cnpj)
        if documento_cliente and documento_parte == documento_cliente:
            candidatas_por_processo[parte.processo_id].append(parte.pk)

    # Documento não é identidade global. Somente uma correspondência
    # objetivamente única dentro do próprio Processo pode reaproveitar a linha
    # histórica; em 0 ou N candidatas, o Cliente receberá nova Parte pendente.
    candidata_unica_por_processo = {
        processo_id: candidatas[0]
        for processo_id, candidatas in candidatas_por_processo.items()
        if len(candidatas) == 1
    }

    for parte in ParteProcesso.objects.select_related("processo__cliente").order_by("pk"):
        tipo = parte.tipo_legado
        cliente_processo = parte.processo.cliente
        vincular_cliente = (
            cliente_processo is not None
            and tipo in {"autor", "reu", "terceiro"}
            and candidata_unica_por_processo.get(parte.processo_id) == parte.pk
        )

        if tipo == "autor":
            parte.posicao = "polo_ativo"
            parte.qualificacao = "autor"
            parte.vinculo_escritorio = "cliente" if vincular_cliente else "outro"
        elif tipo == "reu":
            parte.posicao = "polo_passivo"
            parte.qualificacao = "reu"
            parte.vinculo_escritorio = (
                "cliente" if vincular_cliente else "parte_contraria"
            )
        elif tipo == "terceiro":
            parte.posicao = "terceiro"
            parte.qualificacao = "terceiro_interessado"
            parte.vinculo_escritorio = "cliente" if vincular_cliente else "outro"
        else:
            # advogado_contrario (ou qualquer valor histórico inesperado) não
            # possui relação objetiva com uma parte. A linha é preservada como
            # participante legado, sem inferir representação.
            parte.posicao = "legado"
            parte.qualificacao = "advogado_contrario_legado"
            parte.vinculo_escritorio = "legado"
            parte.registro_legado = True

        if vincular_cliente:
            parte.cliente_id = cliente_processo.pk

        parte.save(
            update_fields=[
                "cliente",
                "vinculo_escritorio",
                "posicao",
                "qualificacao",
                "registro_legado",
            ]
        )

    for processo in processos.values():
        if not processo.cliente_id:
            continue
        participante = ParteProcesso.objects.filter(
            processo_id=processo.pk,
            cliente_id=processo.cliente_id,
        ).first()
        if participante is None:
            participante = ParteProcesso.objects.create(
                processo_id=processo.pk,
                cliente_id=processo.cliente_id,
                nome="",
                cpf_cnpj="",
                vinculo_escritorio="cliente",
                posicao=None,
                qualificacao=None,
                atuacao_ministerio_publico="",
                tipo_legado="",
                registro_legado=False,
                classificacao_pendente=True,
            )
        RepresentanteParte.objects.get_or_create(
            parte_id=participante.pk,
            tipo="interno",
            usuario_id=processo.responsavel_id,
            defaults={
                "nome_externo": "",
                "oab": "",
                "uf_oab": "",
                "telefone": "",
                "email": "",
                "fingerprint_externo": "",
            },
        )


def desfazer_mapeamento(apps, schema_editor):
    ParteProcesso = apps.get_model("processos", "ParteProcesso")
    # Linhas sem tipo legado foram criadas por esta migration e não existiam em
    # 0006; removê-las no reverse restaura exatamente o estado anterior.
    ParteProcesso.objects.filter(tipo_legado="").delete()
    ParteProcesso.objects.update(
        cliente=None,
        vinculo_escritorio=None,
        posicao=None,
        qualificacao=None,
        atuacao_ministerio_publico="",
        registro_legado=False,
        classificacao_pendente=False,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("processos", "0007_participantes_representantes_schema"),
    ]

    operations = [
        migrations.RunPython(migrar_partes_legadas, desfazer_mapeamento),
    ]
