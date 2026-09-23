from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.urls import reverse


@login_required
def index(request):
    # Rota antiga preservada para favoritos: o Laboratório virou aba de
    # Processos, que aplica módulo + habilitação na view de destino.
    return redirect(reverse("processos:lista") + "?aba=laboratorio")
