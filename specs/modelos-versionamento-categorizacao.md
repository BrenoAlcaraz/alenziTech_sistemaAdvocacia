# Spec — Versionamento e categorização de Modelos de Peça

## Objetivo

Módulo Modelos hoje sobrescreve o conteúdo original a cada edição (sem
histórico) e usa `categoria` como texto livre sem padronização. Esta
feature adiciona (1) histórico de versões com possibilidade de reverter
e (2) um catálogo fechado de categorias por tenant, com filtro na
listagem — trazendo `categoria` para o mesmo padrão que `area_direito`
já tem hoje.

## Comportamento esperado

### Versionamento
- Toda edição de `ModeloPeca` (`titulo`, `categoria`, `area_direito`,
  `conteudo`) salva a versão anterior como snapshot antes de aplicar a
  mudança — não só um log de quem/quando.
- Detalhe do modelo ganha uma aba/seção "Histórico" listando as versões
  anteriores (autor da edição, data, diff ou conteúdo completo).
- Quem pode editar o modelo (dono ou habilitação `modelos_editar_alheio`)
  também pode reverter para uma versão anterior — reverter é uma nova
  edição (gera nova versão no histórico, não apaga a atual).
- Excluir o modelo (`ModeloPeca.delete`) remove também seu histórico de
  versões (`on_delete=CASCADE`) — não há retenção de histórico órfão.

### Categorização
- Nova entidade `CategoriaModeloPeca` (nome, tenant via schema — mesmo
  padrão multitenant do módulo) substitui o texto livre atual.
- `ModeloPeca.categoria` passa de `CharField` para `ForeignKey` a
  `CategoriaModeloPeca` (`on_delete=PROTECT` — não permite excluir
  categoria em uso).
- Nova habilitação `modelos_gerir_categorias` (criar/editar/excluir
  categoria do catálogo) — mesmo padrão de `modelos_editar_estilo`
  (Administrador mantém bypass).
- Listagem de Modelos ganha filtro por categoria (dropdown), somando ao
  filtro de busca textual já existente.
- Migration de dados: categorias distintas já usadas em `ModeloPeca`
  viram linhas de `CategoriaModeloPeca` automaticamente, preservando o
  vínculo (sem perda de dado histórico).

## Regras de negócio relevantes

- Reaproveita autorização de módulo (`MODULO_MODELOS`) e o padrão
  "dono OU habilitação alheia" já existente para editar — reverter usa
  a mesma checagem de `editar`.
- Igual à edição/exclusão hoje: editar/reverter modelo alheio notifica
  o autor original (reaproveita `Notificacao`, mesmo texto padrão de
  "foi editado").
- Categoria é institucional (banco compartilhado do tenant, sem autoria
  individual) — mesma decisão de 2026-08-31 que já rege o acervo de
  Modelos.

## Fora do escopo

- Versionamento/histórico do `EstiloEscritorio` (config única do
  tenant, sem autoria — fora desta spec).
- Diff visual lado a lado entre versões (mostrar conteúdo completo da
  versão antiga é suficiente nesta primeira versão).
- Categorias hierárquicas (subcategoria) — catálogo é lista simples.
- Importação (`importar`) ganhar seleção de categoria do catálogo é
  natural (mesmo formulário), mas qualquer mudança de UX de importação
  além de trocar o campo de texto por dropdown fica fora.

## Critérios de aceite

- Editar um modelo preserva o conteúdo anterior consultável no
  histórico do detalhe; reverter aplica uma versão antiga como atual e
  gera nova entrada no histórico.
- `categoria` de `ModeloPeca` só aceita valores do catálogo
  (`CategoriaModeloPeca`) do tenant; não é mais possível digitar texto
  livre.
- Usuário sem `modelos_gerir_categorias` (e sem ser Administrador) não
  acessa criar/editar/excluir categoria do catálogo.
- Excluir categoria em uso por algum `ModeloPeca` é bloqueado
  (`PROTECT`).
- Listagem de Modelos filtra por categoria selecionada, combinável com
  a busca textual existente.
- Migration converte categorias de texto livre já existentes em
  `ModeloPeca` para o catálogo sem perda de vínculo.
