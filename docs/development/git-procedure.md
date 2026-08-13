---
title: Procedimento Git
status: canonical
owner: development
last_reviewed: 2026-08-06
---

# Procedimento Git

## Objetivo

Definir o procedimento de Git para qualquer execução de trabalho neste
repositório: auditoria do working tree, staging, commit, push,
tratamento de falha de push, operações de alto risco e a política de
line endings do projeto. Este documento é executor-agnóstico — aplica-se
a qualquer pessoa ou agente que opere Git neste repositório.

Este documento assume que a sequência de execução de
[workflow.md](workflow.md) já foi seguida até a etapa correspondente.
Ele não repete os critérios de quando um Work Item pode ser concluído —
ver [quality-gates.md](quality-gates.md) — nem o protocolo de Work Items
em si — ver
[docs/delivery/work/README.md](../delivery/work/README.md).

## Git — preflight

Antes de qualquer implementação, é obrigatório registrar:

```bash
git branch --show-current
git log -1 --oneline
git status --short
```

Quando a sincronização com o remoto for relevante para a execução em
questão:

```bash
git status -sb
```

`fetch` não é executado automaticamente como parte deste preflight —
apenas quando a execução exigir de fato comparar local e remoto (ver
"Push" abaixo). Rodar `git fetch` sem necessidade não faz parte deste
procedimento padrão.

## Git — working tree

Regras que governam qualquer alteração no diretório de trabalho:

- mudanças preexistentes no working tree pertencem ao usuário até prova
  em contrário;
- não sobrescrever;
- não resetar;
- não limpar (`clean`);
- não incluir uma alteração preexistente no escopo da execução
  silenciosamente.

Arquivos não rastreados (`??` em `git status --short`) também contam
como mudança preexistente relevante — `git diff` não mostra arquivos não
rastreados. Por isso, a verificação de escopo de qualquer execução deve
sempre combinar a revisão de diff com:

```bash
git status --short
```

Se essa verificação revelar uma alteração fora do escopo declarado da
execução — feita pelo executor atual ou já presente antes de a execução
começar — a execução deve parar, relatar o que foi encontrado, e nunca
usar um comando destrutivo para "limpar" o que foi encontrado.

## Git — staging

Política: **staging deve ser explícito e baseado no escopo da execução**
(do Work Item, quando houver um).

Preferir:

```bash
git add caminho/arquivo1 caminho/arquivo2
```

Não usar como padrão:

```text
git add .
git add -A
```

Antes de qualquer commit, revisar o que está staged:

```bash
git diff --cached --name-status
git diff --cached --stat
git diff --cached --check
```

Um arquivo staged fora do escopo esperado da execução bloqueia o commit
até ser esclarecido — não é aceitável commitar "porque já estava
staged".

Staging preexistente feito pelo usuário antes do início da execução não
deve ser removido silenciosamente.

## Git — commit

### Padrão observado no histórico

Confirmado pela leitura do histórico completo do branch (não apenas os
commits mais recentes): o padrão predominante é

```text
tipo(escopo): descrição
```

ou, para commits de documentação que não tocam um módulo específico:

```text
tipo: descrição
```

Tipos confirmados no histórico: `feat`, `fix`, `docs`, `refactor`,
`chore`, `style`. O escopo entre parênteses, quando presente, é
predominantemente o nome de um app/módulo (`accounts`, `clientes`,
`processos`, `configuracoes`, etc.). Commits de documentação nesta
branch de reorganização (`docs/reorganizacao-harness`) usam
consistentemente `docs:` sem escopo entre parênteses. Um pequeno número
de commits mais antigos no histórico não segue esse padrão (por exemplo,
o commit inicial do repositório) — não são tratados como referência.

Este documento **não impõe** escopo entre parênteses quando ele não
fizer sentido para o commit em questão (como já ocorre nos commits
`docs:` desta branch).

### Regras de mensagem

- curta;
- descritiva do efeito real da mudança, não da intenção original;
- sem prometer uma mudança que não foi de fato entregue no commit;
- sem inventar hash de commit antes de o commit existir — o hash só é
  conhecido depois que `git commit` roda.
- sem adicionar automaticamente metadados de coautoria, fornecedor ou
  ferramenta, a menos que instruído explicitamente para a execução em
  questão.

### Autorização

Commit só ocorre quando explicitamente autorizado para a execução em
andamento. Nenhum executor — humano ou agente — deve presumir essa
autorização por padrão; ela depende do Work Item e/ou da sessão em que a
execução ocorre, conforme
[docs/delivery/work/README.md#regras-de-execução-para-agentes](../delivery/work/README.md#regras-de-execução-para-agentes).

## Git — push

Push só ocorre quando explicitamente autorizado para a execução em
andamento.

Procedimento normal:

```bash
git push
```

### Falha de push

Se ocorrer um erro remoto ou transitório **depois que o commit local já
existe**, o commit local não desaparece por causa dessa falha. Não usar
nenhuma das ações abaixo apenas por causa da falha de push:

```text
criar um novo commit
resetar
rebasear
usar --force
amendar o commit
```

Procedimento correto diante de falha de push:

1. verificar o estado local:

   ```bash
   git status -sb
   git log -2 --oneline
   ```

2. quando necessário, comparar local e remoto:

   ```bash
   git fetch origin
   ```

3. se o local estiver apenas à frente do remoto (sem divergência real),
   repetir o push normal.

Uma falha de transporte remoto (rede, autenticação transitória, etc.)
não apaga o commit local — o procedimento é diagnosticar e tentar
novamente, não reescrever o histórico.

## Git — operações de alto risco

As operações abaixo **não são executadas por padrão**, sem autorização
explícita para a execução em andamento:

```text
git reset --hard
git clean -fd
git clean -fdx
git push --force
git push --force-with-lease
git rebase
git commit --amend
git restore .
git checkout -- .
```

Também não se deleta branch ou tag silenciosamente.

Nenhuma dessas operações deve ser usada apenas para obter um working
tree "limpo" mais rápido — isso não é motivo válido para uma operação
destrutiva.

## Line endings — auditoria

Antes de qualquer alteração relacionada a `.gitattributes`, confirmar o
estado real da configuração e do inventário do repositório — este
estado pode mudar entre execuções e não deve ser presumido a partir de
uma leitura anterior deste documento:

```bash
git config --get core.autocrlf
git config --get core.eol
git config --get core.safecrlf
test -f .gitattributes && cat .gitattributes || true
git ls-files
git ls-files --eol
```

`core.autocrlf` é uma configuração local, por usuário/máquina — pode
variar entre ambientes de desenvolvimento (`true`, `false` ou `input`).
É exatamente por isso que a política de line endings deste repositório
não depende dela: `.gitattributes` é a autoridade, não a configuração
local de quem estiver operando.

`git ls-files --eol` pode revelar arquivos já rastreados cujo conteúdo
no working tree está em CRLF, mesmo com o índice armazenando LF —
tipicamente arquivos commitados antes de uma regra de `.gitattributes`
cobri-los, ou editados por uma ferramenta que não normalizou o
conteúdo. Arquivos binários genuínos (por exemplo, `.docx`) são
detectados automaticamente pelo Git como não-texto (`-text` em `git
ls-files --eol`), independentemente de atributo declarado.

A lista exata de arquivos afetados, e sua contagem, mudam a cada
commit — este documento não registra essa fotografia. Uma execução que
precisar dela deve gerá-la com os comandos acima e registrar o
resultado no relatório dessa execução, não neste documento canônico.

## `.gitattributes`

`.gitattributes` é a **autoridade de line endings deste repositório**.
Objetivo: manter os arquivos de texto do projeto com LF no repositório e
no working tree, independentemente de `core.autocrlf`, enquanto tipos de
arquivo tradicionalmente associados ao Windows podem manter CRLF quando
existirem.

Regras decorrentes desta política:

- a configuração global de Git do usuário **não deve** ser alterada por
  este projeto — este documento não instrui ninguém a rodar `git config
  --global core.autocrlf ...` como requisito do projeto;
- o Git deve obedecer aos atributos declarados no repositório, e não à
  configuração local de quem estiver operando;
- uma renormalização retroativa de arquivos já rastreados que ainda
  estejam em CRLF no working tree (`git add --renormalize .` ou
  equivalente) é, quando necessária, um trabalho separado, auditável e
  explicitamente autorizado — nunca parte de uma execução de rotina
  deste workflow.

A política de `.gitattributes` deve acompanhar os tipos de arquivo
textuais e binários efetivamente usados pelo repositório — não uma
lista genérica de extensões não rastreadas. Ao introduzir uma extensão
nova relevante ao projeto, revisar se ela precisa de uma regra
explícita nesta política, seguindo a auditoria descrita em "Line
endings — auditoria" acima.

## Referências

- [workflow.md](workflow.md)
- [quality-gates.md](quality-gates.md)
- [commands.md](commands.md)
- [docs/delivery/work/README.md](../delivery/work/README.md)
