# Spec — Clientes: cadastro completo, busca e vínculos

## Objetivo

Expandir o cadastro de Cliente (documento por nacionalidade, endereço
estruturado, dados pessoais), habilitar busca na listagem, adicionar
exclusão definitiva e dois blocos novos no detalhe (Clientes
relacionados, Tarefas relacionadas).

## Comportamento esperado

### Formulário de criação/edição

- Checkbox Brasileiro/Estrangeiro, "Brasileiro" marcado por padrão.
  - Brasileiro: campo de documento rotulado "CPF/CNPJ", com validação de
    CPF/CNPJ.
  - Estrangeiro: campo rotulado "Documento", digitação livre, sem
    validação de CPF/CNPJ.
- CPF e telefone recebem máscara de entrada e validação, na digitação e
  no salvamento.
- Novos campos: Nacionalidade (travada em "Brasileira" se brasileiro;
  lista suspensa de nacionalidades se estrangeiro), Estado civil,
  Profissão, RG (habilitado só se brasileiro).
- Endereço estruturado substitui o campo único `endereco` (texto livre):
  - Brasileiro: preenche CEP → sistema busca endereço automaticamente
    (integração com serviço de CEP) → libera só Número e Complemento
    para digitação; demais campos ficam travados com o resultado da
    busca.
  - Estrangeiro: endereço inteiro digitado manualmente; campo CEP
    travado/desabilitado.

### Listagem

- Busca por CPF/CNPJ e por nome (hoje a listagem não tem nenhum filtro).

### Exclusão definitiva

- Nova ação "Excluir", distinta de "Desativar" (`ativo=False`, já
  existente). Remove o Cliente; lançamentos, custas, honorários, tarefas
  e compromissos vinculados permanecem no sistema, com a referência ao
  cliente desfeita.

### Detalhe do cliente — blocos novos

- Aba "Clientes relacionados": lista outros clientes que estão do
  **mesmo polo** (ambos no polo ativo, ou ambos no polo passivo) de
  algum processo em comum.
- Card "Tarefas relacionadas": mesmo padrão do card equivalente de
  Processos (`processos-ajustes-formulario-detalhe.md`) — lista
  funcional, clique numa tarefa abre ela no módulo de Tarefas, botão
  "ver todas" filtra o módulo de Tarefas por este cliente.

## Regras de negócio relevantes

- "Clientes relacionados" depende de os dois clientes terem sido
  cadastrados manualmente como Parte do mesmo processo — não há hoje
  vínculo automático Cliente↔Parte (ponto em aberto já registrado em
  `docs/modules/processos.md`). Dois clientes que nunca foram cadastrados
  como Parte não aparecem vinculados entre si, mesmo que o processo os
  relacione de outra forma.
- A busca por CEP depende de integração com serviço externo de CEP —
  escolha do provedor é decisão técnica de implementação, não de
  produto.

## Fora de escopo

- Dedup automática por CPF/CNPJ entre clientes.
- Cardinalidade de múltiplos endereços/contatos por cliente.
- Materialização automática do Cliente como Parte de processo (item que
  destravaria "Clientes relacionados" por completo) — fica para quando
  `docs/modules/processos.md` resolver esse ponto em aberto.

## Critérios de aceite

- Cadastro de cliente estrangeiro libera digitação livre no campo de
  documento e de endereço, sem exigir CEP nem validar CPF/CNPJ.
- Cadastro de cliente brasileiro exige CPF/CNPJ válido, libera RG,
  trava nacionalidade em "Brasileira", e busca automaticamente o
  endereço por CEP.
- Buscar por parte de um CPF/CNPJ ou de um nome na listagem retorna os
  clientes correspondentes.
- Excluir um cliente o remove da listagem; um lançamento financeiro que
  o referenciava continua existindo, mostrando "cliente excluído" em vez
  de erro.
- Dois clientes cadastrados como Parte no mesmo polo do mesmo processo
  aparecem um para o outro na aba "Clientes relacionados".
