---
id: PDR-0012
title: Relação simétrica de processos apensos
status: accepted
owner: product-and-engineering
decision_date: 2026-08-20
last_reviewed: 2026-08-31
supersedes: []
source_files: []
---

# PDR-0012 — Relação simétrica de processos apensos

## Contexto

A especificação canônica de Processos descrevia apensos com linguagem de
“processo principal” e processo ligado ao principal. Essa formulação admite
uma interpretação hierárquica que não corresponde à primeira versão aprovada
pelo Product Owner para a navegação entre Processos relacionados.

## Decisão

Nesta primeira versão, apensos formam uma relação explícita, simétrica e
bidirecional entre dois Processos existentes:

```text
Processo A ↔ Processo B
```

Se A exibe B como apenso, B também exibe A. Nenhum dos lados é pai, filho,
principal ou dependente. Os dois Processos:

- mantêm identificação própria;
- permanecem registros independentes;
- preservam seus próprios Cliente, responsável, equipe, status, fase,
  participantes, representantes, autoridades, andamentos, prazos e documentos;
- não herdam nem propagam propriedades entre si;
- não têm dados copiados ou fundidos pela relação.

Cada vínculo relaciona somente o par explicitamente selecionado. A relação não
é transitiva: A ↔ B e B ↔ C não criam nem inferem A ↔ C.

O vínculo pode ser removido sem excluir qualquer dos Processos. A exclusão real
de um Processo pode eliminar seus vínculos, mas nunca o Processo relacionado.

## Relação com a documentação anterior

Esta decisão substitui somente a interpretação hierárquica das referências a
“processo principal” na seção de Apensos e nos fluxos correspondentes de
`docs/product/modules/processos.md`. Ela não apaga o histórico dessa linguagem,
não altera PDR-0001/PDR-0011 e não modifica as decisões de participantes,
representação, autorização ou responsabilidade.

Uma hierarquia principal/dependente poderá ser reconsiderada futuramente, mas
exigirá nova decisão de produto. Ela não é inferida desta relação simétrica.

PDR-0013 substituiu depois o modelo de Partes, e PDR-0014 introduziu o
conceito de integrante habilitado. Nenhuma dessas decisões altera a regra
de independência: partes, advogados e integrantes habilitados não são
propagados entre apensos.

## Consequências

- a interface apresenta “Apensos” nos dois Processos relacionados;
- a navegação é bidirecional;
- um par lógico possui um único vínculo persistido;
- self-link e duplicidade do mesmo par são inválidos;
- segurança de leitura e mutação deve ser verificada nos dois objetos;
- nenhuma árvore, raiz, profundidade, ordenação hierárquica ou fechamento
  transitivo integra esta versão.

## Fora do escopo desta decisão

- hierarquia principal/filho;
- apensação automática;
- importação ou fusão de dados;
- propagação de participantes, responsáveis, status, andamentos ou documentos;
- árvore recursiva e transitividade;
- tipos adicionais de relação entre Processos;
- IA.

## Critérios de aceite funcionais

- relacionar A a B faz B aparecer em A e A aparecer em B;
- repetir A ↔ B ou enviar B ↔ A não cria segundo vínculo;
- A ↔ A é rejeitado;
- ambos os Processos permanecem independentes;
- remover a relação preserva A e B;
- somente Processos visíveis ao usuário aparecem nos cards e contadores;
- criar ou remover exige direito de mutação sobre os dois Processos.

## Fontes

- decisão direta do Product Owner registrada em 2026-08-20;
- [Processos](../modules/processos.md);
- [PDR-0010](PDR-0010-autorizacao-escopo-responsabilidade-processos.md).
