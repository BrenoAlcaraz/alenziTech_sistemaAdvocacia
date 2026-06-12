from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def index(request):
    # Futuramente: integrar com IA para geração de peças jurídicas.
    # Por ora apenas formulário visual e placeholder.
    return render(request, "laboratorio/index.html", {"item_ativo": "laboratorio"})
