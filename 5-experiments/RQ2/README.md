# RQ2 — Retrieval Robustness to Unanticipated Scenario Analysis Inaccuracies

Esta bateria tem 20 Desired Adaptation Scenarios: a referência D0, 11 modificações isoladas (D1–D11) e 8 combinadas (D12–D19). Todos passam pelo Retriever de produção do DejaVú, sem simulação física.

D0 é o diagnóstico gerado para `LIFT_OBJECT` no run μ = 0,140 da RQ1.2. As demais configurações mudam só o Given de D0, cada uma derivada de forma independente.

A interpretação está em [analysis.md](analysis.md), e as tabelas geradas em [output/summary.md](output/summary.md). A figura do artigo é `figures/rq2_similarity_plotly`, gerada por `generate_rq2_plotly.py`.

## Como reproduzir

Na raiz do projeto, use o `.venv` do projeto. As versões usadas estão em `requirements.txt` (Python 3.13.5); para um ambiente novo, `pip install -r 5-experiments/RQ2/requirements.txt`. O Kaleido 1.x precisa do Chrome ou do Chromium para exportar PDF, SVG e PNG.

```bash
.venv/Scripts/python.exe 5-experiments/RQ2/run_rq2.py      # bateria -> output/
.venv/Scripts/python.exe 5-experiments/RQ2/plot_rq2.py     # figuras -> figures/ (lê output/)
.venv/Scripts/python.exe 5-experiments/RQ2/generate_rq2_plotly.py   # figura final do artigo -> figures/
.venv/Scripts/python.exe -m unittest discover -s 5-experiments/RQ2 -p "test_*.py"
```

A execução é determinística: rodar de novo produz os mesmos CSVs, e um dos testes confere isso. A bateria leva cerca de 25 s; a maior parte do tempo vai para a conversão para DNF feita pelo sympy.

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `diagnoses.json` | Especificação das 20 configurações: D0 como foi registrado na RQ1.2 (com a origem e o ranking gravado no run) e as mudanças de cada Dk sobre o Given de D0 |
| `inputs/` | Cópias do catálogo e dos pesos usados e dos arquivos do run de origem de D0, com hashes; ver [inputs/README.md](inputs/README.md) |
| `requirements.txt` | Versões das bibliotecas usadas |
| `exploratory_reference.json` | Valores e domínios da reprodução independente das equações, usados **só para comparação** |
| `run_rq2.py` | Executa a bateria com `SimilarityBasedAdapter` (filtro de When e `calculate_scenario_similarity`), ordena como `dejavu.py` e decompõe cada escore com os helpers de `dejavu_similarity.py`, conferindo a decomposição contra o escore de produção |
| `plot_rq2.py` | Gera as figuras a partir de `output/results.csv` e `output/rankings.csv` |
| `generate_rq2_plotly.py` | Gera a figura final do artigo a partir dos mesmos CSVs. Antes de exportar, valida os dados e a figura: mapeamento da numeração do artigo para os IDs da bateria, 100 escores, posição de D0, mudanças do Top-1 e do Top-3 nos CSVs, valores plotados iguais aos dos CSVs e o traçado das linhas |
| `test_rq2.py` | 22 testes das propriedades da bateria, incluindo a origem de D0 e os insumos copiados em `inputs/` |
| `analysis.md` | Interpretação matemática e semântica |

Saídas em `output/`:

| Arquivo | Conteúdo |
|---|---|
| `results.csv` | Uma linha por diagnóstico e candidato: escore, posição, variação em relação a D0, e S_param, P e S_cond de cada cláusula, com os parâmetros compartilhados, os que só o diagnóstico declara e os que só o candidato declara |
| `rankings.csv` | Uma linha por diagnóstico: ranking, Top-1, Top-3, margem entre Top-1 e Top-2, empates, mudanças em relação a D0, tau de Kendall e os dois candidatos que o DejaVú tentaria (`MAX_ATTEMPTS = 2`) |
| `jaccard.csv` | Cada par de predicados comparado: regiões e Jaccard |
| `comparison.csv` | Escores reais comparados à reprodução independente, e escores com os domínios da reprodução (análise de sensibilidade) |
| `domains.csv` | Domínios usados (os do catálogo) comparados aos da reprodução |
| `friction_domain_check.csv` | D0 e D2 com outros limites do domínio de atrito |
| `integration_replay.csv` | Rankings gravados nas baterias finais da RQ1.1 e da RQ1.2, recalculados; só é gerado quando as pastas `results/`, que não são versionadas, existem |
| `summary.md` | Tabelas geradas a partir dos resultados |

Figuras em `figures/`, em PDF, PNG e SVG (o HTML interativo não é versionado):

- `similarity_scores`: similaridade de C1–C5 por diagnóstico, na ordem D0–D19;
- `candidate_rankings`: posição de cada candidato no ranking por diagnóstico;
- `rq2_similarity_plotly`: figura final do artigo. É lida a partir de D0, que fica numa faixa central. O eixo X segue a ordem D11…D1 | D0 | D12…D19: as modificações isoladas ficam espelhadas à esquerda (D1 encostado em D0) e as combinadas à direita, sem subgrupos. As linhas de cada candidato passam pelas 20 configurações, D0 inclusive, só como guia de leitura. Com `--lines within-blocks`, elas ficam dentro de cada bloco; com `--lines none`, a figura é um scatter sem linhas. O marcador preenchido indica que o candidato está no Top-3. **A figura usa a numeração do artigo, que difere dos IDs da bateria** (`diagnoses.json` e CSVs). O script deriva o mapeamento comparando as modificações, confere o Given gravado no `results.csv` e grava a correspondência em `rq2_similarity_plotly_labels.csv`;
- `similarity_rankings`: a figura de ranking com a similaridade no eixo Y. O marcador preenchido indica que o candidato está no Top-3, e o vazado, que está na 4ª ou 5ª posição. Acima ficam o Top-1 e a mudança do conjunto do Top-3.

O eixo Y de `similarity_scores` vai de 0,3 a 1. Depois do filtro de When, nenhum escore fica abaixo de 1/3, que aparece marcado na figura. Para a escala completa, mude `Y_RANGE` para `(0, 1)` em `plot_rq2.py`.

## Observações

- Nenhum arquivo de produção foi alterado. O catálogo, os pesos e os domínios são os de `3-dejavu/configs/`, copiados em `inputs/dejavu_configs/`.
- O código do Retriever (`3-dejavu/src/similarity/` e `similarity_based_adapter.py`) é o do commit `a1e4cd1`, sem alterações locais. Na árvore de trabalho, `dejavu.py` e `retry_policy.py` tinham mudanças não commitadas que não afetam a RQ2: daqui só se importa `MAX_ATTEMPTS`, que não mudou.
- Os domínios da reprodução independente só entram na análise de sensibilidade (`comparison.csv`, coluna `spec_domains`), identificada como tal.
- A pasta `5-experiments/run_similarity_only/` contém a versão anterior da RQ2, com outro catálogo (7 candidatos) e D_ref com atrito 0,315. Ela não é usada aqui.
