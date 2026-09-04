# Spec — Habilitações granulares de criar, editar e adicionar andamento em Processos

Decisão de produto: [PDR-0017](../docs/decisions/PDR-0017-habilitacoes-criar-editar-andamento-processos.md)
(complementa [PDR-0010](../docs/decisions/PDR-0010-autorizacao-escopo-responsabilidade-processos.md)).

## Objetivo

Aplicar, nas views de Processos, as três habilitações granulares já
existentes no kernel e hoje sem nenhum efeito prático:
`processos_criar`, `processos_editar` e `processos_andamento_adicionar`.

## Comportamento esperado

| Habilitação | View | Sem a habilitação |
|---|---|---|
| `processos_criar` | `processos:novo` | `PermissionDenied` (403), `GET` e `POST` |
| `processos_editar` | `processos:editar` | `PermissionDenied` (403), `GET` e `POST` |
| `processos_andamento_adicionar` | `processos:adicionar_movimentacao` | `PermissionDenied` (403) no `POST` |

Cada view passa a checar, nesta ordem, antes de qualquer efeito:

1. `tem_permissao_modulo(request.user, MODULO_PROCESSOS)` (já existe);
2. `tem_habilitacao(request.user, MODULO_PROCESSOS, <item>)` (novo).

Padrão a seguir: `apps/clientes/views.py` (`novo`/`editar`), já
validado em produção.

## Regras de negócio relevantes

- Administrador do escritório mantém acesso a criar, editar e
  adicionar andamento independentemente destas habilitações — o bypass
  já existe no kernel (`habilitacao_efetiva`/`ctx.is_admin`), nenhuma
  lógica nova é necessária para isso.
- Falta de habilitação bloqueia no backend, inclusive tentativa direta
  por `POST`; não é suficiente ocultar o link/botão na UI.
- `processos:editar` continua carregando o objeto pelo QuerySet de
  mutação já existente (`_processos_mutaveis`) — escopo de
  responsável/Administrador não muda; a habilitação é uma checagem
  adicional, não substitui o escopo.
- Nenhuma outra view de Processos (arquivar, reabrir, apensos, partes)
  passa a exigir habilitação granular.
- `processos_usar_ia` e `processos_usar_laboratorio` não são tocadas.

## Fora do escopo

- `processos_usar_ia`, `processos_usar_laboratorio`.
- Habilitação nova para arquivar, reabrir, apensos ou partes de
  processo.
- Qualquer alteração a escopo de leitura/mutação por responsável,
  responsabilidade obrigatória, ou `processos_atribuir_responsavel`
  (PDR-0014).
- Qualquer alteração ao módulo Clientes.
- Mudança de UI além do necessário para refletir o bloqueio (ex.:
  ocultar link/botão quando a habilitação faltar, análogo ao que já
  existe para `processos_atribuir_responsavel`).

## Critérios de aceite

- Usuário com módulo `processos` habilitado mas sem `processos_criar`
  não acessa `processos:novo` (`GET`) nem cria processo (`POST`).
- Usuário com módulo `processos` habilitado mas sem `processos_editar`
  não acessa `processos:editar` (`GET`) nem edita (`POST`), mesmo para
  processo do seu próprio escopo de mutação.
- Usuário com módulo `processos` habilitado mas sem
  `processos_andamento_adicionar` não adiciona andamento (`POST`) em
  `processos:adicionar_movimentacao`.
- Administrador do escritório continua criando, editando e adicionando
  andamento sem depender de nenhuma das três habilitações.
- Arquivar, reabrir, apensos e partes continuam funcionando como hoje,
  sem exigir habilitação nova.
- Testes de autorização cobrindo os três blocos acima (positivo e
  negativo, incluindo `POST` direto) em
  `apps/processos/tests/test_autorizacao.py`.
