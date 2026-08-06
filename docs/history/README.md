---
title: Histórico do projeto
status: canonical
owner: product-and-engineering
last_reviewed: 2026-08-06
---

# Histórico do projeto

Este diretório preserva documentos produzidos em fases anteriores do
desenvolvimento do Breno - LawSystem.

Os arquivos aqui armazenados:

- registram decisões, planos e estados anteriores;
- ajudam a compreender a evolução do produto;
- não constituem documentação canônica vigente;
- não devem ser usados isoladamente para definir novas implementações.

Quando um documento histórico divergir da documentação canônica, devem
prevalecer:

1. decisões de produto aprovadas;
2. decisões arquiteturais aprovadas;
3. especificações canônicas dos módulos;
4. documentação de segurança;
5. tarefa ativa aprovada.

Agentes de IA não devem tratar arquivos deste diretório como instruções
atuais, salvo quando a tarefa solicitar expressamente uma análise histórica.

## Organização

- `phase-1/` preserva checkpoints e o encerramento formal da Fase 1;
- `legacy-plans/` preserva planos anteriores e documentos substituídos por
  decisões posteriores;
- `snapshots/` preserva fotografias de estados anteriores do projeto;
- `source-material/` contém materiais originais usados como fonte
  (documentos do especialista jurídico, consolidações e fichas técnicas);
- `audits/` contém diagnósticos produzidos por agentes de IA em momentos
  específicos;
- `SHA256SUMS.txt` registra a integridade dos materiais externos
  preservados em `source-material/` e `audits/`.

Pontos importantes sobre este diretório:

- fontes originais não são automaticamente canônicas — sua autoridade é
  descrita individualmente em `source-material/README.md`;
- auditorias são fotografias de determinado momento e não se atualizam
  quando o código muda — ver `audits/README.md`;
- decisões extraídas dessas fontes devem ser registradas formalmente em
  PDRs ou ADRs antes de orientar implementações novas;
- documentos históricos não devem ser editados para parecer atuais; use o
  manifesto SHA-256 para detectar alterações acidentais nos materiais
  externos.
