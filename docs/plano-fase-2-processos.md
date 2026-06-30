# Plano Fase 2.2 — Processos (Pasta Jurídica Básica)

## Status: Concluído em nível básico ✅

Todas as funcionalidades do escopo foram implementadas, testadas no navegador e commitadas.

---

## Checklist de Implementação

- [x] Revisar model `Processo` — campos confirmados, OK
- [x] Adicionar campos jurídicos: `fase`, `gratuidade_justica_status`, `data_distribuicao`
- [x] Alterar `MovimentacaoProcessual.data` de `auto_now_add` para `default=timezone.now`
- [x] Adicionar `@property prazo_urgente` e `@property prazo_label` ao model
- [x] Criar migration `0002` e aplicar com `migrate_schemas`
- [x] Criar `apps/processos/forms.py` com `ProcessoForm`, `ParteProcessoForm`, `MovimentacaoProcessualForm`
- [x] Implementar view `lista()` com `exclude(status="arquivado")`
- [x] Implementar view `detalhe()` com `select_related` + `prefetch_related`
- [x] Implementar view `novo()` usando `ProcessoForm` (POST salva no banco)
- [x] Implementar view `editar()` usando `ProcessoForm(instance=processo)`
- [x] Implementar view `adicionar_parte()` — rota POST-only, formulário inline
- [x] Implementar view `adicionar_movimentacao()` — rota POST-only, formulário inline
- [x] Implementar view `arquivar()` — soft state `status="arquivado"` via POST
- [x] Implementar view `reabrir()` — `status="ativo"` via POST
- [x] Implementar view `arquivados()` — lista processos com `status="arquivado"`
- [x] Atualizar `apps/processos/urls.py` — 9 rotas criadas
- [x] Atualizar `templates/processos/lista.html` — dados reais, link para arquivados
- [x] Atualizar `templates/processos/detalhe.html` — dados reais, abas, formulários inline, banner de arquivado
- [x] Atualizar `templates/processos/form.html` — formulário Django real com widgets customizados
- [x] Criar `templates/processos/arquivados.html` — lista de arquivados, reabrir inline
- [x] Remover mocks de `views.py` (`PROCESSOS_MOCK`, `MOVIMENTACOES_MOCK`, `PARTES_MOCK`)
- [x] Remover contadores falsos `(1)` das abas Prazos e Documentos
- [x] Testar CRUD completo via navegador
- [x] Validar `item_ativo` em todas as views
- [x] Validar 404 em processos inexistentes

---

## Funcionalidades entregues

| Funcionalidade | Rota | View |
|---|---|---|
| Listagem de ativos | `GET /processos/` | `lista()` |
| Criar processo | `GET/POST /processos/novo/` | `novo()` |
| Listar arquivados | `GET /processos/arquivados/` | `arquivados()` |
| Detalhe | `GET /processos/<pk>/` | `detalhe()` |
| Editar | `GET/POST /processos/<pk>/editar/` | `editar()` |
| Arquivar | `POST /processos/<pk>/arquivar/` | `arquivar()` |
| Reabrir | `POST /processos/<pk>/reabrir/` | `reabrir()` |
| Adicionar movimentação | `POST /processos/<pk>/movimentacoes/nova/` | `adicionar_movimentacao()` |
| Adicionar parte | `POST /processos/<pk>/partes/nova/` | `adicionar_parte()` |

---

## Models utilizados

### `Processo`

| Campo | Tipo | Observações |
|---|---|---|
| `titulo` | `CharField` | Obrigatório |
| `numero` | `CharField` | Opcional, formato CNJ |
| `area_direito` | `CharField` choices | 9 áreas |
| `instancia` | `CharField` | 4 opções fixas no form |
| `vara_juizo` | `CharField` | Opcional |
| `valor_causa` | `DecimalField` | Opcional |
| `status` | `CharField` choices | ativo/suspenso/encerrado/arquivado |
| `fase` | `CharField` choices | 6 fases processuais |
| `gratuidade_justica_status` | `CharField` choices | 5 opções |
| `data_distribuicao` | `DateField` | Opcional |
| `prazo_proximo` | `DateField` | Opcional; alimenta `prazo_urgente` e `prazo_label` |
| `cliente` | `FK → Cliente` | `SET_NULL`; obrigatório no form |
| `responsavel` | `FK → User` | `SET_NULL`; definido automaticamente na view `novo()` |
| `criado_em` | `DateTimeField` | `auto_now_add` |

Properties:
- `prazo_urgente` → `bool` — prazo em ≤ 3 dias
- `prazo_label` → `str` — "em N dias", "hoje", "amanhã", "prazo vencido", "sem prazo"

### `MovimentacaoProcessual`

| Campo | Tipo | Observações |
|---|---|---|
| `processo` | `FK → Processo` | CASCADE, `related_name="movimentacoes"` |
| `descricao` | `TextField` | Obrigatório |
| `data` | `DateTimeField` | `default=timezone.now`; widget `datetime-local` |
| `autor` | `FK → User` | `SET_NULL`; definido na view via `commit=False` |
| `tipo` | `CharField` choices | andamento/prazo/decisao/audiencia/outro |

### `ParteProcesso`

| Campo | Tipo | Observações |
|---|---|---|
| `processo` | `FK → Processo` | CASCADE, `related_name="partes"` |
| `nome` | `CharField` | Obrigatório |
| `tipo` | `CharField` choices | autor/reu/terceiro/advogado_contrario |
| `cpf_cnpj` | `CharField` | Opcional |

---

## Forms implementados

### `ProcessoForm`

- 11 campos: `titulo`, `numero`, `cliente`, `area_direito`, `fase`, `instancia`, `vara_juizo`, `valor_causa`, `data_distribuicao`, `gratuidade_justica_status`, `prazo_proximo`
- `cliente` declarado explicitamente como `ModelChoiceField` (queryset: `Cliente.objects.filter(ativo=True)`)
- `instancia` declarado como `ChoiceField` com 4 opções fixas
- Datas usam `DateInput(type="date", format="%Y-%m-%d")`
- `status` e `responsavel` excluídos intencionalmente — definidos na view

### `ParteProcessoForm`

- 3 campos: `nome`, `tipo`, `cpf_cnpj`

### `MovimentacaoProcessualForm`

- 3 campos: `tipo`, `data`, `descricao`
- `data` declarado explicitamente como `DateTimeField` com `initial=timezone.now`, `input_formats=["%Y-%m-%dT%H:%M"]`, widget `DateTimeInput(type="datetime-local", format="%Y-%m-%dT%H:%M")`

---

## Decisões técnicas

- **`status="arquivado"` como soft state** — não existe campo `ativo`. Arquivamento usa `status` já presente no model, sem migration adicional.
- **`exclude(status="arquivado")` em vez de `filter(status="ativo")`** — mais robusto: processos com `status="suspenso"` ou `status="encerrado"` aparecem na listagem principal, pois só o arquivamento retira da lista.
- **`commit=False` para `responsavel` e `autor`** — campos FK definidos na view antes de salvar, mantendo-os fora do formulário.
- **`DateTimeInput` com `format` e `input_formats` para `data` de movimentação** — necessário para compatibilidade bidirecional com o input HTML `datetime-local`.
- **`DateInput` com `format="%Y-%m-%d"` para campos `DateField`** — necessário para pré-preenchimento correto no modo edição.
- **`select_related + prefetch_related` no detalhe** — evita N+1 queries ao renderizar partes e movimentações.
- **`timezone.localdate()` em vez de `date.today()`** — respeita o timezone configurado no Django.
- **Rota `arquivados/` antes de `<int:pk>/`** — estáticas antes de dinâmicas para evitar ambiguidade de URL.
- **`reabrir()` redireciona para detalhe** — serve tanto o fluxo do detalhe quanto o da lista de arquivados; o usuário tem confirmação visual imediata do novo estado.

---

## Decisões de produto

- **Processo arquivado sai da listagem principal** — `exclude(status="arquivado")` garante que apenas processos ativos, suspensos e encerrados aparecem em `/processos/`.
- **Processo arquivado continua acessível por URL direta** — `get_object_or_404(Processo, pk=pk)` sem filtro de status no detalhe.
- **Reabrir volta para `status="ativo"`** — sem preservar status anterior (suspenso/encerrado), pois esses estados ainda não têm fluxo de entrada pela interface.
- **Cliente obrigatório no formulário de criação** — `required=True` no `ModelChoiceField`.
- **Responsável definido automaticamente** — `processo.responsavel = request.user` na view `novo()`.
- **Arquivar por confirmação JS** — `onclick="return confirm(...)"` no botão do detalhe, sem modal dedicado.
- **Partes e movimentações via formulários inline** — mesmo padrão de UX, POST-only, sem tela separada.
- **Documentos e Prazos ficam para futuro** — abas presentes no template com empty state; contadores removidos.

---

## Arquivos principais

| Arquivo | Descrição |
|---|---|
| `apps/processos/models.py` | 3 models: `Processo`, `MovimentacaoProcessual`, `ParteProcesso` |
| `apps/processos/forms.py` | 3 forms: `ProcessoForm`, `ParteProcessoForm`, `MovimentacaoProcessualForm` |
| `apps/processos/views.py` | 9 views |
| `apps/processos/urls.py` | 9 rotas |
| `apps/processos/migrations/0001_initial.py` | Migration inicial |
| `apps/processos/migrations/0002_*.py` | Campos jurídicos + `data` de movimentação |
| `templates/processos/lista.html` | Listagem de ativos + link para arquivados |
| `templates/processos/detalhe.html` | Detalhe com abas, formulários inline, banner de arquivado |
| `templates/processos/form.html` | Formulário de criação e edição |
| `templates/processos/arquivados.html` | Lista de arquivados + reabrir inline |

---

## Pendências futuras

### Alta prioridade (impacto direto no uso diário)

- **Edição/exclusão de partes** — hoje só é possível adicionar
- **Edição/exclusão de movimentações** — hoje só é possível adicionar
- **Campos adicionais de partes** — OAB, e-mail, telefone, qualificação completa, endereço

### Média prioridade

- **Prazos processuais estruturados** — model `PrazoProcessual` com `data_limite`, `tipo`, `cumprido`, `dias_uteis`
- **Cálculo de prazos úteis** — excluindo feriados e fins de semana
- **Documentos processuais** — upload real, categorização, download, versionamento
- **Busca/filtros reais** — a barra de busca visual existe no template sem lógica real
- **Paginação** — quando o volume justificar

### Baixa prioridade / longo prazo

- **Permissões por grupo/cargo** — usuários comuns vs. gerente/dono do tenant
- **Auditoria/logs** — quem arquivou, editou, reabriu e quando
- **Lista/filtros por status/fase** — suspensos, encerrados, em fase recursal
- **Apensos** — processos relacionados/vinculados
- **Importação de movimentações de tribunais** — e-SAJ, PJe, TJSP
- **Integração com IA** — análise de petição inicial, contestação, sentença, recursos, execução
- **Qualificação completa das partes** — endereço, estado civil, profissão, representante legal

---

## Próximos passos recomendados

**Fase 2.3 — Tarefas** — vinculadas a processos e clientes, com prazo, responsável e status de conclusão.

Justificativa: tarefas são o workflow operacional mais imediato para o usuário de escritório. Sem controle de tarefas, o usuário depende de ferramentas externas para acompanhar atividades cotidianas (pesquisar jurisprudência, revisar petição, protocolar, ligar para cliente).
