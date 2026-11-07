# RQ1.1 — Registro de decisões

Decisões tomadas na revisão da Etapa 0 (novembro de 2026). Referência para a implementação, para revisão e para o manuscrito. Uma decisão só muda aqui, com o motivo.

## Estado das etapas

| Etapa | Situação |
|---|---|
| 0. Infraestrutura de medição | Concluída; evidências em `etapa0/results/` (ignorada pelo git) |
| 1. Linha de base dos casos de falha | Concluída; evidências em `etapa1/results/` (ignorada pelo git) |
| 2. Bancada exploratória | Concluída; script e dados em `bancada/` |
| 3. Semântica de C2 e C7 | Decidida (seção Candidatos) |
| 4. Implementação de C1, C2 e C7 | Concluída; C7 ainda sem execução em run real |
| 5. Retry | Implementado e testado com poucos runs |
| 6. Fail-safe | Implementado e testado com poucos runs |
| 7. Integração | Quatro caminhos vistos em 7 runs fora dos 25; evidências em `quatro_caminhos/results/` |
| 7b. Correção do transporte (F5) | Implementada; bancada e 3 runs reais fora dos 25 (0,19 A; 0,1575 B; 0,035 C); evidências em `f5_transporte/results/` |
| 8. Bateria RQ1.1 (25 atritos) | Pendente |

## Resultado de cada execução

| # | Decisão |
|---|---|
| R1 | A, B e C são classificados pelo **objetivo global**. O `success` da adaptação é informação de apoio. |
| R2 | Objetivo global: distância 3D do cubo ao alvo até 5 cm e garra aberta (≥ 6 cm), no último tick. Não exige zero contatos nem repouso. |
| R3 | Nova categoria **E — falha não detectada**: `success` da adaptação, sem retry ou fail-safe, e objeto fora do alvo. |
| R7 | O objetivo global continua sem exigir que o objeto tenha sido segurado. Em 0,035, o C1 antigo levou a uma entrega por acaso; com fail-safe, uma falha detectada interrompe o run antes disso. A rever se voltar a ocorrer. |
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
| F5 | **Transporte desacelera nos últimos 5 cm** (`transport_object_task.py`), com a mesma regra da rotina de recuperação. Motivo: com velocidade máxima até o fim, cada passo (~4 cm) passa da tolerância de 5 mm e o braço pode ficar num ciclo em Y sobre o alvo, que só termina por acaso. Em 0,035 o ciclo durou 142 ticks no run real (307 s) e 325 na bancada (~520 s estimados), perto do limite de 600 s da R6. Na bancada (125 runs, atritos fora dos 25, 5 posições): o transporte mais longo cai de 325 para 20 ticks; o nominal passa de 16 para 18 ticks; 3 runs mudam de caminho, todos para menos falhas (0,19 com −2 mm em Y: B → A; 0,055 em duas posições: E → B, o cubo deixava de cair na parada brusca); violações no lift e os caminhos C e D não mudam. A mudança é no controlador nominal, não no DejaVu, e o artigo declara isso. Os runs reais da Etapa 1 deixam de servir de referência para o modo `validate` da bancada nos casos com transporte. Dados em `bancada/results/transport*`. |

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
| A5 | A execução é tratada como determinística: um run por atrito, sem repetições. A física é determinística (4 repetições idênticas tick a tick na bancada); a única variação conhecida é a adaptação começar um tick mais tarde (ver o fim deste registro). Causa suspeita, não confirmada: o Managing espera o Manager por no máximo 5 s por tick, enquanto o Manager espera o DejaVu sem limite durante o diagnóstico. Fica como limitação conhecida; se um run da bateria divergir do esperado, é a primeira hipótese a verificar. |

## Candidatos

| # | Decisão |
|---|---|
| K1 | **Revista após a bancada.** C1, C2, C6 e C7 usam a mesma rotina de pegada (subir, alinhar, descer à altura do centro, fechar, subir) e diferem só no atrito efetivo dos dedos: ×3 em C1 e C6, ×7 em C2 e C7. Os nomes e o GWDT do catálogo não mudam. |
| K2 | O artigo declara que sucção e ajuste de preensão são simulados por atrito efetivo, e que aumentar a força real da garra não recuperou casos de forma consistente na bancada. |
| K5 | O valor ×7 foi escolhido na bancada, com atritos fora dos 25, e é declarado como parâmetro do experimento. |
| K6 | C7 fica implementado. Na bancada, C6 recuperou todas as violações de transporte, então C7 pode não ser acionado; o artigo relata isso, sem forçar um cenário para ele. |
| K3 | Sem sensores novos por enquanto. `grip_pressure`, `object_secured`, `joint_torque` e outros ficam `not_observed` no relato do Then do candidato. |
| K4 | C3, C4, C5 e C8 ficam no catálogo como candidatos de ranking, sem execução física, e isso é declarado no artigo. |

## Retry e fail-safe (implementados)

| # | Decisão |
|---|---|
| P1 | Ao fim da task adaptativa, objeto sem 2 contatos ou abaixo de 10 cm é falha imediata. Os 30 ticks ficam para pós-condições de trajeto. |
| P2 | Retry permitido quando o objeto não está seguro, continua dentro dos limites da mesa, a tarefa não terminou e há menos de 2 tentativas. Não usa o When nem a altura do Given. |
| P3 | No máximo 2 tentativas por episódio, com reuso do ranking original e controle pelo Evaluator. O artigo declara o limite, porque o monitor fica preso em `ERR`. |
| P4 | **Revista após a bancada.** Não restaura o atrito entre as tentativas: cada candidato define o próprio valor. O atrito aplicado fica registrado no log. |
| P5 | O DejaVu decide o próximo candidato ou o fail-safe; o Manager executa, respeitando a prioridade do ASM interno. |
| P6 | Fail-safe: parar o braço na pose atual, manter a garra como está, registrar o motivo, notificar pelo console e terminar o run com resultado explícito. É diferente de `SAFE_ABORT`, que abre a garra. |

## Medições que corrigiram a auditoria inicial

- A força normal medida ao segurar o cubo é de cerca de 170 N, no limite do motor, e não cerca de 26 N, como a estimativa inicial. A conta estática (cerca de 61 N de atrito disponível contra 9,8 N de peso) não explica o escorregamento; o E1 investiga isso.
- Em 0,14, a garra fechou a cerca de 1 cm do alvo de pegada. O fechamento prematuro não explica esse caso.
- Em 0,135, a falha anterior foi um erro do pipeline, não do candidato. Agora o vacuum roda e satisfaz o Then, mas o cubo cai depois e termina a 6,8 cm: é o primeiro exemplo de E.

## Resultado da Etapa 1 (versão `677d133`)

Uso exclusivo para classificar causas. Nenhum parâmetro foi ajustado.

| Atrito | Fase violada | Resultado | O que aconteceu com o C1 |
|---|---|---|---|
| 0,155 | Transporte | Falha detectada | Fechou acima do cubo (EE a 5,0 cm), com 36° de desalinhamento; sem contato |
| 0,145 | Transporte | Falha detectada | Pegou a borda: 3,3 cm fora do centro, 34° e força de 6 e 27 N; perdeu no tick seguinte |
| 0,14 | Lift | Falha detectada | Fechou acima do cubo (EE a 5,3 cm), com 17°; sem contato |
| 0,135 | Transporte | E — não detectada | Segurou a 170 N, deslizou 7 mm e caiu no step 77, depois do `success` no step 69 |
| 0,10 | Lift | Falha detectada | Segurou por 4 ticks sem deslizar, 2,4 cm fora do centro; perda súbita a 10 cm |
| 0,06 / 0,04 / 0,02 | Lift | Falha detectada | Alinhado, 170 N, perdeu em 1 a 2 ticks; atrito efetivo previsto de 0,18, 0,12 e 0,06 |
| 0,01 | Lift | Timeout | Nunca fechou: o cubo saiu da mesa a cerca de 0,65 m/s |
| 0,13 / 0,16 (controles) | Lift / Transporte | B | Alinhado, sem deslizar, objetivo global atingido |

Variação entre execuções: em 2 dos 11 runs (0,13 e 0,04), o vacuum começou um tick mais tarde que nos runs anteriores, mudando a distância final (1,5 para 2,1 cm; 45,0 para 34,4 cm), sem mudar a categoria. O resultado não é estritamente determinístico. Causa ainda não confirmada.
