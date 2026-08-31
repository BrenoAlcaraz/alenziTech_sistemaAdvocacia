# Breno - LawSystem

Sistema jurídico SaaS white label, multi-tenant, para escritórios de
advocacia. Monólito modular Django, PostgreSQL, isolamento por schema
PostgreSQL por tenant (`django-tenants`) — cada escritório é um tenant
isolado; a plataforma SaaS (tenants, planos, assinaturas) fica em um
schema público compartilhado.

## Documentação

Ponto de entrada para pessoas e agentes de IA: [AGENTS.md](AGENTS.md).

- [docs/PRODUCT.md](docs/PRODUCT.md) — o que o produto é e faz.
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — como o sistema é
  estruturado, padrões a reutilizar, limites que não podem ser quebrados.
- [docs/STATUS.md](docs/STATUS.md) — o que existe, o que falta, próximos
  passos.
- [docs/decisions/](docs/decisions/) — decisões de produto duráveis (PDRs).
- [docs/development/COMMANDS.md](docs/development/COMMANDS.md) —
  ambiente, testes, migration, build, Git.
- `specs/` — features em andamento (efêmero).

Não carregue estes documentos inteiros por padrão — ver a regra de
contexto em [AGENTS.md](AGENTS.md#carregamento-de-contexto).
