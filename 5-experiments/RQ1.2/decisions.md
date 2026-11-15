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
| 7. Sequência 0,170 → 0,060 (escopo S1) | Concluída (2026-11-08); resultado da RQ1.2 na seção "Etapa 7" |
| 8. Q6 e extensão 0,040 → 0,010 (escopo S1 revisto) | Concluída (2026-11-09); seção "Etapa 8" |

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
- **Evidências:** `sequencia/results/curta/`, ignorada pelo git. A tabela foi gerada por `sequencia/analisar.py`.
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

## Testes do passo 3 (bloqueio do DejaVu depois de uma adaptação interna) — 2026-11-08

Evidências em `testes/results/` (ignorada pelo git). Configuração: `../experiment_configs/rq1_2_teste_bloqueio.json`.

**Teste 1 — 0,14 → 0,04, com `--preserve-knowledge`.**
- **0,14:** caminho B. Incorpora o LIFT_OBJECT_VACUUM_ASSIST (`<= 0.15`).
- **0,04, o que aconteceu:**
  - o Manager ativou o cenário evoluído no step 15, e a sucção não segurou o cubo;
  - o monitor detectou a violação do LIFT_OBJECT_VACUUM_ASSIST no step 23;
  - o diagnóstico falhou: `Nenhuma feature estática encontrada para 'LIFT_OBJECT_VACUUM_ASSIST'`.
- **Causa:** o Diagnoser só usa as execuções em que o cenário violado esteve ativo. Neste teste, só o próprio run de 0,04, então não havia com o que comparar. Na sequência completa, o cenário fica ativo e satisfeito de 0,135 a 0,060 antes de 0,04, o que dá histórico.
- **Correção da P0b confirmada:** depois dos runs, os arquivos locais (22 CSVs e `environment.yaml`) ficaram idênticos ao estado anterior.

**P8 — Pipeline do DejaVu falha e o run segue sem fail-safe** (decisão pendente, Q6).
- No teste 1, sem recomendação, o Manager seguiu a sequência nominal com a garra vazia. O run "completou" com o cubo a 37,4 cm do alvo, sem adaptação e sem fail-safe. A falha foi detectada (evento `violation`), mas não foi tratada.
- Na RQ1.1 isso nunca ocorreu, e a R6 tornava qualquer `execution_error` motivo para invalidar a bateria.
- Para a sequência completa, não é esperado, pelo histórico descrito acima. Se ocorrer, é relatado como limitação.
- **Q6:** um erro no pipeline (sem recomendação possível) deve acionar o fail-safe, com o motivo registrado? Recomendação: sim. A mudança só age quando há erro no pipeline, o que não aconteceu em nenhum run da RQ1.1.

**Teste 2 — 0,14 → 0,06 → 0,04, com `--preserve-knowledge`.** Sem timeout ou erro, e o conhecimento passou corretamente entre os runs.

| μ | Ativados pelo Manager | Violação | Diagnóstico | Adaptação | Caminho | Incorporado |
|---|---|---|---|---|---|---|
| 0,14 | — | LIFT_OBJECT, step 23 | `<= 0.32` | C1, sucesso | B | LIFT_OBJECT_VACUUM_ASSIST |
| 0,06 | lift evoluído, step 15 | — | — | — | A | — |
| 0,04 | lift evoluído, step 15 | LIFT_OBJECT_VACUUM_ASSIST, step 23 | `<= 0.05` | C2, sucesso | B | LIFT_OBJECT_VACUUM_ASSIST_ADJUST_GRIP_FORCE, Given `finger_contacts >= 2 AND lateral_friction <= 0.32 AND lateral_friction <= 0.05` |

- **O bloqueio (P7) não ocorre neste caso, e o `main.py` não muda.**
  - A tarefa de sucção termina e devolve o Managing ao TRANSPORT_OBJECT.
  - O ASM do Manager avança para esse cenário de domínio pela troca de subtarefa (step 23), e isso desliga `_post_adaptation`. No step 24, a primeira tentativa do DejaVu foi enviada.
  - O comportamento é determinístico, porque a tarefa sempre retoma o transporte. Uma falha do cenário evoluído de transporte não foi observada: na bancada, ele não falha em nenhum μ da sequência.
- **O ranking mudou em 0,04: C2 (0,897) ficou à frente do C1 (0,887).**
  - O limiar diagnosticado (`<= 0.05`) é estreito, e a sobreposição com o `lateral_friction <= 0.4` do Given do C1 diminui. Na RQ1.1 (`<= 0.27`), o C1 vencia.
  - É efeito da métrica sobre uma região mais estreita, não um aprendizado de que a sucção falhou. O texto não deve sugerir isso.
- **O cenário incorporado a partir de um cenário evoluído** herda o Given restringido da origem (`<= 0.32`), mais o diagnóstico (`<= 0.05`). A cláusula redundante é correta e pode ser simplificada na figura.

**P0b — O runner alterava o ambiente local** (corrigido em 2026-11-08).
- **O problema:** ao fim de cada run, `_restore_base()` copiava o `base/` sobre as configurações reais e a pasta de dataset. Com isso, apagava os 22 CSVs versionados em `3-dejavu/output/arm/antecipated_scenario_dataset/` e trocava o `environment.yaml` local.
- **A correção:** o runner guarda o estado local antes do primeiro run (em `results/_local_state_before_runs`, que sobrevive a uma interrupção) e o restaura depois de cada run.
- **Por que os experimentos não mudam:** o build gera os 9 arquivos de configuração e o dataset de cada experimento, e o runner aplica tudo antes do run.
- **Verificação:**
  - um teste isolado de salvar e restaurar;
  - nos testes 1 e 2, os arquivos locais ficaram idênticos (md5) ao estado anterior.

## Escopo da RQ1.2 (decidido em 2026-11-08)

| # | Decisão |
|---|---|
| S1 | **A RQ1.2 é uma sequência de 0,170 a 0,060**, com o conhecimento preservado, nos 13 valores da RQ1.1 dessa faixa. **Motivo:** a RQ1.2 pergunta se o conhecimento incorporado é reaproveitado, e isso só pode ser testado onde a adaptação incorporada funciona. A RQ1.1 mostrou que a sucção (C1) recupera o lift até 0,060 e não recupera em 0,040, 0,020 e 0,010. O corte vem do resultado da RQ1.1, definido antes de rodar a RQ1.2, e o artigo declara isso. |
| S2 | **Mensagem da RQ1.2:** depois que o DejaVú incorpora uma adaptação validada, as ocorrências seguintes na região incorporada são tratadas pelo ASM como comportamento previsto (adaptação interna do Manager), sem violação e sem acionar o DejaVú. |
| S3 | **O que relatar:** (1) as incorporações, com o GWDT e os limiares; (2) por atrito, RQ1.1 × RQ1.2, se precisou do DejaVú ou se foi tratado pelo conhecimento incorporado; (3) a divisão do espaço comportamental por faixa de μ e por fase (cenário original ou incorporado). |
| S4 | **Limitações a declarar:** sequência única, determinística e numa só ordem (os limiares dependem do que foi visto antes); região aprendida a partir de poucas amostras e mais larga que o validado (ex.: 0,155 passa a usar a sucção de forma preventiva, Q4); abaixo de 0,1425, as duas fases usam conhecimento incorporado e a segunda aplicação é fisicamente redundante (o ASM organiza o conhecimento por fase); refinar o conhecimento incorporado quando ele não basta (μ < 0,060) é trabalho futuro. |
| S5 | **Fora do escopo:** a Q6 (fail-safe quando o diagnóstico falha) e a E3 (o cenário criado em 0,040 nos testes) não são necessárias para a RQ1.2. A Q6 fica registrada como melhoria futura. |
| S6 | As correções feitas para a RQ1.2 (P1–P4, P6) são descritas no artigo como parte do mecanismo (o Manager avalia cenários evoluídos com parâmetros contextuais; o ASM-SM é gerado do ASM evoluído), não como defeitos. A regressão (etapa 4) mostra que a RQ1.1 não muda. |

**Revisão do escopo (2026-11-09).** S1, S4 e S5 mudam, e entra a S7; S2, S3 e S6 continuam valendo.
- **S1 revista:** a sequência vai de 0,170 a 0,010 (os 16 valores da RQ1.1 dessa faixa). O trecho de 0,040 a 0,010 roda como continuação do 0,060 da sequência principal (Etapa 8). **Motivo:** mostrar também o que acontece quando o conhecimento incorporado não basta: o refinamento de um cenário incorporado (0,040) e o limite do catálogo, com parada segura (0,020 e 0,010).
- **S4 revista:** a afirmação de que a segunda aplicação é "fisicamente redundante" vale só onde os dois cenários incorporados usam a sucção (0,05 < μ ≤ 0,1425). Em μ ≤ 0,05, o cenário de transporte reduz a pegada reforçada pelo de lift (Etapa 8). O refinamento deixa de ser trabalho futuro.
- **S5 revista:** a Q6 foi aceita e implementada, porque o pipeline do artigo prevê o fail-safe quando o diagnóstico não é possível. A E3 (agora o cenário criado em 0,040 na sequência) faz parte da RQ1.2.
- **S7 (nova): uma falha sem recuperação não altera o ASM.** Em 0,020, a E1 foi violada, C6 e C7 falharam e o run terminou em fail-safe. A E1 não é restringida, e nada é incorporado. **Motivos:**
  1. A abordagem só evolui o ASM com uma adaptação validada (candidato com sucesso e objetivo global atingido), que fornece o Do do novo cenário.
  2. O diagnóstico (`lateral_friction <= 0.04`) não aponta a causa observada, que é a E1 reduzir o atrito definido pela E3. Restringir a E1 por atrito registraria uma causa falsa.
  3. Sem alternativa validada, restringir a E1 deixaria o transporte em μ ≤ 0,04 sem cenário previsto, e a próxima ocorrência terminaria do mesmo jeito (DejaVú, candidatos, fail-safe).
  4. Retirar ou invalidar conhecimento sem substituto é outro mecanismo, de revisão de conhecimento, que não está no pipeline do artigo.
  
  **No artigo, cada ponto em sua seção:**

  | Ponto | Seção | Motivo |
  |---|---|---|
  | O ASM só cresce com adaptações validadas | Descrição da abordagem (AsmEvolver) e desenho da RQ1.2 | É uma escolha de projeto: impede incorporar conhecimento não validado. Não é apresentada como limitação |
  | Cenário incorporado falha, nenhum candidato recupera: o conhecimento fica como está e o sistema termina em fail-safe | Resultados da RQ1.2 (0,020 e 0,010) | É o comportamento observado, e seguro |
  | Não há revisão do conhecimento incorporado que falhou sem substituto: ele continua a ser aplicado, e a mesma falha pode se repetir | Limitações e trabalho futuro | Consequência do ponto anterior |
  | Interferência entre cenários incorporados de fases diferentes (abordagem): o ASM organiza o conhecimento por fase e não considera o efeito de uma adaptação anterior | Limitações e trabalho futuro (composição de adaptações entre fases) | Observada em 0,020 |
  | Intensidade da interferência (experimento): cada candidato fixa o atrito dos dedos num valor absoluto | Ameaças à validade | Simplificação do simulador |

## Etapa 7 — Resultado da RQ1.2 (sequência 0,170 → 0,060, 2026-11-08)

`execute_simulations.py --preserve-knowledge` com os 13 valores da RQ1.1 de 0,170 a 0,060, versão `20dd3bb`.
- **Configuração:** `../experiment_configs/rq1_2_sequencia.json`.
- **Evidências:** `sequencia/results/principal/`, ignorada pelo git.
- **Tabelas:** geradas por `sequencia/comparar_rq1_1.py` e `sequencia/analisar.py`.
- **ASM final:** `asm_evoluido_rq1_2.json`, versionado, para a figura `arm_asm_evoluida.pdf`.
- **Execução:**
  - nenhum timeout, erro de pipeline ou condição não avaliada no Manager;
  - em cada run, o ASM de entrada é o de saída do anterior;
  - os arquivos locais ficaram idênticos (md5) ao estado anterior.

| μ | RQ1.1 (conhecimento reiniciado) | RQ1.2 (conhecimento preservado) | Incorporado |
|---|---|---|---|
| 0,170 | violação TRANSPORT; DejaVú, C6 | violação TRANSPORT; DejaVú, C6 | **E1** TRANSPORT_OBJECT_VACUUM_ASSIST, `lateral_friction <= 0.335` |
| 0,160 | violação TRANSPORT; DejaVú, C6 | E1 ativada (step 20); sem violação | — |
| 0,155 | sem violação | E1 ativada (step 20); sem violação | — |
| 0,150 | violação TRANSPORT; DejaVú, C6 | E1 ativada (step 20); sem violação | — |
| 0,145 | violação TRANSPORT; DejaVú, C6 | E1 ativada (step 20); sem violação | — |
| 0,140 | violação LIFT; DejaVú, C1 | violação LIFT; DejaVú, C1 | **E2** LIFT_OBJECT_VACUUM_ASSIST, `lateral_friction <= 0.1425` |
| 0,135 | violação TRANSPORT; DejaVú, C6 | E2 (step 15) e E1 (step 19); sem violação | — |
| 0,130 a 0,060 (6 valores) | violação LIFT; DejaVú, C1 | E2 (step 15) e E1 (steps 19–20); sem violação | — |

Resumo:
- **DejaVú acionado:** em 12 das 13 configurações na RQ1.1 e em 2 na RQ1.2 (as incorporações).
- **Reutilização:** 11 configurações foram tratadas pelo conhecimento incorporado, como adaptação interna do Manager, sem violação. Dez delas violavam na RQ1.1; a outra é 0,155, ativação preventiva (Q4).
- **Objetivo:** 13 de 13 nas duas. Distância final na RQ1.2 de 1,3 a 1,9 cm.
- **Duração da tarefa:** com reutilização, 64 steps em todos os 11 runs, praticamente o nominal (65 em 0,155 na RQ1.1). Na RQ1.1, os 10 que violavam levavam de 89 a 120 steps, porque a recuperação vinha depois do escorregamento.
- **Limiar do lift:** 0,1425, como previsto pela reprodução. Ele é o ponto médio entre 0,145 (o último run sem violação no lift) e 0,140, porque o dataset preservado inclui os runs anteriores da sequência. Na RQ1.1, isolado, era 0,32.
- **Espaço comportamental resultante** (cenário usado em cada fase):

| Faixa de μ | Lift | Transporte |
|---|---|---|
| μ > 0,335 | LIFT_OBJECT (original) | TRANSPORT_OBJECT (original) |
| 0,1425 < μ ≤ 0,335 | LIFT_OBJECT (original) | E1 (incorporado, C6) |
| μ ≤ 0,1425 | E2 (incorporado, C1) | E1 (incorporado, C6) |

## Etapa 8 — Q6 e extensão 0,040 → 0,010 (2026-11-09)

**Q6 implementada.** Um erro no pipeline do DejaVú (sem diagnóstico ou sem ranking) leva ao fail-safe, com o motivo `pipeline_<etapa>`.
- `3-dejavu/src/retry_policy.py`: `decide_after_pipeline_error(stage)`.
- `3-dejavu/src/dejavu.py`: no erro do pipeline, registra a decisão (`retry_decision`, tentativa 0) e envia o fail-safe ao Manager, que o executa pelo mesmo caminho do `attempts_exhausted`.
- `3-dejavu/tests/test_measurement.py`: 1 teste novo. Os 40 testes do DejaVú e os 6 do Manager passam.
- **Não muda resultados anteriores:** nenhum run da RQ1.1 nem da Etapa 7 tem evento `pipeline_error`. Na extensão também não houve, então a Q6 não foi exercitada.

**Runner:** `execute_simulations.py --carry-from <run>` faz o primeiro run do lote começar do ASM e do dataset deixados por um run já executado.

**Execução.** `execute_simulations.py --preserve-knowledge --carry-from RQ1.2/sequencia/results/principal/22_0_060 23_0_040 24_0_020 25_0_010`.
- **Configuração:** `../experiment_configs/rq1_2_sequencia_extensao.json`.
- **Evidências:** `sequencia/results/extensao/`, ignorada pelo git.
- **Tabelas:** `sequencia/analisar.py` e `sequencia/comparar_rq1_1.py` com as duas pastas (`principal` e `extensao`), que formam uma só cadeia.
- **Verificação:**
  - o ASM de entrada de cada run é o de saída do anterior, inclusive de 0,060 para 0,040;
  - nenhum timeout nem erro de pipeline;
  - o DejaVu Console não se conectou, como na Etapa 7, então a espera inicial é a mesma.

| μ | RQ1.1 | RQ1.2 | Incorporado |
|---|---|---|---|
| 0,040 | violação LIFT; C1 falha, C2 recupera (C) | E2 ativada (step 15), a sucção não segura; violação de E2 (step 23); diagnóstico `<= 0.05`; C2 em 1º (0,897 × C1 0,887), sucesso (B); objetivo a 1,8 cm | **E3** LIFT_OBJECT_VACUUM_ASSIST_ADJUST_GRIP_FORCE, `... AND lateral_friction <= 0.05`, `adjust_grip_force()`; E2 restringida a `> 0.05` |
| 0,020 | violação LIFT; C1 e C2 falham; fail-safe (D) | E3 ativada (step 15), o lift segura; E1 ativada (step 20); violação de E1 no transporte (step 40); diagnóstico `<= 0.04`; C6 e C7 falham; fail-safe `attempts_exhausted` (D) | — |
| 0,010 | violação LIFT; C1 não termina, cubo cai da mesa; fail-safe (D) | E3 ativada (step 15), não segura; violação de E3 (step 23); diagnóstico `<= 0.015`; C2 e C1 falham; fail-safe `attempts_exhausted` (D) | — |

Análise:
- **Refinamento (0,040).** O cenário incorporado E2 é tratado como qualquer cenário violado:
  - o Given de E2 é restringido pela negação do diagnóstico;
  - E3 nasce de E2 (`evolved_from`) e herda as transições de E2.
  - Com o histórico de E2 (0,135 a 0,060), o limiar fica entre o último sucesso e a falha.
  - O C2 em 1º lugar é efeito da métrica sobre um limiar estreito (Etapa 6, teste 2), não um aprendizado.
- **0,020: os cenários incorporados de fases diferentes interferem.**
  - A ordem dos eventos foi esta:
    - E3 fixa o atrito dos dedos em 7,0 (`lateralFriction → 7.0`, step 16), e o lift segura;
    - E1 aplica a sucção e fixa o atrito em 3,0 (step 21), reduzindo a pegada;
    - o cubo escorrega no transporte.
  - E1 foi aprendido quando o lift usava a pegada nominal ou o C1 (atrito ≤ 3,0). Cada tarefa de recuperação fixa um valor absoluto de atrito, uma simplificação do simulador.
  - Não dá para afirmar que, sem essa redução, o 0,020 teria sucesso. Com 7,0, o atrito efetivo é 0,14, abaixo do que o transporte exigiu na RQ1.1 (violações até μ = 0,170), e o C7 (7,0) também falhou como recuperação.
- **0,010: limite do catálogo.**
  - A pegada de E3 não segura (atrito efetivo de 0,07).
  - O diagnóstico de E3 foi possível porque E3 tinha histórico do 0,020, onde o lift deu certo. A P8 não ocorreu.
  - O C2, mesmo Do de E3, foi tentado primeiro, porque o ranking não exclui o Do do cenário violado.
- **Sem evolução em 0,020 e 0,010:** o objetivo não foi atingido, então nada é incorporado.

Resumo da sequência completa (16 configurações, 0,170 → 0,010):
- **DejaVú acionado:** 15 na RQ1.1, 5 na RQ1.2 (3 incorporações e 2 fail-safes).
- **Reutilização sem violação:** 11, como na Etapa 7.
- **Objetivo:** 14/16 nas duas.
- **ASM:** de 7 para 10 cenários (E1, E2, E3) e de 13 para 26 transições. `asm_evoluido_rq1_2.json` foi atualizado com o ASM final (o de saída de 0,040, igual ao de 0,010).

Espaço comportamental resultante:

| Faixa de μ | Lift | Transporte |
|---|---|---|
| μ > 0,335 | LIFT_OBJECT (original) | TRANSPORT_OBJECT (original) |
| 0,1425 < μ ≤ 0,335 | LIFT_OBJECT (original) | E1 (C6) |
| 0,05 < μ ≤ 0,1425 | E2 (C1) | E1 (C6) |
| μ ≤ 0,05 | E3 (C2) | E1 (C6) |

Validação de cada região: E1 de 0,160 a 0,060 (em 0,040 não chegou a ser ativado); E2 de 0,135 a 0,060; E3 só no lift de 0,020. Em μ ≤ 0,05, a combinação E3 + E1 não atingiu o objetivo em nenhum run.
