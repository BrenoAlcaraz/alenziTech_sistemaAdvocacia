"""
Helper compartilhado pelos testes de rollback/reaplicação de migration de
"processos" (test_migrations.py, test_migrations_apensos.py,
test_migrations_participantes.py).

Esses testes rolam "processos" para um estado anterior ao HEAD enquanto
mantêm as demais apps no próprio HEAD. Isso quebra se o HEAD de outra
app passar a depender (direta ou indiretamente) de uma migration de
"processos" posterior ao alvo do rollback — ex.: `financeiro.0003`
depende de `processos.0012` (PDR-0014). Pedir ao executor esse HEAD ao
mesmo tempo que pede "processos" de volta a uma migration anterior gera
um plano com a mesma migration marcada para aplicar e para reverter
(`InvalidMigrationPlan`), ou, sem esse erro, contamina
`project_state()` fazendo os models refletirem migrations de
"processos" além do alvo pretendido.
"""


def targets_seguros_para_rollback(graph, alvo):
    """
    Lista de nodes seguros para passar a `MigrationExecutor.migrate()`/
    `project_state()` ao rolar a app de `alvo` para trás: cada outra app
    fica no próprio HEAD, exceto quando o HEAD dessa app depender de uma
    migration de `alvo[0]` posterior a `alvo` — nesse caso, usa a última
    migration dessa app anterior a essa dependência.
    """
    app_alvo = alvo[0]
    alcancavel_do_alvo = {node for node in graph.forwards_plan(alvo) if node[0] == app_alvo}

    def depende_de_algo_proibido(node):
        return any(
            dep[0] == app_alvo and dep not in alcancavel_do_alvo
            for dep in graph.forwards_plan(node)
        )

    nodes = [alvo]
    for leaf in graph.leaf_nodes():
        if leaf[0] == app_alvo:
            continue
        if not depende_de_algo_proibido(leaf):
            nodes.append(leaf)
            continue
        cadeia_da_app = [node for node in graph.forwards_plan(leaf) if node[0] == leaf[0]]
        seguro = next(
            (node for node in reversed(cadeia_da_app) if not depende_de_algo_proibido(node)),
            None,
        )
        if seguro is not None:
            nodes.append(seguro)
    return nodes
