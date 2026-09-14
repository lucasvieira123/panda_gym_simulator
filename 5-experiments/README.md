# 5-experiments — Experiment Runner

Sistema de automação de baterias de experimentos para o simulador de braço robótico.
Gera configurações completas a partir de patches, executa cada simulação de forma isolada e coleta os outputs por experimento.

---

## Quick Start

```bash
# 1. Gerar os arquivos de entrada de cada experimento
python 5-experiments/build_simulations.py --config friction_sweep

# 2. Executar todos os experimentos em sequência
python 5-experiments/execute_simulations.py

# 3. Ou executar experimentos específicos
python 5-experiments/execute_simulations.py 04_0_50 12_0_155
```

> **Pré-requisito:** Execute com o `.venv` ativo. DejaVu e Manager **não** devem estar rodando — o execute script os inicia automaticamente.

---

## Estrutura de Pastas

```
5-experiments/
├── base/                         ← snapshot das configs atuais dos componentes
│   ├── managing/
│   │   ├── environment.yaml
│   │   ├── simulation.yaml
│   │   ├── target_goal.yaml
│   │   └── scripts.yaml
│   ├── manager/arm/
│   │   └── asm.json
│   └── dejavu/
│       ├── arm/
│       │   ├── scenario_catalogue.json
│       │   └── scenario_state_machine.yaml
│       ├── dejavu_conf.yaml
│       ├── weights_config.yaml
│       └── antecipated_scenario_dataset/
├── experiment_configs/            ← definições de baterias de experimentos
│   └── friction_sweep.json
├── results/                       ← gerado automaticamente (ignorado pelo git)
│   └── <nome_experimento>/
│       ├── experiment.json        ← metadados e patches usados
│       ├── inputs/                ← configs completas geradas pelo build
│       └── outputs/               ← coletados após a execução
│           ├── manager_traces/
│           ├── managing_traces/
│           ├── dejavu_traces/
│           ├── similarities/
│           └── dataset/
├── build_simulations.py
└── execute_simulations.py
```

---

## Como Funciona

### Base snapshot

A pasta `base/` contém uma cópia das configs *atuais* dos três componentes (Managing, Manager, DejaVu). É o ponto de partida de todo experimento e o ponto de restauração após cada execução. Se as configs dos componentes mudarem, atualize manualmente os arquivos em `base/`.

### Geração de inputs — `build_simulations.py`

Lê um arquivo JSON de `experiment_configs/`, aplica os patches de cada experimento sobre o snapshot base e salva as configs completas em `results/<nome>/inputs/`. Cada experimento declara **apenas o que muda** — o restante é herdado do base.

### Execução — `execute_simulations.py`

Para cada experimento, o script:

1. Limpa os diretórios de traços dos componentes.
2. Sobrescreve as configs reais com os inputs gerados.
3. Inicia DejaVu, Manager (com `--experiment`) e Managing como subprocessos.
4. Aguarda o Managing terminar (ele auto-encerra após os episódios).
5. Para Manager e DejaVu, restaura as configs do base, coleta os outputs.

Logs de cada componente são prefixados em tempo real:

```
[dejavu  ] 14:32:01 | Flask running on port 5000
[manager ] 14:32:03 | DejaVu conectado.
[managing] 14:32:04 | Episode 1 started
```

---

## Definindo Experimentos

Crie um arquivo `.json` em `experiment_configs/` seguindo o formato abaixo. Cada entrada em `experiments` representa uma execução isolada.

```json
{
  "name": "Nome da Bateria",
  "description": "Descrição geral",
  "experiments": [
    {
      "name": "01_meu_experimento",
      "description": "O que este caso testa",
      "patches": {
        "managing": {
          "environment.yaml": {
            "objects.0.lateral_friction": 0.13
          },
          "simulation.yaml": {
            "episodes": 3
          }
        }
      }
    }
  ]
}
```

> **Convenção de nomes:** prefixe com número sequencial (`01_`, `02_`…) para garantir a ordem de execução ao rodar a bateria completa.

### Componentes disponíveis para patch

| Componente | Arquivos |
|---|---|
| `managing` | `environment.yaml`, `simulation.yaml`, `target_goal.yaml`, `scripts.yaml` |
| `manager`  | `arm/asm.json` |
| `dejavu`   | `arm/scenario_catalogue.json`, `arm/scenario_state_machine.yaml`, `dejavu_conf.yaml`, `weights_config.yaml` |

### Operações de patch

| Operação | Descrição | Exemplo |
|---|---|---|
| `"a.b.c": value` | Navega por chaves (dict) ou índices numéricos (lista) e define o valor. | `"objects.0.lateral_friction": 0.13` |
| `"$add_scenario"` | Adiciona ou substitui um cenário em `scenarios`. | `{"key": "...", "data": {...}}` |
| `"$add_transition"` | Acrescenta uma transição em `transitions`. | `{"from": "...", "to": "..."}` |
| `"$remove_scenario"` | Remove um cenário de `scenarios` pela chave. | `"nome_do_cenario"` |

---

## Outputs Coletados

| Pasta | Origem | Conteúdo |
|---|---|---|
| `manager_traces/`  | `1-manager/traces/` | Traços do ciclo MAPE-K do Manager |
| `managing_traces/` | `2-managing/traces/` | Traços da simulação PyBullet |
| `dejavu_traces/`   | `3-dejavu/output/arm/traces/` | Pipeline DejaVu tick a tick |
| `similarities/`    | `3-dejavu/output/arm/similarities/` | Scores de similaridade por episódio |
| `dataset/`         | `3-dejavu/output/arm/antecipated_scenario_dataset/` | CSVs do monitor de cenários antecipados |

Junto com os outputs, cada pasta de experimento contém `experiment.json` com o nome, descrição e patches exatos utilizados — rastreabilidade completa do run.
