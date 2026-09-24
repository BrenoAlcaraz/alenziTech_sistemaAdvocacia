from django.urls import path
from . import views, views_grupos

app_name = "financeiro"

urlpatterns = [
    path("financeiro/", views.index, name="index"),
    path("financeiro/grafico/", views.grafico, name="grafico"),
    path("financeiro/processos-por-cliente/", views.processos_por_cliente, name="processos_por_cliente"),
    path("financeiro/custas/", views.custas, name="custas"),
    path("financeiro/previa-ocorrencias/", views.previa_ocorrencias, name="previa_ocorrencias"),
    path("financeiro/lancamentos/novo/", views.form_lancamento, name="form_lancamento"),
    path("financeiro/lancamentos/<int:pk>/editar/", views.editar_lancamento, name="editar_lancamento"),
    path("financeiro/lancamentos/<int:pk>/marcar-pago/", views.marcar_pago, name="marcar_pago"),
    path("financeiro/lancamentos/<int:pk>/cancelar/", views.cancelar_lancamento, name="cancelar_lancamento"),
    path(
        "financeiro/lancamentos/<int:pk>/cancelar-recorrencia/",
        views.cancelar_recorrencia,
        name="cancelar_recorrencia",
    ),
    path("financeiro/lancamentos/<int:pk>/reabrir/", views.reabrir_lancamento, name="reabrir_lancamento"),
    path("financeiro/lancamentos/<int:pk>/excluir/", views.excluir_lancamento, name="excluir_lancamento"),
    path("financeiro/lancamentos/<int:pk>/anexo/", views.anexo_lancamento, name="anexo_lancamento"),
    path("financeiro/lancamentos/<int:pk>/anexar/", views.anexar_lancamento, name="anexar_lancamento"),
    path(
        "financeiro/lancamentos/<int:pk>/comprovante-pagamento/",
        views.comprovante_pagamento_lancamento,
        name="comprovante_pagamento_lancamento",
    ),
    path(
        "financeiro/lancamentos/<int:pk>/anexar-comprovante/",
        views.anexar_comprovante_lancamento,
        name="anexar_comprovante_lancamento",
    ),
    path("financeiro/custas/nova/", views.form_custa, name="form_custa"),
    path("financeiro/custas/<int:pk>/anexo/", views.anexo_custa, name="anexo_custa"),
    path("financeiro/custas/<int:pk>/reembolsar/", views.form_reembolsar_custa, name="form_reembolsar_custa"),
    path(
        "financeiro/custas/cliente/<int:cliente_id>/",
        views.extrato_custas_cliente,
        name="extrato_custas_cliente",
    ),
    path(
        "financeiro/custas/cliente/<int:cliente_id>/creditar/",
        views.form_creditar_custa,
        name="form_creditar_custa",
    ),
    path("financeiro/custas/aviso-saldo/", views_grupos.aviso_saldo_custa, name="aviso_saldo_custa"),
    path("financeiro/custas/grupo/novo/", views_grupos.novo_grupo, name="novo_grupo_custas"),
    path(
        "financeiro/custas/grupo/<int:grupo_id>/",
        views_grupos.extrato_custas_grupo,
        name="extrato_custas_grupo",
    ),
    path(
        "financeiro/custas/grupo/<int:grupo_id>/creditar/",
        views_grupos.form_creditar_custa_grupo,
        name="form_creditar_custa_grupo",
    ),
    path(
        "financeiro/custas/grupo/<int:grupo_id>/membros/adicionar/",
        views_grupos.adicionar_membro_grupo,
        name="adicionar_membro_grupo",
    ),
    path(
        "financeiro/custas/grupo/<int:grupo_id>/membros/<int:cliente_id>/remover/",
        views_grupos.remover_membro_grupo,
        name="remover_membro_grupo",
    ),
    path("financeiro/custas/grupo/<int:grupo_id>/apagar/", views_grupos.apagar_grupo, name="apagar_grupo"),
    path("financeiro/honorarios/", views.honorarios_lista, name="honorarios_lista"),
    path("financeiro/honorarios/novo/", views.form_honorario, name="form_honorario"),
    path("financeiro/honorarios/<int:pk>/editar/", views.editar_honorario, name="editar_honorario"),
    path(
        "financeiro/honorarios/<int:pk>/confirmar-recebimento/",
        views.confirmar_recebimento_honorario,
        name="confirmar_recebimento_honorario",
    ),
    path("financeiro/honorarios/<int:pk>/cancelar/", views.cancelar_honorario, name="cancelar_honorario"),
    path("financeiro/honorarios/<int:pk>/documento/", views.documento_honorario, name="documento_honorario"),
    path(
        "financeiro/honorarios/<int:pk>/regime/",
        views.definir_regime_honorario,
        name="definir_regime_honorario",
    ),
    path("financeiro/solicitacoes/", views.solicitacoes_lista, name="solicitacoes_lista"),
    path("financeiro/solicitacoes/nova/", views.form_solicitacao, name="form_solicitacao"),
    path("financeiro/solicitacoes/<int:pk>/editar/", views.editar_solicitacao, name="editar_solicitacao"),
    path("financeiro/solicitacoes/<int:pk>/", views.detalhe_solicitacao, name="detalhe_solicitacao"),
    path("financeiro/solicitacoes/<int:pk>/anexo/", views.anexo_solicitacao, name="anexo_solicitacao"),
    path(
        "financeiro/solicitacoes/<int:pk>/comprovante-pagamento/",
        views.comprovante_pagamento_solicitacao,
        name="comprovante_pagamento_solicitacao",
    ),
    path("financeiro/solicitacoes/<int:pk>/processar/", views.processar_solicitacao, name="processar_solicitacao"),
]
