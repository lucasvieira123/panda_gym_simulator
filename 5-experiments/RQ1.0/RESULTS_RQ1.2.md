# Cláusula `lateral_friction` diagnosticada — experimentos 09 a 25

Extração da cláusula `lateral_friction <= xxx` do bloco `DIAGNOSE` nos traces do DejaVu (`outputs/dejavu_traces/`), para cada execução da varredura de friction (`5-experiments/RQ1.1/results/`).

## Metodologia

1. Para cada pasta de experimento (`09_0_18` a `25_0_010`), localizado o único arquivo de trace em `outputs/dejavu_traces/`.
2. Em cada trace, localizada a linha `│  Nome  : diagnosed_TRANSPORT_OBJECT_unanticipated` ou `│  Nome  : diagnosed_LIFT_OBJECT_unanticipated` (nome real do cenário é `LIFT_OBJECT`, não `LIFT`).
3. Extraída a linha `│  Given :` imediatamente abaixo desse `Nome`, e dela o valor de `lateral_friction <= xxx`.
4. Cruzado com `experiment.json` de cada pasta para confirmar o `lateral_friction` configurado no ambiente (consistente com o nome da pasta).

## Tabela

| Execução | Friction configurado | Cenário diagnosticado | Cláusula `lateral_friction` diagnosticada |
|---|---:|---|---|
| 09_0_18 | 0.18 | diagnosed_TRANSPORT_OBJECT_unanticipated | `<= 0.34` |
| 10_0_17 | 0.17 | diagnosed_TRANSPORT_OBJECT_unanticipated | `<= 0.335` |
| 11_0_16 | 0.16 | diagnosed_TRANSPORT_OBJECT_unanticipated | `<= 0.33` |
| 12_0_155 | 0.155 | diagnosed_TRANSPORT_OBJECT_unanticipated | `<= 0.3275` |
| 13_0_150 | 0.15 | diagnosed_TRANSPORT_OBJECT_unanticipated | `<= 0.325` |
| 14_0_145 | 0.145 | diagnosed_TRANSPORT_OBJECT_unanticipated | `<= 0.3225` |
| 15_0_140 | 0.14 | diagnosed_LIFT_OBJECT_unanticipated | `<= 0.32` |
| 16_0_135 | 0.135 | diagnosed_LIFT_OBJECT_unanticipated *(reclassificado, ver nota)* | `<= 0.3175` *(estimado, ver nota)* |
| 17_0_130 | 0.13 | diagnosed_LIFT_OBJECT_unanticipated | `<= 0.315` |
| 18_0_120 | 0.12 | diagnosed_LIFT_OBJECT_unanticipated | `<= 0.31` |
| 19_0_110 | 0.11 | diagnosed_LIFT_OBJECT_unanticipated | `<= 0.305` |
| 20_0_100 | 0.10 | diagnosed_LIFT_OBJECT_unanticipated | `<= 0.30` |
| 21_0_080 | 0.08 | diagnosed_LIFT_OBJECT_unanticipated | `<= 0.29` |
| 22_0_060 | 0.06 | diagnosed_LIFT_OBJECT_unanticipated | `<= 0.28` |
| 23_0_040 | 0.04 | diagnosed_LIFT_OBJECT_unanticipated | `<= 0.27` |
| 24_0_020 | 0.02 | diagnosed_LIFT_OBJECT_unanticipated | `<= 0.26` |
| 25_0_010 | 0.01 | diagnosed_LIFT_OBJECT_unanticipated | `<= 0.255` |

## Nota — reclassificação e estimativa em `16_0_135`

### O que o trace bruto realmente diagnosticou

O trace de `16_0_135` tem um único bloco `DIAGNOSE`, com cenário `diagnosed_TRANSPORT_OBJECT_unanticipated`, e a cláusula extra adicionada pela árvore de decisão foi `finger_contacts <= 1.0` — não uma condição de `lateral_friction`. Esse é o mesmo experimento marcado como **ANÔMALO** em `RESULTS_RQ1.1.md`: no step 22 a percepção registra 12 cm de altura e 2 contatos, no step 23 já registra 7 cm e 0 contatos, mas a SM só emite UNSAT no step 38 (`ERR_23`, transport), quando na verdade a perda de altura e contatos aconteceu na fase de lift. Ou seja, a classificação `TRANSPORT_OBJECT` é um artefato da defasagem de um tick entre percepção e transição, não o cenário fisicamente correto.

### Reclassificação

Dado que a perda de altura/contatos ocorreu durante o `lift` (não o `transport`), o cenário correto para efeito de análise é `diagnosed_LIFT_OBJECT_unanticipated`, em linha com os experimentos vizinhos (15 e 17, que também caem em `ERR_19`/lift).

### Estimativa do valor de `lateral_friction`

O valor `<= 0.3175` **não vem do trace** (o pipeline de similaridade travou nesse experimento por um bug `float → int`, então a árvore nunca chegou a diagnosticar uma cláusula de `lateral_friction` de fato). Ele foi estimado a partir do padrão exato observado nos outros 16 experimentos válidos.

Ajustando os pares (friction configurado, `lateral_friction` diagnosticado) da tabela, todos os 16 pontos — tanto os diagnosticados como `TRANSPORT_OBJECT` quanto os `LIFT_OBJECT` — obedecem exatamente à mesma reta:

```
lateral_friction_diagnosticado = 0.5 × lateral_friction_configurado + 0.25
```

(erro nulo em todos os 16 pontos, de 0.18 a 0.01). Aplicando a fórmula a 0.135:

```
0.5 × 0.135 + 0.25 = 0.3175
```

Esse valor é, portanto, uma **inferência por interpolação linear exata do padrão observado**, não uma extração do log. Deve ser tratado como estimativa para preencher a lacuna causada pelo bug do experimento 16, e revalidado quando `16_0_135` for reexecutado após a correção do parser `float → int` no pipeline de similaridade.
