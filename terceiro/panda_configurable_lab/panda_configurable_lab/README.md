# Panda Configurable Lab

Camada configurável sobre `panda-gym` para criar simulações robóticas a partir de arquivos YAML.

Esta versão foca em uma tarefa customizada de **Push configurável**, permitindo configurar:

- mesa/cena;
- robô Panda;
- objetos;
- objetivos;
- obstáculos;
- recompensa sparse/dense;
- critério de sucesso;
- política simples de teste;
- logs do experimento.

> Observação: esta versão não usa diretamente `gym.make("PandaPush-v3")`. Ela cria um ambiente customizado juntando `PyBullet + Panda + ConfigurablePushTask + RobotTaskEnv`.

## 1. Instalação

Recomendado: Python 3.10 ou 3.11.

```bash
conda create -n panda-config python=3.11 -y
conda activate panda-config

pip install -r requirements.txt
```

## 2. Executar exemplo

```bash
python run_experiment.py --config configs/custom_push_environment.yaml
```

Ou:

```bash
python -m panda_configurable_lab.cli --config configs/custom_push_environment.yaml
```

Os resultados serão salvos em:

```text
results/custom_push_environment/
```

Arquivos gerados:

```text
steps.jsonl
events.jsonl
summary.csv
```

## 3. O que dá para configurar

### Robô

```yaml
robot:
  control_type: "ee"       # "ee" ou "joints"
  block_gripper: true
  base_position: [-0.6, 0.0, 0.0]
```

### Simulação

```yaml
simulation:
  render_mode: "human"     # "human", "rgb_array" ou null
```

### Mesa

```yaml
scene:
  table:
    length: 1.1
    width: 0.7
    height: 0.4
    x_offset: -0.3
    lateral_friction: 1.0
    spinning_friction: 0.001
```

### Objetos

Suporta inicialmente:

- `box`;
- `sphere`;
- `cylinder`.

```yaml
objects:
  - name: "cube_1"
    type: "box"
    size: [0.04, 0.04, 0.04]
    mass: 1.0
    initial_position: [0.0, 0.0, 0.02]
    color: [0.1, 0.2, 0.9, 1.0]
    lateral_friction: 0.8
```

### Objetivos

Um objetivo:

```yaml
goals:
  mode: "fixed"
  targets:
    - object: "cube_1"
      position: [0.30, 0.10, 0.02]
      tolerance: 0.05
      visual_marker: true
```

Múltiplos objetivos:

```yaml
goals:
  mode: "fixed"
  targets:
    - object: "cube_1"
      position: [0.25, -0.10, 0.02]
      tolerance: 0.05
      visual_marker: true
    - object: "cube_2"
      position: [0.25, 0.10, 0.02]
      tolerance: 0.05
      visual_marker: true
```

### Obstáculos

```yaml
obstacles:
  - name: "wall_1"
    type: "box"
    size: [0.06, 0.30, 0.08]
    mass: 0.0
    position: [0.15, 0.00, 0.04]
    color: [0.9, 0.1, 0.1, 1.0]
```

## 4. Políticas disponíveis

Configuradas via `policy.name` no YAML ou trocadas em tempo de execução com `change_task_mode`.

| Nome | Descrição | `block_gripper` |
|---|---|---|
| `random` | Ações aleatórias. Útil para debug e exploração. | qualquer |
| `hold` | Robô parado. Útil para observar o estado da cena. | qualquer |
| `greedy_goal` | Move o end-effector diretamente ao goal. Funciona bem para Reach. | qualquer |
| `greedy_push` | Posiciona o ee atrás do cubo e empurra em direção ao goal. Goals no chão (`z ≈ 0.02`). | `false` (fecha garra durante push) |
| `greedy_pick_and_place` | Pega o cubo e deposita no goal. Suporta goals no ar (`z > 0`). Requer `block_gripper: false`. | `false` (obrigatório) |

### Detalhes de cada política

**`greedy_push`**

Duas fases:
1. *Approach* — posiciona o ee atrás do cubo (lado oposto ao goal).
2. *Push* — empurra o cubo em direção ao goal com força mínima garantida.

Quando o goal muda em tempo de execução e a nova approach está do lado oposto, o ee sobe automaticamente para passar por cima do cubo sem empurrá-lo na direção errada.

```yaml
policy:
  name: "greedy_push"
  gain: 5.0
```

**`greedy_pick_and_place`**

Oito fases em sequência:

```
OPEN → HOVER → LOWER → GRASP → LIFT → CARRY → PLACE → RELEASE
```

1. *Open* — abre a garra.
2. *Hover* — move o ee para acima do cubo.
3. *Lower* — desce até o cubo com garra aberta.
4. *Grasp* — fecha a garra e segura por alguns steps.
5. *Lift* — levanta até a altura de trânsito.
6. *Carry* — move horizontalmente para acima do goal.
7. *Place* — desce até o goal com garra fechada.
8. *Release* — abre a garra e solta o cubo.

Requer `block_gripper: false` no config do robô.

```yaml
robot:
  block_gripper: false

policy:
  name: "greedy_pick_and_place"
  gain: 5.0
```

## 5. Sistema de comandos em tempo de execução

É possível modificar a simulação enquanto ela está rodando, editando o arquivo `runtime_commands.yaml` sem parar o processo.

### Configurar no YAML principal

```yaml
runtime:
  command_file: "runtime_commands.yaml"
  poll_every_steps: 1
```

### Operações disponíveis

#### `change_goal`

Muda a posição do goal sem resetar nada. O cubo e o robô permanecem onde estão.

```yaml
- id: "novo_goal"
  enabled: true
  operation: "change_goal"
  target_object: "cube_1"
  position: [0.10, -0.20, 0.02]
  tolerance: 0.05
  visual_marker: true
```

#### `change_task_mode`

Muda o goal **e/ou** a política sem resetar a física. O cubo fica exatamente onde foi deixado.
Ideal para transições como push → pick_and_place no meio do episódio.

```yaml
- id: "push_para_pick"
  enabled: true
  operation: "change_task_mode"
  at_episode: 0
  at_step: 40
  target_object: "cube_1"
  position: [0.10, 0.10, 0.15]   # goal no ar
  tolerance: 0.05
  visual_marker: true
  policy: "greedy_pick_and_place"
```

Campos opcionais: se `position`/`target_object` forem omitidos, só a política é trocada.

#### `change_task`

Troca para uma das 6 tasks padrão do panda-gym. A janela permanece aberta, mas a cena é reconstruída do zero (robô e objetos voltam às posições iniciais).

```yaml
- id: "para_reach"
  enabled: true
  operation: "change_task"
  task: "reach"           # reach | push | slide | pick_and_place | stack | flip
  reward_type: "dense"
  policy: "greedy_goal"
```

### Controle de quando o comando dispara

| Campo | Descrição |
|---|---|
| `enabled: true/false` | Habilita ou desabilita o comando |
| `id` | Identificador único — cada id só dispara uma vez por sessão |
| `at_episode: N` | Dispara apenas no episódio N |
| `at_step: N` | Dispara apenas no step N do episódio |

Se `at_episode` e `at_step` forem omitidos, o comando dispara no primeiro step em que for lido com `enabled: true`.

## 6. Estrutura do projeto

```text
panda_configurable_lab/
  cli.py
  config_loader.py
  configurable_push_task.py
  env_factory.py
  logger.py
  policies.py
  runner.py

configs/
  custom_push_environment.yaml
  multi_object_push_environment.yaml
  push_with_obstacle.yaml

run_experiment.py
requirements.txt
```

## 7. Próximas extensões

1. `ConfigurablePickAndPlaceTask`.
2. `ConfigurableStackTask`.
3. Perturbações temporais durante o episódio.
4. Macro-ações configuráveis.
5. `save_state` / `restore_state` para testar planos.
6. Integração posterior com MAPE-K.
