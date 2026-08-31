# Comandos de desenvolvimento

## Ambiente

- Python: sem versão mínima fixada no repositório. `requirements/base.txt`
  fixa `django>=5.2,<5.3`, `django-tenants==3.10.1`.
- PostgreSQL obrigatório (`django_tenants.postgresql_backend`) — SQLite
  não funciona.
- Node/npm só para compilar CSS (Tailwind).

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements/development.txt
cp .env.example .env
npm install
```

Ferramentas **não** configuradas neste repositório — não presumir:
pytest, Ruff, Black, isort, mypy, pre-commit, tox, coverage, Docker,
Celery, Redis, CI.

## Banco / multitenancy

```bash
python manage.py migrate_schemas --shared   # schema público
python manage.py migrate_schemas            # todos os schemas de tenant
python manage.py makemigrations --check --dry-run
```

`python manage.py migrate` é, neste projeto, o mesmo comando que
`migrate_schemas` (django-tenants substitui o `migrate` padrão). Não há
fluxo canônico documentado de provisioning de tenant — `create_tenant`/
`create_domain`/`create_tenant_superuser` existem (django-tenants) mas
nenhum procedimento oficial define ordem/parâmetros.

## Testes

```bash
python manage.py test apps.<app>                    # suíte de um app
python manage.py test apps.<app>.tests.<modulo>      # um arquivo
python manage.py test                                # tudo
```

Runner é o padrão do Django; testes usam `TenantTestCase`
(django-tenants), exigem PostgreSQL real.

- **Mudança pequena**: teste alvo do que mudou.
- **Feature normal**: teste alvo + suíte do app antes de considerar
  pronto.
- **Mudança crítica** (autorização, IDOR/escopo, migration, kernel
  compartilhado): teste alvo + suíte do app + suítes de qualquer app
  consumidor do contrato alterado. Testes negativos (acesso negado,
  objeto fora de escopo, mutação sem efeito) são obrigatórios aqui.

Não repetir teste/gate sem motivo: evidência de uma sessão anterior
continua válida se o delta não tocou o arquivo/contrato que ela cobre.

## Django

```bash
python manage.py check              # validação estrutural, roda rápido
python manage.py runserver
python manage.py shell
```

Rodar `check` + `makemigrations --check --dry-run` para qualquer mudança
em `models.py`/`forms.py`/`views.py`/`urls.py`/settings.

## Migration

- Migration já aplicada é imutável — correção é sempre nova migration.
- Migration nova exige leitura integral do arquivo gerado antes de aceitar.
- Migration de dados (não só schema): testar com dados existentes,
  nulos e duplicados; considerar rollback/reapply quando reversível ou
  arriscada.
- Um `DELETE` (`RunPython`) seguido de `ALTER TABLE` na mesma tabela,
  na mesma migration, pode falhar em PostgreSQL com "pending trigger
  events" quando há linhas referenciadas por FK — se acontecer, separar
  com `atomic = False`, não reordenar operações às cegas.

## Frontend / Tailwind

```bash
npm run build     # compila static/css/output.css uma vez
npm run watch      # modo watch
```

Só necessário quando classe/template/CSS de entrada mudou. `content` do
Tailwind escaneia `templates/**/*.html`, `apps/**/*.html`,
`static/js/**/*.js` — **não** escaneia `.py`; uma classe usada só como
atributo de widget em um `forms.py` pode não ser reconhecida pelo build.
Antes de aceitar um `npm run build` completo, revisar o diff de
`static/css/output.css` — pode remover classes de outros módulos não
relacionados à mudança atual; nesse caso, prefira um patch manual das
classes realmente novas.

## Git

Preflight, sempre antes de alterar algo:

```bash
git branch --show-current
git log -1 --oneline
git status --short
```

- Staging explícito por arquivo (`git add caminho`), nunca `git add -A`/`.`.
- Revisar staged antes de commitar: `git diff --cached --stat`,
  `git diff --cached --check`.
- Mensagem: `tipo(escopo): descrição` (`feat`, `fix`, `docs`, `refactor`,
  `chore`, `style`) — curta, descreve o efeito real.
- Commit e push só com autorização explícita da sessão em andamento.
- Nunca `--force`, `reset --hard`, `clean -fd`, `rebase`,
  `commit --amend`, `checkout -- .`/`restore .` sem autorização
  explícita — nem mesmo para "limpar" o working tree mais rápido.
- Falha de push (rede/auth) não apaga o commit local — diagnosticar
  (`git fetch`, comparar local/remoto) e tentar de novo; nunca reescrever
  histórico por causa disso.
- `.gitattributes` é a autoridade de line endings do repositório —
  arquivos de texto em LF, independentemente do `core.autocrlf` local.
