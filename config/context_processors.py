# Páginas raiz dos módulos: as de entrada da sidebar e Configurações (menu do
# usuário). Nelas o cabeçalho não oferece "Voltar".
PAGINAS_RAIZ = {
    "dashboard:painel",
    "processos:lista",
    "modelos:lista",
    "financeiro:index",
    "chat:lista",
    "agenda:index",
    "clientes:lista",
    "configuracoes:index",
}


def navegacao(request):
    """Indica ao layout se a tela atual é a página raiz de um módulo."""
    match = getattr(request, "resolver_match", None)
    return {"pagina_raiz": bool(match) and match.view_name in PAGINAS_RAIZ}
