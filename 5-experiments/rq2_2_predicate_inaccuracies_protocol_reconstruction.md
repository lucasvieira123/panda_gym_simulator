# Investigação read-only — Protocolo experimental da RQ2.2 (Predicate Inaccuracies)

Nenhum arquivo foi modificado nesta investigação. Toda leitura foi feita sobre o estado do repositório na branch `feat/interceptor_pattern`, commit `9f6ca34`, incluindo consultas diretas aos CSVs/JSON já gerados e uma checagem em Python (só leitura, sem gravação) para contagens agregadas.

**Pergunta de pesquisa (RQ2.2 — Predicate Inaccuracies):** *"How do variations in the numerical thresholds and relational operators within existing conditions affect the stability of DejaVu's similarity-based adaptation retrieval?"*

**Referência (D_ref, primeira adaptação LIFT_OBJECT validada em RQ1):**

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

Candidato de referência: `C_ref` = Lift Slip — Low Friction Surface (`C1`).

---

## 1. LOCALIZAÇÃO DO EXPERIMENTO

| Componente | Caminho | Função/trecho | Finalidade | Tipo |
|---|---|---|---|---|
| **Definição dos cenários (fonte de verdade)** | `5-experiments/run_similarity_only/configs/desired_scenario.json` | Array de 922 objetos `{name, comment, given, when, do, then}` | Contém os 897 pontos da grade `RQ2_R_H##_C##_F##` — a única parte do arquivo cujo `comment` se autodenomina **"RQ2.2 REGION GRID"** explicitamente (ex.: linha 204) | **Define** o experimento |
| **Classificador de perturbação** | `5-experiments/run_similarity_only/classify_rq2_grid_perturbations.py` | Docstring (linhas 1-14) rotula explicitamente: *"RQ2.2 -- classificacao complementar da grade fatorial (Height x Contacts x Friction) em Baseline / Threshold-only / Operator-only / Combined"*; função `classify()` (52-68) | Classifica cada ponto `R_*` comparando operador e valor contra a referência; **exclui explicitamente** grupos A/B/C (linha 13-14: *"Cenarios de omissao/adicao/sweep local (grupos A/B/C) sao explicitamente excluidos"*) | **Processa/classifica** resultados já calculados — não recalcula similaridade |
| **Pipeline oficial de cálculo** | `5-experiments/run_similarity_only/decompose_rq2_similarity.py` | `compute_decomposition()` (158-212), `render_group_r_section()` (361-421, título fixo na linha 366: *"Grupo R -- grade fatorial de regiões (RQ2.2: Height x Contacts x Friction)"*) | Chama diretamente `calculate_scenario_similarity`/`calculate_conditional_similarity` reais de `3-dejavu/src/similarity/dejavu_similarity.py`; gera os CSVs/`.md` oficiais | **Define + calcula** (é o Retriever real, sem reimplementação) |
| **Motor de similaridade (infraestrutura, não específico da RQ2.2)** | `3-dejavu/src/similarity/dejavu_similarity.py` | `calculate_conditional_similarity`, `_tversky_similarity`, parser de operadores relacionais (linha 66: `oneOf("<= >= < > == !=")`) | Implementação de produção do Retriever, mesma usada em RQ1 | Infraestrutura |
| **Resultados agregados (saída)** | `5-experiments/run_similarity_only/rq2_analysis/rq2_grid_perturbation_classification.csv`, `rq2_grid_direction_summary.json`, `rq2_summary.csv`, `rq2_full_ranking.csv`, `rq2_analysis.md` | — | Artefatos gerados, já existentes no repositório antes desta investigação | **Resultado**, não definição |

**Nomes alternativos buscados além de "RQ2.2"**: `region grid`, `Threshold-only`, `Operator-only`, `Combined`, `direction-preserving`/`direction-changing`, `factorial grid`. Não há ocorrências literais de "sensitivity analysis" nem "predicate inaccuracies" nos artefatos — são a formulação da pergunta de pesquisa, não nomes usados no código.

---

## 2. VARIAÇÕES DE LIMIARES NUMÉRICOS

Evidência: `classify_rq2_grid_perturbations.py` (linhas 36-40, `REFERENCE_CLAUSES`) e reconstrução direta a partir de `rq2_grid_perturbation_classification.csv` (897 linhas), via consulta somente-leitura.

| Predicado original | Valores testados (operador original mantido) | Nº de níveis |
|---|---|---|
| `object_lift_height_cm < 10` | `5, 9, 10, 11, 25, 50` | 6 |
| `finger_contacts < 2` | `1, 2, 3, 4, 5` | 5 |
| `lateral_friction <= 0.315` | `0.1, 0.3, 0.315, 0.33, 0.4, 0.5, 1.0` | 7 |

Consistente com uma grade nominal **9 (H) × 10 (C) × 10 (F) = 900** pontos, da qual **897 existem de fato** em `desired_scenario.json` (`rq2_grid_direction_summary.json`, campo `grid_size_gap: 3`).

**As 3 combinações "ausentes" não são lacunas não executadas.** O próprio script documenta (linhas 196-222) que `H03xC02xF02`/`F03`/`F04` são **idênticas caractere-a-caractere** a cenários já existentes em outros grupos (`C11`, `A0`, `C03` respectivamente) e foram **reaproveitadas sem duplicar nem recalcular**.

**Origem dos valores — evidência de código, não inferência.** Exemplo de comentário (`R_H01_C01_F01`, linha 204 de `desired_scenario.json`): *"Height: left; broad-domain 5% anchor. Contacts: left; exhaustive distinct nonempty proper integer prefix. Friction: left; broad-domain 5% anchor."* Os níveis foram gerados por um **procedimento nomeado por região/direção** ("left"/"right", "broad-domain anchor", "local tightening/relaxation", "exhaustive integer prefix"), descrito apenas textualmente. **Não identificado no repositório**: nenhum script gerador programático desses 897 objetos foi encontrado — a lógica exata que decide as frações/percentuais por nível existe só como texto no `comment`, não como código auditável.

**Independente ou cumulativo a partir de D_ref?** Cada ponto `R_H##_C##_F##` varia **as 3 cláusulas simultaneamente** a partir de D_ref — não é "um predicado por vez" como nos grupos A/B. Por desenho, a RQ2.2 sempre testa a combinação completa (H,C,F) de uma vez; a variação estritamente unidimensional é coberta em paralelo pelo Grupo C.

**Grupo C (variação pura de `lateral_friction`, 1 predicado por vez, C01–C16, 16 pontos)**: tecnicamente uma "variação de limiar numérico" pura (operador `<=` mantido em 100% dos 16 pontos). O comentário de cada ponto (ex. `C01`, linha 84) diz *"Este valor pertence a grade previamente proposta para RQ2; confirme sua correspondência com o histórico da RQ1 antes de descrevê-lo no artigo"* — sem menção a "RQ2.1" nem "RQ2.2". Busca literal por "RQ2.1" em todo `5-experiments/` não retornou nenhuma ocorrência — esse rótulo não existe no repositório. **Não identificado no repositório**: se o Grupo C pertence à RQ2.1 ou à RQ2.2 segundo a intenção do autor original. Por eliminação temática (varia só limiar, preserva operador — bate com a definição de RQ2.2), o Grupo C é um candidato defensável a compor a RQ2.2 junto ao Grupo R, mas isso é inferência de enquadramento, não confirmação por rótulo explícito.

---

## 3. VARIAÇÕES DE OPERADORES RELACIONAIS

Operadores efetivamente presentes nas 897 linhas do CSV (consulta somente-leitura):

| Predicado | Operadores testados | Operador original | Substituição observada |
|---|---|---|---|
| `object_lift_height_cm` | `{<, >=}` | `<` | apenas `<` → `>=` |
| `finger_contacts` | `{<, >=}` | `<` | apenas `<` → `>=` |
| `lateral_friction` | `{<=, >=}` | `<=` | apenas `<=` → `>=` |

**Nenhum outro operador foi testado em lugar nenhum da grade** — não há `>`, `==` nem `!=` em nenhuma das 897 linhas, para nenhum dos 3 predicados. Constatação direta dos dados, não inferência.

**Categoria "Operator-only" (só o operador muda, valor numérico == referência exata)** — 7 pontos, de `rq2_grid_perturbation_classification.csv`:

| Cenário | Given completo | Top-1 | Referência é Top-1? | Margem |
|---|---|---|---|---:|
| `R_H03_C02_F08` | `height<10 ∧ contacts<2 ∧ friction>=0.315` | Parallel Arm Lift | **NÃO** | −0.002940613026820027 |
| `R_H03_C07_F03` | `height<10 ∧ contacts>=2 ∧ friction<=0.315` | Lift Slip | sim | +0.13539272030651328 |
| `R_H03_C07_F08` | `height<10 ∧ contacts>=2 ∧ friction>=0.315` | Lift Slip | sim | +0.052614942528735664 |
| `R_H07_C02_F03` | `height>=10 ∧ contacts<2 ∧ friction<=0.315` | Lift Slip | sim | +0.13539272030651328 |
| `R_H07_C02_F08` | `height>=10 ∧ contacts<2 ∧ friction>=0.315` | Lift Slip | sim | +0.052614942528735664 |
| `R_H07_C07_F03` | `height>=10 ∧ contacts>=2 ∧ friction<=0.315` | Lift Slip | sim | +0.08750000000000013 |
| `R_H07_C07_F08` | `height>=10 ∧ contacts>=2 ∧ friction>=0.315` | Lift Slip | sim | +0.004722222222222294 |

Só **1 dos 7** flipa o Top-1 (`R_H03_C02_F08`, negação lógica completa das 3 cláusulas simultaneamente).

**Individual vs. combinado**: como o grid é fatorial em 3 dimensões, existem pontos com 1, 2 ou 3 operadores trocados simultaneamente. "Operator-only" (7 pontos) é o subconjunto raro onde o(s) operador(es) muda(m) mas o valor numérico fica cravado exatamente na referência; a maioria cai em "Combined" (683 pontos — operador **e** valor mudam juntos, 76% da grade).

**Mudança simultânea de operador e limiar**: sim, é o caso mais comum (683/897).

**Operador excluído — evidência ou não?** Não há comentário nem docstring explicando por que só `<`↔`>=` (e `<=`↔`>=`) foram escolhidos, e não, por exemplo, `<=`↔`<` (fronteira estrita/não-estrita) ou `==`. **Não identificado no repositório**: a justificativa de design para restringir a apenas a inversão de direção lógica. É plausível que a escolha reflita as duas direções logicamente opostas de cada predicado (`<` inverte para o complemento lógico exato `>=`, não para `>`), mas isso é leitura da estrutura dos dados, não algo documentado.

---

## 4. EXECUÇÃO E CONTROLE EXPERIMENTAL

- **Catálogo**: `5-experiments/run_similarity_only/configs/scenario_catalogue.json`, comparado byte-a-byte com `3-dejavu/configs/arm/scenario_catalogue.json` (produção, RQ1) — **idênticos**. Os 7 candidatos são todos relacionados a `LIFT_OBJECT` (nenhum candidato `TRANSPORT_OBJECT` no catálogo).
- **Pesos/config de similaridade**: `configs/weights_config.yaml` comparado byte-a-byte com `3-dejavu/configs/weights_config.yaml` — **idênticos**. `alpha=0.9`, `beta=0.1`, pesos de `given/when/then=1.0` cada.
- **When e Then**: checagem sobre os 922 objetos de `desired_scenario.json` — `when` é `"grasp_completed == 1"` em 100% dos casos, `then` é `"object_lift_height_cm >= 10 AND finger_contacts >= 2"` em 100% dos casos, sem exceção.
- **Como cada cenário é submetido**: `decompose_rq2_similarity.py::compute_decomposition()` instancia `DiagnosedScenario` a partir de cada item e chama `calculate_scenario_similarity()` real contra cada um dos 7 candidatos — Retriever-only, sem Manager/Managing/simulação física (confirmado também em `rq2_protocol_readonly_inspection.md`, linha 91).
- **Métricas registradas**: `final_similarity`, decomposição em `given/when/then_similarity`, componente paramétrico (Jaccard) e penalidade estrutural (Tversky) por cláusula, parâmetros compartilhados/faltantes/extras (`rq2_similarity_decomposition.csv`); agregados de rank/score/margem/flags de empate (`rq2_summary.csv`).
- **Quantas configurações**: Grupo R = 897 (900 nominal, 3 reaproveitadas); Grupo C = 16; Grupo A = 7; Grupo B = 3.

**Diferença entre protocolo antigo e o que produziu os resultados finais**: existe, mas **não afeta a RQ2.2**. Em sessão anterior de trabalho neste repositório, o Grupo B foi redesenhado de 4 pontos isolados (B1–B4 em paralelo) para 3 pontos cumulativos (B1→B2→B3). Nenhum arquivo relacionado à RQ2.2 (Grupo R ou Grupo C) foi alterado nesse processo. O pipeline foi re-executado depois dessa mudança; a última rodada (922 cenários) validou 6433 dos 6454 registros com divergência 0.0 contra o `.jsonl` de produção anterior — os 21 sem correspondência são exatamente o Grupo B novo.

---

## 5. RESULTADOS E RASTREABILIDADE

Fonte: `rq2_analysis/rq2_summary.csv` + `rq2_grid_perturbation_classification.csv`, gerados pela última execução de `decompose_rq2_similarity.py`.

### Grupo R — RQ2.2 (897 pontos nativos; tabela ponto-a-ponto completa está em `rq2_full_ranking.csv`/`rq2_summary.csv`, filtrando `experiment_id` iniciado em `R_`)

| Categoria | Total (897) | Total (900, reconciliado) | C_ref único Top-1 | Outro único Top-1 | Empate no topo | Margem mín. | Margem máx. |
|---|---:|---:|---:|---:|---:|---:|---:|
| Baseline | 0 | 1 | 1 | 0 | 0 | 0.07983716475095781 | 0.07983716475095781 |
| Threshold-only | 207 | 209 | 209 | 0 | 0 | 0.02011494252873558 | 0.1798371647509578 |
| Operator-only | 7 | 7 | 6 | 1 | 0 | −0.002940613026820027 | 0.13539272030651328 |
| Combined | 683 | 683 | 641 | 6 | 36 | −0.00766283524904221 | 0.16666666666666674 |
| **Total** | **897** | **900** | — | — | — | — | — |

**Candidatos que mudaram de Top-1 em relação a D_ref**: 7 pontos (Combined + o 1 já listado em Operator-only). Quem assume é sempre `reposition_and_regrip()` (candidato Parallel Arm Lift — Contact Loss, C2) — confirmado em `rq2_grid_direction_summary.json` e em `rq2_analysis.md` (linha 66: *"reposition_and_regrip(): 7 ponto(s) do grid"*).

### Grupo C — variação pura de `lateral_friction` (16 pontos)

Reproduzido de `rq2_analysis.md` (linhas 40-54), valores exatamente como no arquivo:

| ID | friction testado | Top-1 | score C_ref | 2º melhor | score 2º | margem |
|---|---:|---|---:|---|---:|---:|
| C01 | 0.340 | Lift Slip | 0.98333 | Parallel Arm Lift | 0.89655 | +0.08678 |
| C02 | 0.335 | Lift Slip | 0.98194 | Parallel Arm Lift | 0.89655 | +0.08539 |
| C03 | 0.330 | Lift Slip | 0.98056 | Parallel Arm Lift | 0.89655 | +0.08400 |
| C04 | 0.3275 | Lift Slip | 0.97986 | Parallel Arm Lift | 0.89655 | +0.08331 |
| C05 | 0.325 | Lift Slip | 0.97917 | Parallel Arm Lift | 0.89655 | +0.08261 |
| C06 | 0.3225 | Lift Slip | 0.97847 | Parallel Arm Lift | 0.89655 | +0.08192 |
| C07 | 0.320 | Lift Slip | 0.97778 | Parallel Arm Lift | 0.89655 | +0.08123 |
| C09 | 0.310 | Lift Slip | 0.97500 | Parallel Arm Lift | 0.89655 | +0.07845 |
| C10 | 0.305 | Lift Slip | 0.97361 | Parallel Arm Lift | 0.89655 | +0.07706 |
| C11 | 0.300 | Lift Slip | 0.97222 | Parallel Arm Lift | 0.89655 | +0.07567 |
| C12 | 0.290 | Lift Slip | 0.96944 | Parallel Arm Lift | 0.89655 | +0.07289 |
| C13 | 0.280 | Lift Slip | 0.96667 | Parallel Arm Lift | 0.89655 | +0.07011 |
| C14 | 0.270 | Lift Slip | 0.96389 | Parallel Arm Lift | 0.89655 | +0.06734 |
| C15 | 0.260 | Lift Slip | 0.96111 | Parallel Arm Lift | 0.89655 | +0.06456 |
| C16 | 0.255 | Lift Slip | 0.95972 | Parallel Arm Lift | 0.89655 | +0.06317 |

*(Falta `C08` na sequência — não existe no `desired_scenario.json`; não identificado no repositório por que esse índice foi pulado.)*

**Top-1 nunca muda no Grupo C** — Lift Slip permanece líder em toda a faixa 0.255–0.340, margem sempre positiva e decrescente conforme o limiar se afasta da referência (0.315), sem inversão em nenhum ponto.

**Divergência entre artefatos**: nenhuma encontrada — a validação automática do próprio pipeline (`validate_against_jsonl`) compara contra o `.jsonl` de produção mais recente e reporta divergência 0.0 para todos os pontos pré-existentes. **O artefato correspondente à avaliação final é `rq2_analysis/rq2_summary.csv` + `rq2_full_ranking.csv`** gerados pela última execução de `decompose_rq2_similarity.py`.

---

## 6. EMPATES E SELEÇÃO EFETIVA

- **Existem empates na RQ2.2**: sim, **36 casos**, todos na categoria "Combined" do Grupo R (`rq2_grid_direction_summary.json`, `tie_at_top: 36`). Zero empates em Threshold-only e Operator-only.
- **Candidatos empatados vs. candidato efetivamente retornado**: método responsável é `results.sort(key=lambda s: s["similarity_result"], reverse=True)` em `main.py:115` (mesmo padrão em `decompose_rq2_similarity.py`) — `sort`/`sorted` do Python são **estáveis**. Em empate, **o retornado como Top-1 é o que aparece primeiro na ordem de iteração do `scenarios` do `scenario_catalogue.json`** — sem critério de desempate semântico. Documentado em `rq2_protocol_readonly_inspection.md` (linha 88): *"Empates? Resolvidos pela ordem de declaração no JSON do catálogo... não há regra de desempate explícita/documentada"*, evidência em `dejavu.py:236-239`.
- **O script contabiliza empate como "vitória"?** Não — `build_summary()` calcula `is_exact_tie = (reference_sim == best_other_sim)` como campo separado de `top1_is_reference`. Os 36 empates do Grupo R aparecem com `top1_is_reference=True` **e** `is_exact_tie_at_top=True` simultaneamente — a retenção do Top-1 nesses 36 casos é um **artefato de ordem de declaração**, não vitória por margem.

---

## 7. SÍNTESE PARA A REDAÇÃO DO ARTIGO

### A. Desenho experimental — variação de limiares

O protocolo de limiares da RQ2.2 varia simultaneamente os três limiares numéricos do Given de referência (`object_lift_height_cm`, `finger_contacts`, `lateral_friction`) dentro de uma grade fatorial combinatória de 9×10×10 níveis (900 combinações nominais, 897 materializadas, 3 reaproveitadas de cenários idênticos de outros grupos sem recálculo). Cada nível foi construído por um procedimento nomeado por direção/região, documentado apenas descritivamente nos comentários de `desired_scenario.json`, sem script gerador auditável no repositório. Paralelamente existe um desenho de varredura unidimensional (Grupo C, 16 pontos) que varia só `lateral_friction`, mantendo os demais predicados fixos e o operador `<=` inalterado — sua filiação a RQ2.1 vs. RQ2.2 não está rotulada explicitamente em nenhum artefato.

### B. Desenho experimental — variação de operadores

Cada um dos três predicados teve seu operador testado em exatamente duas formas: a original e sua inversão lógica direta (`<`→`>=` para altura e contatos; `<=`→`>=` para atrito). Nenhuma outra substituição (`>`, `==`, `!=`, ou troca entre `<`/`<=`) foi testada em nenhum ponto do repositório. A variação de operador ocorre sempre dentro da mesma grade fatorial, produzindo 7 pontos "puros" (só operador muda) e 683 pontos "combinados" (operador e valor mudam juntos).

### C. Tabela consolidada

| Grupo | RQ rotulada no repo | Nº de configurações | Predicados variados por vez | Top-1 mudou | Empates |
|---|---|---:|---|---:|---:|
| A (omissão) | não rotulado "RQ2.1" no código | 7 | 1 cláusula removida | 3/7 | 0 |
| B (adição, cumulativo) | idem | 3 | cumulativo (+1/passo) | 0/3 | 0 |
| C (limiar de atrito) | não rotulado explicitamente | 16 | 1 (`lateral_friction`) | 0/16 | 0 |
| R (grade H×C×F) | **"RQ2.2" explícito em 3 arquivos** | 897 (900 reconciliado) | 3 simultâneos | 7/897 | 36/897 |

### D. Fenômenos observados que merecem discussão nos Results

1. **Assimetria de robustez por dimensão**: taxa de flip muito mais sensível a `finger_contacts` (8.0% no nível C02) do que a `object_lift_height_cm` ou `lateral_friction` isoladamente.
2. **Inversão de operador raramente muda o Top-1 sozinha**: dos 7 "Operator-only", só 1 (negação simultânea das 3 cláusulas) flipa.
3. **36 retenções de Top-1 por empate exato, não por margem** — quase 4% da grade retém o candidato de referência só por ordem de declaração no catálogo.
4. **Grupo C é monotônico e nunca flipa** — contraste limpo com o Grupo R: variação pura de 1 threshold parece estruturalmente mais estável que variação combinada de 3 predicados com possível inversão de operador.

### E. Limitações de interpretação a respeitar

- O Retriever nunca rejeita por baixa similaridade e sempre retorna um Top-1 — "recuperação bem-sucedida" significa recuperação de *algum* candidato, não de um candidato aceitável por critério absoluto.
- Apenas `apply_vacuum_assist()` tem execução física validada em trace real do RQ1; `heavy_lift()` está implementado mas nunca disparado; os outros 5 seriam *no-op* silencioso. A RQ2.2 mede exclusivamente estabilidade de ranking/score, não consequência funcional/física.
- Os 36 empates dependem de ordem de declaração no catálogo — um reordenamento trivial do JSON mudaria quais desses 36 casos "retêm" a referência, sem qualquer mudança física ou de métrica.
- A filiação RQ2.1/RQ2.2 do Grupo C permanece indefinida nos artefatos — decisão editorial, não constatação factual.

### F. Texto para Experimental Design (ACM TAAS)

> *RQ2.2 evaluates the sensitivity of DejaVu's similarity-based retrieval to perturbations of the numerical thresholds and relational operators already present in the reference Desired Adaptation Scenario's Given clause, while leaving the When, Then, candidate catalogue, and similarity weights unchanged from the RQ1 configuration. Starting from the validated reference $D_{\mathrm{ref}}$ (Given: $\mathit{object\_lift\_height\_cm} < 10 \land \mathit{finger\_contacts} < 2 \land \mathit{lateral\_friction} \leq 0.315$), we constructed a factorial grid over the three predicates, combining nine levels of the height threshold, ten levels of the contacts threshold, and ten levels of the friction threshold; for each predicate, exactly two relational operators were exercised — the original operator and its direct logical inversion ($<\!\to\!\geq$ for height and contacts, $\leq\!\to\!\geq$ for friction) — yielding 897 realized configurations out of a nominal $9\times10\times10=900$ (three points were structurally identical to configurations already present in other experimental groups and were reused without recomputation). Each configuration was submitted independently to the production `SimilarityBasedAdapter` retrieval routine, and the resulting ranking, Top-1 candidate, similarity score, and margin over the runner-up were recorded, together with an explicit tie flag distinguishing an exact-score tie at the top of the ranking from a strict, margin-based retention of the reference candidate. A complementary one-dimensional sweep of the friction threshold alone (sixteen points, sixteen values, operator held constant) was additionally evaluated to isolate the effect of a single-predicate magnitude change from the combined three-predicate perturbations of the main grid.*

---

## Resumo do que ficou marcado como "não identificado no repositório"

1. Script/fórmula exata geradora dos 897 níveis da grade (só existe descrição textual nos `comment`).
2. Filiação explícita RQ2.1 vs. RQ2.2 do Grupo C (variação pura de atrito).
3. Justificativa de design para restringir operadores testados apenas à inversão lógica direta (não `>`, `==`, `!=`, nem troca de fronteira estrita/não-estrita).
4. Por que o índice `C08` foi pulado na sequência do Grupo C.
