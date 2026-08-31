---
title: WI-0002 — Escopo e responsabilidade de Clientes
status: canonical
owner: delivery
last_reviewed: 2026-08-31
---

# WI-0002 — Escopo e responsabilidade de Clientes

## Estado

done

## Fase do roadmap

Fase: Fase B — Aplicar escopo de dados

Dependência: [WI-0001](WI-0001-autorizacao-backend-clientes.md)
(`done`, commit `da19001`).

## Objetivo

Aplicar escopo de dados por responsável ao módulo Clientes, sobre a
autorização já aplicada pelo WI-0001: escopo de visualização
(`somente_seus`/`todos`), autorização sobre objeto (IDOR intra-tenant →
404), `Cliente.responsavel` obrigatório, reatribuição restrita ao
Administrador, seletor visual com o backend como fonte de verdade. Sem
escopo por equipe.

## Estado entregue

O mecanismo completo (parâmetro `?escopo=` sem estado persistente,
distinção leitura versus mutação, regra de responsabilidade na
criação/edição, "Da equipe" como placeholder sem efeito funcional) está
documentado em
[authorization-matrix.md#clientes](../../security/authorization-matrix.md#clientes)
e [data-scope.md](../../security/data-scope.md#aplicação-por-módulo) —
não duplicado aqui.

## Decisões técnicas não óbvias

- `Cliente.responsavel.on_delete` mudou de `SET_NULL` (incompatível com
  campo obrigatório) para `PROTECT` — impede excluir um `User` que
  ainda seja responsável por algum `Cliente`. Nenhum fluxo do HEAD
  exclui `User` fisicamente; se isso mudar no futuro, o tratamento é
  decisão de outro item.
- Migration `0006_cliente_responsavel_obrigatorio.py` remove, de forma
  reproduzível (`RunPython`, não `DELETE` manual), qualquer `Cliente`
  remanescente com `responsavel IS NULL` antes de tornar o campo
  obrigatório — autorizado pelo Product Owner como salvaguarda para
  dado fictício; contagem no ambiente de desenvolvimento era zero antes
  da migration.
- Campo "pesquisável por nome" no seletor de responsável é filtro
  client-side em JavaScript vanilla (sem nova dependência de frontend).

## Correção pós-review (antes do commit)

Review técnico independente encontrou e corrigiu, na mesma sessão:

1. `?escopo=` vazio era tratado como ausente (recebia o padrão em vez
   de ser negado) — corrigido para distinguir ausente de presente-e-
   inválido.
2. Campo de responsável na edição mostrava o editor, não o responsável
   real do cliente, para conta não administradora — corrigido.
3. `editar`/`desativar`/`reativar` usavam o `QuerySet` de leitura, não
   um `QuerySet` de mutação dedicado — um usuário não administrador com
   nível máximo `todos` mutava qualquer cliente do tenant, violando a
   regra de que "todos" é alcance de visualização, não de mutação.
   Corrigido com `_clientes_mutaveis`, restrito a Administrador ou
   posse.

8 testes adicionados para cobrir os três pontos; suítes completas
revalidadas após a correção (ver "Evidência final").

## Critérios de aceite

Os 20 critérios funcionais aprovados (escopo de leitura por
`somente_seus`/`todos`; 404 para cliente fora do escopo em
`detalhe`/`editar`/`desativar`/`reativar`; responsabilidade forçada e
imune a `POST` adulterado na criação; reatribuição exclusiva do
Administrador restrita a usuários ativos; rejeição de `?escopo=`
inválido/acima do máximo com 403; "Da equipe" sem efeito funcional;
nenhum `Cliente` sem `responsavel`) estão todos com evidência de teste
automatizado — ver `apps/clientes/tests/test_escopo.py`. Não repetidos
aqui; a especificação vigente é
[authorization-matrix.md#clientes](../../security/authorization-matrix.md#clientes).

## Achados fora do escopo ainda relevantes

- **`static/css/output.css` desatualizado independentemente deste WI.**
  Um `npm run build` completo (Tailwind) produz um diff de 57
  inserções/107 remoções não relacionado a este item — hipótese não
  confirmada: `tailwind.config.js` escaneia apenas `templates/`,
  `apps/**/*.html` e `static/js/`, não arquivos `.py` com `widgets`
  Tailwind. Nesta entrega, o gate foi satisfeito com um patch manual
  mínimo (4 classes), evitando remover estilo de outros módulos.
  Impacto para qualquer WI futuro que rode `npm run build` sem cautela:
  risco de remover estilo visual de módulos não relacionados. Destino
  provável: item de manutenção de build, ou ajustar `content` de
  `tailwind.config.js`.

## Git e encerramento

Branch: `docs/reorganizacao-harness`.

Commit de implementação (H1): `07675f7` — "feat(clientes): aplicar
escopo e responsabilidade".

## Evidência final

```text
python manage.py test apps.clientes -v 1 --noinput
→ 57 testes (26 WI-0001 + 31 test_escopo.py) — OK

python manage.py test apps.accounts -v 1 --noinput
→ 86 testes — OK

python manage.py check
→ System check identified no issues (0 silenced).

python manage.py makemigrations --check --dry-run
→ No changes detected

git diff --check → aprovado, sem saída
```

Validação manual do Product Owner — **aprovada** em 2026-08-18 (escopo
"somente os seus"/"todos", IDOR em URL direta, criação e reatribuição
pelo Administrador).

- [x] critérios de aceite com evidência;
- [x] diff revisado e escopo respeitado;
- [x] `current-state.md` atualizado (commit H2, separado do H1);
- [x] achados laterais registrados acima.

## Referências

- [current-state/clientes.md](../current-state/clientes.md)
- [authorization-matrix.md#clientes](../../security/authorization-matrix.md#clientes)
- [data-scope.md](../../security/data-scope.md)
- [WI-0001 — Autorização backend de Clientes](WI-0001-autorizacao-backend-clientes.md)
