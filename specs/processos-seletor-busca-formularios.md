# Spec — Seletor de Processo com busca em todos os formulários

## Objetivo

Padronizar todo campo que referencia um Processo, em qualquer formulário
do sistema, para exibir "Título — Número" e permitir busca por
digitação, em vez do `<select>` simples usado hoje na maioria das telas.

## Comportamento esperado

- Todo campo de seleção de Processo (Clientes, Financeiro, Agenda,
  Intimações, Custas Judiciais e qualquer outro formulário que
  referencie processo) passa a:
  - Exibir cada opção como "Título — Número" (já é o padrão usado no
    seletor de Apensos, `ProcessoApensoChoiceField`).
  - Permitir digitar para filtrar as opções (autocomplete/combobox), em
    vez de exigir rolar uma lista longa num `<select>` comum.

## Regras de negócio relevantes

- A lista de processos oferecida em cada campo continua restrita ao
  mesmo escopo/autorização que já se aplica hoje em cada formulário
  (ex.: só processos do escopo de mutação de quem cria uma Intimação) —
  a mudança é só de interface de seleção, nunca de quais processos
  aparecem.

## Fora de escopo

- Qualquer mudança na regra de autorização/escopo de quem pode vincular
  um processo a outro registro.

## Critérios de aceite

- Digitar parte do título ou do número de um processo em qualquer campo
  desse tipo filtra as opções em tempo real.
- Nenhum campo desse tipo, em nenhum formulário do sistema, continua
  sendo um `<select>` sem busca.
