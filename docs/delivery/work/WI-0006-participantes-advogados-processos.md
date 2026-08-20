---
title: WI-0006 — Participantes processuais e advogados das partes
status: canonical
owner: delivery
last_reviewed: 2026-08-20
---

# WI-0006 — Participantes processuais e advogados das partes

## Estado

in_progress

## Fase do roadmap

Fase: Fase C — Integridade de domínio

Objetivo relacionado: materializar em Processos as dimensões de participante,
representação e autoridade aprovadas por PDR-0001 e PDR-0011, sobre a fronteira
de autorização e responsabilidade entregue pelo H1 do WI-0005.

## Objetivo

Evoluir a aba Partes para taxonomia estruturada, autoridade separada e múltiplos
advogados por parte, preservando dados legados, garantindo o Cliente do Processo
como participante automático único e aplicando o preenchimento idempotente do
responsável tanto pela identidade conhecida por FK quanto pela correspondência
exata de CPF/CNPJ normalizado.

## Resultado observável pelo Product Owner

### Ao concluir este WI

- na aba Partes do Processo existe a nova classificação processual;
- participantes aparecem agrupados em Polo Ativo, Polo Passivo e Outros;
- advogado deixa de ser tipo de parte;
- cada parte pode possuir múltiplos advogados;
- advogados aparecem abaixo da respectiva parte;
- é possível adicionar e remover advogado da parte;
- o Cliente vinculado aparece automaticamente, inclusive sem CPF/CNPJ, e pode
  aguardar classificação sem receber qualificação jurídica inferida;
- classificar ou alterar a classificação preserva o participante e registra
  histórico;
- o cliente vinculado ao processo pode receber automaticamente o responsável do
  processo como advogado interno pela regra exata de CPF/CNPJ.

### Ainda não estará coberto

- Apensos e relação Processo ↔ Processo;
- WI-0007;
- alteração do escopo ou da responsabilidade do WI-0005;
- equipe como autorização;
- IA e Laboratório.

## Contexto e motivação

O H1 do WI-0005 está publicado no commit
`1b3f731d0a0e29c27f8747a7819b1ef18a5274f2`, com implementação e review
técnico aprovados. Sua validação manual foi deliberadamente adiada pelo Product
Owner para execução conjunta após WI-0005, WI-0006 e WI-0007; por isso WI-0005
permanece `in_progress`, sem H2 e sem alteração comportamental neste item.

O risco deste WI é alto/moderado: mudança de schema, migration de dados
existentes, relacionamento 1:N, autorização por objeto, integração com Cliente
e `Processo.responsavel`, e preservação de registros legados cuja semântica não
pode ser inferida.

## Evidência do estado atual

Auditoria do HEAD inicial
`1b3f731d0a0e29c27f8747a7819b1ef18a5274f2`:

- `ParteProcesso.tipo` mistura `autor`, `reu`, `terceiro` e
  `advogado_contrario` em um único campo;
- não existem models de representante nem autoridade processual;
- a aba Partes lista registros linearmente e permite somente adicionar parte;
- `PerfilUsuario` não possui OAB/UF-OAB;
- `Processo.responsavel` é obrigatório e a fronteira de mutação usa
  `_processos_mutaveis()`: responsável para não-admin e todos para Admin;
- o usuário não-admin com nível Todos lê processo alheio, mas não o modifica;
- `Processo.cliente` e `Cliente.cpf_cnpj` permitem a comparação exata aprovada,
  sem necessidade de buscar outro Cliente do tenant.

## Resultado esperado

`ParteProcesso` separa vínculo com escritório, posição estrutural e
qualificação; juiz é persistido como autoridade; representantes são registros
normalizados 1:N; advogado interno referencia `User` e externo possui campos
profissionais; automação compara CPF/CNPJ normalizado apenas com
`Processo.cliente`; constraints e lógica idempotente evitam duplicidade; novas
mutações reutilizam a fronteira do WI-0005 e retornam 404 fora dela; migrations
preservam todas as linhas históricas.

## Fontes canônicas

- [PDR-0001](../../product/decisions/PDR-0001-participantes-processuais.md)
- [PDR-0011](../../product/decisions/PDR-0011-taxonomia-representacao-participantes-processos.md)
- [PDR-0010](../../product/decisions/PDR-0010-autorizacao-escopo-responsabilidade-processos.md)
- [Processos](../../product/modules/processos.md)
- [Visão geral de segurança](../../security/overview.md)
- [Modelo de autorização](../../security/authorization-model.md)
- [Escopo de dados](../../security/data-scope.md)
- [Matriz de autorização — Processos](../../security/authorization-matrix.md#processos)
- [Roadmap](../roadmap.md)
- [WI-0005](WI-0005-escopo-responsabilidade-processos.md)

## Arquivos do HEAD a auditar antes da implementação

- `apps/processos/models.py`, `forms.py`, `views.py`, `urls.py`, `admin.py`;
- `apps/processos/services.py`, `migrations/`, `tests/`;
- `templates/processos/`;
- `apps/clientes/models.py`;
- `apps/accounts/models.py`, `permissoes.py`, `decorators.py`;
- configuração de PostgreSQL/django-tenants e harness de migrations.

## Escopo permitido

### Pode alterar

- models, forms, views, URLs, services e admin de `apps/processos`;
- aba Partes em `templates/processos/`;
- testes existentes de Processos necessários para o novo contrato estrutural;
- documentação diretamente necessária ao WI e à decisão de produto.

### Pode criar

- PDR-0011 e atualização de seus índices;
- migrations explícitas de schema e dados;
- testes de participantes, representantes, migration, autorização e IDOR;
- parcial de template para card de participante.

### Migrations

Obrigatórias. Schema inicial anulável, data migration preservadora e schema
final obrigatório devem permanecer separados. Validar PostgreSQL,
django-tenants, dados preexistentes, rollback e reaplicação. Nenhum `DELETE` de
linhas legadas.

### Documentação

- este Work Item e sua evidência de execução;
- PDR-0011, índices de decisões e referência do módulo Processos;
- `current-state.md` somente após H1/review/fechamento, não nesta preparação.

## Fora de escopo

- Apensos, cards de apensos ou relação Processo ↔ Processo;
- WI-0007;
- novas habilitações de Processos;
- equipe, `Da equipe` ou hierarquia como autorização;
- mudanças no kernel de Accounts ou na fronteira do WI-0005;
- cadastro profissional/OAB em Accounts;
- diretório global de advogados externos;
- documentos, IA e Laboratório.

## Regras funcionais e técnicas

- seletor agrupado: Autor/Embargante/Recorrente; Réu/Embargado/Recorrido;
  Terceiro Interessado/Ministério Público/Amicus Curiae/Juiz;
- grupo visual não substitui posição e qualificação separadas;
- Ministério Público registra atuação como parte ou fiscal;
- juiz usa model de autoridade, com tipo, nome, vara/órgão e observação;
- cada parte admite zero, um ou vários representantes;
- interno referencia `User`; externo registra nome, OAB, UF, telefone e e-mail;
- não existe OAB inventada para interno;
- remoção exclui somente representação;
- documento é normalizado para dígitos e comparado por igualdade exata;
- somente `Processo.cliente` pode ser reconhecido pela automação;
- `Processo.responsavel` é o representante automático e não pode duplicar;
- `Processo.cliente` possui um único participante por FK; quando ainda não há
  classificação informada, somente esse vínculo pode permanecer pendente;
- nome e CPF/CNPJ de participante vinculado a Cliente são exibidos a partir do
  cadastro atual de Cliente;
- mudanças de classificação preservam o PK e registram estado anterior, novo,
  data/hora e usuário quando disponível;
- constraints e validação de domínio impedem combinações incompatíveis da
  taxonomia, MP incompleto, legado normal e representante híbrido;
- reenvio externo idêntico é idempotente dentro da mesma Parte por identidade
  normalizada;
- `advogado_contrario` legado é preservado sem associação inferida.

## Segurança e autorização

- leitura segue `_processos_no_escopo()` do WI-0005;
- mutações seguem `_processos_mutaveis()` do WI-0005;
- não-admin com Todos lê processo alheio, mas não adiciona/remove advogado;
- URL/POST fora da fronteira retorna 404 sem mutação;
- Admin modifica qualquer Processo do schema atual;
- nenhum queryset de runtime atravessa schemas de tenants.

## Decisões abertas e bloqueios

Nenhuma `OPEN-*` afeta este item. PDR-0011 registra as decisões diretas do
Product Owner e complementa PDR-0001 sem substituí-lo.

## Dependências

- H1 do WI-0005 em `1b3f731d0a0e29c27f8747a7819b1ef18a5274f2`;
- PostgreSQL e django-tenants;
- `Processo.cliente`, `Processo.responsavel` e `auth.User` existentes.

## Critérios de aceite

- [x] dez opções disponíveis e mapeadas aos três grupos;
- [x] posição, qualificação e vínculo persistidos separadamente;
- [x] juiz é autoridade separada e Ministério Público preserva duas atuações;
- [x] advogado não é parte e a cardinalidade zero/um/vários existe no banco;
- [x] interno reutiliza User e externo registra dados profissionais sem CPF;
- [x] adicionar, exibir e remover advogado preservam entidades relacionadas;
- [x] automação por CPF/CNPJ usa somente o Cliente do Processo e é idempotente;
- [x] Cliente do Processo possui participante automático único, inclusive sem
  CPF/CNPJ, com classificação pendente sem inferência jurídica;
- [x] criação, alteração de Cliente e migration reconciliam o participante sem
  apagar silenciosamente informação anterior;
- [x] identidade vinculada exibe dados atuais de Cliente;
- [x] mudança de classificação preserva o participante e gera histórico;
- [x] taxonomia, Ministério Público, legado e separação interno/externo possuem
  validação de domínio e constraints de banco;
- [x] reenvio idêntico do mesmo representante externo na mesma Parte é
  idempotente;
- [x] usuário Todos não modifica participantes de processo alheio e recebe 404;
- [x] Admin adiciona/remove advogado em processo alheio do tenant;
- [x] migrations preservam autor, réu, terceiro e advogado_contrario;
- [x] WI-0005, WI-0007 e Apensos permanecem inalterados.

## Testes esperados

### Existentes a considerar

- `apps/processos/tests/test_autorizacao.py`;
- `apps/processos/tests/test_escopo.py`;
- `apps/processos/tests/test_migrations.py`;
- suítes de Accounts e Clientes como regressão obrigatória.

### Novos testes

- taxonomia, agrupamento e autoridade;
- zero, um e múltiplos representantes;
- interno, externo, exibição e remoção;
- normalização, matching positivo/negativo e idempotência;
- IDOR para Somente os seus/Todos e caminho Admin;
- migration histórica, preservação, rollback e reaplicação.
- Cliente automático na criação/edição, sem documento, sincronização,
  unicidade, identidade atual e representante interno;
- classificação pendente, transições com histórico e autorização/IDOR;
- combinações inválidas da taxonomia/MP/legado e representantes híbridos;
- reenvio externo normalizado e idempotente.

## Correções após review independente

O review técnico independente inicial reprovou o primeiro staged com cinco
findings. O delta-review independente posterior aprovou integralmente os
Findings 2 e 4. As correções dos Findings 1, 3 e 5 foram implementadas nesta
rodada final e aguardam novo delta-review independente; este registro não as
declara aprovadas antes dessa revisão.

O escopo acumulado das correções permanece restrito aos cinco findings:

1. Cliente automático: vínculo por FK, estado pendente restrito, sincronização
   na criação/edição e migration, identidade atual, unicidade e advogado
   automático inclusive sem CPF/CNPJ.
2. Histórico: model normalizado e fluxo mínimo de classificação/alteração que
   preserva o PK e registra usuário HTTP.
3. Integridade: validação de model e constraints para taxonomia, MP, pendência e
   legado, também aplicáveis a ORM/Admin.
4. Representantes: interno exige User e campos externos vazios; externo exige
   User nulo e identidade profissional mínima.
5. Idempotência externa: fingerprint de identidade normalizada com unicidade
   condicionada à mesma Parte.

### Comandos de validação

- `.venv\Scripts\python.exe manage.py test apps.processos --noinput`
- `.venv\Scripts\python.exe manage.py test apps.accounts --noinput`
- `.venv\Scripts\python.exe manage.py test apps.clientes --noinput`
- `.venv\Scripts\python.exe manage.py check`
- `.venv\Scripts\python.exe manage.py makemigrations --check --dry-run`
- `npm run build`
- `git diff --check`
- `git diff --cached --check`

## Quality gates

- [x] testes alvo executados
- [x] testes negativos executados
- [x] suítes Processos, Accounts e Clientes executadas
- [x] migration PostgreSQL/django-tenants, rollback e reaplicação validados
- [x] `manage.py check` e migrations pendentes verificados
- [x] frontend Tailwind recompilado e revisado
- [x] `git diff --check`
- [x] diff revisado integralmente
- [x] links e documentação verificados

## Atualizações documentais esperadas

Registrar comandos e resultados neste WI. Não atualizar `current-state.md` nem
marcar Fase B formalmente concluída enquanto o fechamento/validação manual do
WI-0005 estiver pendente.

## Achados fora do escopo

- `npm run build` informa que a base `caniuse-lite` está desatualizada. O build
  conclui normalmente; atualizar dependências não pertence ao WI-0006.

## Evidência de execução

### Estado inicial

Branch: `docs/reorganizacao-harness`

HEAD: `1b3f731d0a0e29c27f8747a7819b1ef18a5274f2`

Git status: limpo; branch sincronizada com
`origin/docs/reorganizacao-harness` após `git fetch origin`.

### Arquivos alterados

- `apps/processos/admin.py`
- `apps/processos/forms.py`
- `apps/processos/migrations/0007_participantes_representantes_schema.py`
- `apps/processos/migrations/0008_migrar_partes_legadas.py`
- `apps/processos/migrations/0009_participantes_campos_obrigatorios.py`
- `apps/processos/models.py`
- `apps/processos/services.py`
- `apps/processos/tests/test_autorizacao.py`
- `apps/processos/tests/test_escopo.py`
- `apps/processos/tests/test_migrations_participantes.py`
- `apps/processos/tests/test_participantes.py`
- `apps/processos/urls.py`
- `apps/processos/views.py`
- `docs/delivery/work/WI-0006-participantes-advogados-processos.md`
- `docs/governance/decision-index.md`
- `docs/product/decisions/PDR-0011-taxonomia-representacao-participantes-processos.md`
- `docs/product/decisions/README.md`
- `docs/product/modules/processos.md`
- `static/css/output.css`
- `tailwind.config.js`
- `templates/processos/_parte_card.html`
- `templates/processos/detalhe.html`

### Testes executados

- correção final dos Findings 1, 3 e 5:
  `.venv\Scripts\python.exe manage.py test
  apps.processos.tests.test_participantes --noinput` — 37/37 verdes; cobre
  exclusão individual/em massa pelo Admin, cascata legítima do Processo, troca
  A → B → A, constraint bidirecional de legado, bypass de representante
  híbrido, normalização equivalente da OAB, persistência do fingerprint com
  `update_fields`, identidade externa por Parte e gaps de histórico;
- `.venv\Scripts\python.exe manage.py test apps.processos --noinput` — 88/88
  verdes na execução final;
- `.venv\Scripts\python.exe manage.py test apps.accounts --noinput` — 86/86
  verdes na execução final;
- `.venv\Scripts\python.exe manage.py test apps.clientes --noinput` — 57/57
  verdes na execução final;
- `.venv\Scripts\python.exe manage.py test
  apps.processos.tests.test_migrations_participantes --verbosity 2 --noinput`
  — 1/1 verde na primeira execução isolada e 1/1 verde na segunda execução
  isolada; em ambas, PostgreSQL/django-tenants executou o ciclo histórico
  `0006 → 0009 → 0006 → 0009` com preservação das PKs legadas e criação do
  participante pendente diante de múltiplas candidatas documentais.

- `.venv\Scripts\python.exe manage.py test
  apps.processos.tests.test_participantes --verbosity 2 --noinput` — 12/12
  verdes na primeira rodada incremental; os reforços posteriores foram
  incluídos na suíte final.
- `.venv\Scripts\python.exe manage.py test
  apps.processos.tests.test_migrations_participantes --verbosity 2 --noinput` —
  1/1 verde em PostgreSQL/django-tenants, com estado histórico `0006`,
  aplicação até `0009`, criação do Cliente automático pendente inclusive sem
  documento, rollback e reaplicação.
- `.venv\Scripts\python.exe manage.py test
  apps.processos.tests.test_participantes --noinput` — 27/27 verdes após as
  correções do review; 11 testes adicionais cobrem Cliente automático,
  pendência, identidade, histórico, constraints, autorização e idempotência
  externa.
- `.venv\Scripts\python.exe manage.py test apps.processos --noinput` — 78/78
  verdes na execução final; inclui 28 testes novos deste WI,
  negativos de módulo/escopo/IDOR, constraints e migration histórica.
- `.venv\Scripts\python.exe manage.py test apps.accounts --noinput` — 86/86
  verdes na execução final sobre o grafo final de migrations.
- `.venv\Scripts\python.exe manage.py test apps.clientes --noinput` — 57/57
  verdes na execução final sobre o grafo final de migrations.

### Validações executadas

- `.venv\Scripts\python.exe manage.py check` — executado; zero issues.
- `.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` —
  executado; `No changes detected`.
- `npm run build` — executado; aprovado e `static/css/output.css` regenerado;
  aviso não bloqueante de `caniuse-lite` desatualizada.
- migration `0008`: cardinalidade 0/1/N validada sem busca global de Cliente;
  duas candidatas com documento equivalente foram preservadas, nenhuma foi
  vinculada arbitrariamente e uma nova Parte automática pendente foi criada;
- migration `0009`: constraint PostgreSQL rejeitou `registro_legado=False`
  combinado a taxonomia reservada ao legado por `bulk_create` e
  `QuerySet.update`, preservando o estado legado histórico válido;
- Django Admin: delete individual e em massa do participante correspondente ao
  Cliente atual foram bloqueados; participante de Cliente anterior permaneceu
  removível sem interferir na cascata de exclusão do próprio Processo;
- fingerprint externo: OAB alfanumérica, UF, nome, telefone e e-mail
  equivalentes convergiram na mesma Parte; `save(update_fields=...)` persistiu
  o novo fingerprint; Partes distintas aceitaram a mesma identidade externa.
- `git diff --check` — executado; nenhuma ocorrência.
- `git diff --cached --check` — executado; nenhuma ocorrência no staging
  final.
- validação dos cinco documentos alterados — links locais existentes, newline
  final, ausência de NUL, trailing whitespace e linhas só com espaços: aprovado.
- self-review por busca dirigida e leitura do diff: nenhum advogado novo como
  parte; juiz separado; nenhuma lista serializada; nenhuma limitação 1:1;
  Regra A por FK independente de documento e Regra B por matching exato;
  classificação pendente sem valor jurídico inventado; identidade de Cliente
  dinâmica; histórico normalizado; constraints de duplicidade/taxonomia/MP/
  legado/representantes; mutação de classificação sob `_processos_mutaveis()`;
  nenhuma implementação de Apensos, equipe como autorização, WI-0007 ou IA.

### Resultado

Findings 2 e 4 permanecem aprovados pelo delta-review anterior. As correções
dos Findings 1, 3 e 5 foram implementadas, testadas e aguardam novo
delta-review independente. O item continua `in_progress`, sem H1, sem H2 e sem
marcação `done` nesta preparação.

### Commit

Não autorizado nesta execução.

Git final: 22 arquivos do WI-0006 em staging explícito; working tree sem
alterações unstaged; nenhum commit e nenhum push.

## Encerramento

- [x] critérios de aceite verificados;
- [x] testes/validações registrados;
- [x] diff revisado;
- [x] escopo respeitado;
- [ ] current-state atualizado quando aplicável;
- [x] roadmap atualizado somente se necessário;
- [x] achados laterais registrados;
- [x] Git final registrado.
