# Friction Sweep — Resultados auditados

Varredura sistemática de `lateral_friction` de 0.800 a 0.010. Foram executados 25 experimentos, com um episódio por configuração.

> **Fontes primárias:** traces do DejaVu (`outputs/dejavu_traces/`) para UNSAT, estado da máquina, similaridade e evaluation; traces do Managing (`outputs/managing_traces/`) para steps observados, `is_success` e distância física final.
>
> **Importante:** em `goal_sequence`, o `is_success` do Managing indica que a sequência interna de subtasks terminou. Ele não garante que o objeto esteja fisicamente no goal. Por isso, `is_success` e sucesso físico aparecem em colunas separadas.

---

## Tabela geral

| # | Experimento | Friction | UNSAT? | Step UNSAT | Estado observado | Fase da falha | Steps observados | `grasp_attempts` | Score | Cenário candidato | Evaluation | `is_success` | Distância final | Objeto < 5 cm? | Observação |
|---|---|---:|---|---:|---|---|---:|---:|---:|---|---|---|---:|---|---|
| 01 | 01_0_80  | 0.800 | Não | —  | —      | Nenhuma | 64  | 1 | —     | — | —                    | True  | 1.75 cm   | Sim | A pega nominal satisfez lift e transport; objeto colocado dentro de 5 cm. |
| 02 | 02_0_70  | 0.700 | Não | —  | —      | Nenhuma | 64  | 1 | —     | — | —                    | True  | 1.56 cm   | Sim | A pega nominal satisfez lift e transport; objeto colocado dentro de 5 cm. |
| 03 | 03_0_60  | 0.600 | Não | —  | —      | Nenhuma | 64  | 1 | —     | — | —                    | True  | 1.62 cm   | Sim | A pega nominal satisfez lift e transport; objeto colocado dentro de 5 cm. |
| 04 | 04_0_50  | 0.500 | Não | —  | —      | Nenhuma | 64  | 1 | —     | — | —                    | True  | 1.51 cm   | Sim | A pega nominal satisfez lift e transport; objeto colocado dentro de 5 cm. |
| 05 | 05_0_40  | 0.400 | Não | —  | —      | Nenhuma | 64  | 1 | —     | — | —                    | True  | 0.59 cm   | Sim | A pega nominal satisfez lift e transport; objeto colocado dentro de 5 cm. |
| 06 | 06_0_30  | 0.300 | Não | —  | —      | Nenhuma | 64  | 1 | —     | — | —                    | True  | 0.62 cm   | Sim | A pega nominal satisfez lift e transport; objeto colocado dentro de 5 cm. |
| 07 | 07_0_25  | 0.250 | Não | —  | —      | Nenhuma | 64  | 1 | —     | — | —                    | True  | 1.87 cm   | Sim | A pega nominal satisfez lift e transport; objeto colocado dentro de 5 cm. |
| 08 | 08_0_20  | 0.200 | Não | —  | —      | Nenhuma | 64  | 1 | —     | — | —                    | True  | 3.23 cm   | Sim | A pega nominal satisfez lift e transport; objeto colocado dentro de 5 cm. |
| 09 | 09_0_18  | 0.180 | Sim | 39 | ERR_23 | Transport | 79  | 2 | 0.547 | `Lift Slip — Low Friction Surface` | success (2 ticks)    | True  | 2.93 cm   | Sim | Vacuum refez a pega e manteve 2 contatos durante o novo lift; o transporte recuperou a entrega. |
| 10 | 10_0_17  | 0.170 | Sim | 38 | ERR_23 | Transport | 98  | 2 | 0.468 | `Lift Slip — Low Friction Surface` | success (8 ticks)    | True  | 2.30 cm   | Sim | Vacuum refez a pega e manteve 2 contatos durante o novo lift; o transporte recuperou a entrega. |
| 11 | 11_0_16  | 0.160 | Sim | 38 | ERR_23 | Transport | 100 | 2 | 0.467 | `Lift Slip — Low Friction Surface` | success (8 ticks)    | True  | 1.97 cm   | Sim | Vacuum obteve 2 contatos no segundo fechamento e os manteve até retomar o transporte. |
| 12 | 12_0_155 | 0.155 | Sim | 41 | ERR_23 | Transport | 93  | 2 | 0.466 | `Lift Slip — Low Friction Surface` | failure/timeout (30) | True  | 9.01 cm   | **Não** | No step 51, a garra fechou sem contatos. Nos steps 52–56, somente o braço subiu enquanto o objeto permaneceu sobre a mesa; no step 57, o transporte foi retomado com a garra vazia. Uma causa possível, mas não comprovada isoladamente, é o desalinhamento horizontal de aproximadamente 3,2 cm entre o end effector e o centro do objeto no fechamento. |
| 13 | 13_0_150 | 0.150 | Sim | 38 | ERR_23 | Transport | 92  | 2 | 0.465 | `Lift Slip — Low Friction Surface` | success (6 ticks)    | True  | 1.35 cm   | Sim | Vacuum obteve 2 contatos no segundo fechamento e os manteve até retomar o transporte. |
| 14 | 14_0_145 | 0.145 | Sim | 38 | ERR_23 | Transport | 99  | 2 | 0.465 | `Lift Slip — Low Friction Surface` | failure/timeout (30) | True  | 28.03 cm  | **Não** | A falha foi causada por um ajuste inadequado do grasp durante o vacuum. No step 51, o fechamento desalinhado produziu 2 contatos apenas momentâneos; no step 52, eles foram perdidos antes da elevação. O braço subiu sozinho e retomou o transporte com a garra vazia. No fechamento, havia aproximadamente 3,3 cm de desalinhamento horizontal, e o objeto foi empurrado em vez de ficar preso de forma estável. |
| 15 | 15_0_140 | 0.140 | Sim | 23 | ERR_19 | Lift | 73  | 2 | 0.978 | `Lift Slip — Low Friction Surface` | failure/timeout (30) | True  | 41.43 cm  | **Não** | A adaptação não ajustou a garra à altura correta para realizar o grasp com vacuum. No step 28, a garra fechou no ar com 0 contatos e não movimentou o objeto; nos steps 29–32, somente o braço subiu e, no step 33, o transporte foi retomado com a garra vazia. O `phase_threshold` de 4,5 cm permitiu que a aproximação fosse considerada concluída prematuramente. |
| 16 | **16_0_135 — ANÔMALO** | 0.135 | Sim | 38 | ERR_23 | **Inconclusiva; registrada como Transport** | 65  | 1 | —     | — (pipeline interrompido) | não iniciada (erro)  | True  | 39.85 cm  | **Não** | **Defasagem aparente da SM e erro `float → int`; excluído da fronteira.** |
| 17 | 17_0_130 | 0.130 | Sim | 23 | ERR_19 | Lift | 75  | 2 | 0.976 | `Lift Slip — Low Friction Surface` | success (1 tick)     | True  | 1.50 cm   | Sim | Vacuum refez a pega, sustentou 2 contatos até atingir a altura exigida e permitiu concluir a entrega. |
| 18 | 18_0_120 | 0.120 | Sim | 23 | ERR_19 | Lift | 81  | 2 | 0.975 | `Lift Slip — Low Friction Surface` | success (1 tick)     | True  | 1.85 cm   | Sim | Vacuum refez a pega, sustentou 2 contatos até atingir a altura exigida e permitiu concluir a entrega. |
| 19 | 19_0_110 | 0.110 | Sim | 22 | ERR_19 | Lift | 73  | 2 | 0.974 | `Lift Slip — Low Friction Surface` | success (1 tick)     | True  | 1.42 cm   | Sim | Vacuum refez a pega, sustentou 2 contatos até atingir a altura exigida e permitiu concluir a entrega. |
| 20 | 20_0_100 | 0.100 | Sim | 23 | ERR_19 | Lift | 78  | 2 | 0.972 | `Lift Slip — Low Friction Surface` | failure/timeout (30) | True  | 35.11 cm  | **Não** | O objeto escorregou no lift original. Durante o vacuum, o segundo grasp ficou mal posicionado, com aproximadamente 2,3 cm de desalinhamento horizontal. A garra obteve 2 contatos momentâneos, mas a pega ficou instável e o objeto escorregou novamente durante o novo lift, no step 32; o transporte foi retomado com a garra vazia. |
| 21 | 21_0_080 | 0.080 | Sim | 22 | ERR_19 | Lift | 74  | 2 | 0.969 | `Lift Slip — Low Friction Surface` | success (1 tick)     | True  | 2.26 cm   | Sim | Após o objeto escorregar no lift original, a adaptação realizou um segundo grasp bem alinhado: no step 29, o end effector estava a aproximadamente 1,4 cm do centro do objeto no plano horizontal e obteve 2 contatos. Esses contatos foram mantidos durante todo o novo lift e o transporte, sem nova queda; o objeto atingiu 14 cm de altura, foi levado ao destino e terminou a 2,26 cm do goal. |
| 22 | 22_0_060 | 0.060 | Sim | 23 | ERR_19 | Lift | 73  | 2 | 0.967 | `Lift Slip — Low Friction Surface` | failure/timeout (30) | True  | 47.80 cm  | **Não** | O objeto escorregou durante o lift original. A adaptação aplicou `vacuum_assist` e realizou uma segunda tentativa de grasp, mas o contato ficou instável ou mal posicionado: no step 28, houve 2 contatos por apenas um tick; no step 29, os contatos foram perdidos durante a nova elevação. O objeto girou, caiu novamente e foi deslocado lateralmente sobre a mesa; o transporte prosseguiu com a garra vazia. O ajuste inadequado do grasp é uma inferência física sustentada pela perda imediata dos contatos, pela rotação acentuada e pelo deslocamento lateral do objeto. |
| 23 | 23_0_040 | 0.040 | Sim | 23 | ERR_19 | Lift | 78  | 2 | 0.964 | `Lift Slip — Low Friction Surface` | failure/timeout (30) | True  | 44.98 cm  | **Não** | O segundo grasp não apresentou desalinhamento grosseiro e chegou a produzir 2 contatos. Durante a nova elevação, porém, os contatos caíram para 1 e depois para 0, acompanhados de forte rotação e deslocamento lateral do objeto. Neste run, a falha é mais compatível com atrito efetivo insuficiente para o `vacuum_assist` sustentar o objeto do que com um grasp mal posicionado. |
| 24 | 24_0_020 | 0.020 | Sim | 23 | ERR_19 | Lift | 76  | 2 | 0.961 | `Lift Slip — Low Friction Surface` | failure/timeout (30) | True  | 34.22 cm  | **Não** | O `vacuum_assist` realizou o segundo fechamento e obteve 2 contatos por apenas um tick, mas não conseguiu mantê-los durante a nova elevação; o objeto voltou à mesa e o transporte prosseguiu vazio. O comportamento é consistente com atrito efetivo insuficiente nessa faixa. |
| 25 | 25_0_010 | 0.010 | Sim | 23 | ERR_19 | Lift | 502* | 1 | 0.960 | `Lift Slip — Low Friction Surface` | waiting               | False | 198.05 cm | **Não** | Neste caso extremo, o `vacuum_assist` não alcançou um novo fechamento nem contato: permaneceu ativo enquanto o objeto se afastava até o timeout externo. Portanto, não houve sequer uma nova pega para testar sua sustentação; ainda assim, o run integra a faixa `≤ 0.040` em que nenhuma recuperação física foi observada. |

> \* O experimento 25 não concluiu o episódio. `502` é o último step registrado antes do timeout externo de 600 segundos do runner, e não o total normal de um episódio concluído.

### Significado das colunas

| Coluna | Significado |
|---|---|
| **Step UNSAT** | Primeiro step em que o trace do DejaVu registra `SAT=False` e `*** UNSAT ***`. |
| **Estado observado** | Estado efetivamente registrado no trace. `ERR_19` corresponde à falha da pós-condição de `LIFT_OBJECT`; `ERR_23`, à falha da pós-condição de `TRANSPORT_OBJECT`. |
| **Fase da falha** | Interpretação da fase em que a SM detectou o problema. No experimento 16, ela é inconclusiva porque a percepção e a transição apresentam uma defasagem aparente. |
| **Steps observados** | Maior step presente no trace do Managing. Para 01–24, coincide com o término da sequência; no caso 25, é apenas o último step antes do encerramento externo. |
| **`grasp_attempts`** | Contador do Manager incrementado quando `grasp_completed` muda de 0 para 1. Na implementação atual, isso é inferido pela largura da garra; portanto, o valor não prova contato nem re-grasp bem-sucedido. |
| **Score** | Maior similaridade registrada; em todos os 16 arquivos de similaridade, o primeiro candidato é `Lift Slip — Low Friction Surface`. |
| **Cenário candidato** | Cenário do catálogo com a maior similaridade e cuja ação foi recomendada. O experimento 16 não possui candidato porque o pipeline falhou antes de produzir o ranking. |
| **Evaluation** | Avaliação do DejaVu da postcondição do cenário diagnosticado. O contador começa somente depois que a subtask adaptativa termina. |
| **`is_success`** | Valor bruto emitido pelo Managing. Em `goal_sequence`, reflete `_all_done()` da sequência, não a distância final do objeto. |
| **Distância final** | Último valor 3D `Dist Cubo→target` registrado pelo Managing. |
| **Objeto < 5 cm?** | Verificação independente da posição física final usando o limiar configurado de 0.05 m. |
| **Observação** | Síntese descritiva do comportamento registrado. Quando a causa de baixo nível não é demonstrada pelo trace, a observação limita-se ao resultado verificável. |

---

## Mapa dos erros por fase

| Classificação | Experimentos | Significado |
|---|---|---|
| **Sem erro/UNSAT** | 01, 02, 03, 04, 05, 06, 07, 08 | A sequência não entrou em estado `ERR`. |
| **Erro no transport (`ERR_23`)** | 09, 10, 11, 12, 13, 14 | Ao terminar `transport_to_goal()`, pelo menos uma pós-condição falhou: distância ao goal ≤ 5 cm, altura ≥ 10 cm ou contatos ≥ 2. |
| **Erro no lift (`ERR_19`)** | 15, 17, 18, 19, 20, 21, 22, 23, 24, 25 | Ao terminar `lift_object()`, o objeto não satisfazia simultaneamente altura ≥ 10 cm e contatos ≥ 2. |
| **Anômalo/inconclusivo** | **16** | O trace registra `ERR_23`, mas há evidência de que o objeto perdeu altura e contatos na transição do lift enquanto a SM aprovou `PHI_19` com valores aparentemente defasados. Não deve ser usado para inferir a fronteira entre `ERR_19` e `ERR_23`. |

O experimento 16 permanece na tabela com seu valor bruto (`ERR_23`) para preservar a rastreabilidade. A classificação “inconclusiva” é uma avaliação de validade do run, não uma alteração do dado registrado.

---

## Resultados observados

### Operação sem UNSAT — experimentos 01 a 08

- Para friction de 0.800 a 0.200, nenhum UNSAT foi registrado.
- Todas as execuções terminaram em 64 steps, com `grasp_attempts=1`.
- Não foram gerados arquivos de similaridade, pois o pipeline de diagnóstico/adaptação não foi ativado.
- Em todas elas, o objeto terminou fisicamente dentro de 5 cm do goal.

### UNSAT associado a TRANSPORT_OBJECT — experimentos 09 a 14

- Para friction de 0.180 a 0.145, o primeiro UNSAT ocorreu em `ERR_23`, entre os steps 38 e 41.
- Antes da falha, o objeto chegou a satisfazer a condição de lift; depois perdeu altura e contatos durante a progressão para transporte/place.
- O candidato selecionado foi `Lift Slip — Low Friction Surface`, com score entre 0.465 e 0.547.
- A evaluation terminou em success nos experimentos 09, 10, 11 e 13. Esses quatro também terminaram fisicamente dentro de 5 cm do goal.
- A evaluation terminou por timeout nos experimentos 12 e 14. Eles finalizaram, respectivamente, a 9.01 cm e 28.03 cm do goal, apesar de `is_success=True`.

#### Por que o experimento 12 falhou entre dois casos bem-sucedidos?

O resultado não foi causado apenas pelo valor nominal da friction. Os traces mostram trajetórias de queda e resultados de re-grasp diferentes:

| Experimento | Situação antes/depois da adaptação | Resultado do segundo fechamento |
|---|---|---|
| 11 — friction 0.160 | O objeto já estava a aproximadamente 28 cm do goal quando a recuperação começou. | Obteve dois contatos no step 50, foi levantado e terminou a 1.97 cm do goal. |
| 12 — friction 0.155 | O objeto chegou a 2 cm do goal com 12 cm de altura no step 36, perdeu os contatos no step 37, ultrapassou o goal e estabilizou a aproximadamente 9 cm. | `grasp_attempts` passou para 2 no step 51, mas `finger_contacts` permaneceu em 0. O braço subiu sem o objeto. |
| 13 — friction 0.150 | O objeto estava a aproximadamente 21 cm do goal quando a recuperação começou. | Obteve dois contatos no step 48, foi levantado e terminou a 1.35 cm do goal. |

No experimento 12, a causa imediata comprovada é a falha física do segundo grasp: houve fechamento da garra, mas não houve contato. Mesmo assim, `VacuumAssistTask` terminou quando o end effector alcançou sua altura-alvo, pois sua condição de término não verifica a altura nem os contatos do objeto. O Managing então retomou o transport com a garra vazia, e o objeto permaneceu a aproximadamente 9 cm do goal.

A posição, orientação e temporização da queda são explicações plausíveis para o re-grasp malsucedido, mas os traces atuais não permitem isolar qual delas foi a causa de baixo nível. Portanto, o experimento 12 deve permanecer como falha observada da estratégia de recuperação, não ser descartado. São necessárias repetições de 0.160, 0.155 e 0.150 para determinar se o comportamento é recorrente.

### UNSAT associado a LIFT_OBJECT — experimentos 15 e 17 a 25

- O primeiro UNSAT ocorreu em `ERR_19`, normalmente nos steps 22 ou 23.
- O candidato selecionado continuou sendo `Lift Slip — Low Friction Surface`, agora com score entre 0.960 e 0.978.
- A diferença de score descreve a maior similaridade estrutural entre o cenário diagnosticado em `LIFT_OBJECT` e o candidato. O score, isoladamente, não demonstra que a adaptação terá sucesso físico.

#### O que `vacuum_assist` representa neste simulador

O nome `vacuum_assist` identifica a estratégia de adaptação, mas a implementação atual não simula uma força de sucção nem cria uma conexão rígida entre a garra e o objeto. A estratégia aumenta o `lateralFriction` dos dois dedos para `3.0`, aproxima novamente o end effector da posição corrente do objeto, fecha a garra e executa um novo lift. Dessa forma, o objeto continua dependendo de contatos físicos estáveis com os dedos; o baixo `lateral_friction` configurado para o objeto ainda influencia a capacidade de sustentação.

A `VacuumAssistTask` considera a adaptação concluída quando o end effector alcança a altura-alvo. Sua condição de término não verifica se o objeto acompanhou o movimento, se atingiu a altura esperada ou se os dois contatos foram mantidos. Por isso, a subtask pode terminar e devolver o controle ao transporte mesmo quando a garra está vazia.

Resultados da adaptação nesse conjunto:

| Resultado observado | Experimentos | Evidência |
|---|---|---|
| Evaluation success e objeto final < 5 cm | 17, 18, 19, 21 | A postcondição foi satisfeita e a entrega física final ficou dentro do limiar. |
| Evaluation timeout e objeto final > 5 cm | 15, 20, 22, 23, 24 | A sequência interna terminou, mas a recuperação física não ocorreu. |
| Evaluation permaneceu waiting | 25 | A subtask adaptativa não terminou antes do timeout externo. |

Não há, nesta bateria, uma fronteira monotônica demonstrada para a eficácia do vacuum. Há recuperação em 0.130, 0.120, 0.110 e 0.080, mas falha em 0.140, 0.100 e 0.060. Para `lateral_friction ≤ 0.040`, nenhuma execução apresentou recuperação física: em 0.040 e 0.020, houve contatos momentâneos que não foram sustentados durante o novo lift; em 0.010, o `vacuum_assist` não chegou a realizar um novo fechamento antes do timeout externo. Assim, `≤ 0.040` pode ser tratado como um limite operacional observado nesta bateria, mas não como uma fronteira física ou estatisticamente comprovada.

A comparação das tentativas de recuperação mostra que o resultado não depende apenas do valor nominal de friction. Em 0.080, o segundo grasp obteve dois contatos e os manteve durante o novo lift e o transporte. Em 0.060, os dois contatos duraram apenas um tick e foram seguidos por queda, rotação e deslocamento lateral. Em 0.040, a perda foi progressiva, de dois contatos para um e depois zero; em 0.020, os contatos também foram apenas momentâneos. No caso extremo de 0.010, não ocorreu um segundo fechamento antes do timeout. Essas diferenças evidenciam a influência conjunta do atrito, do posicionamento, da orientação e da dinâmica instantânea do re-grasp.

Também não é possível inferir apenas de `vacuum_friction × lateral_friction` que o mecanismo sustenta ou não uma massa de 1 kg. Essa conclusão exigiria medir ou controlar forças normais, contatos e dinâmica do grasp.

### Como interpretar os ticks da evaluation

O DejaVu permanece em `waiting` enquanto `APPLY_VACUUM_ASSIST` está ativa. O contador começa quando a subtask muda e a evaluation entra em `evaluating`.

Assim, `success (1 tick)` significa “postcondição satisfeita no primeiro tick de avaliação após o término da subtask adaptativa”, e não “vacuum resolveu no tick imediatamente seguinte ao UNSAT”. Nos traces:

- experimento 17: UNSAT no step 23; evaluation success no step 35;
- experimento 18: step 23 → 36;
- experimento 19: step 22 → 35;
- experimento 21: step 22 → 35.

---

## Caso anômalo — `16_0_135`

O experimento `16_0_135` apresentou dois problemas distintos.

### Defasagem aparente entre percepção e estado da SM

- No step 22, o trace registra altura de 12 cm e dois contatos.
- No step 23, a percepção já registra altura de 7 cm e zero contatos.
- Ainda no step 23, a SM aceita as guards de lift usando valores compatíveis com o tick anterior e avança para `S22`/TRANSPORT.
- O primeiro UNSAT só é emitido no step 38, quando a ação de transporte termina e a postcondição de `ERR_23` é verificada.

Os traces demonstram uma defasagem aparente de um tick entre os valores impressos na percepção e os valores usados na transição. Eles não bastam, sozinhos, para classificar o problema como uma race condition concorrente.

### Erro no pipeline de similaridade

O diagnóstico adicionou a condição `finger_contacts <= 1.0`. Durante o processamento, o pipeline tentou converter a string `1.0` diretamente para `int` e falhou:

```text
[PIPELINE] Erro: invalid literal for int() with base 10: '1.0'
```

Consequências observadas:

- nenhum arquivo de similaridade foi produzido;
- nenhuma evaluation foi iniciada;
- `grasp_attempts` permaneceu em 1;
- a sequência interna terminou em 65 steps, mas o objeto ficou a 39.85 cm do goal;
- `is_success=True` foi um falso positivo em relação à posição física.

Esse experimento deve ser repetido depois da correção do parser `float → int` para gerar um resultado comparável aos demais.

---

## Experimento 25 — stall até o timeout externo

No experimento `25_0_010`:

- o primeiro UNSAT ocorreu no step 23, em `ERR_19`;
- a adaptação foi enviada, mas permaneceu em `APPLY_VACUUM_ASSIST`/`waiting`;
- no último registro, `task_aborted=0` e `is_success=False`;
- o objeto estava a 1.9805 m do goal e fora da região útil da tarefa;
- o runner encerrou o processo pelo limite externo de 600 segundos, antes do `max_steps=1000` do episódio.

Portanto, o resultado deve ser descrito como stall sem progresso até o timeout externo, não como loop infinito comprovado nem como abort interno. A implementação de `VacuumAssistTask` não possui timeout ou condição de falha para o caso em que o objeto deixa de ser alcançável.

---

## Conclusões limitadas a esta bateria

- **Fronteira observada de detecção:** não houve UNSAT em 0.200; houve em 0.180. Isso descreve somente estes runs.
- **Mudança provisória do estado de falha:** entre os runs considerados válidos para essa comparação, 0.145 produziu `ERR_23` e 0.140 produziu `ERR_19`.
- **Run excluído da inferência dessa fronteira:** 0.135/experimento 16 registrou `ERR_23`, mas é anômalo e inconclusivo por causa da defasagem entre percepção e transição; o dado bruto continua documentado.
- **Adaptação com sucesso físico:** 09, 10, 11, 13, 17, 18, 19 e 21.
- **Adaptação avaliada sem recuperação física:** 12, 14, 15, 20, 22, 23 e 24.
- **Pipeline interrompido antes da adaptação:** 16.
- **Adaptação sem conclusão antes do timeout externo:** 25.
- **Falsos positivos do `is_success`:** 12, 14, 15, 16, 20, 22, 23 e 24.
- **Candidato mais similar:** `Lift Slip — Low Friction Surface` em todos os 16 casos que produziram arquivo de similaridade.
- **Limite operacional observado do `vacuum_assist`:** para `lateral_friction ≤ 0.040`, nenhuma execução apresentou recuperação física. Esse resultado vale para esta bateria e não estabelece uma fronteira física ou estatisticamente comprovada.

Como foi executado apenas um episódio por valor de friction, as transições acima devem ser tratadas como observações desta bateria, não como limiares estatisticamente estabelecidos. Para estimar fronteiras robustas, são necessárias múltiplas repetições por configuração e o relato da taxa de sucesso físico.

---

## Limitação conhecida da coleta de outputs

No runner atual, `_restore_base()` é chamado antes de `_collect_outputs()`. Como a restauração também substitui o diretório do dataset, os arquivos presentes em `outputs/dataset/` correspondem ao dataset base restaurado, e não necessariamente ao estado produzido durante o experimento.

Essa limitação não altera os números desta tabela, calculados a partir de traces e similarities, mas precisa ser corrigida antes de usar `outputs/dataset/` como evidência experimental.
