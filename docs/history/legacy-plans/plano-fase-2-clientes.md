# Plano Fase 2 — CRUD Real — Módulo Clientes

## Status: Concluído ✅

Todas as funcionalidades planejadas foram implementadas, testadas no navegador e commitadas.

---

## Checklist de Implementação

- [x] Revisar model `Cliente` — campos confirmados, OK
- [x] Adicionar campo `ativo = models.BooleanField(default=True)` ao model
- [x] Criar migration `0002_cliente_ativo` e aplicar com `migrate_schemas`
- [x] Criar `apps/clientes/forms.py` com `ClienteForm`
- [x] Implementar view `lista()` com query real (`filter(ativo=True)`)
- [x] Implementar view `detalhe()` com `get_object_or_404(ativo=True)`
- [x] Implementar view `novo()` usando `ClienteForm` (POST salva no banco)
- [x] Implementar view `editar()` usando `ClienteForm(instance=cliente)`
- [x] Implementar view `desativar()` — soft delete via POST (marca `ativo=False`)
- [x] Implementar view `inativos()` — lista `Cliente.objects.filter(ativo=False)`
- [x] Implementar view `reativar()` — marca `ativo=True` via POST
- [x] Atualizar `apps/clientes/urls.py` — todas as rotas criadas
- [x] Atualizar `templates/clientes/lista.html` — dados reais + link "Ver inativos"
- [x] Atualizar `templates/clientes/detalhe.html` — dados reais + botões Editar/Desativar
- [x] Atualizar `templates/clientes/form.html` — form Django real com widgets customizados
- [x] Criar `templates/clientes/inativos.html` — lista de inativos + botão Reativar
- [x] Remover `CLIENTES_MOCK` e `PROCESSOS_MOCK_CLIENTE` de `views.py`
- [x] Testar CRUD completo via navegador
- [x] Validar `item_ativo` em todas as views
- [x] Validar 404 em URLs de clientes inativos ou inexistentes

---

## Funcionalidades entregues

| Funcionalidade | Rota | View |
|---|---|---|
| Listagem de ativos | `GET /clientes/` | `lista()` |
| Criar cliente | `GET/POST /clientes/novo/` | `novo()` |
| Listar inativos | `GET /clientes/inativos/` | `inativos()` |
| Detalhe | `GET /clientes/<pk>/` | `detalhe()` |
| Editar | `GET/POST /clientes/<pk>/editar/` | `editar()` |
| Desativar | `POST /clientes/<pk>/desativar/` | `desativar()` |
| Reativar | `POST /clientes/<pk>/reativar/` | `reativar()` |

---

## Pendências futuras (fora do escopo atual)

Estas funcionalidades foram intencionalmente deixadas para etapa posterior:

- **Busca/filtros reais** — a barra de busca visual já existe no template, sem lógica real
- **Paginação** — implementar quando o volume de clientes justificar
- **Validação avançada de CPF/CNPJ** — formato e dígito verificador
- **Permissões por grupo/cargo** — usuários comuns vs. gerente/dono do tenant
- **Hard delete restrito a gerente/dono** — com aviso explícito de perda de histórico de processos
- **Auditoria/logs** — registro de quem desativou/reativou/editou um cliente e quando
- **Contagem real de processos** — `num_processos` no card da lista (depende do módulo Processos)

---

## Decisões técnicas registradas

- **Soft delete em vez de hard delete** — `Processo.cliente` usa `on_delete=SET_NULL`; deletar definitivamente um cliente tornaria os processos órfãos de contexto. Soft delete preserva o histórico.
- **`ativo` como `BooleanField(default=True)`** — todos os registros existentes ficaram ativos automaticamente na migration, sem necessidade de backfill manual.
- **Formulário com `HiddenInput` para `tipo`** — o toggle visual PF/PJ usa botões HTML com JavaScript mínimo que atualiza o hidden input, evitando select nativo e mantendo o visual customizado.
- **`get_object_or_404(Cliente, pk=pk, ativo=True)`** — clientes desativados retornam 404 nas rotas de detalhe e edição, impedindo acesso por URL direta.
