---
title: Clientes
status: canonical
owner: product-and-engineering
last_reviewed: 2026-08-13
related_pdrs:
  - PDR-0001
  - PDR-0009
---

# Clientes

## Objetivo

Manter a pasta canônica das pessoas ou organizações atendidas pelo
escritório e seus vínculos com processos e documentos.

## Escopo funcional

- cadastro e edição de clientes;
- consulta da pasta do cliente;
- documentos do cliente;
- processos relacionados ao cliente;
- criação de processo a partir do cliente;
- clientes relacionados por processo compartilhado;
- reutilização do cliente como participante representado em um
  processo.

## Atores e expectativas de acesso

O Administrador do escritório deve poder acessar e gerenciar a pasta
de qualquer cliente do tenant. Demais usuários devem poder acessar
clientes conforme o papel de acesso e o escopo de dados que lhes forem
aplicados — por exemplo, um usuário com atuação restrita a processos
sob sua responsabilidade não deveria alcançar pastas de clientes fora
desse escopo.

Esta seção descreve uma necessidade funcional, não uma matriz técnica
definitiva de permissões. A matriz final de papéis, habilitações e
escopo é [docs/security/authorization-matrix.md](../../security/authorization-matrix.md).
O estado de aplicação dessas regras no backend deve ser verificado no
código e em [docs/delivery/current-state/clientes.md](../../delivery/current-state/clientes.md).
A autorização e o escopo de dados devem ser aplicados no backend, não
apenas ocultando elementos de interface.

## Conceitos e entidades

Os conceitos deste módulo são definidos no
[glossário funcional](../glossary.md), seção "Clientes e processos":
cliente, pasta do cliente, cliente representado, cliente relacionado,
participante processual, vínculo com o escritório, entre outros. Este
documento não redefine esses termos.

## Regras funcionais

- Os dados do cliente não devem ser redigitados ao vinculá-lo como
  participante de um processo; o cadastro de Cliente é reaproveitado.
- Um processo pode possuir vários clientes representados
  simultaneamente.
- A pasta do cliente mostra os processos aos quais ele está vinculado.
- Clientes relacionados são derivados de processos compartilhados entre
  eles, e não de um vínculo cadastrado manualmente entre clientes.
- Um processo compartilhado por mais de um cliente não deve ser
  duplicado para aparecer nas pastas de cada um; é o mesmo processo
  referenciado a partir de cada pasta.
- Criar um processo a partir da pasta do cliente deve levar o cliente
  já preenchido no novo processo.
- Documentos do cliente pertencem à pasta do cliente.
- O vínculo entre cliente e processo deve ser íntegro: o servidor deve
  rejeitar uma associação inconsistente, mesmo que a requisição tenha
  sido manipulada no navegador.
- Ao selecionar um cliente em um formulário relacionado a processo, os
  seletores dependentes de processo não podem oferecer processos
  incompatíveis com o cliente selecionado.
- Autorização e escopo de dados devem ser aplicados no backend.

Os seguintes pontos não são decididos por esta especificação, por não
haver decisão expressa nas fontes consolidadas:

- critério de deduplicação de clientes por CPF/CNPJ;
- formato técnico de armazenamento dos documentos do cliente;
- exclusão física versus exclusão lógica de um cliente;
- cardinalidade de endereços ou contatos por cliente.

## Fluxos principais

1. Cadastrar cliente.
2. Anexar documento à pasta do cliente.
3. Criar processo a partir da pasta do cliente, com o cliente já
   preenchido.
4. Consultar os processos vinculados a um cliente.
5. Consultar os clientes relacionados a partir de processos
   compartilhados.
6. Reutilizar um cliente já cadastrado como participante de um
   processo, sem redigitar seus dados.

## Integrações e dependências

- Depende do módulo Processos para exibir processos vinculados,
  clientes relacionados e para a criação de processo a partir da pasta
  do cliente.
- Fornece o cadastro reaproveitado por Processos ao registrar um
  cliente como participante processual (ver
  [processos.md](processos.md) e PDR-0001).
- A vinculação de documentos ao cliente depende de uma infraestrutura
  comum de arquivos ainda não formalizada nesta especificação.

## Fora do escopo imediato

- OCR de documentos do cliente.
- Classificação automática de documentos.
- Criação automática de cliente por IA.
- Integração externa de armazenamento de documentos.

## Pontos em aberto

- Critério de deduplicação de clientes por CPF/CNPJ.
- Formato técnico de armazenamento dos documentos do cliente
  (pertence à arquitetura).
- Exclusão física versus exclusão lógica de um cliente.
- Cardinalidade de endereços ou contatos por cliente.
- Mecanismo de criação rápida de cliente durante o fluxo de criação de
  processo (modal, nova aba ou redirecionamento) — mencionado como
  recomendação técnica nas fontes históricas, sem confirmação formal;
  ver [processos.md](processos.md).

## Critérios de aceite funcionais

- Um cliente já vinculado a um processo aparece automaticamente entre
  os participantes desse processo, com nome e CPF/CNPJ preenchidos a
  partir do cadastro de Cliente, sem exigir nova digitação.
- A pasta do cliente exibe os processos aos quais ele está vinculado.
- Clientes relacionados aparecem na pasta do cliente, derivados de
  processos compartilhados, sem duplicação do processo entre as
  pastas.
- Criar um processo a partir da pasta do cliente resulta em um
  processo com o cliente já preenchido.
- Documentos anexados a um cliente aparecem na pasta desse cliente.
- Um vínculo inconsistente entre cliente e processo é rejeitado pelo
  servidor, mesmo que a requisição tenha sido manipulada no navegador.

## Referências canônicas

- [Glossário funcional](../glossary.md)
- [PDR-0001 — Participantes processuais](../decisions/PDR-0001-participantes-processuais.md)
- [PDR-0009 — Sequência revisada da Fase 2](../decisions/PDR-0009-sequencia-fase-2.md)
- [Visão do produto](../vision.md)
- [Escopo do produto](../scope.md)
- [Política de terminologia](../../governance/terminology-policy.md)
