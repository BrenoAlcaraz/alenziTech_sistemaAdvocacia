from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# Dados temporários apenas para layout — substituir futuramente por queries reais
# Dias com compromissos no mês de junho/2026 (para marcar pontos no calendário)
COMPROMISSOS_JUNHO = {
    6:  [{"tipo": "audiencia"}, {"tipo": "reuniao"}],
    8:  [{"tipo": "audiencia"}, {"tipo": "prazo"}],
    11: [{"tipo": "reuniao"}],
    13: [{"tipo": "prazo"}],
    15: [{"tipo": "prazo"}],
}


@login_required
def index(request):
    # Futuramente: gerar calendário dinâmico com compromissos reais do mês
    return render(request, "agenda/index.html", {
        "mes_label": "Junho 2026",
        "compromissos_por_dia": COMPROMISSOS_JUNHO,
        "filtro": request.GET.get("filtro", "equipe"),
        "item_ativo": "agenda",
        "dia_hoje": 6,
        "dias_semana": ["DOM", "SEG", "TER", "QUA", "QUI", "SEX", "SÁB"],
        "dias_mes": [str(i) for i in range(1, 31)],
    })


@login_required
def form_compromisso(request):
    return render(request, "agenda/form.html", {"item_ativo": "agenda"})
