from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from apps.accounts.permissoes import tem_habilitacao, tem_permissao_modulo
from apps.accounts.permissoes_constants import HAB_PROCESSOS_USAR_LABORATORIO, MODULO_PROCESSOS


@login_required
def index(request):
    if not tem_permissao_modulo(request.user, MODULO_PROCESSOS):
        raise PermissionDenied
    if not tem_habilitacao(request.user, MODULO_PROCESSOS, HAB_PROCESSOS_USAR_LABORATORIO):
        raise PermissionDenied
    # Futuramente: integrar com IA para geração de peças jurídicas.
    # Por ora apenas formulário visual e placeholder.
    return render(request, "laboratorio/index.html", {"item_ativo": "laboratorio"})
