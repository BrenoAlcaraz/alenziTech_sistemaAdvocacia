# Encerramento da Fase 1

## Escopo concluído

### Infraestrutura
- Multi-tenancy configurada: PostgreSQL 16 + django-tenants, schema por escritório
- Schemas `public` e `demo` criados, migrations aplicadas e sincronizadas
- `auth.User` + `PerfilUsuario` OneToOne com sinal de criação automática
- Autenticação completa: login, logout, `@login_required`, `@requer_admin_escritorio`
- CSRF 100% nos formulários com POST
- PRG (Post/Redirect/Get) com proteção contra open redirect em todas as views de ação
- Context processor `tenant_config` injeta `tenant` e `config_visual` em todos os templates

### Módulos funcionais
- **Dashboard**: métricas reais (clientes, processos, tarefas, compromissos, financeiro)
- **Clientes**: CRUD completo, desativar/reativar, filtro de inativos
- **Processos**: CRUD completo, movimentações, partes, arquivar/reabrir, filtros
- **Tarefas**: CRUD completo, quadro kanban, lista, transições de status
- **Financeiro — Lançamentos**: CRUD completo, filtros, marcar pago, cancelar, reabrir
- **Financeiro — Custas Judiciais**: formulário real usando `CustaJudicial`, saldo por cliente calculado
- **Agenda**: CRUD completo, compromissos com participantes e vínculos
- **Chat**: sala global funcional com envio de mensagens e histórico por tenant
- **Modelos de peças**: CRUD completo, busca, importação de PDF e DOCX
- **Configurações**: editar perfil, editar escritório, criar usuário, equipes, permissões por papel

### Permissões (fundação provisória)
- Models `PermissaoPapel`, `PermissaoUsuario`, `HabilitacaoPapel`, `HabilitacaoUsuario` criados
- Papéis ativos: `administrador_escritorio`, `limitado`, `financeiro`
- Seeds populados via migration para os papéis `limitado` e `financeiro`
- Interface de configuração de permissões por papel disponível no painel admin
- Decorator `@requer_admin_escritorio` aplicado nas rotas de gestão

---

## Decisões adiadas para a Fase 2

### Permissões e acesso
- Aplicação efetiva de `tem_permissao_modulo()` e `tem_habilitacao()` nas views
- Filtragem de querysets por nível (`somente_seus` vs. `todos`)
- Acesso filtrado por responsável e equipe
- Regras de visibilidade por módulo (IDOR intra-tenant intencional na Fase 1)

### Funcionalidades de módulo
- Chat em tempo real via Django Channels (WebSocket)
- Conversas individuais e em grupo
- Notificações reais (sino sem dados na Fase 1)
- Calendário dinâmico na Agenda (view de calendário removida por ser estática)
- OCR para PDFs escaneados no módulo Modelos
- Estilo do escritório (`EstiloEscritorio`) — aba "Meu estilo" reservada
- Exportação de documentos e relatórios
- Laboratório de IA (módulo `laboratorio` é shell visual)
- Exclusão de custas judiciais

### SaaS e billing
- Configuração real de Planos e Assinaturas (saas_billing existe mas sem dados)
- Bloqueio por limites de plano (processos, usuários)
- Pagamentos e renovação de assinatura

### Qualidade e infraestrutura
- Testes automatizados (unitários e de integração)
- Refatoração do singleton `ConfiguracaoEscritorio.objects.get_or_create(pk=1)` para lookup sem PK fixa
- Docker e containerização
- Configuração de segurança HTTPS (`SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_HSTS_SECONDS`)
- Remoção do fallback inseguro de `SECRET_KEY` em `settings/base.py`
- `django-debug-toolbar` (declarado em `requirements/development.txt` mas não ativado)

---

## Limitações conhecidas e aceitas

| Limitação | Módulo | Observação |
|---|---|---|
| Arquivo original de PDF/DOCX não armazenado | Modelos | Texto extraído e salvo; arquivo descartado após import |
| PDFs escaneados sem suporte (sem OCR) | Modelos | Mensagem de aviso exibida ao usuário |
| Chat sem tempo real | Chat | Envio funcional via HTTP; sem WebSocket |
| Regras financeiras mínimas | Financeiro | Sem conciliação bancária, parcelamento ou aprovação |
| Plano SaaS não configurado | Billing | Badge mostra "Não configurado" onde não há assinatura |
| Permissões não enforçadas nas views | Accounts | Fundação construída; aplicação prevista para Fase 2 |
| Grupos legados `gerente` e `advogado` | Accounts | Preservados no banco; não atribuíveis a novos usuários |

---

## Estado do banco (demo) no encerramento

| Entidade | Contagem |
|---|---|
| Usuários | 2 |
| Clientes | 10 |
| Processos | 7 |
| Tarefas | 5 |
| Compromissos | 6 |
| Lançamentos Financeiros | 9 |
| Custas Judiciais | 0 |
| Conversas (sala global) | 1 |
| Mensagens | 7 |
| Modelos de peças | 5 |
| Escritórios (public) | 2 |
| Planos | 0 |
| Assinaturas | 0 |

---

## Commit de encerramento

```
HEAD: 5bc4d88 feat(modelos): implementar modelos e importacao de documentos
```

As correções finais desta etapa (Fase 2.14B) serão commitadas separadamente após revisão literal.
