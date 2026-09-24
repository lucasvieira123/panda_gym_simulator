# RQ2 — Inspeção read-only do repositório antes de congelar o protocolo experimental

**RQ2 — Retrieval Robustness to Scenario Analysis Inaccuracies.** Investiga como variações estruturais e paramétricas no `Given` do Desired Adaptation Scenario (produzido pela fase Unanticipated Scenario Analysis) afetam a estabilidade da recuperação de conhecimento adaptativo.

Cenário de referência:

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

Comportamento recuperado e validado na RQ1: `apply_vacuum_assist()`.

Nenhum arquivo foi modificado, nenhum comportamento novo foi implementado, nenhum experimento foi executado. Investigação feita por leitura direta de código (`1-manager/`, `2-managing/`, `3-dejavu/`), testes empíricos isolados (funções chamadas diretamente via Python, sem tocar produção) e grep exaustivo sobre os traces reais do RQ1 em `5-experiments/results/` e `5-experiments/RQ1.0/results/`.

---

## 1. Executabilidade dos comportamentos do catálogo

Catálogo real usado no RQ1: `3-dejavu/configs/arm/scenario_catalogue.json` (cópia em `5-experiments/base/dejavu/arm/scenario_catalogue.json`).

Mecanismo de execução real: [`2-managing/src/main.py:21-36`](../2-managing/src/main.py#L21), função `_make_task()` — um `if/elif` **fechado**, não um dicionário dinâmico construído a partir do catálogo:

```python
def _make_task(strategy: str, sim, robot, configs):
    ...
    if strategy == "APPLY_VACUUM_ASSIST":      return create_vacuum_assist(sim, robot, configs)
    if strategy == "HEAVY_LIFT":               return create_heavy_lift(sim, robot, configs)
    ...
    return None
```

Em [`_handle_command()`](../2-managing/src/main.py#L39) (linha 56): `scenario = cmd.get("to", "").replace("()", "").upper().strip()`; se `_make_task` devolver `None`, linha 63 loga **"Adaptação desconhecida: '...' — ignorada"** e nada acontece fisicamente.

### Tabela — os 7 comportamentos do catálogo

| # | comportamento | cenário candidato | implementação Python real | no dispatcher `_make_task` | execução confirmada em trace real | veredito |
|---|---|---|---|---|---|---|
| 1 | `apply_vacuum_assist()` | `lift_slip_low_friction` | **sim** — `VacuumAssistTask` ([vacuum_assist_task.py:23-108](../2-managing/src/tasks/object_delivery/vacuum_assist_task.py#L23)) | sim ([main.py:31](../2-managing/src/main.py#L31)) | **sim** — `Task: VACUUM_ASSIST` em 15/16 experimentos com diagnóstico do RQ1 | **(d) executado e validado** |
| 2 | `increase_grip_pressure()` | `cobot_lift_grip_pressure` | não | não | não (só em `outputs/similarities/*.jsonl`, como candidato avaliado) | (a) só descrito no catálogo |
| 3 | `emergency_vacuum_pump()` | `suction_arm_vacuum_loss` | não | não | não | (a) só descrito no catálogo |
| 4 | `reposition_and_regrip()` | `parallel_arm_contact_loss` | não | não | não | (a) só descrito no catálogo |
| 5 | `extend_lift_phase()` | `lightweight_arm_height_only` | não | não | não | (a) só descrito no catálogo |
| 6 | `reduce_lift_speed()` | `heavy_duty_arm_motor_overload` | não | não | não | (a) só descrito no catálogo |
| 7 | `heavy_lift()` | `cobot_incremental_heavy_transport` | **sim** — `HeavyLiftTask` ([heavy_lift_task.py:60-179](../2-managing/src/tasks/object_delivery/heavy_lift_task.py#L60)) | sim ([main.py:32](../2-managing/src/main.py#L32)) | **NÃO encontrada em nenhum trace real** (48 pastas de resultados vasculhadas) | **(c) integrada, nunca disparada** |

### Evidência física (não é stub)

`VacuumAssistTask` e `HeavyLiftTask` chamam `self.sim.set_lateral_friction("panda", link, valor)` — API real do PyBullet via panda_gym (`changeDynamics(...)`) — e `HeavyLiftTask` também escreve em `self._robot.joint_forces[:7]`, atributo real do robô Panda (`panda_gym.envs.robots.panda.Panda`). Ambas têm máquinas de fase completas (aproximação → grasp → lift) que movem o end-effector de fato.

Confirmação física direta rodando `grep "Task " */outputs/managing_traces/*.log` nas 25 pastas do RQ1:

```
09_0_18  → OBJECT_DELIVERY_SEQUENCE | VACUUM_ASSIST
...      → (mesmo padrão em todas as 15 pastas com diagnóstico)
25_0_010 → OBJECT_DELIVERY_SEQUENCE | VACUUM_ASSIST
```

`HEAVY_LIFT` **nunca** aparece como valor do campo `Task` em nenhuma das 25 pastas.

### Nota estrutural importante

Mesmo se o Retriever escolhesse um dos 5 comportamentos sem implementação como Top-1, o Manager enviaria `send_adapt()` normalmente e o Managing responderia "Adaptação desconhecida... ignorada" — sem crash, mas sem qualquer efeito físico. Isso nunca foi observado nos traces reais (0 ocorrências fora de `similarities`), mas é o comportamento estrutural previsto do código caso algum dia aconteça.

Também existem `RETRY_GRASP`/`SAFE_ABORT` — cenários `"type": "adaptive"` já embutidos no próprio ASM ([`1-manager/configs/arm/asm.json:89-100`](../1-manager/configs/arm/asm.json#L89)), tratados pelo planner interno do Manager, **não** pelo pipeline de descoberta do DejaVu. É um caminho de adaptação separado do catálogo de similaridade.

---

## 2. Comportamento do Retriever (`SimilarityBasedAdapter`)

Código: [`3-dejavu/src/similarity_based_adapter.py`](../3-dejavu/src/similarity_based_adapter.py). Testado empiricamente (não só lido) para os casos de borda pedidos.

| pergunta | resposta | evidência |
|---|---|---|
| Sempre retorna o Top-1? | **Sim, incondicionalmente** — `recommend()` pega `sorted_results[0]` sem nenhuma checagem de qualidade | [:58-67](../3-dejavu/src/similarity_based_adapter.py#L58) |
| Threshold mínimo / rejeição por baixa similaridade? | **Não existe.** Mesmo o score mínimo teórico (~0.333, pois `when` é idêntico em todo o catálogo e contribui 1/3 fixo) é aceito como Top-1 | mesmo trecho |
| Catálogo vazio? | Graceful — `calculate_similarity` retorna `[]`, `recommend([])` retorna `None` (sem crash) | testado diretamente |
| Sem candidatos semanticamente próximos? | **Nenhuma rejeição** — sempre devolve o melhor dos disponíveis, por pior que seja | mesmo mecanismo acima |
| Empates? | Resolvidos **pela ordem de declaração no JSON do catálogo** (Python `list.sort()` é estável) — não há regra de desempate explícita/documentada | [`dejavu.py:236-239`](../3-dejavu/src/dejavu.py#L236) (`results.sort(...)`) |
| Given vazio (`""`)? | **Quebra** — `pyparsing.ParseException` dentro do parser | testado empiricamente agora |
| Given `None`? | **Quebra** — `AttributeError: 'NoneType' object has no attribute 'expandtabs'` | testado empiricamente agora |
| Ranking sem acionar adaptação física? | **Sim, totalmente possível e seguro** — `calculate_similarity()`/`recommend()` só leem JSON/YAML locais, zero I/O com Manager/Managing/simulação | confirmado por leitura + é exatamente o que `5-experiments/run_similarity_only/` já faz |

### Ressalva crítica sobre Given vazio/None

Os crashes acontecem **dentro do módulo de similaridade**. No pipeline real ([`dejavu.py:225-249`](../3-dejavu/src/dejavu.py#L225)), todo o bloco de diagnóstico está dentro de um `try/except Exception as e: _log(writer, f"[PIPELINE] Erro: {e}")` — então na prática **não derruba o processo**, mas aquele tick simplesmente não produz nenhuma similaridade/adaptação, só um log genérico de erro.

---

## 3. Reprodutibilidade da simulação

- **Seed fixo**: [`2-managing/src/main.py:105`](../2-managing/src/main.py#L105) → `gym_env.reset(seed=configs["simulation"]["seed"])`, com `seed: 42` fixo em [`2-managing/configs/simulation.yaml:1`](../2-managing/configs/simulation.yaml#L1). **Mesma seed em toda execução** — o RQ1 nunca variou isso, só `objects.0.lateral_friction` (via patch de `environment.yaml`).
- `episodes: 1` — cada experimento roda um único episódio.
- Posição inicial do objeto é **valor fixo de config** (`initial_position: [-0.25, 0.0, 0.02]` em [`environment.yaml:21`](../5-experiments/base/managing/environment.yaml#L21)), não depende da seed do gym.

### Achado relevante

O próprio comentário do autor em `environment.yaml:23` diz:

```yaml
lateral_friction: 0.5  # 0.130 (escorrega no lift) 0.155 (escorrega no place)  0.5 (normal)
```

Sugerindo que valores ~0.155 deveriam disparar um cenário de escorregão na fase **PLACE**, diferente do de **LIFT**. Testei isso diretamente: no experimento real `12_0_155` (friction=0.155), o `managing_traces` também mostra só `Task: VACUUM_ASSIST` — ou seja, esse comportamento alternativo de PLACE **nunca foi de fato observado** nos dados reais do RQ1, apesar do comentário sugerir que existiria.

### O que seria necessário para dois comportamentos adaptativos distintos sob condições comparáveis

Como seed e posição inicial são constantes fixas (não variadas por experimento), e a única variável perturbada no RQ1 (`lateral_friction`, faixa 0.01–0.18) sempre produziu o mesmo comportamento executado (`VACUUM_ASSIST`) em toda a faixa testada, **não há precedente empírico** de uma segunda execução física real com outro comportamento. Conseguir isso exigiria perturbar outro parâmetro (ex. `objects.object_1.mass`, para aproximar o perfil do candidato `cobot_incremental_heavy_transport`/`heavy_lift()`) **e validar experimentalmente** se isso de fato leva o Retriever a escolher `heavy_lift()` como Top-1 **e** o Manager a de fato despachá-lo — isso está fora do escopo desta leitura (nada foi executado).

---

## Respostas diretas

### A. Quais comportamentos alternativos a `apply_vacuum_assist()` poderiam ser executados no mesmo cenário físico?

Apenas `heavy_lift()` tem chance estrutural real (implementado + integrado ao dispatcher). Os outros 5 nunca seriam executados fisicamente, mesmo escolhidos como Top-1 — seriam sempre "no-op" com log de "adaptação desconhecida". E mesmo `heavy_lift()` nunca foi observado sendo escolhido/executado em nenhum experimento real do RQ1 — não há confirmação empírica de que ele seja alcançável a partir de uma perturbação do `given`.

### B. Avaliar consequências funcionais da mudança de Top-1, ou limitar a RQ2 à estabilidade da recuperação?

Recomendação: **limitar o núcleo da RQ2 à estabilidade da recuperação** (ranking/score/identidade do Top-1). Avaliar consequência funcional só é honesto para o par `apply_vacuum_assist()` (validado) vs. `heavy_lift()` (implementado mas nunca disparado) — e isso exigiria primeiro confirmar experimentalmente que dá pra fazer `heavy_lift()` virar Top-1 e ser de fato despachado, o que hoje não está demonstrado. Pode entrar como extensão opcional/exploratória, não como parte garantida do protocolo.

### C. O Retriever suporta todas as omissões estruturais do Given, inclusive Given vazio?

Não. Omissão **parcial** de parâmetro dentro de uma cláusula não vazia (caso já mapeado na análise anterior do mecanismo de similaridade — ver `diagnoser_admissible_parameters_RQ2.md`) é bem tratada via penalidade Tversky. Mas Given **totalmente vazio ou `None`** quebra o módulo com exceção não tratada — só não derruba o processo porque o `dejavu.py` tem um try/except genérico ao redor.

### D. Existe mecanismo de rejeição quando o catálogo não oferece conhecimento suficientemente semelhante?

Não. `recommend()` sempre devolve o melhor disponível, sem threshold mínimo. `None` só ocorre com catálogo literalmente vazio, nunca por baixa similaridade.

### E. Limitações do código atual a considerar antes de congelar o protocolo

1. Só 1 de 7 comportamentos tem execução física validada; `heavy_lift` implementado mas nunca disparado; os outros 5 são no-op garantido.
2. Sem threshold/rejeição no Retriever — risco de "adaptação forçada" com baixíssima similaridade real.
3. Given vazio/`None` quebra o módulo (mascarado só pelo try/except externo do orquestrador em `dejavu.py`).
4. Empates dependem da ordem de declaração no JSON do catálogo, não de regra semântica.
5. Bug de tipo `int` vs `"10.0"` em `dejavu_similarity.py` (documentado em `diagnoser_admissible_parameters_RQ2.md`) continua valendo para qualquer Given sintético gerado no RQ2.
6. O código do Diagnoser pode (estruturalmente) concatenar condições de múltiplas folhas "True" com AND — risco lógico se o RQ2 forçar `depth > 1` na árvore.
7. **O DejaVu só é acionado pelo Manager quando `state.goal_status != "violated"`** ([`1-manager/src/main.py:95-98`](../1-manager/src/main.py#L95)) — se o ASM interno já reconhece a violação via seu próprio planner, a recomendação do Retriever é computada mas **ignorada** em favor do plano interno (`planner.plan(state)`). Um Top-1 diferente calculado pelo DejaVu pode nunca chegar a ser executado por essa prioridade estrutural.
8. Sem precedente empírico de duas execuções físicas distintas a partir de condições comparáveis — precisaria ser validado experimentalmente antes de assumir que é possível.

---

## Apêndice — arquitetura MAPE-K confirmada

- **Monitor/Analyze/Plan**: [`1-manager/src/main.py`](../1-manager/src/main.py) — laço principal (linhas 70-138). Recebe percepção do managing, chama `analyzer.analyze()`, envia estado ao DejaVu via `api.send_to_dejavu()` e recebe `dj["adaptation"]` (dict com `candidate_name`, `do`, `score`, vindo do `SimilarityBasedAdapter`).
- **Execute (lado Manager)**: [`1-manager/src/execute.py`](../1-manager/src/execute.py) — classe `Executor`. `send_adapt()` (linhas 8-11) pega a string `do`, faz `.upper()` e manda via WebSocket `{"action": "adapt", "to": "APPLY_VACUUM_ASSIST()"}`. Chamado em `1-manager/src/main.py:101`: `executor.send_adapt(dj_adaptation["do"])`.
- **Execute real (lado Managing/exemplar)**: `2-managing/src/main.py`, `_handle_command()` + `_make_task()` — único despachante string→callable do repositório para as ações do catálogo.

Não há nenhum outro despachante no repo (busquei `execute_adaptation`, `apply_adaptation`, `action_executor`, `getattr`/`eval` genéricos — nenhuma ocorrência fora do padrão acima).
