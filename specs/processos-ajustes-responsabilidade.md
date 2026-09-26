# Ajustes do módulo Processos — responsabilidade, partes e atalhos

## Objetivo
Dez ajustes pedidos pelo sócio: responsabilidade atribuída a vários
usuários, representante e gratuidade por parte, agenda com processo e
clientes travados, e ajustes pontuais de tela/validação.

## Comportamento esperado
1. Formulário de processo sem "Responsável"; `responsavel` vira
   `criado_por` (não exibido).
2. `responsaveis` (N usuários): enxergam e editam o processo, recebem
   avisos DJEN/DataJud/honorários e os prazos gerados na Agenda (1º
   atribuído = responsável do Prazo, demais = participantes; sem nenhum
   → `criado_por`). Criador continua vendo/editando. Atribuem: admin e
   quem tem `processos_atribuir_responsavel` (qualquer usuário); gerente
   de equipe (membros ativos não-gerentes das equipes que gerencia).
   Campo "Atribuir responsável(is)" no card do detalhe e no formulário
   (só para quem pode). Bandeira na lista só para o atribuído; etiqueta
   "Responsáveis" no detalhe para todos; filtro "Responsabilidade".
3. Título sempre em maiúsculas.
4. Representante (N por parte: sócio/administrador, pai/mãe, tutor,
   curador, outro) exibido na parte como o advogado; não é parte.
5. Gratuidade de justiça (checkbox) em partes de polo ativo, passivo e
   terceiro interessado.
6. Novo compromisso aberto pelo processo: processo e clientes (todos
   os do processo) travados; compromisso aparece para todos os
   clientes do processo.
7. Aba "Apensos e relacionados".
8. Botão voltar para a lista no detalhe.
9. Número de processo único (comparação só por dígitos, inclui
   arquivados; vazio permitido).
10. Laboratório: peça sempre "Petição inicial".

## Fora do escopo
Agenda com N clientes gravados; constraint de número único no banco.

## Critérios de aceite
Cada item acima coberto por teste; dados existentes preservados
(responsável atual vira criador e primeiro responsável).
