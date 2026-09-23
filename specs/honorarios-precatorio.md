# Honorários — sub-aba Precatório

## Objetivo

Mostrar quais honorários de sucumbência serão pagos pela Fazenda Pública
e se devem seguir por RPV ou precatório, com decisão final do usuário.

## Comportamento (MVP entregue)

Regras vigentes em [docs/modules/financeiro.md](../docs/modules/financeiro.md)
(Honorários → sub-aba Precatório) e
[docs/modules/processos.md](../docs/modules/processos.md) (Partes → ente público).

## Fora do escopo do MVP

- êxito contratual e crédito principal do cliente (seguem o regime do
  crédito do cliente);
- inferir ente público por nome/CNPJ ou a parte adversa pelo polo do cliente;
- tetos por lei estadual/municipal; salário mínimo automático/data-base;
- acompanhamento da requisição (número, ano orçamentário, status, prazos);
- previsão de recebimento no Financeiro; unificar `devedor_tipo` com a parte.

## Pendente de validação do sócio advogado

- limite aplicado por credor (honorário comparado sozinho, Tema 18 STF);
- estadual 40 SM como padrão; municipal sem sugestão (padrão de 30 SM?);
- parte pública em qualquer polo conta (sistema não sabe o polo do cliente);
- valor comparado: sucumbência corrigida até hoje;
- salário mínimo 2026 = R$ 1.621,00.

## Critérios de aceite

- sugestão por esfera/teto correta e nunca gravada;
- lista só sucumbências não canceladas contra ente público;
- regime muda só por ação do usuário.
