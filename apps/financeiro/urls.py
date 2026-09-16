from django.urls import path
from . import views

app_name = "financeiro"

urlpatterns = [
    path("financeiro/", views.index, name="index"),
    path("financeiro/grafico/", views.grafico, name="grafico"),
    path("financeiro/processos-por-cliente/", views.processos_por_cliente, name="processos_por_cliente"),
    path("financeiro/custas/", views.custas, name="custas"),
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
    path("financeiro/custas/nova/", views.form_custa, name="form_custa"),
    path("financeiro/custas/<int:pk>/anexo/", views.anexo_custa, name="anexo_custa"),
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
    path("financeiro/honorarios/", views.honorarios_lista, name="honorarios_lista"),
    path("financeiro/honorarios/novo/", views.form_honorario, name="form_honorario"),
    path("financeiro/honorarios/<int:pk>/editar/", views.editar_honorario, name="editar_honorario"),
    path(
        "financeiro/honorarios/<int:pk>/confirmar-recebimento/",
        views.confirmar_recebimento_honorario,
        name="confirmar_recebimento_honorario",
    ),
    path("financeiro/honorarios/<int:pk>/cancelar/", views.cancelar_honorario, name="cancelar_honorario"),
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
