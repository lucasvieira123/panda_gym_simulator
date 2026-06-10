# Sistema Autoadaptativo MAPE-K + panda-gym

## Visão Geral

Este projeto implementa um sistema autoadaptativo baseado na arquitetura **MAPE-K** (Monitor–Analyze–Plan–Execute + Knowledge Base), usando o simulador **panda-gym** como representação do *Managed System*.

```
┌─────────────────────────────────────────────────────────────┐
│                    MANAGING SYSTEM                          │
│                                                             │
│   Monitor ──► Analyzer ──► Planner ──► Executor            │
│      │            │            │           │                │
│      └────────────┴────────────┴───────────┘                │
│                        │                                    │
│              Knowledge Base (KB)                            │
└──────────────────────────┬──────────────────────────────────┘
                           │  observações / ações
┌──────────────────────────▼──────────────────────────────────┐
│               MANAGED SYSTEM (panda-gym)                    │
│          PandaReachDense-v3  (simulador PyBullet)           │
└─────────────────────────────────────────────────────────────┘
```

---

## Estrutura dos Arquivos

```
mapek_panda/
├── knowledge_base.py      # KB: dados, config adaptável, situações registradas
├── monitor_analyzer.py    # M e A: coleta de dados e detecção de situações
├── planner_executor.py    # P e E: seleção de planos e aplicação de adaptações
└── main.py                # Loop principal + FaultInjector + relatório
```

---

## Instalação

```bash
pip install panda-gym gymnasium numpy
```

> panda-gym requer PyBullet como backend físico (instalado automaticamente como dependência).

---

## Como Executar

```bash
# Modo headless (sem GUI) — 300 steps
python main.py

# Com renderização PyBullet
python main.py --render

# Injeta falhas não previstas artificialmente
python main.py --inject-faults

# Combinado: 500 steps com falhas e sem GUI
python main.py --steps 500 --inject-faults
```

---

## Papéis dos Componentes MAPE-K

### Knowledge Base (`knowledge_base.py`)
- Armazena o **histórico de observações** (janela deslizante)
- Mantém as **configurações adaptáveis** (`step_size`, thresholds etc.)
- Registra as **situações previstas** com seus planos associados
- Loga **eventos de adaptação** e **situações não previstas** detectadas

### Monitor (`monitor_analyzer.py::Monitor`)
- A cada step, extrai do panda-gym: `achieved_goal`, `desired_goal`, `reward`
- Calcula a **distância euclidiana** ao goal
- Cria uma `Observation` e persiste na KB

### Analyzer (`monitor_analyzer.py::Analyzer`)
- Examina a janela de histórico da KB
- Detecta **situações previstas** (codadas)
- Detecta **situações não previstas** via heurísticas e as loga na KB
- Retorna lista de situações ativas para o Planner

### Planner (`planner_executor.py::Planner`)
- Mapeia situações → planos (`kb.planned_situations`)
- **Prioriza** situações críticas (e.g. `invalid_reward` > `far_from_goal`)
- Resolve conflitos mantendo ambos os planos quando compatíveis

### Executor (`planner_executor.py::Executor`)
- Chama `plan.action(kb)` que modifica `kb.config` in-place
- Retorna `side_effects` (e.g. `trigger_reset=True`) para o loop principal
- Registra cada adaptação no log da KB

---

## Situações Modeladas

### Situações PREVISTAS (SP)

| ID | Situação | Detecção | Adaptação |
|----|----------|----------|-----------|
| SP-1 | Robô longe do goal | dist média > `distance_threshold` (0.10) | Aumenta `step_size` × 1.5 (max 0.30) |
| SP-2 | Reward estagnado | N steps sem melhora no melhor reward | Reduz `step_size` × 0.8, força reset |
| SP-3 | Episódio muito longo | `episode_step_count` ≥ `max_steps_per_episode` (80) | Força reset do episódio |

### Situações NÃO PREVISTAS (SNP)

| ID | Situação | Detecção | Adaptação Criada Dinamicamente |
|----|----------|----------|-------------------------------|
| SNP-1 | Reward inválido (NaN/Inf) | `not math.isfinite(reward)` | Reset + step_size conservador (0.03) |
| SNP-2 | Oscilação perto do goal | variância da distância < 1e-4 e dist ∈ (0.01, 0.08) | Reduz step_size × 0.4 |
| SNP-3 | Trajetória divergente | distância crescendo monotonicamente por 8 steps | Reduz step_size × 0.5 + reset |

> As SNP são detectadas por heurísticas no Analyzer. Quando detectadas, o sistema **cria um plano de adaptação dinamicamente** via `kb.planned_situations.setdefault(...)` e o injeta no fluxo normal de Planner → Executor. Isso simula a auto-expansão da base de conhecimento.

---

## FaultInjector

Para exercitar as situações não previstas sem depender de ocorrências naturais:

| Step | Falha Injetada | SNP Exercitada |
|------|---------------|----------------|
| 40   | Corrompe reward → `NaN` | SNP-1 |
| 120  | Zera ação por 8 steps (robô parado) | SNP-3 |
| 200  | Inverte ação → oscilação forçada | SNP-2 |

---

## Extensibilidade

### Adicionar uma nova situação prevista

```python
# Em knowledge_base.py, dentro de _register_planned_situations():

def plan_high_jerk(kb):
    kb.config["step_size"] = max(kb.config["step_size"] * 0.6, 0.01)
    return {"step_size": kb.config["step_size"]}

self.planned_situations["high_jerk"] = AdaptationPlan(
    name="high_jerk",
    description="Variação brusca de ação: reduzir step_size para suavizar movimento.",
    action=plan_high_jerk,
)
```

```python
# Em monitor_analyzer.py, dentro de _check_planned_situations():

actions = self.kb.last_actions(n=5)  # (adicionar tracking de ações na KB)
if some_jerk_condition(actions):
    detected.append("high_jerk")
```

### Trocar o ambiente panda-gym

Basta mudar a linha em `main.py`:
```python
env = gym.make("PandaPickAndPlace-v3", render_mode=render_mode)
```
O restante do sistema é agnóstico ao ambiente, desde que ele exponha `achieved_goal`/`desired_goal` na observação (padrão GoalEnv do gymnasium).

---

## Diagrama de Sequência por Step

```
Loop principal (main.py)
    │
    ├─ generate_action(obs, kb)        ← usa kb.config["step_size"]
    │
    ├─ env.step(action)                ← MANAGED SYSTEM executa
    │
    ├─ [FaultInjector.maybe_inject()]  ← perturba reward/action artificialmente
    │
    ├─ Monitor.observe()               ← M: coleta e persiste na KB
    │
    ├─ Analyzer.analyze()              ← A: detecta situações (SP + SNP)
    │
    ├─ Planner.plan(situations)        ← P: seleciona e prioriza planos
    │
    ├─ Executor.execute(plans)         ← E: aplica adaptações na KB
    │
    └─ [reset se trigger_reset=True]   ← side effect do Executor
```
