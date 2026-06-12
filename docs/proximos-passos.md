# Próximos Passos

## Fluxo de bootstrap — ordem obrigatória

O bootstrap inicial segue esta sequência e não deve ser alterada sem entendimento prévio.
Cada etapa depende da anterior. Não executar `migrate_schemas` completo (sem `--shared`)
fora deste fluxo sem aprovação explícita.

```
1. migrate_schemas --shared       ← cria tabelas no schema público
2. Criar tenant public via shell  ← registra o schema público no django-tenants
3. Criar tenant demo via shell    ← cria schema demo + roda migrations de tenant automaticamente
4. Criar superusuário no demo     ← cria o primeiro usuário de acesso
5. Configurar hosts do Windows    ← permite resolver demo.localhost
6. Compilar Tailwind              ← gera output.css
7. Rodar servidor                 ← python manage.py runserver
8. Validar no navegador           ← http://demo.localhost:8000/login/
```

---

## Bloco 5 — migrate_schemas --shared

```bash
python manage.py migrate_schemas --shared
```

Cria todas as tabelas no schema `public`:
`django_tenants_*`, `saas_tenants_*`, `saas_billing_*`, `auth_*`, `django_session`, etc.

**Pré-condição:** `.env` configurado e banco `juridico_db` acessível. ✅

> Não rodar `migrate_schemas` sem `--shared` neste momento.
> O comando sem flag migraria todos os tenants existentes — nenhum existe ainda,
> tornando-o desnecessário e potencialmente confuso nesta etapa.

---

## Bloco 6 — Criar tenants via shell

```bash
python manage.py shell
```

```python
from apps.saas_tenants.models import Escritorio, Dominio

# Tenant público — obrigatório para django-tenants funcionar
public = Escritorio(schema_name='public', slug='public', nome='Público')
public.save(verbosity=0)
Dominio.objects.create(domain='localhost', tenant=public, is_primary=True)

# Tenant demo — auto_create_schema=True cria o schema 'demo' e
# roda automaticamente as migrations de todos os TENANT_APPS
demo = Escritorio(schema_name='demo', slug='demo', nome='Escritório Demo')
demo.save(verbosity=0)
Dominio.objects.create(domain='demo.localhost', tenant=demo, is_primary=True)

print(list(Escritorio.objects.values_list('schema_name', flat=True)))
```

---

## Bloco 7 — Criar superusuário no tenant demo

```bash
python manage.py tenant_command createsuperuser --schema=demo
```

Você digita username, email e senha diretamente no terminal.
Nenhuma credencial passa pelo chat.

---

## Bloco 8 — Hosts do Windows

Abra o Notepad como Administrador e edite:

```
C:\Windows\System32\drivers\etc\hosts
```

Adicione a linha:

```
127.0.0.1  demo.localhost
```

Sem isso, o navegador não resolverá `demo.localhost` e retornará ERR_NAME_NOT_RESOLVED.

---

## Bloco 9 — Compilar Tailwind

```bash
npm run build
```

Gera `static/css/output.css` a partir de `static/css/input.css`.
Recompilar sempre que houver alteração nos templates.

---

## Bloco 10 — Rodar o servidor

```bash
python manage.py runserver
```

---

## Bloco 11 — Validar no navegador

URL de acesso: `http://demo.localhost:8000/login/`

- [ ] Página de login carrega com visual correto
- [ ] Login com superusuário funciona
- [ ] Sidebar exibe todos os itens
- [ ] Navegação entre módulos funciona
- [ ] `item_ativo` destaca o item correto na sidebar
- [ ] Header exibe iniciais ou nome do usuário
- [ ] Dados mockados aparecem nas listagens
- [ ] Tailwind aplicado corretamente (cores, tipografia, cards)
