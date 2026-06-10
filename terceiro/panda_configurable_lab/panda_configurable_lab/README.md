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

## 4. Políticas simples disponíveis

Esta versão inclui três políticas apenas para testar a simulação:

```yaml
policy:
  name: "random"
```

```yaml
policy:
  name: "hold"
```

```yaml
policy:
  name: "greedy_goal"
  gain: 5.0
```

A `greedy_goal` é uma política simples que tenta mover o end-effector na direção do primeiro objetivo. Ela não é uma política robótica robusta, serve apenas para testar o loop.

## 5. Estrutura do projeto

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

## 6. Próximas extensões

1. `ConfigurablePickAndPlaceTask`.
2. `ConfigurableStackTask`.
3. Perturbações temporais durante o episódio.
4. Macro-ações configuráveis.
5. `save_state` / `restore_state` para testar planos.
6. Integração posterior com MAPE-K.
