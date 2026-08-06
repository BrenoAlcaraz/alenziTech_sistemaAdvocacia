---
title: Política de terminologia
status: canonical
owner: product-and-engineering
last_reviewed: 2026-08-06
---

# Política de terminologia

## Objetivo

Os termos jurídicos, de produto e de arquitetura devem ser usados de
forma consistente entre sócios, desenvolvedor, documentação, código e
agentes de IA. Esta política define os termos canônicos do projeto e
seus significados, para evitar ambiguidade e uso inconsistente.

## Termos canônicos

| Termo canônico | Significado | Evitar ou distinguir de |
| --- | --- | --- |
| Breno - LawSystem | Nome do produto. | — |
| Sistema jurídico SaaS white label | Categoria do produto: SaaS multi-tenant white label para escritórios de advocacia. | — |
| Monólito modular | Estilo arquitetural atual: uma única aplicação Django dividida em módulos internos. | Microserviços |
| Módulo | Unidade funcional interna da aplicação, implementada como app Django. | Microserviço, serviço independente |
| App Django | Implementação técnica de um módulo dentro do monólito. | Microserviço |
| Tenant | Escritório de advocacia isolado por schema PostgreSQL na plataforma. | — |
| Escritório | Sinônimo de tenant no domínio de negócio. | — |
| Schema público | Schema PostgreSQL compartilhado da plataforma SaaS (tenants, planos, assinaturas). | Schema do escritório |
| Schema do escritório | Schema PostgreSQL isolado de um tenant específico, com seus dados de negócio. | Schema público |
| Administrador do escritório | Autoridade administrativa máxima dentro de um tenant. | Django superuser, Platform Admin |
| Platform Admin | Operador administrativo da plataforma SaaS, fora do escopo de um tenant específico. | Administrador do escritório |
| Papel de acesso | Controla autorização dentro do sistema. | Cargo profissional |
| Cargo profissional | Descrição informativa da função da pessoa, sem efeito sobre permissões. | Papel de acesso |
| Equipe | Agrupamento organizacional de usuários dentro de um tenant. | Departamento (termo depreciado) |
| Gerente de equipe | Relação organizacional de responsabilidade sobre uma equipe. | Papel de acesso global |
| Cliente | Pessoa física ou jurídica atendida pelo escritório. | Participante processual |
| Participante processual | Qualquer pessoa ou entidade com papel formal em um processo. | Cliente |
| Polo processual | Posição estrutural do participante no processo, como polo ativo, polo passivo ou terceiro. | Qualificação processual |
| Qualificação processual | Nome jurídico exercido pelo participante naquele processo ou fase, como requerente, requerido, exequente, executado, embargante, embargado, agravante, agravado, apelante, apelado, recorrente ou recorrido. | Polo processual |
| Representante | Advogado ou procurador que representa um participante no processo. | Parte, participante processual |
| Autoridade processual | Agente do processo com função decisória, como juiz. | Partes do processo |
| Processo apenso | Processo tecnicamente vinculado a outro processo principal. | — |
| Andamento processual | Evento registrado na tramitação de um processo. | Fase processual, status processual |
| Fase processual | Etapa do rito processual em que o processo se encontra. | Andamento processual, status processual |
| Status processual | Situação corrente do processo (ativo, suspenso, arquivado, etc.). | Fase processual, andamento processual |
| Assistente do sistema | Funcionalidade de apoio operacional dentro do produto. | IA jurídica |
| IA jurídica | Funcionalidade de inteligência artificial aplicada a conteúdo jurídico. | Assistente do sistema |

Definições obrigatórias:

- "Administrador do escritório" é a autoridade administrativa máxima
  dentro de um tenant. Não é igual a Django superuser nem a Platform
  Admin.
- "Platform Admin" é o operador administrativo da plataforma SaaS, e não
  se confunde com o Administrador do escritório.
- "Papel de acesso" controla autorização; é distinto de "cargo
  profissional", que é apenas descritivo e não controla permissões.
- "Equipe" substitui o termo técnico antigo "departamento".
- "Gerente de equipe" é uma relação organizacional, não um papel global
  de acesso.
- "Módulo" ou "app Django" não deve ser chamado de microserviço na
  arquitetura atual.
- "Participante processual" não é sinônimo automático de cliente.
- Advogado representante não deve ser tratado como parte no processo.
- Autoridade processual, como juiz, fica separada das partes do
  processo.
- Assistente do sistema e IA jurídica são produtos diferentes.
- Polo processual é posição estrutural.
- Qualificação processual é o nome jurídico exercido pelo participante
  naquele processo ou fase.
- A mesma pessoa não deve ser duplicada apenas porque sua qualificação
  processual mudou.

## Termos históricos ou depreciados

- Perfil mestre
- Departamento
- Grupo gerente
- Grupo advogado
- Microserviço, quando usado para descrever os apps atuais

Estes termos podem permanecer em arquivos históricos, migrations ou
código de compatibilidade legada, mas não devem orientar novas decisões
de produto, arquitetura ou documentação.

## Regra para documentos históricos

Documentos históricos não devem ser alterados apenas para trocar
terminologia. Quando um termo depreciado for citado a partir de um
documento vigente, o documento deve explicar qual é o termo atual
equivalente.

## Regra para código legado

Termos antigos presentes em migrations, banco de dados, grupos legados
ou código de compatibilidade não devem ser renomeados sem uma tarefa
técnica e uma migration específica para isso.
