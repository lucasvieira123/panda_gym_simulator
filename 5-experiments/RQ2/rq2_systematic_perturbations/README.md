# RQ2 — Bateria B: perturbações sistemáticas do diagnóstico

Avaliação alternativa da RQ2. As imprecisões do Given de D0 são organizadas em quatro categorias:

- **A** — adição de parâmetro;
- **B** — omissão de parâmetro;
- **C** — mudança de operador relacional;
- **D** — mudança de limiar.

Nas categorias C e D, a intensidade é medida como distância de Jaccard entre a região original e a modificada, e as direções são opostas. As configurações passam pelo **Retriever de produção**, sem simulação física. A Bateria A (`../`) não foi alterada nem executada de novo.

- **Critérios e seleção:** [exploration/selection_rationale.md](exploration/selection_rationale.md), escrito antes do cálculo dos escores.
- **Comparação com a Bateria A e recomendação:** [comparison.md](comparison.md).

## Como reproduzir

Rode na raiz do projeto, com o `.venv`. As versões das bibliotecas estão em `../requirements.txt`; o Kaleido 1.x precisa do Chrome ou do Chromium.

```bash
.venv/Scripts/python.exe 5-experiments/RQ2/rq2_systematic_perturbations/scripts/explore_perturbations.py --design-only  # etapa 1: desenho e seleção, sem escores
.venv/Scripts/python.exe 5-experiments/RQ2/rq2_systematic_perturbations/scripts/explore_perturbations.py                # etapa 2: escores da exploração
.venv/Scripts/python.exe 5-experiments/RQ2/rq2_systematic_perturbations/scripts/run_selected_battery.py               # B0-B19 -> output/
.venv/Scripts/python.exe 5-experiments/RQ2/rq2_systematic_perturbations/scripts/plot_similarity.py                    # figura -> figures/
.venv/Scripts/python.exe 5-experiments/RQ2/rq2_systematic_perturbations/review/review_checks.py                       # verificações da revisão -> review/
.venv/Scripts/python.exe 5-experiments/RQ2/rq2_systematic_perturbations/review/verify_figure.py                       # figura x dados, a partir do SVG
```

**O que `verify_figure.py` confere.** Ele lê a figura exportada (`figures/rq2_similarity.svg`), e não o objeto do Plotly, e verifica a cadeia toda:

- **Diagnóstico.** O Given de cada configuração é a sua perturbação aplicada a D0.
- **Escores.** Os 100 escores, recalculados com o Retriever de produção, são os do CSV.
- **Marcadores.** Cada marcador desenhado está na coluna, na cor do candidato e na altura do seu escore.
- **Linhas.** Cada linha passa pelos marcadores do seu candidato.
- **Números.** Cada número é o escore do ponto a que o leitor o liga: o da outra ponta da linha de chamada, ou o marcador mais próximo.

O resultado, por configuração e candidato, fica em `review/figure_verification.csv`.

As verificações da revisão (`review/`) **não fazem parte da bateria** e não alteram nenhum arquivo dela. São três:
- quais pares de predicados o Jaccard comparou;
- a sensibilidade dos escores e rankings das Baterias A e B à convenção de inteiros (comprimento do Retriever × cardinalidade discreta);
- uma checagem exploratória das 214 combinações de três perturbações isoladas.

A checagem de ordem 3 mostra que uma mudança no Top-3 é possível com três modificações; ela não estima frequência. O resultado de cada verificação está no adendo de [exploration/selection_rationale.md](exploration/selection_rationale.md).

**O que é determinístico e o que é conferido:**
- a exploração leva cerca de 20 s e a bateria cerca de 10 s, e rodar de novo dá os mesmos arquivos;
- `run_selected_battery.py` para se B0 não reproduzir exatamente o D0 da Bateria A (`../output/results.csv`), ou se algum escore diferir do calculado na exploração;
- `plot_similarity.py` confere que cada ponto é o escore do CSV, com a posição do CSV no hover. Todos os marcadores são cheios: a figura não codifica o Top-3, que está em `output/rankings.csv`.

**Reutilização da Bateria A:**
- o código importa `../run_rq2.py`, que contém o Retriever de produção, a decomposição por cláusula e as métricas de ranking;
- importa também o estilo de `../generate_rq2_plotly.py`;
- lê D0 de `../diagnoses.json`.

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `scripts/perturbations.py` | Referência, operadores das quatro categorias, intensidade, direção, classe do parâmetro, avaliação de cada predicado e a seleção (`SELECTION`). Não lê escores. A avaliação cobre satisfatibilidade, consistência com a observação, relação com a violação representada, viabilidade na aplicação, mensurabilidade, origem e plausibilidade |
| `scripts/explore_perturbations.py` | Etapa 1: desenho e seleção. Etapa 2: escores de todas as perturbações satisfatíveis que o Retriever consegue medir |
| `scripts/run_selected_battery.py` | Roda B0–B19, confere B0 contra a Bateria A e escreve `output/` |
| `scripts/plot_similarity.py` | Figura no estilo da Bateria A |
| `exploration/exploratory_diagnoses.csv` | As 130 perturbações exploradas. Para cada uma: categoria, predicados original e modificado, parâmetros afetados e sua classe, componente de origem, intensidade, direção, Given, as dimensões da avaliação, coincidência com candidatos, seleção e motivo de exclusão |
| `exploration/exploratory_scores.csv` | Escores, ranking e mudanças das 128 perturbações que recebem escore. Ficam de fora o Given vazio e a igualdade em parâmetro contínuo, que o Retriever não mede |
| `exploration/selection_rationale.md` | Critérios, classes de parâmetros, bateria e exclusões (documento original, anterior aos escores), seguidos do adendo de 2026-11-12 com as correções da revisão |
| `review/review_checks.py` | Verificações da revisão, separadas da bateria |
| `review/metric_pairs.csv` | Tipos de par de predicados comparados pelo Jaccard (bateria e exploração) e pares com Jaccard acima de 1, igualdade contra intervalo ou região de comprimento zero |
| `review/integer_convention_scores.csv`, `review/integer_convention_rankings.csv` | Escores e rankings das Baterias A (D0–D19, numeração do artigo) e B (B0–B19) na medida do Retriever e com cardinalidade discreta para inteiros |
| `review/order3_combinations.csv` | As 214 combinações de três perturbações isoladas da B, com rankings e escores nas duas convenções. É exploratória e não faz parte da bateria |
| `review/review_summary.json` | Resumo das verificações |
| `output/selected_diagnoses.csv` | Desenho de B0–B19 |
| `output/similarity_scores.csv` | Por configuração e candidato: escore, posição, variação em relação a B0 e as cláusulas (S_param, penalidade, parâmetros compartilhados e exclusivos, When, Then) |
| `output/rankings.csv` | Por configuração: ranking, Top-1, Top-2, Top-3, mudanças em relação a B0, posição de C1, margem, τ de Kendall |
| `output/interactions.csv` | Combinações: variação conjunta × soma das variações isoladas, por candidato |
| `output/summary.json` | Contagens e as comparações controladas (direção, intensidade, classe) |
| `figures/rq2_similarity.{pdf,svg,png,html}` | Figura (o PNG tem 3168 px de largura). Usa a notação do artigo: a configuração Bk dos CSVs aparece como Dk. Cada escore aparece em cinza, sem o zero inicial, posicionado para que fique claro de qual ponto é: o rótulo fica junto do próprio marcador, e qualquer outro marcador fica pelo menos 2,5 vezes mais longe. Nenhum rótulo toca uma linha, um marcador, a borda da faixa ou outro rótulo, e em cada coluna eles seguem a ordem dos escores. Onde não há posição clara junto ao marcador (marcadores quase sobrepostos num feixe de linhas, interior de picos), o número fica num espaço livre próximo, com um traço fino até o ponto. A análise de cada rótulo está em `rq2_similarity_value_labels.csv`. O gráfico é 60 px mais alto que o da Bateria A, para dar espaço aos rótulos. `plot_similarity.py --no-values` gera a figura sem eles |
| `comparison.md` | Comparação crítica entre as Baterias A e B, com a recomendação |

**Sobre a pasta de resultados:** os resultados estão em `output/`, e não em `results/` como sugeria a estrutura pedida, porque o `.gitignore` do projeto ignorava `5-experiments/**/results/` quando a bateria foi criada.

## Bateria B

Cada configuração é derivada de B0 de forma independente; só o Given muda.

| ID | Cat. | Perturbação | Intensidade / direção |
|---|---|---|---|
| B0 | — | `object_lift_height_cm < 10 AND finger_contacts < 2 AND lateral_friction <= 0.1425` | referência (= D0) |
| B1 | A | + `object_shape_irregular == 1` (C3, C4) | 1 parâmetro |
| B2 | A | + `grasp_alignment_error_cm > 1` (C3) | 1 parâmetro |
| B3 | A | + `planned_lift_acceleration_m_s2 > 2` (C5) | 1 parâmetro |
| B4 | A | + `objects_object_1_mass > 0.5` (nenhum) | 1 parâmetro |
| B5 | B | − `lateral_friction` (distintivo, C1) | 1 parâmetro |
| B6 | B | − `finger_contacts` (compartilhado) | 1 parâmetro |
| B7 | B | − `object_lift_height_cm` (compartilhado) | 1 parâmetro |
| B8 | C | `lateral_friction < 0.1425` | d = 0 (controle) |
| B9 | C | `lateral_friction > 0.1425` | d = 1, disjunto; exclui o atrito observado (0,14) |
| B10 | D | `lateral_friction <= 0.1069` | d = 0,25, restritivo; exclui o atrito observado |
| B11 | D | `lateral_friction <= 0.0356` | d = 0,75, restritivo; exclui o atrito observado |
| B12 | D | `lateral_friction <= 0.19` | d = 0,25, permissivo |
| B13 | D | `lateral_friction <= 0.57` | d = 0,75, permissivo |
| B14 | D | `object_lift_height_cm < 6` | d = 0,44, restritivo (0,40 com cardinalidade discreta) |
| B15 | D | `object_lift_height_cm < 19` | d = 0,50, permissivo (0,47 com cardinalidade discreta) |
| B16 | A+A | B2 + B3 | 2 mudanças |
| B17 | B+B | B5 + B6 | 2 mudanças |
| B18 | A+B | B5 + B4 | 2 mudanças |
| B19 | A+D | B12 + B1 | 2 mudanças |
