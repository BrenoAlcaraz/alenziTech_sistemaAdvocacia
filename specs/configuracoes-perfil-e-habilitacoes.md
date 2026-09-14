# Spec — Configurações: foto de perfil e simplificação de habilitações

## Objetivo

Expor o upload de foto de perfil (campo já existente no modelo) e
simplificar a exibição de habilitações herdadas na tela individual de
usuário.

## Comportamento esperado

- Formulário de edição de perfil pessoal ganha campo de upload de foto —
  usa `PerfilUsuario.avatar`, que já existe no modelo mas não está em
  nenhuma tela hoje.
- Tela de habilitações/permissões individuais de um usuário
  (`configuracoes:usuario_overrides`) deixa de expor o conceito de
  "herdado" como opção separada. Passa a mostrar direto o estado efetivo
  (ligado/desligado) de cada módulo/habilitação — já refletindo o que
  veio herdado do tipo de conta base — editável inline, sem exigir que
  quem está configurando entenda o conceito de herança/override.

## Regras de negócio relevantes

- O mecanismo de override por trás (o que é herdado vs. customizado por
  usuário) continua existindo tecnicamente — só deixa de aparecer como
  rótulo/toggle separado na interface.
- Administrador do escritório continua com bypass total, sem efeito de
  override sobre ele (regra já existente).

## Fora de escopo

- O "bug visual" relatado nas permissões não é tratado nesta spec — não
  foi possível reproduzir de forma consistente (só apareceu numa máquina
  específica, sem efeito funcional). Revisitar se voltar a acontecer.
- Exclusão física de papel dinâmico (gap já registrado em STATUS.md, sem
  relação com este pedido).

## Critérios de aceite

- Usuário consegue trocar a própria foto de perfil pela tela de
  Configurações.
- Tela de overrides de um usuário mostra cada módulo/habilitação como um
  toggle único no estado efetivo atual, sem nenhum rótulo ou opção de
  "herdar" visível.
- Alterar manualmente um toggle nessa tela substitui o valor herdado, sem
  precisar de nenhuma ação extra de "desligar herança".
