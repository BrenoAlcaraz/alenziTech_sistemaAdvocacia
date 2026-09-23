"""
Convite de delegação (PDR-0033): decide se delegar um item da Agenda
Jurídica a outro usuário exige convite (aceitar/recusar) ou é direta, e
cria/responde esse convite.

Não confundir com a confirmação de presença de participante de
Evento (PDR-0020) — conceito separado, que este módulo não altera.
"""

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied

from apps.accounts.decorators import usuario_admin_escritorio
from apps.accounts.escopo import equipes_gerenciadas_pelo_usuario
from apps.accounts.models import ConviteDelegacao, MembroEquipe


def delegacao_exige_convite(delegante, destinatario):
    """
    Retorna True se delegar de `delegante` para `destinatario` exige
    convite; False se a delegação pode ser direta (sem convite).

    Direta (sem convite):
    - `delegante` é Administrador do escritório;
    - `delegante` é gerente ativo de uma Equipe da qual `destinatario` é
      membro ativo e **não-gerente** dessa mesma Equipe.

    Convite obrigatório em qualquer outro caso — inclusive gerente
    delegando para outro gerente da mesma Equipe.
    """
    if usuario_admin_escritorio(delegante):
        return False

    equipes_geridas = equipes_gerenciadas_pelo_usuario(delegante)
    subordinado_direto = MembroEquipe.objects.filter(
        usuario=destinatario,
        equipe__in=equipes_geridas,
        ativo=True,
        equipe__ativo=True,
        eh_gerente=False,
    ).exists()

    return not subordinado_direto


def criar_convite_delegacao(delegante, destinatario, item):
    """Cria e retorna um ConviteDelegacao pendente para `item`
    (item da agenda), sem checar aqui se o convite era necessário —
    a decisão é de quem chama, via `delegacao_exige_convite`."""
    return ConviteDelegacao.objects.create(
        delegante=delegante,
        destinatario=destinatario,
        content_type=ContentType.objects.get_for_model(item),
        object_id=item.pk,
    )


def aceitar_convite(convite, usuario):
    """Aceita `convite` em nome de `usuario` — só o próprio destinatário
    pode responder ao convite, sem checagem de habilitação adicional
    (mesmo princípio da confirmação de presença de participante da
    Agenda, PDR-0020)."""
    _validar_destinatario(convite, usuario)
    convite.aceitar()
    return convite


def recusar_convite(convite, usuario, justificativa=""):
    """Recusa `convite` em nome de `usuario`, com justificativa opcional.
    Só o próprio destinatário pode responder ao convite."""
    _validar_destinatario(convite, usuario)
    convite.recusar(justificativa=justificativa)
    return convite


def _validar_destinatario(convite, usuario):
    if not usuario or usuario.pk != convite.destinatario_id:
        raise PermissionDenied("Só o destinatário do convite pode respondê-lo.")
