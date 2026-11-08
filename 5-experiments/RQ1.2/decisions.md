# RQ1.2 — Registro de decisões

Decisões para a RQ1.2 (*Knowledge Incorporation and Behavioural-Space Evolution*), abertas em 2026-11-08. Referência para a implementação, para revisão e para o manuscrito. Uma decisão só muda aqui, com o motivo.

A RQ1.2 executa uma sequência de atritos decrescentes, de μ = 0,170 a μ = 0,010, **preservando o conhecimento entre execuções** (ASM e dataset do Diagnoser). Os resultados da RQ1.1 (`../RQ1.1/bateria/results/`, versão `37fda0d`) não são alterados nem reexecutados.

## Estado das etapas

| Etapa | Situação |
|---|---|
| 0. Investigação com o código atual | Concluída (2026-11-08); seção "Achados" e scripts em `reproducao/` |
| 1. Correções P2 e P3 (AsmEvolver e Diagnoser), com testes unitários | Concluída (2026-11-08), sem commit; seção "Etapa 1" |
| 2. Correção P4 (ASM-SM gerado do ASM) | Concluída (2026-11-08), sem commit; seção "Etapa 2" |
| 3. Correções P1, P6 e Q1 (Manager e Managing) | Concluída (2026-11-08), sem commit; seção "Etapa 3" |
| 4. Regressão da RQ1.1 (0,17, 0,14 e 0,04) | Concluída (2026-11-08): iguais à bateria; seção "Etapa 4" |
| 5. Modo sequencial do runner (P0) | Concluída (2026-11-08), sem commit; verificada na etapa 6 |
| 6. Sequência curta 0,17 → 0,16 → 0,14 → 0,13 | Concluída (2026-11-08); seção "Etapa 6" |
| 7. Sequência completa 0,170 → 0,010 | Não iniciada |

## Achados com o código atual (versão `77d013c`)

Fontes: eventos `diagnosis` e `asm_evolution` em `../RQ1.1/bateria/results/*/outputs/dejavu_traces/events_*.jsonl`, e os scripts de `reproducao/`. Esses scripts aplicam o Diagnoser e o AsmEvolver atuais a cópias dos CSVs da bateria e não executam o simulador.

| Cenário evoluído | μ da incorporação | Limiar | Origem do valor |
|---|---|---|---|
| TRANSPORT_OBJECT_VACUUM_ASSIST (C6) | 0,170 | `lateral_friction <= 0.335` | Log da RQ1.1. A reprodução sequencial dá o mesmo valor, porque o dataset do primeiro passo é idêntico |
| LIFT_OBJECT_VACUUM_ASSIST (C1) | 0,140 | `lateral_friction <= 0.1425` com o dataset preservado; `<= 0.32` com o dataset reiniciado | 0,1425: reprodução (não está em log). 0,32: log da RQ1.1 |

- 0,140 é a primeira recuperação de lift da sequência, porque de 0,170 a 0,145 as violações ocorreram no transporte e o 0,155 não violou.
- **Por que o limiar muda com o dataset preservado.** O Diagnoser passa a treinar também com os runs de 0,170 a 0,145, em que o LIFT_OBJECT foi cumprido. A árvore então separa 0,145 de 0,140, em vez de separar 0,5 de 0,140.
- **Hipótese da reprodução.** Supõe que os runs anteriores gerariam os mesmos CSVs da RQ1.1. Isso é plausível com o código atual, porque os cenários evoluídos não são ativados (P1), mas não foi executado.

Cenários resultantes das duas incorporações (`reproducao/rq12_two.py`):

```
TRANSPORT_OBJECT_VACUUM_ASSIST   (evolutionary; μ = 0.170, C6)
  Given: finger_contacts >= 2 AND lateral_friction <= 0.335
  When : object_lift_height_cm >= 10
  Do   : apply_vacuum_assist()
  Then : distance_object_goal_cm <= 5 AND object_lift_height_cm >= 10 AND finger_contacts >= 2
  TRANSPORT_OBJECT restringido: Given = finger_contacts >= 2 AND lateral_friction > 0.335

LIFT_OBJECT_VACUUM_ASSIST        (evolutionary; μ = 0.140, C1)
  Given: finger_contacts >= 2 AND lateral_friction <= 0.1425
  When : grasp_completed == 1
  Do   : apply_vacuum_assist()
  Then : object_lift_height_cm >= 10 AND finger_contacts >= 2
  LIFT_OBJECT restringido: Given = finger_contacts >= 2 AND lateral_friction > 0.1425
```

Novas transições:
- LIFT_OBJECT → TRANSPORT_OBJECT_VACUUM_ASSIST;
- TRANSPORT_OBJECT_VACUUM_ASSIST → PLACE_OBJECT e → `__end__`;
- GRASP_OBJECT → LIFT_OBJECT_VACUUM_ASSIST e RETRY_GRASP → LIFT_OBJECT_VACUUM_ASSIST;
- LIFT_OBJECT_VACUUM_ASSIST → TRANSPORT_OBJECT, → SAFE_ABORT e → TRANSPORT_OBJECT_VACUUM_ASSIST.

Valores posteriores que **satisfazem as condições GWDT**. Isso é previsão, não reutilização observada:
- **TRANSPORT_OBJECT_VACUUM_ASSIST:** 0,160, 0,155, 0,150, 0,145 e 0,135. De 0,140 para baixo, só se o lift chegar a 10 cm com 2 contatos.
- **LIFT_OBJECT_VACUUM_ASSIST:** de 0,135 a 0,010.

**Com o código atual não há reutilização.** Os problemas P1 e P6 impedem a ativação dos cenários evoluídos. Até a etapa 7, o artigo só pode falar em correspondência pelas condições.

## Problemas e correções planejadas

| # | Problema | Causa | Correção planejada | Verificação |
|---|---|---|---|---|
| P0 | O runner não preserva o conhecimento | `execute_simulations.py` restaura `asm.json` e dataset do `base/` antes de cada run | Opção `preserve_knowledge` na configuração do experimento: restaurar só no início da sequência; guardar `asm_before_run.json` e `asm_after_run.json`; registrar no `outcome.json` as ativações de cenários evolutivos (`[E]` no trace do Manager) | Sequência de 2 runs: o ASM inicial do 2º é igual ao `asm_after_run.json` do 1º |
| P1 | O Manager não avalia `lateral_friction` | `to_eval_dict()` não tem o campo (TODO em `1-manager/src/knowledge.py:172`); `_eval` (`asm_evaluator.py:19-23`) converte o erro em `False` sem aviso | Incluir `lateral_friction` no contexto; `_eval` registra uma vez cada variável ausente | Teste do AsmEvaluator com o ASM das duas incorporações: em 0,16 casa TRANSPORT_OBJECT_VACUUM_ASSIST, em 0,40 casa TRANSPORT_OBJECT |
| P2 | Uma incorporação repetida sobrescreve o cenário com Given impossível (em 0,16: `> 0.335 AND <= 0.335`; 74 transições duplicadas ao fim) | Causa raiz em P1 e P4: a violação dentro da região evoluída é atribuída ao cenário de domínio restringido. O AsmEvolver não tem salvaguardas | No AsmEvolver: (a) recusar Given insatisfazível, com evento `evolution_rejected`; (b) exigir que o novo Given seja verdadeiro no contexto da violação; (c) chave existente conforme Q3; (d) não duplicar transições | Testes unitários: o caso reproduzido é recusado; o caso de 0,170 continua igual |
| P3 | O diagnóstico fica contraditório com dados não monotônicos (0,150: `<= 0.1575 AND <= 0.1525 AND > 0.1575`; 0,130: `<= 0.1325 AND > 0.1325`) | `unanticipated_scenario_diagnoser.py:118-120` junta com AND as condições de todas as folhas positivas; `asm_evolver.py:20-26` nega cláusula por cláusula | Diagnoser conforme Q2. No AsmEvolver, com mais de uma cláusula, restringir com `NOT (diagnóstico)`; com uma só, manter a forma atual | Reprodução sequencial sem contradições (0,335 em 0,170; 0,1425 em 0,140); os 15 diagnósticos da RQ1.1 iguais aos logs |
| P4 | O monitor do DejaVu não vê o ASM evoluído | YAML do Sismic estático (`antecipated_scenario_monitor.py:20`); mapa subtarefa → evento fixo (`dejavu.py:54-61`) | Gerar o ASM-SM do `asm.json` na inicialização, com `3-dejavu/src/has_model_to_assm.py` (a transformação ASM → ASM-SM do artigo); montar o mapa a partir do ASM, escolhendo o evento habilitado no estado atual. O Identifier passa a reconhecer cenários evolutivos violados | Primeiro: o YAML gerado do ASM base é equivalente ao atual (se não for, reconciliar antes). Depois: bancada de 0,17, 0,14 e 0,04 com os mesmos eventos |
| P5 | Configurações que não violaram ativam cenários evoluídos (0,155 no de transporte, 0,135 no de lift) | Generalização da região diagnosticada | Nenhuma correção de código; tratamento conforme Q4 | Contagem dessas ativações na sequência |
| P6 | O Managing ignora a adaptação de um cenário evolutivo | `plan.py:12` envia a chave (`TRANSPORT_OBJECT_VACUUM_ASSIST`); o Managing só conhece `APPLY_VACUUM_ASSIST` (`2-managing/src/main.py:37`) | Para `evolutionary`, enviar o `do`; para `adaptive`, manter a chave (o `do` do SAFE_ABORT, `abort_grasp()`, não existe no Managing). Conferir o `send_transition` pós-adaptação quando o nó atual for evolutivo | Teste do Planner; sequência curta (etapa 6) |

## Decisões

Aceitas em 2026-11-08, todas conforme a recomendação.

| # | Questão | Decisão |
|---|---|---|
| Q1 | O que a sucção faz quando é aplicada antes da queda, com o objeto seguro. A rotina atual sempre abre a garra e pega de novo: no início do transporte, isso soltaria o cubo a 10 cm | Se a tarefa começar com 2 contatos, aplica só o atrito ×3 e segue para a subida, sem reabrir a garra. Com 0 contatos, a rotina continua a atual; a RQ1.1 não muda, porque lá a tarefa sempre começou com 0 contatos |
| Q2 | Que regra o Diagnoser usa quando a árvore tem várias folhas positivas | Caminho da execução atual (`decision_path`), com os limites simplificados por variável (maior limite inferior, menor superior). Se a árvore classificar a execução atual como sem violação, o diagnóstico falha com erro explícito |
| Q3 | O que fazer se a chave do novo cenário já existir | Recusar a evolução, sem alterar o ASM, e registrar o evento `evolution_rejected` |
| Q4 | Como tratar ativações em configurações que não violaram (P5) | Relatar como aplicação preventiva dentro da região aprendida, com a contagem dessas ativações, e citar a generalização a partir de poucas amostras nas ameaças à validade |
| Q5 | O conhecimento preservado inclui o dataset do Diagnoser? | Sim: ASM e CSVs se acumulam na sequência. O artigo declara isso |

## Etapa 1 — Diagnoser e AsmEvolver (2026-11-08)

Mudanças (sem commit):
- `3-dejavu/src/unanticipated_scenario_diagnoser.py`: `diagnosis(identified, current_execution=None)`. Com a execução atual, a condição vem do caminho dela na árvore (Q2). Sem ela, vale a regra antiga, que só é aceita com uma folha positiva.
- `3-dejavu/src/asm_evolver.py`:
  - a restrição do cenário original nega a conjunção por De Morgan: `(a' OR b')`;
  - `evolve(..., context=percepção)` recusa com `EvolutionRejected` quando a chave já existe (Q3) ou quando o novo Given não vale para os valores observados das variáveis diagnosticadas (P2);
  - não duplica transições.
- `3-dejavu/src/dejavu.py`: passa ao Diagnoser o CSV do run e ao AsmEvolver a percepção; uma recusa vira o evento `evolution_rejected`.
- `3-dejavu/tests/test_evolution.py`: 9 testes novos. Os 31 testes passam.

Verificação com dados reais, sem simulador:
- **`reproducao/regressao_rq1_1.py`:** os 15 diagnósticos da RQ1.1, refeitos com o código novo e o dataset de cada run, são iguais aos logs (0 diferenças).
- **`reproducao/rq12_sequential.py`:** na sequência com conhecimento preservado não há mais condições contraditórias nem transições duplicadas.
  - Limiares sequenciais: 0,335 (0,170); 0,1525 (0,150 a 0,135, transporte); 0,1425 (0,140); 0,1325 (0,130 a 0,010).
  - O ASM final tem só os dois cenários evoluídos.
  - As ocorrências repetidas são recusadas por chave existente, e 0,040 (C2) por não cobrir a situação.
  - Essa reprodução ainda supõe que as ocorrências se repetem, como com o código antigo. Com P1, P4 e P6 corrigidos, elas devem ser tratadas pelos cenários evoluídos, o que só a sequência real mostra.

## Etapa 2 — ASM-SM gerado do ASM (2026-11-08)

Antes de mudar: o YAML do ASM-SM em `3-dejavu/configs/arm/` é idêntico, estado a estado, ao que `has_model_to_assm.py` gera a partir do `asm.json` inicial. Gerar o ASM-SM na inicialização, portanto, não muda nada com o ASM inicial.

Mudanças:
- **Monitor** (`antecipated_scenario_monitor.py`): gera o ASM-SM do `asm.json` na inicialização, em vez de ler o YAML.
- **Conversor** (`has_model_to_assm.py`): cenários evolutivos recebem o tipo `E`, e `NOT` é traduzido.
- **AsmEvolver**: grava `evolved_from` (a chave do cenário de origem) no cenário novo. O Manager ignora o campo.
- **Mapeador de eventos** (`subtask_events.py`, novo): traduz mudanças de subtarefa em eventos do ASM-SM.
  - Cenários de domínio e adaptativos: mapa fixo, igual ao anterior.
  - Cenários evoluídos: o evento só dispara quando o Managing sai da fase, isto é, das subtarefas do Do e do cenário de origem. **Motivo:** o Do de um cenário evoluído é só a ação do candidato (ex.: `apply_vacuum_assist()`), e a tarefa de origem (ex.: o transporte) retoma depois. O Then, herdado da origem, só vale ao fim das duas; checado no fim da sucção, o TRANSPORT_OBJECT_VACUUM_ASSIST acusaria uma violação falsa (objeto ainda a 30 cm do alvo).
- **Contexto do ASM-SM** (`dejavu.py`): recebe da percepção as variáveis do ASM que não estão no contexto fixo, como `lateral_friction`. Com o ASM inicial, não há nenhuma.
- **Documentação:** CLAUDE.md atualizado.

Verificação:
- **Testes:** `3-dejavu/tests/test_evolved_monitor.py` (8 testes; 39 no total, todos passando).
  - O ASM-SM gerado do ASM inicial é igual ao YAML commitado, e os eventos de domínio não mudam.
  - Com o ASM das duas incorporações:
    - 0,5 segue os cenários de domínio;
    - 0,16 passa por TRANSPORT_OBJECT_VACUUM_ASSIST até FINAL, sem violação;
    - 0,13 passa pelos dois cenários evoluídos até FINAL;
    - 0,04 viola LIFT_OBJECT_VACUUM_ASSIST, e a nova incorporação parte dele.
  - Com a regra de fase desligada, os três testes de cenários evoluídos falham.
- **`reproducao/regressao_monitor_rq1_1.py`:** as percepções gravadas nos CSVs dos 25 runs da RQ1.1, passadas pelo monitor novo, dão o mesmo estado do ASM-SM e o mesmo `sat` em todos os ticks (0 diferenças). Contraprova: sem o evento de LIFT, o run nominal diverge em 44 ticks.

## Regras para o manuscrito

| # | Regra |
|---|---|
| M1 | Até a etapa 7, nenhuma frase diz que ocorrências posteriores foram tratadas por um cenário evoluído; usa-se "satisfariam as condições". |
| M2 | O limiar 0,1425 só é apresentado como resultado depois da sequência real. Antes disso, é reprodução a partir da RQ1.1, e o texto diz isso. |
| M3 | A análise antiga (`../RQ1.0/RESULTS_RQ1.2.md`), que classificava 0,135 como LIFT_OBJECT com limiar estimado 0,3175, não é usada. Na bateria atual, 0,135 violou no transporte, com limiar 0,3175 em log. |
| M4 | As correções P1–P4 e P6 são do framework e do exemplar, não do experimento. O artigo as descreve como parte da implementação usada na RQ1.2, e a regressão da etapa 4 mostra que não alteram a RQ1.1. |

## Etapa 3 — Manager e Managing (2026-11-08)

Mudanças:
- **P1** (`1-manager/src/knowledge.py`): `lateral_friction` entra no contexto do ASM. Em `asm_evaluator.py`, uma condição que não pode ser avaliada é registrada uma vez no trace do Manager, em vez de virar falsa em silêncio.
- **P6** (`1-manager/src/plan.py`): para um cenário `evolutionary`, o Manager envia o `do` (`apply_vacuum_assist()` vira `APPLY_VACUUM_ASSIST`). Para os adaptativos, continua enviando a chave (RETRY_GRASP, SAFE_ABORT).
- **Q1** (`2-managing/src/tasks/object_delivery/grip_recovery_tasks.py`): se a tarefa de recuperação começa com os dois dedos em contato com o objeto, aplica o atrito e sobe até a altura de lift a partir da posição de repouso, sem reabrir a garra. Com 0 contatos, a rotina é a mesma da RQ1.1.
- **Tempo de ativação**, conferido nos CSVs da bateria: `grasp_completed` vira 1 ainda em GRASP_OBJECT (2 ticks antes do LIFT_OBJECT), e a altura passa de 10 cm ainda em LIFT_OBJECT. Os cenários evoluídos são avaliados antes de o cenário de domínio avançar pela troca de subtarefa.

Verificação:
- **`1-manager/tests/test_evolved_asm.py`** (novo, 6 testes):
  - o contexto tem `lateral_friction`;
  - com o ASM das duas incorporações, o cenário de transporte evoluído casa em 0,16, e em 0,5 o Manager segue o TRANSPORT_OBJECT;
  - o cenário de lift evoluído casa em 0,13 ao completar a pegada, e não em 0,16;
  - o Planner envia `APPLY_VACUUM_ASSIST`, `RETRY_GRASP` e `SAFE_ABORT`;
  - uma variável ausente é registrada.
- **`bancada/bench_evolved.py`** (física, não o sistema completo): a sequência com a `VacuumAssistTask` de produção, o Manager imitado e o ASM crescendo como na sequência (transporte depois de 0,170; lift depois de 0,140). Resultado em `bancada/results/bench_evolved.csv`:

| μ | ASM | Cenários evoluídos ativados | Violação | Objetivo |
|---|---|---|---|---|
| 0,170 | inicial | — | TRANSPORT, step 41 | não (sem DejaVu na bancada) |
| 0,160; 0,155; 0,150; 0,145 | + transporte | transporte, step 21 | — | sim |
| 0,140 | + transporte | — | LIFT, step 23 | não (sem DejaVu na bancada) |
| 0,135 a 0,060 (7 valores) | + transporte + lift | lift, step 15; transporte, step 19–20 | — | sim |
| 0,040; 0,020; 0,010 | + transporte + lift | lift, step 15 | LIFT, step 21 | não |

Leitura:
- **Reutilização prevista:** depois das duas incorporações, a bancada prevê que os cenários evoluídos evitam a violação em 11 configurações (0,160 a 0,145 e 0,135 a 0,060). Em 0,040, 0,020 e 0,010, a sucção aplicada antes do escorregamento não basta, como o C1 na RQ1.1. Na sequência real, a violação seria do LIFT_OBJECT_VACUUM_ASSIST, e o DejaVu trataria a situação a partir dele.
- **Q4:** 0,155 (sem violação na RQ1.1) passa a ativar o cenário de transporte; 0,135 (violação de transporte na RQ1.1) passa a ativar os dois.
- **Limite:** isso é bancada. Só a sequência real (etapas 6 e 7) mostra o comportamento com Manager, DejaVu e ASM-SM.

## Etapa 4 — Regressão da RQ1.1 com o sistema completo (2026-11-08)

Os runs de 0,17, 0,14 e 0,04 foram refeitos pelo runner, com as correções das etapas 1 a 3 (até `b42fcbd`), as mesmas entradas da bateria (`diff -rq` sem diferenças) e o conhecimento reiniciado.

- **Configuração:** `../experiment_configs/rq1_2_regressao.json`. **Evidências:** `regressao/results/`, ignorada pelo git.
- **Comparação** (`regressao/comparar.py`): **0 diferenças** com a bateria nos três runs. Caminho (B, B, C), objetivo, distância final (1,6, 1,6 e 1,5 cm), último step, violação, diagnóstico, ranking com os scores, tentativas, resultados, decisões de retry e cenários evoluídos são iguais.
- **Diferença esperada e não contada:** o campo `evolved_from` no cenário evoluído.
- **Conclusão:** as correções não alteram a RQ1.1.

## Etapa 5 — Modo sequencial do runner (P0)

Mudanças em `../execute_simulations.py`:
- **Opção `--preserve-knowledge`:** os runs seguem a ordem da linha de comando, e cada um começa com o ASM (`asm_after_run.json`) e o dataset (`outputs/dataset/`) do run anterior. O primeiro começa das suas entradas.
- **Por run:** grava `outputs/asm_before_run.json`.
- **No `outcome.json`**, novos campos:
  - `knowledge` (se o conhecimento foi preservado e de qual run veio);
  - `evolved_scenarios_activated` (linhas `[E]` do trace do Manager, com o step);
  - `asm_evolution_rejected`.

## Etapa 6 — Sequência curta com conhecimento preservado (2026-11-08)

`execute_simulations.py --preserve-knowledge 10_0_17 11_0_16 15_0_140 17_0_130`.
- **Configuração:** `../experiment_configs/rq1_2_sequencia_curta.json`.
- **Evidências:** `sequencia/curta/`, ignorada pelo git. A tabela foi gerada por `sequencia/analisar.py`.
- **Execução:** nenhum timeout ou erro. Em cada run, o ASM de entrada é o ASM de saída do anterior.

| μ | Cenários evoluídos no ASM de entrada | Ativados pelo Manager | Violação | Adaptação | Caminho | Distância | Incorporado |
|---|---|---|---|---|---|---|---|
| 0,17 | — | — | TRANSPORT_OBJECT, step 41 | C6, sucesso | B | 1,6 cm | TRANSPORT_OBJECT_VACUUM_ASSIST, `lateral_friction <= 0.335` |
| 0,16 | transporte | transporte, step 20 | — | — | A | 1,5 cm | — |
| 0,14 | transporte | — | LIFT_OBJECT, step 23 | C1, sucesso | B | 1,6 cm | LIFT_OBJECT_VACUUM_ASSIST, `lateral_friction <= 0.15` |
| 0,13 | transporte, lift | lift, step 15; transporte, step 19 | — | — | A | 1,4 cm | — |

Leitura:
- **Primeira reutilização observada.** Em 0,16 (que violou no transporte na RQ1.1) e em 0,13 (que violou no lift na RQ1.1), os cenários incorporados foram ativados pelo Manager antes do escorregamento. Não houve violação e o objetivo foi atingido. O Manager executou a sucção como adaptação interna (`APPLY_VACUUM_ASSIST`), sem o DejaVu.
- **Limiar do lift.** Nesta sequência curta é 0,15, o ponto médio entre 0,16 (o run anterior mais próximo sem violação no lift) e 0,14, porque os runs de 0,155 a 0,145 não fazem parte dela. Na sequência completa, a reprodução prevê 0,1425.
- **Score do C1 em 0,14:** 0,915 (0,962 na RQ1.1). O limiar diagnosticado mudou, e o C1 continuou em primeiro.
- **Traces do Manager:** nenhuma condição não avaliada. O único `[WARN]` em 0,17 e 0,14 é o mesmo dos runs da bateria: a transição de domínio depois de uma adaptação.
