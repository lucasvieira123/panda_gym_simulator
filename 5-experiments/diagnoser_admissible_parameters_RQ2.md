# Conjunto admissível de parâmetros para perturbações estruturais — RQ2

Análise do `UnanticipatedScenarioDiagnoser` do DejaVu (código, configs e dados reais), feita para definir quais colunas dos traces do braço robótico podem legitimamente ser usadas como perturbações estruturais no RQ2. Nenhum código foi alterado, nenhum experimento foi executado — apenas leitura de `3-dejavu/src/*.py`, dos configs, dos CSVs de `5-experiments/base/` e dos traces/similarities reais de `5-experiments/results/`.

Cenário de referência (Desired Adaptation Scenario):

```
Given:
object_lift_height_cm < 10
AND finger_contacts < 2
AND lateral_friction <= 0.315

When:
grasp_completed == 1

Then:
object_lift_height_cm >= 10
AND finger_contacts >= 2
```

---

## 1–3. Quais colunas entram no Diagnoser, existe seleção explícita, janela temporal

Código: [`unanticipated_scenario_diagnoser.py:66-110`](../3-dejavu/src/unanticipated_scenario_diagnoser.py#L66)

Pipeline de seleção de features — **explícito, automático, roda a cada diagnóstico**, não é um allowlist fixo de parâmetros físicos:

1. Filtra linhas onde `active_scenario_name == scenario_name` (ex. `LIFT_OBJECT`).
2. **Snapshot**: `scenario_rows.groupby("execution").first()` — pega **só a primeira linha** de cada execução dentro da janela daquele cenário. **Não** é uma janela temporal nem usa todas as observações — é 1 snapshot por execução, no instante em que o cenário ficou ativo.
3. Remove colunas do denylist fixo `_DROP_COLS` ([:10-14](../3-dejavu/src/unanticipated_scenario_diagnoser.py#L10)): `sat, execution, episode, step, exec, active_state, active_scenario_name, active_scenario_type, current_subtask, current_task, active_target_name, tipo`.
4. `X_num = X_raw.select_dtypes(include=[np.number, bool])` — descarta colunas string: `objects.object_1.type`, `robot_config.control_type`, `target_goal.type`, `target_goal.targets.0.name`, `target_goal.mode`.
5. `X_all = X_num.loc[:, X_num.nunique() > 1]` — descarta colunas **constantes em todo o dataset de treino** (sem variância entre execuções → zero informação).
6. **Filtro estático**: mantém só colunas onde `std == 0` dentro de **cada** execução — ou seja, valor fixo durante o episódio (configuração do mundo), não uma variável dinâmica de tick a tick.

Rodei esse filtro real contra o dataset base (`5-experiments/base/dejavu/antecipated_scenario_dataset/`) e obtive exatamente **37 colunas estáticas elegíveis** e **48 dinâmicas excluídas** (listas completas na seção 5).

---

## 4. Como `lateral_friction <= 0.315` foi produzido — validado matematicamente

Rastreei o experimento `17_0_130` (`lateral_friction` configurado = **0.13**) e confirmei via [`dejavu.py:130-131,203-206`](../3-dejavu/src/dejavu.py#L130) que o `AntecipatedScenarioDatasetRecorder` grava e **dá flush a cada tick** no MESMO diretório que o Diagnoser lê (`antecipated_scenario_dataset_folder`), **antes** do diagnóstico rodar. Ou seja: quando o diagnóstico dispara (1ª detecção UNSAT do episódio), o dataset de treino já inclui **o próprio episódio corrente**, não só histórico.

O dataset base (`5-experiments/base/dejavu/`) tem 5 execuções históricas "(happy_path)", **todas com `lateral_friction = 0.5`** (confirmado carregando os CSVs). Com o episódio corrente contribuindo `lateral_friction = 0.13`, o conjunto de treino da árvore tinha exatamente **2 valores distintos**: `{0.13 (label=True/unanticipated), 0.5 (label=False)}`.

`sklearn.tree.DecisionTreeClassifier` (`max_depth=3`) escolhe como threshold o **ponto médio** entre os dois valores adjacentes que separam as classes:

```
threshold = (0.13 + 0.50) / 2 = 0.315   ✓ bate exatamente
```

**Validei essa fórmula contra os 16 diagnósticos reais do RQ1.0** — bate em 100% dos casos:

| experimento | friction configurado | threshold diagnosticado | midpoint(friction, 0.5) |
|---|---|---|---|
| 09_0_18 | 0.18 | 0.34 | 0.34 ✓ |
| 10_0_17 | 0.17 | 0.335 | 0.335 ✓ |
| 11_0_16 | 0.16 | 0.33 | 0.33 ✓ |
| 12_0_155 | 0.155 | 0.3275 | 0.3275 ✓ |
| 13_0_150 | 0.150 | 0.325 | 0.325 ✓ |
| 14_0_145 | 0.145 | 0.3225 | 0.3225 ✓ |
| 15_0_140 | 0.140 | 0.32 | 0.32 ✓ |
| **17_0_130** | **0.130** | **0.315** | **0.315 ✓** |
| 18_0_120 | 0.120 | 0.31 | 0.31 ✓ |
| 19_0_110 | 0.110 | 0.305 | 0.305 ✓ |
| 20_0_100 | 0.100 | 0.30 | 0.30 ✓ |
| 21_0_080 | 0.080 | 0.29 | 0.29 ✓ |
| 22_0_060 | 0.060 | 0.28 | 0.28 ✓ |
| 23_0_040 | 0.040 | 0.27 | 0.27 ✓ |
| 24_0_020 | 0.020 | 0.26 | 0.26 ✓ |
| 25_0_010 | 0.010 | 0.255 | 0.255 ✓ |

**Ressalva de transparência**: o CSV específico do episódio ao vivo de `17_0_130` (que deveria se chamar `antecipated_scenario_dataset_20260905_191641.csv`, mesmo timestamp do trace) **não sobreviveu na pasta `outputs/dataset/` coletada** — só os 5 "(happy_path)" aparecem lá. Isso é coerente com `execute_simulations.py:221-228` usar `proc.terminate()` (kill duro no Windows, sem rodar `atexit`) para encerrar o `dejavu.py` a cada experimento; o arquivo pode ter sido perdido nesse encerramento abrupto, ou a coleta rodou antes do SO liberar o handle. Não encontrei o arquivo fisicamente para confirmar por leitura direta — a evidência é a fórmula batendo em 16/16 casos, que considero suficientemente forte, mas registro que não é uma confirmação por leitura direta do CSV daquele episódio específico.

---

## 5–6. Outros parâmetros elegíveis / predicados justificáveis

**Para o episódio `17_0_130` especificamente**: **nenhum outro parâmetro estático poderia ter sido selecionado.** O patch do experimento (`5-experiments/results/17_0_130/experiment.json`) só altera `objects.0.lateral_friction`. Todas as outras colunas estáticas são idênticas entre as 5 execuções base e o episódio corrente → `nunique() == 1` → descartadas no passo 5 do pipeline, **antes mesmo** de chegar ao filtro de features estáticas. `lateral_friction` foi a **única coluna com variância** no conjunto de treino daquele diagnóstico específico.

**Para futuras perturbações estruturais (RQ2)**: qualquer uma das 37 colunas estáticas listadas na seção 5 se torna elegível **se e somente se** o `environment.yaml`/config do experimento introduzir variância nela (mesmo mecanismo do `lateral_friction`). Não há threshold real para nenhuma delas (nunca foram perturbadas) — só a forma do predicado é justificada pelo código (split binário de árvore de decisão, mesmo mecanismo do `lateral_friction`).

---

## 7. O Diagnoser adiciona uma ou múltiplas condições ao Given?

**Empiricamente, nos 16 diagnósticos reais, sempre exatamente UMA condição** (`lateral_friction <= X`). Mas **o código suporta múltiplas** ([:112-117](../3-dejavu/src/unanticipated_scenario_diagnoser.py#L112)):

```python
false_rules = [r for r in rules if r["then"] == "True"]
all_conditions = [cond for r in false_rules for cond in r["if"]]
unanticipated_conditions_str = " AND ".join(all_conditions)
```

Isso concatena com `AND` **todas as condições de todos os caminhos (leaves) que preveem "True"** — inclusive de folhas diferentes da árvore. Com `max_depth=3`, uma única folha pode contribuir até 3 condições, e se houver **mais de uma folha "True"**, as condições de folhas distintas (que na árvore são caminhos alternativos/OR) são artificialmente unidas por `AND` na string final — um risco lógico real caso o conjunto de treino algum dia force `depth > 1` ou múltiplas folhas verdadeiras (não observado até agora porque cada treino real só teve 2 valores distintos do único parâmetro com variância).

**Nota**: a condição extra `(distance_object_goal_cm > 5)` que aparece em `09_0_18`–`14_0_145` **não vem do Diagnoser** — vem do `UnanticipatedScenarioIdentifier` ([`unanticipated_scenario_identifier.py:85-88`](../3-dejavu/src/unanticipated_scenario_identifier.py#L85)), que nega cláusulas `then` violadas do cenário `TRANSPORT_OBJECT` (confirmado: esses 6 casos diagnosticam `TRANSPORT_OBJECT`, não `LIFT_OBJECT` — `then` real: `distance_object_goal_cm <= 5 AND object_lift_height_cm >= 10 AND finger_contacts >= 2`, de `1-manager/configs/arm/asm.json:113`). O Diagnoser, mesmo nesses casos, só contribuiu `lateral_friction <= X` — uma condição.

---

## 8. Risco de vazamento (reward, is_success, sat, comportamento adaptativo)

| fonte de risco | resultado |
|---|---|
| `sat` | **Bloqueado por denylist explícito** (`_DROP_COLS`) — nunca chega ao X |
| `reward`, `is_success` | **DINÂMICOS** (variam tick-a-tick) → excluídos pelo filtro `std==0 por execução` na prática, confirmado rodando o filtro no dataset real (ambos caem na lista "dynamic"). Risco residual: se a janela do cenário tiver 1 única linha, `std` seria trivialmente 0 — caso de borda não observado nos dados reais, mas não impossível |
| `do` / ação adaptativa escolhida | **Não existe como coluna no CSV** — o recorder só grava `perception` (flatten), sem campo de adaptação. Sem risco |
| Uso do **próprio episódio em diagnóstico** | **Risco metodológico real, não de "dado futuro"**: o Diagnoser treina incluindo a linha estática (snapshot) do próprio episódio sendo diagnosticado, junto com o histórico. Não é vazamento temporal (usa só a config inicial, não o desfecho), mas quebra independência treino/diagnóstico — relevante para o desenho de robustez do RQ2 |

---

## Tabela — conjunto admissível de parâmetros

Cobertura representativa das 3 categorias (estático elegível / dinâmico excluído / denylist ou não-numérico excluído).

| parameter | available_at_diagnosis | eligible_for_diagnosis | observed_in_episode | admissible_predicate | evidence_source |
|---|---|---|---|---|---|
| `lateral_friction` | yes | yes | **yes — único parâmetro real observado** | `lateral_friction <= 0.315` (validado, 16/16 casos) | `similarities_20260905_191641.jsonl` (17_0_130) + fórmula midpoint |
| `objects.object_1.mass` | yes | yes (static, categoria idêntica a lateral_friction) | não (nunca perturbado) | forma `mass <= X` / `mass >= X` — **sem threshold real** | filtro static rodado sobre `5-experiments/base/dejavu/antecipated_scenario_dataset/` |
| `objects.object_1.spinning_friction` | yes | yes | não | forma `spinning_friction OP X` — sem threshold real | idem |
| `scene.table.lateral_friction` | yes | yes | não | forma `scene.table.lateral_friction OP X` — sem threshold real | idem |
| `scene.table.spinning_friction` | yes | yes | não | forma `OP X` — sem threshold real | idem |
| `robot_config.block_gripper` (bool) | yes | yes | não | `== True` / `== False` (binário, sem intervalo) | idem |
| `obstacle_in_path` / `obstacle_count_in_path` | yes | yes | não | binário/inteiro — sem threshold real | idem |
| `target_x` / `target_y` / `target_z` | yes | yes | não | forma `OP X` — sem threshold real | idem |
| `object_lift_height_cm` | yes | **NÃO** — dinâmico (varia por tick) | usado pelo **Identifier**, não pelo Diagnoser | já faz parte do `given` base (negação do `then` anticipado) | `unanticipated_scenario_identifier.py:85-88` |
| `finger_contacts` | yes | **NÃO** — dinâmico | idem | idem | idem |
| `grasp_completed` | yes | **NÃO** — dinâmico | não entra no given (é o `when`) | n/a | `asm.json:109` (`when`) |
| `distance_object_goal_cm` | yes | **NÃO** — dinâmico | usado pelo Identifier em `TRANSPORT_OBJECT` (`> 5`) | vem do Identifier, não do Diagnoser | `unanticipated_scenario_identifier.py` + `asm.json:113` |
| `reward` | yes | **NÃO** — dinâmico | não | n/a | filtro static |
| `is_success` | yes | **NÃO** — dinâmico | não | n/a | filtro static |
| `sat` | n/a | **NÃO** — denylist explícito | não | n/a — nunca pode entrar | `unanticipated_scenario_diagnoser.py:10-14` |
| `active_scenario_name` / `type`, `current_subtask` / `task` | n/a | **NÃO** — denylist explícito | não | n/a | idem |
| `objects.object_1.type`, `robot_config.control_type`, `target_goal.type/mode`, `target_goal.targets.0.name` | n/a | **NÃO** — não numérico/bool | não | n/a | `select_dtypes(include=[np.number, bool])` |

---

## Apêndice A — lista completa das 37 colunas estáticas elegíveis

(`std == 0` dentro de cada execução, rodado sobre `5-experiments/base/dejavu/antecipated_scenario_dataset/`)

```
lateral_friction
object_available
objects.object_1.color.0
objects.object_1.color.1
objects.object_1.color.2
objects.object_1.color.3
objects.object_1.initial_position.0
objects.object_1.initial_position.1
objects.object_1.initial_position.2
objects.object_1.mass
objects.object_1.size.0
objects.object_1.size.1
objects.object_1.size.2
objects.object_1.spinning_friction
obstacle_count_in_path
obstacle_in_path
robot_config.base_position.0
robot_config.base_position.1
robot_config.base_position.2
robot_config.block_gripper
scene.table.height
scene.table.lateral_friction
scene.table.length
scene.table.spinning_friction
scene.table.width
scene.table.x_offset
scripts.left_right
scripts.reach_only
scripts.script_1
target_goal.targets.0.position.0
target_goal.targets.0.position.1
target_goal.targets.0.position.2
target_x
target_y
target_z
task_aborted
task_started
```

## Apêndice B — lista completa das 48 colunas dinâmicas excluídas

(variam tick-a-tick dentro da mesma execução — nunca elegíveis para o Diagnoser)

```
action_gripper, action_x, action_y, action_z,
cube_pitch, cube_roll, cube_vx, cube_vy, cube_vz, cube_x, cube_y, cube_yaw, cube_z,
dist_cube_to_target, dist_ee_to_cube, distance_ee_object_cm, distance_object_goal_cm,
ee_vx, ee_vy, ee_vz, ee_x, ee_y, ee_z,
finger_contacts, fingers_width, grasp_attempts, grasp_completed, gripper_width_cm, is_success,
j0, j1, j2, j3, j4, j5, j6, jv0, jv1, jv2, jv3, jv4, jv5, jv6,
object_lift_height_cm,
objects.object_1.current_position.0, objects.object_1.current_position.1, objects.object_1.current_position.2,
reward
```
