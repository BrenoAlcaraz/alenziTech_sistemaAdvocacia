# Breno - LawSystem — instruções do repositório

Sistema jurídico SaaS white label, multi-tenant (schema PostgreSQL por
escritório), construído como monólito modular Django. Ver
[docs/PRODUCT.md](docs/PRODUCT.md) para visão completa.

## Carregamento de contexto

Contexto é recurso limitado. Não leia um documento porque "talvez seja
útil".

```
CLAUDE.md/AGENTS.md (sempre)
→ identificar a área/domínio afetado pela tarefa
→ consultar somente a fonte e a seção necessárias:
   • regra de produto/comportamento esperado → seção relevante de
     docs/PRODUCT.md (ou docs/modules/<x>.md, se existir)
   • padrão técnico / onde fica o quê        → seção relevante de
     docs/ARCHITECTURE.md
   • o que já existe / falta / gap conhecido → seção relevante de
     docs/STATUS.md
   • "por que essa decisão foi tomada"        → o PDR específico em
     docs/decisions/, só se referenciado e necessário
→ ler código e testes da área afetada
→ trabalhar
```

Não leia documentos inteiros por padrão. Prefira a seção relevante.
Leia o documento completo somente quando a tarefa for transversal ou
quando o contexto adicional for realmente necessário. Uma referência
entre documentos não é convite para carregar o documento referenciado
inteiro.

## Fluxo de desenvolvimento (SDD leve)

**Feature relevante**: IDEIA → `specs/<nome>.md` (objetivo, comportamento
esperado, regras de negócio, fora do escopo, plano técnico resumido,
tarefas, critérios de aceite) → implementação em passos pequenos →
testes → review final → apagar a spec.

**Mudança simples**: INSPECT → IMPLEMENT → TEST. Sem spec.

**Bug**: REPRODUCE → IDENTIFY CAUSE → FIX → REGRESSION TEST.

### Antes de apagar uma spec concluída

Promover apenas conhecimento realmente durável; se nada mudou, apenas
apagar:

| Havia na spec... | Vai para... |
|---|---|
| regra de produto nova/alterada | `docs/PRODUCT.md` ou `docs/modules/<x>.md` |
| mudança arquitetural | `docs/ARCHITECTURE.md` |
| decisão durável de produto | novo PDR em `docs/decisions/` |
| mudança de estado relevante | `docs/STATUS.md` |

## Validação proporcional ao risco

| Risco | Verificar |
|---|---|
| Mudança pequena | arquivos afetados, comportamento relacionado, testes da área |
| Feature normal | + reuso existente, impacto direto, critérios da spec |
| Mudança crítica (autenticação, autorização, multitenancy, dados sensíveis, migration, contrato público, mudança arquitetural relevante) | análise ampliada só aqui |

Resultado sempre no formato `Encontrado → impacto → ação` — nunca
relatório narrativo de como a análise foi feita. Não releia o projeto
inteiro, não audite módulos não relacionados, não registre cada comando
ou tentativa intermediária.

## Clean Code

- funções pequenas, responsabilidade única, nomes que expressem intenção;
- evitar duplicação e abstração prematura;
- evitar arquivo gigante; separar responsabilidades;
- regra de negócio no módulo de domínio, nunca em template/apresentação;
- autorização e segurança sempre no backend;
- **SEARCH BEFORE CREATE** — antes de criar helper/service/component
  novo, procurar se já existe algo equivalente no projeto;
- preferir solução simples à solução genérica para o futuro;
- remover código morto quando a alteração tornar isso seguro e evidente;
- comentário no código guarda só racional técnico local não-óbvio
  (por que essa escolha, aqui, agora) — nunca a regra de negócio em si,
  que pertence a `docs/PRODUCT.md`/`docs/modules/` e a um teste.

> Código simples e explícito é preferível a abstração sofisticada.

## Guardas permanentes

- Spec/tarefa delimita o escopo; não invente requisito, não resolva
  decisão em aberto sem registrar, não faça refatoração lateral.
- Mudanças preexistentes no working tree pertencem ao usuário: não
  resetar, não limpar, não sobrescrever. `git status --short` antes de
  qualquer alteração; parar diante de algo não compreendido.
- Staging explícito por arquivo (nunca `git add -A`/`git add .`).
  Commit e push exigem autorização explícita da sessão. Nunca
  `--force`, `reset --hard`, `clean -f`, `rebase` ou `commit --amend`
  sem autorização explícita.
- Alterações em autorização, IDOR/escopo, tenant, dados sensíveis,
  constraints ou migrations preservam os controles de backend,
  isolamento e integridade já estabelecidos (ver
  [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)).
- Migration já aplicada é imutável; correção é sempre uma nova migration.
- Regra de negócio não vive só em comentário de código — vive em
  `docs/PRODUCT.md`/`docs/modules/` e é coberta por teste.

## Onde encontrar o resto

- [docs/PRODUCT.md](docs/PRODUCT.md) — o que o produto é e faz.
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — como o sistema é
  estruturado, padrões a reutilizar, limites que não podem ser quebrados.
- [docs/STATUS.md](docs/STATUS.md) — o que existe, o que falta, próximos
  passos.
- [docs/decisions/](docs/decisions/) — decisões de produto duráveis
  (PDRs), uma por arquivo, consultadas sob demanda.
- [docs/development/COMMANDS.md](docs/development/COMMANDS.md) —
  comandos de ambiente, teste, migration, build e Git.
- `specs/` — features em andamento (efêmero; vazio quando nada está em
  progresso).
