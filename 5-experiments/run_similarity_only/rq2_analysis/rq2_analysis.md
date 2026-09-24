# RQ2.0 -- Retrieval Robustness to Scenario Analysis Inaccuracies

Relatório único gerado por `decompose_rq2_similarity.py`, chamando diretamente as funções reais de `3-dejavu/src/similarity/dejavu_similarity.py` (`calculate_scenario_similarity`, `calculate_conditional_similarity`, `calculate_parameters_similarity`, `_parameter_similarity_weighted_avg`, `_extract_parameters`, `_tversky_similarity`). Nenhuma fórmula foi reimplementada; nenhuma simulação física foi executada.

**Candidato de referência**: identificado pelo campo `do == "apply_vacuum_assist()"` (a chave do catálogo `lift_slip_low_friction` não é preservada nem no JSONL de produção nem nos CSVs -- só name/given/when/do/then).

**Nota sobre as descrições**: o campo `comment` do `desired_scenario.json` de entrada não é usado por nenhuma função do Retriever e não aparece em nenhum output oficial (`Scenario.to_dict()` só serializa type/name/given/when/do/then). A coluna `description` abaixo foi reconstruída a partir do sufixo do nome do cenário (convenção `RQ2_<ID>_<descrição>`), não do comentário original.

## Validação

- Comparado contra `similarities_20260920_010433.jsonl` (mais recente em `output/similarities/`).
- Comparados 6433 de 6454 registros. Maior divergência absoluta: 0.00e+00
- Combinações presentes aqui mas ausentes no jsonl (ex.: cenários novos ainda não rodados por main.py): 21 -- normal se `desired_scenario.json` foi editado depois do último run de main.py.
- RESULTADO: valores idênticos (dentro de erro de ponto flutuante) aos registros do experimento.

## Grupo A -- omissões estruturais

| ID | descrição | Top-1 | score Top-1 | rank referência | score referência | melhor concorrente | score concorrente | margem (assinada) | Top-1 == referência? | empate exato? |
|---|---|---|---|---|---|---|---|---|---|---|
| A0 | baseline full context | Lift Slip — Low Friction Surface | 0.97639 | 1 | 0.97639 | Parallel Arm Lift — Contact Loss | 0.89655 | 0.07984 | sim | nao |
| A1 | omit friction | Parallel Arm Lift — Contact Loss | 1.00000 | 2 | 0.98413 | Parallel Arm Lift — Contact Loss | 1.00000 | -0.01587 | **NAO** | nao |
| A2 | omit contacts | Lift Slip — Low Friction Surface | 0.94871 | 1 | 0.94871 | Parallel Arm Lift — Contact Loss | 0.83333 | 0.11538 | sim | nao |
| A3 | omit height | Lift Slip — Low Friction Surface | 0.94871 | 1 | 0.94871 | Parallel Arm Lift — Contact Loss | 0.83333 | 0.11538 | sim | nao |
| A4 | height only | Parallel Arm Lift — Contact Loss | 0.96970 | 2 | 0.94444 | Parallel Arm Lift — Contact Loss | 0.96970 | -0.02525 | **NAO** | nao |
| A5 | contacts only | Parallel Arm Lift — Contact Loss | 0.96970 | 2 | 0.94444 | Parallel Arm Lift — Contact Loss | 0.96970 | -0.02525 | **NAO** | nao |
| A6 | friction only | Lift Slip — Low Friction Surface | 0.87361 | 1 | 0.87361 | Parallel Arm Lift — Contact Loss | 0.66667 | 0.20694 | sim | nao |

## Grupo B -- adições estruturais

| ID | descrição | Top-1 | score Top-1 | rank referência | score referência | melhor concorrente | score concorrente | margem (assinada) | Top-1 == referência? | empate exato? |
|---|---|---|---|---|---|---|---|---|---|---|
| B1 | incremental step1 add mass | Lift Slip — Low Friction Surface | 0.89947 | 1 | 0.89947 | Cobot Industrial — Incremental Heavy Part Transfer | 0.88655 | 0.01292 | sim | nao |
| B2 | incremental step2 add mass gripper width | Lift Slip — Low Friction Surface | 0.85139 | 1 | 0.85139 | Cobot Industrial — Incremental Heavy Part Transfer | 0.84063 | 0.01076 | sim | nao |
| B3 | incremental step3 add mass gripper width grasp attempts | Lift Slip — Low Friction Surface | 0.81849 | 1 | 0.81849 | Cobot Industrial — Incremental Heavy Part Transfer | 0.80896 | 0.00953 | sim | nao |

## Grupo C -- variação paramétrica de lateral_friction

| ID | descrição | Top-1 | score Top-1 | rank referência | score referência | melhor concorrente | score concorrente | margem (assinada) | Top-1 == referência? | empate exato? |
|---|---|---|---|---|---|---|---|---|---|---|
| C01 | friction 0.340 | Lift Slip — Low Friction Surface | 0.98333 | 1 | 0.98333 | Parallel Arm Lift — Contact Loss | 0.89655 | 0.08678 | sim | nao |
| C02 | friction 0.335 | Lift Slip — Low Friction Surface | 0.98194 | 1 | 0.98194 | Parallel Arm Lift — Contact Loss | 0.89655 | 0.08539 | sim | nao |
| C03 | friction 0.330 | Lift Slip — Low Friction Surface | 0.98056 | 1 | 0.98056 | Parallel Arm Lift — Contact Loss | 0.89655 | 0.08400 | sim | nao |
| C04 | friction 0.3275 | Lift Slip — Low Friction Surface | 0.97986 | 1 | 0.97986 | Parallel Arm Lift — Contact Loss | 0.89655 | 0.08331 | sim | nao |
| C05 | friction 0.325 | Lift Slip — Low Friction Surface | 0.97917 | 1 | 0.97917 | Parallel Arm Lift — Contact Loss | 0.89655 | 0.08261 | sim | nao |
| C06 | friction 0.3225 | Lift Slip — Low Friction Surface | 0.97847 | 1 | 0.97847 | Parallel Arm Lift — Contact Loss | 0.89655 | 0.08192 | sim | nao |
| C07 | friction 0.320 | Lift Slip — Low Friction Surface | 0.97778 | 1 | 0.97778 | Parallel Arm Lift — Contact Loss | 0.89655 | 0.08123 | sim | nao |
| C09 | friction 0.310 | Lift Slip — Low Friction Surface | 0.97500 | 1 | 0.97500 | Parallel Arm Lift — Contact Loss | 0.89655 | 0.07845 | sim | nao |
| C10 | friction 0.305 | Lift Slip — Low Friction Surface | 0.97361 | 1 | 0.97361 | Parallel Arm Lift — Contact Loss | 0.89655 | 0.07706 | sim | nao |
| C11 | friction 0.300 | Lift Slip — Low Friction Surface | 0.97222 | 1 | 0.97222 | Parallel Arm Lift — Contact Loss | 0.89655 | 0.07567 | sim | nao |
| C12 | friction 0.290 | Lift Slip — Low Friction Surface | 0.96944 | 1 | 0.96944 | Parallel Arm Lift — Contact Loss | 0.89655 | 0.07289 | sim | nao |
| C13 | friction 0.280 | Lift Slip — Low Friction Surface | 0.96667 | 1 | 0.96667 | Parallel Arm Lift — Contact Loss | 0.89655 | 0.07011 | sim | nao |
| C14 | friction 0.270 | Lift Slip — Low Friction Surface | 0.96389 | 1 | 0.96389 | Parallel Arm Lift — Contact Loss | 0.89655 | 0.06734 | sim | nao |
| C15 | friction 0.260 | Lift Slip — Low Friction Surface | 0.96111 | 1 | 0.96111 | Parallel Arm Lift — Contact Loss | 0.89655 | 0.06456 | sim | nao |
| C16 | friction 0.255 | Lift Slip — Low Friction Surface | 0.95972 | 1 | 0.95972 | Parallel Arm Lift — Contact Loss | 0.89655 | 0.06317 | sim | nao |

## Grupo R -- grade fatorial de regiões (RQ2.2: Height x Contacts x Friction)

Total de pontos no grid: **897**.

- Top-1 == referência (`apply_vacuum_assist()`): 890/897 (99.2%)
- Top-1 mudou de identidade: 7/897 (0.8%)
- Empates exatos (margem == 0.0): 36
- Margem assinada: mínimo=-0.00766, máximo=0.17984, média=0.08734

**Para quem o Top-1 muda, quando muda:**

- `reposition_and_regrip()`: 7 ponto(s) do grid

**Taxa de mudança de Top-1 por nível de cada dimensão do grid:**

Altura (H):
| H | total | Top-1 mudou | taxa |
|---|---|---|---|
| 01 | 100 | 0 | 0.0% |
| 02 | 100 | 2 | 2.0% |
| 03 | 97 | 3 | 3.1% |
| 04 | 100 | 2 | 2.0% |
| 05 | 100 | 0 | 0.0% |
| 06 | 100 | 0 | 0.0% |
| 07 | 100 | 0 | 0.0% |
| 08 | 100 | 0 | 0.0% |
| 09 | 100 | 0 | 0.0% |

Contatos (C):
| C | total | Top-1 mudou | taxa |
|---|---|---|---|
| 01 | 90 | 0 | 0.0% |
| 02 | 87 | 7 | 8.0% |
| 03 | 90 | 0 | 0.0% |
| 04 | 90 | 0 | 0.0% |
| 05 | 90 | 0 | 0.0% |
| 06 | 90 | 0 | 0.0% |
| 07 | 90 | 0 | 0.0% |
| 08 | 90 | 0 | 0.0% |
| 09 | 90 | 0 | 0.0% |
| 10 | 90 | 0 | 0.0% |

Fricção (F):
| F | total | Top-1 mudou | taxa |
|---|---|---|---|
| 01 | 90 | 0 | 0.0% |
| 02 | 89 | 0 | 0.0% |
| 03 | 89 | 0 | 0.0% |
| 04 | 89 | 0 | 0.0% |
| 05 | 90 | 0 | 0.0% |
| 06 | 90 | 0 | 0.0% |
| 07 | 90 | 0 | 0.0% |
| 08 | 90 | 1 | 1.1% |
| 09 | 90 | 3 | 3.3% |
| 10 | 90 | 3 | 3.3% |

O ponto-a-ponto completo dos 897 cenários (score, rank, margem por candidato) está em `rq2_summary.csv` e `rq2_full_ranking.csv` -- filtre por `experiment_id` começando com `R_`.

## Por que a recuperação muda nas omissões estruturais (Grupo A)

- **A0 (baseline)**: `apply_vacuum_assist()` given = 0.92917 (paramétrico=0.92917, penalidade=0.00000). `reposition_and_regrip()` given = 0.68966 (paramétrico=1.00000, penalidade=0.31034).
- **A1 (sem lateral_friction em D)**: `apply_vacuum_assist()` given sobe para 0.95238 (penalidade cai de 0.00000 para 0.04762 -- deixa de ser penalizado pelo *valor* de friction diferente, passa a ser penalizado só pela beta leve de ter um parâmetro extra não usado).
- Só que `reposition_and_regrip()` sobe **muito mais**: de 0.68966 para 1.00000 (penalidade cai de 0.31034 para 0.00000 -- deixa de ser penalizado pela alpha PESADA de 'faltar' lateral_friction, porque agora D também não tem mais esse parâmetro).
- **A assimetria alpha=0.9/beta=0.1 explica tudo**: faltar um parâmetro que D tem custa caro (peso alpha); ter um parâmetro extra que D não tem custa pouco (peso beta). Remover `lateral_friction` de D beneficia MUITO mais quem já não tinha esse parâmetro (`reposition_and_regrip`) do que quem já tinha um valor compatível (`apply_vacuum_assist`). O resultado individual da referência melhora, mas o do concorrente melhora mais -- é uma perda por competição relativa, não um erro de cálculo.

- **A4/A5 (só resta 1 sintoma)**: o vencedor passa a depender de **quantos parâmetros extras não usados** cada candidato carrega -- `apply_vacuum_assist()` tem 2 extras (penalidade=0.16667), `reposition_and_regrip()` tem só 1 extra (penalidade=0.09091). Menos extras = menos penalidade beta acumulada = vence.
- **A6 (só resta lateral_friction)**: `apply_vacuum_assist()` ainda compartilha esse parâmetro (given=0.62083), `reposition_and_regrip()` não tem `lateral_friction` no given -- zero sobreposição, penalidade máxima (given=0.00000). Sobreposição imperfeita ainda vale mais que nenhuma sobreposição.

## Efeito das adições estruturais (Grupo B)

Cada cenário B preserva o Given completo do baseline (A0) e acrescenta UM parâmetro extra (não presente na referência original) com um limiar fisicamente genérico (não aprendido pelo Diagnoser). Isso testa o efeito de **adicionar** informação contextual, o oposto do Grupo A.

- **B1** (incremental step1 add mass): Top-1 = `apply_vacuum_assist()` (score 0.89947), referência em rank 1 (margem 0.01292).
- **B2** (incremental step2 add mass gripper width): Top-1 = `apply_vacuum_assist()` (score 0.85139), referência em rank 1 (margem 0.01076).
- **B3** (incremental step3 add mass gripper width grasp attempts): Top-1 = `apply_vacuum_assist()` (score 0.81849), referência em rank 1 (margem 0.00953).

## Variação paramétrica de lateral_friction (Grupo C)

| Cenário | Given(vac) paramétrico | Given(vac) penalidade | Given(vac) final | Final(vac) |
|---|---|---|---|---|
| C01 | 0.95000 | 0.00000 | 0.95000 | 0.98333 |
| C02 | 0.94583 | 0.00000 | 0.94583 | 0.98194 |
| C03 | 0.94167 | 0.00000 | 0.94167 | 0.98056 |
| C04 | 0.93958 | 0.00000 | 0.93958 | 0.97986 |
| C05 | 0.93750 | 0.00000 | 0.93750 | 0.97917 |
| C06 | 0.93542 | 0.00000 | 0.93542 | 0.97847 |
| C07 | 0.93333 | 0.00000 | 0.93333 | 0.97778 |
| C09 | 0.92500 | 0.00000 | 0.92500 | 0.97500 |
| C10 | 0.92083 | 0.00000 | 0.92083 | 0.97361 |
| C11 | 0.91667 | 0.00000 | 0.91667 | 0.97222 |
| C12 | 0.90833 | 0.00000 | 0.90833 | 0.96944 |
| C13 | 0.90000 | 0.00000 | 0.90000 | 0.96667 |
| C14 | 0.89167 | 0.00000 | 0.89167 | 0.96389 |
| C15 | 0.88333 | 0.00000 | 0.88333 | 0.96111 |
| C16 | 0.87917 | 0.00000 | 0.87917 | 0.95972 |

- **O único componente que muda é o termo paramétrico (Jaccard) de `lateral_friction`** -- a penalidade estrutural permanece 0.0 em toda a grade, porque variar só o threshold nunca altera quais parâmetros aparecem no Given.
- O ranking permanece estável na faixa testada porque `reposition_and_regrip()` não depende de `lateral_friction` (seu score fica constante), e a referência nunca cai abaixo desse piso constante dentro da grade avaliada.

## Dados completos

- `rq2_summary.csv` -- 1 linha por Desired Adaptation Scenario (Top-1, rank/score da referência, melhor concorrente, margem assinada, flags de empate/retenção).
- `rq2_full_ranking.csv` -- ranking completo (1 linha por par cenário-candidato).
- `rq2_similarity_decomposition.csv` -- decomposição completa (Given/When/Then, componente paramétrico e penalidade estrutural de cada cláusula, parâmetros compartilhados/ausentes/extras).
