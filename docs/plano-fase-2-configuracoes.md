# Plano Fase 2.7 — Configurações/Perfil

**Status**: concluído em nível básico  
**Data de conclusão**: 2026-07-08

---

## Objetivo do módulo

Organizar a estrutura administrativa do escritório dentro do tenant: listar usuários reais, permitir edição de perfil e cadastrar dados básicos do escritório.

---

## Funcionalidades entregues

| Funcionalidade | Status |
|---|---|
| Listagem real de usuários do tenant | ✅ |
| Remoção de `USUARIOS_MOCK` | ✅ |
| Contador real de usuários ativos | ✅ |
| Proteção contra `PerfilUsuario` inexistente | ✅ |
| Botão "Editar perfil" em `/configuracoes/` | ✅ |
| Tela `/configuracoes/perfil/editar/` | ✅ |
| Edição de `nome_completo` | ✅ |
| Edição de `cargo` | ✅ |
| Model `ConfiguracaoEscritorio` (tenant-specific) | ✅ |
| Migration `configuracoes.0001_initial` | ✅ |
| Admin de `ConfiguracaoEscritorio` | ✅ |
| Tela `/configuracoes/escritorio/` | ✅ |
| Card "Dados do escritório" em `/configuracoes/` | ✅ |
| Edição de `nome_escritorio`, `nome_fantasia`, `cnpj` | ✅ |
| Edição de `email`, `telefone`, `endereco`, `site`, `observacoes` | ✅ |
| Campo `site` aceita `google.com` → normaliza para `https://google.com` | ✅ |

---

## Decisões técnicas

### `PerfilUsuario` sem `AbstractUser`

O projeto usa `auth.User` padrão + `PerfilUsuario` OneToOne. Isso evita complexidade de migração de `AbstractUser` e mantém compatibilidade com `django-tenants`. O sinal `post_save` em `accounts/signals.py` cria o perfil automaticamente ao criar um novo usuário. A view usa `get_or_create` como segunda linha de defesa para usuários criados antes do signal.

### `ConfiguracaoEscritorio` sem FK para `Escritorio`

`Escritorio` vive no schema público (`SHARED_APPS`). Uma FK de um model tenant para um model público criaria uma referência cross-schema que o PostgreSQL não honra com integridade referencial real dentro do schema do tenant. A solução é um model simples sem FK — o isolamento é garantido pelo próprio schema do django-tenants.

### Singleton por tenant com `get_or_create(pk=1)`

`ConfiguracaoEscritorio` segue o padrão singleton: cada tenant tem exatamente um registro de configuração. A regra é aplicada na camada de aplicação via `get_or_create(pk=1)`. Em um schema recém-criado, o primeiro registro recebe `pk=1`. Ninguém apaga o único registro de configuração do escritório.

### Campo `site` como `CharField` no form

`models.URLField` exige esquema (`https://`) tanto no browser (via `type="url"`) quanto no servidor (via `URLValidator`). Para aceitar entrada intuitiva como `google.com`, o campo `site` foi sobrescrito no form como `forms.CharField`, e `clean_site()` normaliza a entrada antes de qualquer validação:

```python
def clean_site(self):
    site = self.cleaned_data.get("site", "").strip()
    if not site:
        return ""
    if not site.startswith(("http://", "https://")):
        site = f"https://{site}"
    try:
        URLValidator()(site)
    except DjangoValidationError:
        raise forms.ValidationError("Insira um endereço de site válido.")
    return site
```

Comportamento resultante:

| Entrada | Salvo no banco |
|---|---|
| `(vazio)` | `""` |
| `google.com` | `https://google.com` |
| `www.google.com` | `https://www.google.com` |
| `https://google.com` | `https://google.com` |
| `nao-e-url` | erro de validação |

### `plano_nome` e `limite_usuarios` hardcoded

O billing/SaaS (`saas_billing`) ainda não tem fluxo real implementado. `plano_nome = "Mestre"` e `limite_usuarios = 10` são placeholders temporários. A substituição por dados reais de `Assinatura` fica para etapa futura.

### `cargo` apenas descritivo

`PerfilUsuario.cargo` é um campo de texto livre sem controle de permissão. Permissões reais usarão `auth.Group` e `auth.Permission` em etapa futura. O campo `cargo` serve apenas para exibição.

---

## Models criados/alterados

### `apps/accounts/models.py` (sem alteração)

`PerfilUsuario` já existia. Nenhum campo novo adicionado.

### `apps/configuracoes/models.py` (criado)

```python
class ConfiguracaoEscritorio(models.Model):
    nome_escritorio = models.CharField(max_length=255, blank=True)
    nome_fantasia   = models.CharField(max_length=255, blank=True)
    cnpj            = models.CharField(max_length=18, blank=True)
    email           = models.EmailField(blank=True)
    telefone        = models.CharField(max_length=30, blank=True)
    endereco        = models.TextField(blank=True)
    site            = models.URLField(blank=True)
    observacoes     = models.TextField(blank=True)
    criado_em       = models.DateTimeField(auto_now_add=True)
    atualizado_em   = models.DateTimeField(auto_now=True)
```

---

## Views implementadas

### `apps/configuracoes/views.py`

| View | URL | Descrição |
|---|---|---|
| `index` | `/configuracoes/` | Lista usuários reais + card escritório |
| `editar_perfil` | `/configuracoes/perfil/editar/` | Edita `nome_completo` e `cargo` |
| `editar_escritorio` | `/configuracoes/escritorio/` | Edita dados do escritório |

Helper:

```python
def _obter_configuracao_escritorio():
    configuracao, _ = ConfiguracaoEscritorio.objects.get_or_create(pk=1)
    return configuracao
```

---

## Forms criados

### `apps/accounts/forms.py`

`PerfilUsuarioForm` — campos: `nome_completo`, `cargo`.

### `apps/configuracoes/forms.py`

`ConfiguracaoEscritorioForm` — campos: `nome_escritorio`, `nome_fantasia`, `cnpj`, `email`, `telefone`, `endereco`, `site`, `observacoes`. Campo `site` sobrescrito como `CharField` com `clean_site()`.

---

## Templates criados/alterados

| Template | Ação |
|---|---|
| `templates/configuracoes/index.html` | Adaptado para dados reais + card escritório + botão "Editar perfil" |
| `templates/configuracoes/editar_perfil.html` | Criado — form de perfil |
| `templates/configuracoes/editar_escritorio.html` | Criado — form de dados do escritório |

---

## Migrations

| Migration | App | Descrição |
|---|---|---|
| `0001_initial` | `configuracoes` | Cria tabela `ConfiguracaoEscritorio` |

Nenhuma migration foi necessária para `accounts` — `PerfilUsuario` já existia.

---

## Limitações conhecidas

- `plano_nome` e `limite_usuarios` são hardcoded — billing não implementado
- Sem avatar de usuário (aguarda definição de media em produção)
- Sem logo do escritório (mesma razão)
- Sem validação/máscara de CNPJ e telefone — apenas texto livre
- Sem permissões reais — `cargo` é apenas descritivo
- Sem criação/convite de usuários
- Sem alteração de senha ou e-mail
- Sem auditoria/logs

---

## Pendências futuras

- Permissões reais com `auth.Group` e `auth.Permission`
- Decorator/mixin de verificação de cargo para proteger views
- Criação/convite de usuários por e-mail
- Alteração de senha (`PasswordChangeForm`)
- Edição de e-mail (requer confirmação por e-mail)
- Avatar do usuário (`ImageField`, upload, `MEDIA_URL`)
- Logo do escritório (mesma cadeia de upload)
- Validação de CNPJ (dígitos verificadores)
- Máscara de telefone e CNPJ no frontend
- Limite real de usuários via `saas_billing.Assinatura`
- Auditoria/logs de alterações de perfil e escritório
- Controle de acesso por cargo em todos os módulos
- Dados fiscais mais completos (IE, regime tributário, endereço de cobrança)
- Configuração de aparência/white-label operacional (diferente de `ConfiguracaoVisual` do SaaS)

---

## Próximos passos recomendados

**Fase 2.8 — Permissões iniciais e controle de acesso**

Iniciar com diagnóstico completo antes de implementar. Objetivo:

- Usar `auth.Group` para categorizar usuários por cargo
- Decorator ou mixin customizado para proteger views por grupo
- Base estrutural para escalar permissões em todos os módulos
