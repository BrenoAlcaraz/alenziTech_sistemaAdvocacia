# Plano Fase 2 — CRUD Real — Módulo Clientes

## Visão Geral

Implementar o primeiro módulo com funcionalidade real: **Gestão de Clientes com CRUD completo**.
Manter a estrutura visual e layout atual. Substituir dados mockados por queries reais ao banco.
O padrão criado aqui será replicado para todos os outros módulos após validação.

---

## Escopo do Módulo `clientes` na Fase 2

### Funcionalidades a implementar

**1. Listar Clientes (READ)**
- Query real: `Cliente.objects.all()`
- Template: `templates/clientes/lista.html` (já existe)
- Exibir nome, tipo (PF/PJ), CPF/CNPJ, telefone, num_processos
- Se não houver clientes no banco: exibir apenas empty_state (sem mock como fallback)

**2. Detalhar Cliente (READ)**
- Query real: `get_object_or_404(Cliente, pk=pk)`
- Template: `templates/clientes/detalhe.html` (já existe)
- Exibir dados completos: nome, tipo, CPF/CNPJ, email, telefone, endereço, observações
- Abas: Processos (mock ou real), Contatos (mock)
- Botões: Editar, Deletar

**3. Criar Cliente (CREATE)**
- Form: `templates/clientes/form.html` (já existe, reutilizar)
- Modo: "novo"
- Campos: tipo (select PF/PJ), nome/razão social, CPF/CNPJ, email, telefone, endereço, observações
- POST handler: validar, salvar, redirect para detalhe
- Permissão: apenas usuários logados (`@login_required`)

**4. Editar Cliente (UPDATE)**
- Form: `templates/clientes/form.html` (já existe, reutilizar)
- Modo: "editar"
- GET: pré-popular form com dados do cliente
- POST: validar, atualizar, redirect para detalhe
- Permissão: apenas usuários logados

**5. Deletar/Inativar Cliente (DELETE)**
- Opção 1 — Soft delete: adicionar campo `ativo` (BooleanField) ao model
- Opção 2 — Hard delete: remover registro fisicamente
- Recomendação: **soft delete** para manter referências em processos
- View `deletar()`: marca como `ativo=False` ou remove, redirect para lista
- Button na tela de detalhe com confirmação
- Permissão: apenas usuários logados

---

## Sequência de Implementação

### 1. Revisar/Ajustar o Model `Cliente`

**Arquivo:** `apps/clientes/models.py`

Campos existentes (confirmados):
```python
class Cliente(models.Model):
    TIPO_CHOICES = [
        ("PF", "Pessoa Física"),
        ("PJ", "Pessoa Jurídica"),
    ]
    
    tipo = models.CharField(max_length=2, choices=TIPO_CHOICES, default="PF")
    nome_razao_social = models.CharField(max_length=255)
    cpf_cnpj = models.CharField(max_length=18, blank=True)
    email = models.EmailField(blank=True)
    telefone = models.CharField(max_length=20, blank=True)
    endereco = models.TextField(blank=True)
    observacoes = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
```

**Possível ajuste:** adicionar `ativo = models.BooleanField(default=True)` para soft delete.

**Decisão:** só adicionar `ativo` se aprovado explicitamente — não adicionar sem sua confirmação.

**Status:** modelo atual já tem método `iniciais()` definido. Usar como está.

### 2. Criar/Atualizar Migration (se necessário)

**Status:** não criar migration nova sem aprovação explícita.

Se adicionar campo `ativo` (após aprovação):
```bash
python manage.py makemigrations clientes
python manage.py migrate_schemas
```

### 3. Implementar View `lista()`

**Arquivo:** `apps/clientes/views.py`

```python
@login_required
def lista(request):
    clientes = Cliente.objects.filter(ativo=True)  # Excluir inativos
    return render(request, "clientes/lista.html", {
        "clientes": clientes,
        "item_ativo": "clientes"
    })
```

**Fallback:** se `clientes.count() == 0`, exibir empty_state no template.

### 4. Implementar View `detalhe()`

**Arquivo:** `apps/clientes/views.py`

```python
@login_required
def detalhe(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk, ativo=True)
    # Processos relacionados (query real ou mock temporário)
    processos = Processo.objects.filter(cliente_id=pk)  # Se FK existir
    return render(request, "clientes/detalhe.html", {
        "cliente": cliente,
        "processos": processos,
        "aba_ativa": request.GET.get("aba", "processos"),
        "item_ativo": "clientes"
    })
```

### 5. Implementar View `criar()` + Form

**Arquivo novo:** `apps/clientes/forms.py`

```python
from django import forms
from apps.clientes.models import Cliente

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['tipo', 'nome_razao_social', 'cpf_cnpj', 'email', 'telefone', 'endereco', 'observacoes']
```

**Arquivo:** `apps/clientes/views.py`

```python
from apps.clientes.forms import ClienteForm

@login_required
def criar(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            cliente = form.save()
            return redirect('clientes:detalhe', pk=cliente.pk)
    else:
        form = ClienteForm()
    return render(request, "clientes/form.html", {
        "form": form,
        "modo": "novo",
        "item_ativo": "clientes"
    })
```

**Template:** ajustar `templates/clientes/form.html` para renderizar form real em vez de campos mockados.

### 6. Implementar View `editar()`

**Arquivo:** `apps/clientes/views.py`

```python
@login_required
def editar(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk, ativo=True)
    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            cliente = form.save()
            return redirect('clientes:detalhe', pk=cliente.pk)
    else:
        form = ClienteForm(instance=cliente)
    return render(request, "clientes/form.html", {
        "form": form,
        "modo": "editar",
        "cliente": cliente,
        "item_ativo": "clientes"
    })
```

### 7. Implementar View `deletar()`

**Arquivo:** `apps/clientes/views.py`

```python
@login_required
def deletar(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk, ativo=True)
    if request.method == 'POST':
        cliente.ativo = False  # Soft delete
        cliente.save()
        return redirect('clientes:lista')
    return render(request, "clientes/confirmar_delecao.html", {
        "cliente": cliente,
        "item_ativo": "clientes"
    })
```

**Template:** criar `templates/clientes/confirmar_delecao.html` com confirmação ou usar modal.

### 8. Atualizar URLs

**Arquivo:** `apps/clientes/urls.py`

Verificar se as rotas existem:
```python
from django.urls import path
from . import views

app_name = 'clientes'

urlpatterns = [
    path('clientes/', views.lista, name='lista'),
    path('clientes/<int:pk>/', views.detalhe, name='detalhe'),
    path('clientes/novo/', views.criar, name='criar'),  # Colocar ANTES de <int:pk>
    path('clientes/<int:pk>/editar/', views.editar, name='editar'),
    path('clientes/<int:pk>/deletar/', views.deletar, name='deletar'),
]
```

**Nota:** a rota `novo/` deve vir ANTES de `<int:pk>/` para não conflitar.

### 9. Atualizar Templates

**`templates/clientes/lista.html`**
- Remover `CLIENTES_MOCK`
- Iterar sobre `clientes` do contexto real
- Adicionar empty_state se `not clientes`
- Botão "Novo cliente" → redirect para `clientes:criar`

**`templates/clientes/detalhe.html`**
- Remover `PROCESSOS_MOCK_CLIENTE`
- Exibir dados reais de `cliente` (ORM)
- Iterar sobre `processos` reais
- Botões: Editar → `clientes:editar`, Deletar → `clientes:deletar`

**`templates/clientes/form.html`**
- Renderizar form Django real com `{{ form.as_p }}` ou custom bootstrap
- Manter visual consistente com o resto do projeto
- Fields: tipo (select), nome_razao_social, cpf_cnpj, email, telefone, endereco, observacoes

---

## O que NÃO fazer nesta etapa

❌ Implementar permissões granulares (apenas `@login_required` por enquanto)  
❌ Implementar busca/filtros reais (todos os dados, sem filtro)  
❌ Implementar paginação (adicionar se >100 registros)  
❌ Adicionar testes automatizados (posso ajudar depois)  
❌ Validar CPF/CNPJ realmente (formato básico OK)  
❌ Adicionar foto/avatar do cliente (upload real vem depois)  
❌ Implementar CRUD de outros módulos (clientes first, depois replicar padrão)  

---

## Checklist de Implementação

- [ ] Revisar model `Cliente` (✅ já revisado — OK)
- [ ] Decidir se adiciona `ativo` (aguardando aprovação)
- [ ] Criar migration se necessário (não executar sem aprovação)
- [ ] **Criar `apps/clientes/forms.py`** com `ClienteForm`
- [ ] Implementar view `lista()` com query real (remover mock)
- [ ] Implementar view `detalhe()` com `get_object_or_404`
- [ ] Implementar view `criar()` usando `ClienteForm`
- [ ] Implementar view `editar()` usando `ClienteForm`
- [ ] Implementar view `deletar()` (soft delete ou hard delete)
- [ ] Atualizar `apps/clientes/urls.py`
- [ ] Atualizar `templates/clientes/lista.html` → query real + empty_state
- [ ] Atualizar `templates/clientes/detalhe.html` → dados reais
- [ ] Atualizar `templates/clientes/form.html` → form Django real
- [ ] Testar CRUD completo via navegador
- [ ] Validar `item_ativo` em todas as views
- [ ] Validar navegação (criar → detalhe → editar → lista → deletar)

---

## Próximo passo após Clientes

Após Clientes estar 100% funcional e validado:

1. Replicar o padrão (listagem → detalhe → criar → editar → deletar) para:
   - Processos
   - Tarefas
   - Financeiro
   - Agenda
   - Chat
   - Modelos

2. Cada módulo seguirá a mesma estrutura, apenas adaptando models e fields específicos.

3. Após todos os CRUD reais, adicionar:
   - Permissões granulares
   - Busca/filtros
   - Paginação
   - Validações de negócio
