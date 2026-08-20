---
id: PDR-0011
title: Taxonomia e representação de participantes de Processos
status: accepted
owner: product-and-engineering
decision_date: 2026-08-20
last_reviewed: 2026-08-20
supersedes: []
complements:
  - PDR-0001
source_files: []
---

# PDR-0011 — Taxonomia e representação de participantes de Processos

## Contexto

[PDR-0001](PDR-0001-participantes-processuais.md) separa vínculo com o
escritório, posição estrutural, qualificação processual, representação e
autoridade. O Product Owner aprovou a taxonomia inicial da experiência da aba
Partes e a regra de preenchimento do advogado interno do cliente já vinculado
ao processo.

Este PDR complementa PDR-0001. PDR-0001 permanece aceito, vigente e não é
substituído por esta decisão.

## Decisão

### Taxonomia inicial e agrupamento visual

| Opção na interface | Posição estrutural | Qualificação processual | Grupo visual |
| --- | --- | --- | --- |
| Autor | polo ativo | autor | Polo Ativo |
| Embargante | polo ativo | embargante | Polo Ativo |
| Recorrente | polo ativo | recorrente | Polo Ativo |
| Réu | polo passivo | réu | Polo Passivo |
| Embargado | polo passivo | embargado | Polo Passivo |
| Recorrido | polo passivo | recorrido | Polo Passivo |
| Terceiro Interessado | terceiro | terceiro interessado | Outros |
| Ministério Público | posição própria do Ministério Público | Ministério Público, com atuação como parte ou fiscal da ordem jurídica | Outros |
| Amicus Curiae | terceiro | amicus curiae | Outros |
| Juiz | autoridade separada | não se aplica | Outros |

Os grupos são uma decisão de experiência visual. Não constituem um único campo
de domínio e não substituem as dimensões obrigatórias de PDR-0001.

### Juiz e demais participantes

Juiz aparece no seletor do grupo visual Outros, mas é persistido como
autoridade processual separada, nunca como parte. O registro inicial contém
tipo `juiz`, nome, vara ou órgão e observação opcional. `Processo.vara_juizo`
pode ser usado como sugestão inicial, sem impedir ajuste. Autoridade não recebe
advogado.

Ministério Público permanece apto a atuar como parte ou fiscal da ordem
jurídica. A forma de atuação integra o vínculo processual.

### Advogados e cardinalidade

Advogado não é tipo de parte. Cada participante admite zero, um ou vários
representantes em relação normalizada 1:N.

- advogado interno referencia diretamente o `User` já existente, sem segunda
  ficha e sem OAB inventada;
- advogado externo registra nome, número da OAB, UF da OAB, telefone e e-mail;
  CPF não é obrigatório;
- remover advogado exclui somente o vínculo de representação, preservando
  usuário, participante e processo;
- o mesmo usuário interno não pode ser duplicado na mesma parte.

O valor legado `advogado_contrario` não pode ser oferecido em novos cadastros.

### Cliente automático e classificação pendente

O `Cliente` vinculado em `Processo.cliente` possui automaticamente um único
participante correspondente no mesmo Processo. A identidade desse participante
é o próprio objeto `Cliente`: nome e CPF/CNPJ exibidos vêm do cadastro atual de
Cliente, inclusive quando o documento estiver vazio, sem redigitação ou cópia
como fonte primária.

Como o sistema não pode inferir Autor, Réu ou qualquer outra qualificação, esse
participante pode nascer em estado explícito de classificação pendente. O estado
é transitório e exclusivo de participante com FK real de Cliente e vínculo com
o escritório; nenhuma parte externa ou registro legado pode utilizá-lo. Quando
a classificação é informada, o mesmo participante mantém sua identidade e PK,
deixa o estado pendente e passa a obedecer à taxonomia desta decisão.

Mudanças relevantes de posição, qualificação ou forma de atuação do Ministério
Público preservam o participante e geram histórico normalizado com estado
anterior, estado novo, data/hora e usuário responsável quando disponível.

### Preenchimento automático do advogado interno

Ao cadastrar uma parte, o sistema compara somente dígitos do CPF/CNPJ
informado com o CPF/CNPJ do `Cliente` vinculado ao próprio `Processo`.

O vínculo automático ocorre apenas quando:

1. ambos os documentos são não vazios;
2. os valores são exatamente iguais após normalização;
3. o cliente comparado é `Processo.cliente`.

Nesse caso, `Processo.responsavel` é vinculado como advogado interno da parte.
A operação é idempotente e não cria duplicata. Nome, busca aproximada,
`contains` ou outro cliente do escritório não identificam a parte.

### Dados legados

`autor`, `reu` e `terceiro` são migrados para as dimensões estruturadas
equivalentes. Como `advogado_contrario` não contém informação suficiente para
identificar objetivamente qual parte era representada, sua linha é preservada
como registro legado, sem associação arbitrária, e fica indisponível para novos
cadastros. Nenhuma linha é excluída pela migration.

### Autorização

As operações de participante e representante reutilizam integralmente a
fronteira de [PDR-0010](PDR-0010-autorizacao-escopo-responsabilidade-processos.md):
leitura segue o escopo de leitura do Processo; não administrador só modifica
processo sob sua responsabilidade; Administrador do escritório modifica
qualquer processo do tenant. Objeto fora da fronteira de mutação retorna 404.

## Consequências

- `ParteProcesso` passa a registrar vínculo, posição e qualificação em campos
  distintos;
- o Cliente do Processo possui vínculo automático único, inicialmente pendente
  quando não há classificação jurídica informada;
- alterações de classificação preservam a identidade e produzem histórico;
- autoridades e representantes passam a possuir entidades próprias;
- a interface pode crescer para múltiplos representantes sem campos seriados ou
  limite artificial;
- a preservação do valor legado fica explícita e auditável;
- OAB de usuário interno só poderá ser exibida quando existir fonte real futura.

## Fora do escopo desta decisão

- apensos e relação Processo ↔ Processo;
- equipe como autorização ou escopo;
- novas habilitações granulares de Processos;
- diretório global de advogados externos;
- ampliação de Accounts apenas para cadastrar OAB;
- IA e Laboratório.

## Critérios de aceite funcionais

- as dez opções aparecem nos três grupos definidos;
- o Cliente do Processo aparece automaticamente uma única vez, mesmo sem
  CPF/CNPJ, usando o cadastro de Cliente como fonte da identidade;
- a classificação pendente é restrita ao Cliente automático e sua definição ou
  alteração preserva o participante e registra histórico;
- juiz é autoridade separada;
- Ministério Público registra sua forma de atuação;
- advogado nunca é criado como parte;
- uma parte aceita zero, um ou vários advogados;
- advogado interno reutiliza usuário e externo aceita os dados profissionais;
- o preenchimento automático usa apenas o mesmo Cliente do Processo e é
  idempotente;
- remoção preserva usuário, parte e processo;
- dados legados permanecem integralmente preservados.

## Fontes

- decisão direta do Product Owner registrada em 2026-08-20;
- [PDR-0001 — Participantes processuais](PDR-0001-participantes-processuais.md);
- [PDR-0010 — Autorização, escopo e responsabilidade de Processos](PDR-0010-autorizacao-escopo-responsabilidade-processos.md).
