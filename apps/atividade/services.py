from .models import LogAtividade


def registrar_atividade(usuario, tipo, descricao, *, processo=None):
    """
    Ponto único de escrita do log de atividade. Chamado explicitamente
    em cada ação relevante (nunca via signal genérico de post_save) —
    a descrição legível exige o contexto que só a view tem no momento
    da ação. Participa da transação corrente: se a gravação falhar, a
    ação inteira falha (sem caminho paralelo silencioso).
    """
    return LogAtividade.objects.create(
        usuario=usuario, tipo=tipo, descricao=descricao, processo=processo
    )
