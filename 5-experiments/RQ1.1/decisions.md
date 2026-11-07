# RQ1.1 — Registro de decisões

Decisões tomadas na revisão da Etapa 0 (novembro de 2026). Referência para a implementação, para revisão e para o manuscrito. Uma decisão só muda aqui, com o motivo.

## Estado das etapas

| Etapa | Situação |
|---|---|
| 0. Infraestrutura de medição | Concluída; evidências em `etapa0/results/` (ignorada pelo git) |
| 1. Linha de base dos casos de falha | Aguarda autorização |
| 2. Bancada exploratória (E1–E7) | Pendente |
| 3. Semântica de C2 e C7 | Pendente |
| 4. Implementação de C2 e C7 | Pendente |
| 5. Retry | Pendente |
| 6. Fail-safe | Pendente |
| 7. Integração | Pendente |
| 8. Bateria RQ1.1 (25 atritos) | Pendente |

## Resultado de cada execução

| # | Decisão |
|---|---|
| R1 | A, B e C são classificados pelo **objetivo global**. O `success` da adaptação é informação de apoio. |
| R2 | Objetivo global: distância 3D do cubo ao alvo até 5 cm e garra aberta (≥ 6 cm), no último tick. Não exige zero contatos nem repouso. |
| R3 | Nova categoria **E — falha não detectada**: `success` da adaptação, sem retry ou fail-safe, e objeto fora do alvo. |
| R4 | O `success` continua valendo com um tick de Then satisfeito. A exploração mede com que frequência o cubo cai depois; se for frequente, esta decisão é reaberta. |
| R5 | O ASM só evolui no fim do episódio e com o objetivo global atingido. **Implementado.** |
| R6 | Na bateria final, qualquer `execution_error` ou `runner_timeout` invalida a bateria: corrige-se a causa, registra-se o motivo e refazem-se os 25 runs. |

## Física e parâmetros

| # | Decisão |
|---|---|
| F1 | `phase_threshold = 0.045` fica congelado na aproximação nominal. O artigo declara que o cenário de escorregamento depende desse valor, introduzido no commit `8f49e5a`. |
| F2 | A tolerância do vacuum será decidida após o E4, com atritos fora dos 25. Se for defeito, muda só no vacuum, antes do congelamento, e fica registrada no artigo. |
| F3 | `distance_object_goal_cm` continua truncado e só em X e Y nas pós-condições. O artigo declara isso, e o objetivo global usa a distância real. |
| F4 | Os limites de 30 ticks (avaliação), 60 ticks (task adaptativa) e 5 ticks (início) são pré-declarados e congelados antes da etapa 8. Só podem ser revistos com atritos fora dos 25. |

## Diagnóstico

| # | Decisão |
|---|---|
| D1 | O Diagnoser treina com os 5 CSVs nominais mais a execução atual, e o limiar resulta do ponto médio entre 0,5 e o atrito do run. O artigo descreve isso e não o apresenta como evidência de generalização. |

## Calibração e avaliação

| # | Decisão |
|---|---|
| A1 | Toda calibração usa atritos fora dos 25, como 0,157, 0,142, 0,105 e 0,065. |
| A2 | Os 9 casos de falha podem ser rodados na etapa 1 só para classificar a causa, sem ajustar parâmetros. O artigo declara que os 25 valores já eram conhecidos. |
| A3 | Os 25 runs nominais são o resultado principal. Sensibilidade pré-declarada: posição inicial ±2 mm nos 17 atritos com violação (34 runs). |
| A4 | Os 8 atritos sem violação ficam de fora da sensibilidade. |

## Candidatos

| # | Decisão |
|---|---|
| K1 | `adjust_grip_force()`: reposicionar, pegar de novo e aumentar `joint_forces[7:9]`. C7 usa o mesmo mecanismo no transporte. Catálogo e artigo declaram isso. |
| K2 | Se o E1 mostrar que mais força não ajuda, C2 e C7 seguem assim e o resultado é relatado, sem trocar a estratégia para forçar o cenário C. |
| K3 | Sem sensores novos por enquanto. `grip_pressure`, `object_secured`, `joint_torque` e outros ficam `not_observed` no relato do Then do candidato. |
| K4 | C3, C4, C5 e C8 ficam no catálogo como candidatos de ranking, sem execução física, e isso é declarado no artigo. |

## Retry e fail-safe (a implementar)

| # | Decisão |
|---|---|
| P1 | Ao fim da task adaptativa, objeto sem 2 contatos ou abaixo de 10 cm é falha imediata. Os 30 ticks ficam para pós-condições de trajeto. |
| P2 | Retry permitido quando o objeto não está seguro, continua dentro dos limites da mesa, a tarefa não terminou e há menos de 2 tentativas. Não usa o When nem a altura do Given. |
| P3 | No máximo 2 tentativas por episódio, com reuso do ranking original e controle pelo Evaluator. O artigo declara o limite, porque o monitor fica preso em `ERR`. |
| P4 | Restaurar o atrito original dos dedos antes da segunda tentativa, registrando isso no log. |
| P5 | O DejaVu decide o próximo candidato ou o fail-safe; o Manager executa, respeitando a prioridade do ASM interno. |
| P6 | Fail-safe: parar o braço na pose atual, manter a garra como está, registrar o motivo, notificar pelo console e terminar o run com resultado explícito. É diferente de `SAFE_ABORT`, que abre a garra. |

## Medições que corrigiram a auditoria inicial

- A força normal medida ao segurar o cubo é de cerca de 170 N, no limite do motor, e não cerca de 26 N, como a estimativa inicial. A conta estática (cerca de 61 N de atrito disponível contra 9,8 N de peso) não explica o escorregamento; o E1 investiga isso.
- Em 0,14, a garra fechou a cerca de 1 cm do alvo de pegada. O fechamento prematuro não explica esse caso.
- Em 0,135, a falha anterior foi um erro do pipeline, não do candidato. Agora o vacuum roda e satisfaz o Then, mas o cubo cai depois e termina a 6,8 cm: é o primeiro exemplo de E.
