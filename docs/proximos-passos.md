# Próximos Passos

## Status da Fase 1 — Concluída

✅ Bloco 1 — Verificar PostgreSQL  
✅ Bloco 2 — Criar banco juridico_db  
✅ Bloco 3 — Criar .env  
✅ Bloco 4 — makemigrations  
✅ Bloco 5 — migrate_schemas --shared  
✅ Bloco 6 — Criar tenants public e demo  
✅ Bloco 7 — Criar superusuário no schema demo  
✅ Bloco 8 — Hosts Windows  
✅ Bloco 9 — Compilar Tailwind  
✅ Bloco 10 — Rodar servidor  
✅ Bloco 11 — Validar no navegador  

**Fase 1 — Estrutura Visual** finalizada com sucesso.

---

## Fase 2.1 — Clientes (CRUD Real) — Concluída ✅

Todas as funcionalidades implementadas, testadas e commitadas:

✅ Listagem real (`Cliente.objects.filter(ativo=True)`)  
✅ Criação real (`ClienteForm` + POST)  
✅ Detalhe real (`get_object_or_404` com `ativo=True`)  
✅ Edição real (`ClienteForm(instance=cliente)`)  
✅ Soft delete / desativação (`ativo=False`)  
✅ Tela de clientes inativos  
✅ Reativação (`ativo=True`)  
✅ Mocks removidos de `views.py`  

### Pendências futuras de Clientes (não bloqueantes)

Estas funcionalidades serão implementadas em etapa posterior, após os demais módulos terem CRUD real:

- Busca/filtros reais (a barra de busca visual já existe no template)
- Paginação (quando o volume de clientes justificar)
- Validação avançada de CPF/CNPJ (formato e dígito verificador)
- Permissões por grupo/cargo (usuários comuns vs. gerente/dono)
- Hard delete restrito a gerente/dono (com aviso de perda de histórico)
- Auditoria/logs de ações sobre clientes
- Contagem real de processos por cliente no card da lista

---

## Fase 2.2 — Processos (próximo módulo)

### Objetivo

Implementar CRUD real do módulo Processos, seguindo o mesmo padrão estabelecido em Clientes.

### O que o model `Processo` já tem

- `titulo`, `numero`, `area_direito`, `instancia`, `vara_juizo`
- `valor_causa`, `status`, `prazo_proximo`
- `cliente` (ForeignKey → Cliente)
- `responsavel` (ForeignKey → User)
- `criado_em`
- Relacionamentos: `MovimentacaoProcessual`, `ParteProcesso`

### Escopo da Fase 2.2

**Funcionalidades a implementar (na sequência):**

1. **Listagem real** — `Processo.objects.filter(ativo=True)` ou todos (sem soft delete ainda)
2. **Criação real** — `ProcessoForm` + POST handler
3. **Detalhe real** — dados do processo + movimentações + partes
4. **Edição real** — `ProcessoForm(instance=processo)`
5. **Soft delete / desativação** — campo `ativo` se não existir (verificar model)
6. **Vínculo com Cliente** — na tela de detalhe do cliente, processos reais aparecem

### Não fazer na Fase 2.2

- Busca/filtros reais
- Permissões granulares
- Integração com APIs de tribunais
- Upload de documentos processuais
- Automações jurídicas

---

## Após Processos estar funcional

Replicar o padrão para os demais módulos na ordem de prioridade de negócio:

1. **Tarefas** — vinculadas a processos e clientes
2. **Agenda** — compromissos e prazos
3. **Financeiro** — lançamentos e custas por processo
4. **Modelos** — templates de peças jurídicas
5. **Chat** — conversas internas por processo ou geral
6. **Configurações** — usuários do escritório por tenant

Cada módulo seguirá o mesmo padrão: listar → detalhar → criar → editar → desativar/reativar.
