# RQ2 — Robustez da recuperação a imprecisões do diagnóstico

*How do inaccuracies in the Desired Adaptation Scenario affect the similarity scores and top-k ranking of candidate adaptations retrieved by DejaVú?*

Esta análise interpreta os resultados de `run_rq2.py`. As tabelas completas estão em `output/summary.md` e nos CSVs de `output/`. Os valores estão arredondados a 4 casas, e todos vêm do Retriever de produção.

A RQ2 mede só a **recuperação**, isto é, os escores e a ordenação dos candidatos. Ela não avalia o sucesso físico da adaptação.

## 1. O que foi executado

| Item | No repositório |
|---|---|
| Retriever | `SimilarityBasedAdapter.calculate_similarity` (`3-dejavu/src/similarity_based_adapter.py`): filtro de When (`similarity/when_filter.py`) e depois `calculate_scenario_similarity` (`similarity/dejavu_similarity.py`) por candidato |
| Ordenação e Top-1 | a mesma instrução do estágio RETRIEVE de `dejavu.py` (`similarities.sort(key=…similarity_result, reverse=True)`) e `SimilarityBasedAdapter.recommend` |
| Estruturas GWDT | `DiagnosedScenario` e `CandidateScenario` (`scenario/`), com cláusulas `ConditionalExpression` |
| Catálogo | `3-dejavu/configs/arm/scenario_catalogue.json`, igual à especificação da RQ2 (C1–C5 de lift; C6–C8 de transporte, excluídos pelo filtro de When) |
| Pesos | `3-dejavu/configs/weights_config.yaml`: α = 0,9, β = 0,1, `given = when = then = 1`; os `parameter_weights` só têm nomes de exemplo (`parameter_1`, `parameter_n`), logo w_p = 1 para todos os parâmetros |
| Domínios | `monitored_parameters` do catálogo (seção 5) |

**D0 é o diagnóstico efetivamente gerado.** O evento `diagnosis` do run 0,140 da RQ1.2 (`RQ1.2/sequencia/results/principal/15_0_140`, episódio 1, step 23, cenário ativo `LIFT_OBJECT`) registra:
- Given: `(object_lift_height_cm < 10) AND (finger_contacts < 2) AND lateral_friction <= 0.1425`;
- When: `grasp_completed == 1`;
- Then: `object_lift_height_cm >= 10 AND finger_contacts >= 2`.

Esse diagnóstico é o da especificação. O Do registrado pelo Diagnoser é o marcador `"TBD"`, que corresponde ao `to_be_retrieved`; a cláusula Do não entra no cálculo. Os parênteses não mudam os escores (há um teste para isso).

O D0 reproduz bit a bit o ranking que o DejaVú gravou durante aquele run:

| | C1 | C2 | C3 | C4 | C5 |
|---|---:|---:|---:|---:|---:|
| Escore | 0,9126 | 0,8966 | 0,8318 | 0,7076 | 0,5903 |

**Integração.** Além da bateria, o runner recalculou os 20 rankings gravados durante as baterias finais (15 da RQ1.1 e 5 da RQ1.2), com o catálogo e os pesos de cada run. Os 20 saem na mesma ordem, com diferença de escore igual a zero. Isso confirma que a execução isolada e o Retriever dentro do pipeline são o mesmo cálculo. Não foram executadas simulações físicas da RQ2.

## 2. A métrica no código, comparada às equações

As equações 5.1–5.4 da especificação correspondem à implementação, com os seguintes detalhes do código.

- **Jaccard por comprimento de região.**
  - O código mede o comprimento hi − lo da região, sem contar valores. Para `int`, a desigualdade estrita usa deslocamento 1: `x < 10` é [0, 9] e `x > 1` é [2, max]. Para `float`, o deslocamento é 1e-9.
  - Por isso `finger_contacts < 2` mede 1 (o intervalo [0, 1]), não 2 valores. Nesta bateria isso não pesa, porque os predicados de contatos do diagnóstico e dos candidatos são sempre idênticos.
- **Igualdade.**
  - Dois predicados `==` dão 1 se o valor coincide e 0 se não coincide.
  - Um `==` contra uma região dá 1/|região|.
  - Na bateria só ocorre o primeiro caso: `object_shape_irregular == 1`, `payload_swing_risk == 1` e o When.
- **Arredondamento.** O Jaccard é arredondado a 5 casas (`round(…, 5)`), o que gera diferenças da ordem de 1e-6 em relação às frações exatas. A menor distância entre posições vizinhas da bateria é 0,0041, então o arredondamento não altera nenhuma ordem.
- **S_param** é a média, com pesos, só dos parâmetros compartilhados.
- **Penalização P_k** é 1 − Tversky sobre os **nomes** dos parâmetros. O resultado de cada cláusula é `max(0, S_param − P_k)`, e o escore final é a média das três cláusulas com peso 1.
- **Casos não exercitados pela bateria** (o que segue é leitura do código):
  - Uma cláusula com parâmetros, mas nenhum compartilhado, dá S_param = 0 e P = 1, logo 0.
  - Se as duas cláusulas não tiverem nenhum parâmetro, `_tversky_similarity` divide 0 por 0.
  - Um parâmetro repetido na mesma cláusula fica só com a última ocorrência no pareamento.
- **Empates.** A ordenação é estável, então candidatos empatados mantêm a ordem do catálogo. Não há regra de desempate semântica. Um teste confirma isso com um candidato duplicado.
- **O Retriever nunca rejeita.** Sempre há um Top-1. Após o filtro de When, todo candidato tem S_When = 1, logo nenhum escore fica abaixo de 1/3.

## 3. Resultado geral

| D | Modificação | C1 | C2 | C3 | C4 | C5 | Top-3 | Margem Top-1/Top-2 |
|---|---|---:|---:|---:|---:|---:|---|---:|
| D0 | referência | **0,9126** | 0,8966 | 0,8318 | 0,7076 | 0,5903 | C1 C2 C3 | 0,0160 |
| D1 | atrito ≤ 0,25 | **0,9425** | 0,8966 | 0,8318 | 0,7076 | 0,5903 | C1 C2 C3 | 0,0459 |
| D2 | atrito ≥ 0,1425 | 0,8873 | **0,8966** | 0,8318 | 0,7076 | 0,5903 | C2 C1 C3 | 0,0092 |
| D3 | − atrito | 0,9683 | **1,0000** | 0,9198 | 0,7956 | 0,6783 | C2 C1 C3 | 0,0317 |
| D4 | + geometria | 0,8357 | 0,8421 | **0,8769** | 0,7426 | 0,5419 | C3 C2 C1 | 0,0348 |
| D5 | + desalinhamento | 0,8357 | 0,8421 | **0,8769** | 0,6593 | 0,5419 | C3 C2 C1 | 0,0348 |
| D6 | + aceleração | 0,8357 | **0,8421** | 0,7835 | 0,6593 | 0,6545 | C2 C1 C3 | 0,0064 |
| D7 | + oscilação | 0,8357 | **0,8421** | 0,7835 | 0,6593 | 0,6545 | C2 C1 C3 | 0,0064 |
| D8 | + massa | 0,8357 | **0,8421** | 0,7835 | 0,6593 | 0,5419 | C2 C1 C3 | 0,0064 |
| D9 | altura < 12 | **0,8924** | 0,8662 | 0,8621 | 0,6773 | 0,6078 | C1 C2 C3 | 0,0261 |
| D10 | altura < 20 | **0,8541** | 0,8088 | 0,7920 | 0,6199 | 0,6780 | C1 C2 C3 | 0,0453 |
| D11 | − contatos | **0,8610** | 0,8333 | 0,7380 | 0,6441 | 0,4630 | C1 C2 C3 | 0,0276 |
| D12 | + geometria + desalinhamento | 0,7876 | 0,8085 | **0,9040** | 0,6967 | 0,5113 | C3 C2 C1 | 0,0955 |
| D13 | − atrito + geometria + desalinhamento | 0,8217 | 0,8421 | **0,9653** | 0,7426 | 0,5419 | C3 C2 C1 | 0,1232 |
| D14 | + aceleração + oscilação | 0,7876 | **0,8085** | 0,7528 | 0,6286 | 0,6912 | C2 C1 C3 | 0,0209 |
| D15 | − atrito + aceleração + oscilação | 0,8217 | **0,8421** | 0,7835 | 0,6593 | 0,7524 | C2 C1 C3 | 0,0204 |
| D16 | altura < 20 + aceleração + oscilação | 0,7291 | 0,7208 | 0,7130 | 0,5409 | **0,7351** | C5 C1 C2 | 0,0060 |
| D17 | − atrito + altura < 20 + aceleração + oscilação | 0,7340 | 0,7544 | 0,7436 | 0,5715 | **0,7963** | C5 C2 C3 | 0,0419 |
| D18 | altura < 12 + geometria + desalinhamento | 0,7674 | 0,7782 | **0,9192** | 0,6765 | 0,5288 | C3 C2 C1 | 0,1410 |
| D19 | − atrito + altura < 12 + geometria + desalinhamento | 0,7914 | 0,8118 | **0,9804** | 0,7224 | 0,5595 | C3 C2 C1 | 0,1686 |

**Mudanças em relação a D0, entre as 19 modificações:**
- **Top-1:** muda em 15. Fica igual só em D1, D9, D10 e D11.
- **Ordem do Top-3:** muda em 15.
- **Composição do Top-3:** muda em 2.
  - Em D16, C5 entra e C3 sai.
  - Em D17, C5 entra e C1 sai.
- **Ordem completa:** muda em 16; D10 só troca C4 e C5 nas posições 4 e 5.

**Empates e margens:**
- Não há empates, nem exatos nem abaixo de 1e-9.
- A menor margem entre Top-1 e Top-2 é a de D16 (0,0060).

Essas proporções descrevem só esta bateria, cujas modificações foram escolhidas à mão. Não são estimativas da robustez do Retriever em geral.

**Quem ocupa o Top-1 nas 20 configurações:**
- C2 em 7;
- C3 em 6;
- C1 em 5;
- C5 em 2;
- C4 em nenhuma.

## 4. Mecanismo geral: o Given decide, e o Then dá uma vantagem fixa a cada candidato

Na bateria, When e Then são sempre os de D0. Por isso, S_When e S_Then de cada candidato são **constantes** nas 20 configurações (há um teste para isso), e toda variação vem do Given:

`Sim(D, C) = (S_Given(D, C) + S_When(C) + S_Then(C)) / 3`

| Candidato | S_When | S_Then | Por quê | Escore máximo (S_Given = 1) |
|---|---:|---:|---|---:|
| C1 | 1 | 0,9524 | Then de C1 tem `object_secured` a mais (β): P = 1 − 2/2,1 | 0,9841 |
| C2 | 1 | 1,0000 | Then idêntico ao do diagnóstico | 1,0000 |
| C3 | 1 | 0,9413 | `object_secured` a mais e altura ≥ 12 (J = 88/90) | 0,9804 |
| C4 | 1 | 0,4778 | falta `finger_contacts` (α) e sobra `object_secured` (β): P = 0,5 | 0,8259 |
| C5 | 1 | 0,3889 | falta `finger_contacts`, sobra `payload_oscillation_deg`, altura ≥ 20 (J = 80/90) | 0,7963 |

Assim, **Ci fica acima de Cj quando S_Given(Ci) − S_Given(Cj) > S_Then(Cj) − S_Then(Ci)**. As vantagens de Given necessárias para os pares que decidem a bateria são:

| Para ficar acima de… | C1 precisa de | C3 precisa de | C5 precisa de |
|---|---:|---:|---:|
| C2 | +0,0476 | +0,0587 | +0,6111 |
| C1 | — | +0,0111 | +0,5635 |
| C3 | −0,0111 | — | +0,5524 |

Essa decomposição explica todas as trocas de posição. Três consequências se destacam:
- **C2 tem o Then idêntico ao do diagnóstico.** Qualquer modificação que reduza a vantagem de Given de C1 para menos de 0,0476 coloca C2 em primeiro.
- **C4 nunca chega ao Top-3.** O Then de C4 deixa seu escore máximo em 0,8259, abaixo de C1, C2 e C3 em quase toda a bateria.
- **C5 depende de mudanças grandes no Given.** Só chega ao Top-1 quando o Given dos demais é derrubado por várias penalizações ao mesmo tempo.

## 5. Contrastes

As células abaixo são S_Given = S_param − P, extraídas de `output/summary.md`.

### A. D0 × D3 — omitir o atrito

Em D0, o atrito tem dois papéis ao mesmo tempo:
- **Para C1**, é o único par imperfeito: J = 0,1425/0,4 = 0,35625, o que leva o S_param a 0,7854, sem penalização.
- **Para C2**, é o único desencontro estrutural: um parâmetro só do diagnóstico, que custa α e dá P = 1 − 2/2,9 = 0,3103, levando o S_Given a 0,6897.

A vantagem de Given de C1 é 0,0957, maior que o 0,0476 exigido, e C1 fica em primeiro por (0,0957 − 0,0476)/3 = 0,0160.

Em D3, o Given do diagnóstico passa a ser exatamente o de C2 (altura e contatos), e S_Given(C2) = 1. Com o Then também idêntico, **Sim(D3, C2) = 1,0**.

C1 também sobe, de 0,9126 para 0,9683: o par de atrito parcial sai da média e S_param vira 1. Mas o atrito agora existe só no candidato, o que custa β e dá P = 0,0476, logo S_Given(C1) = 0,9524. C1 ganha 0,0557, enquanto C2 ganha 0,1034. O motivo é a assimetria α = 0,9 contra β = 0,1: um parâmetro presente só no diagnóstico custa nove vezes mais que um presente só no candidato.

C3, C4 e C5 também sobem, porque deixam de pagar α pelo atrito que não declaram.

Semanticamente, ao perder a pista que distingue o baixo atrito, o diagnóstico passa a coincidir com a recuperação genérica por força de preensão.

### B. D0 × D2 — inverter o operador do atrito

O parâmetro continua presente, então a estrutura não muda: as penalizações de todos os candidatos são as mesmas de D0. Muda só a região, que passa de [0; 0,1425] para [0,1425; 2]. Como só C1 declara atrito, **só o escore de C1 se altera**:
- O J vai de 0,35625 para 0,12875, isto é, a interseção [0,1425; 0,4] (0,2575) dividida pela união [0, 2].
- O S_Given(C1) cai de 0,7854 para 0,7096.
- A vantagem de C1 sobre C2 vira 0,0199, menor que 0,0476. C2 fica em primeiro, por 0,0092.

Dois pontos merecem atenção:
1. **Manter o parâmetro não preserva sua contribuição.** A inversão contradiz o "baixo atrito" de C1, mas a região invertida ainda se sobrepõe à de C1, e o J não vai a zero. Como as outras duas cláusulas não mudam, C1 continua com 0,8873.
2. **O efeito depende do limite superior do domínio,** que entra na união. Rodando o mesmo código de produção com outros domínios de atrito (`output/friction_domain_check.csv`):

| Domínio do atrito | J(D2, C1) | C1 | C2 | Top-1 |
|---|---:|---:|---:|---|
| [0, 2] (catálogo) | 0,12875 | 0,8873 | 0,8966 | C2 |
| [0, 1] | 0,25750 | 0,9016 | 0,8966 | C1 |
| [0, 0,6] | 0,42917 | 0,9207 | 0,8966 | C1 |

Com domínio [0; 0,6], o diagnóstico **invertido** ficaria mais similar a C1 (0,9207) do que o diagnóstico correto (0,9126). A métrica compara medidas de regiões: o sentido de uma desigualdade só importa pelo quanto a região se sobrepõe à do candidato dentro do domínio declarado.

### C. D0 × D4 e D5 — condições geométricas

Uma condição nova tem efeito oposto sobre quem a declara e quem não a declara.

**Em D4 (`object_shape_irregular == 1`):**
- **C3 declara o mesmo predicado** (J = 1). Os parâmetros compartilhados passam de 2 para 3, e os que sobram em C3 caem de 2 para 1. Com isso, P vai de 0,3548 para 0,25, S_param de 0,9091 para 0,9394, e S_Given(C3) sobe de 0,5543 para 0,6894.
- **C1 e C2 ganham um parâmetro só do diagnóstico** (α): P(C1) vai de 0 para 0,2308 e P(C2) de 0,3103 para 0,4737.
- C3 passa C2 por 0,1631 de Given, contra 0,0587 necessários, e fica em primeiro por 0,0348.

**Em D5 (`grasp_alignment_error_cm > 1`):** os valores são os mesmos de D4, exceto C4. C4 também declara a geometria, mas não o desalinhamento, e por isso cai de 0,7426 (D4) para 0,6593 (D5).

Nos dois casos, C3 é favorecido porque é o único candidato que declara a condição com a mesma região. A métrica não interpreta geometria: o ganho vem do parâmetro compartilhado e da penalização que o candidato deixa de pagar.

### D. D4/D5 × D12/D13 (e D18/D19) — condições combinadas

**Em D12 (geometria e desalinhamento):**
- C3 compartilha 4 dos 5 parâmetros do diagnóstico, e só o atrito fica de fora: P = 0,1837 e S_Given = 0,7709.
- C1 e C2 passam a ter dois parâmetros que só o diagnóstico declara: P(C1) = 0,375 e P(C2) = 0,5745.
- A margem de C3 cresce de 0,0348 (D4) para 0,0955.

**Em D13 (sem o atrito):**
- O conjunto de parâmetros do diagnóstico fica igual ao de C3, logo P = 0 e S_Given = S_param = 0,9545. O único desvio é o limiar de altura: `< 10` contra `< 12`, que dá J = 9/11 no domínio inteiro.
- C1 também melhora em relação a D12, de 0,7876 para 0,8217: o par de atrito parcial sai da média, e o atrito de C1 passa a custar só β.
- A margem cresce para 0,1232.

**Em D18 e D19:** alinhar também a altura (`< 12`) leva o Given de C3 a J = 1 em todos os pares. D19 atinge o máximo possível para C3, (1 + 1 + 0,9413)/3 = 0,9804.

Ou seja, as condições complementares somam o mesmo efeito duas vezes: cada uma aumenta os parâmetros compartilhados com C3 e as penalizações dos demais. Omitir o atrito retira a última penalização de C3.

### E. D6/D7 × D14–D17 — instabilidade dinâmica

C5 começa com uma desvantagem fixa no Then (S_Then = 0,3889). Para chegar ao Top-1, precisa de uma vantagem de Given de 0,5635 sobre C1 e de 0,6111 sobre C2.

| D | S_Given(C5) | Rival decisivo: Top-1, ou Top-2 quando C5 lidera (S_Given) | Vantagem de C5 | Necessária | Posição de C5 |
|---|---:|---|---:|---:|---:|
| D6/D7 | 0,5746 | C2 0,5263 | +0,0483 | +0,6111 | 5ª |
| D14 | 0,6847 | C2 0,4255 | +0,2592 | +0,6111 | 4ª |
| D15 | 0,8684 | C2 0,5263 | +0,3421 | +0,6111 | 4ª |
| D16 | 0,8163 | C1 0,2350 | +0,5813 | +0,5635 | **1ª** |
| D17 | 1,0000 | C2 0,2632 | +0,7368 | +0,6111 | **1ª** |

**Por que uma condição dinâmica sozinha, ou as duas juntas, não bastam:** o Given de C5 melhora, mas o limiar de altura de C5 (`< 20`) continua divergente (J = 9/19 contra `< 10`). Além disso, cada condição custa aos rivais só uma ou duas penalizações α.

**Em D16, três mudanças atuam juntas:**
- a altura `< 20` dá J = 1 a C5 e derruba o J de altura de C1, C2 e C4 para 9/19 (e o de C3 para 11/19);
- as duas condições dinâmicas somam 2α aos rivais.

Mesmo assim, a margem de C5 sobre C1 é a menor da bateria (0,0060). Em D17, sem o atrito, o Given de C5 fica idêntico ao do diagnóstico, e a margem sobe para 0,0419.

### F. D0 × D8 — informação sem correspondência

Nenhum candidato declara `object_mass`. Por isso, nenhum par novo é formado, o S_param de todos fica igual ao de D0, e cada candidato ganha um parâmetro a mais que só o diagnóstico declara. Mesmo assim, o Top-1 muda de C1 para C2: a penalização de Tversky é uma razão, e o mesmo parâmetro extra custa valores diferentes a cada candidato.

| Candidato | Compartilhados | P em D0 | P em D8 | Aumento |
|---|---:|---:|---:|---:|
| C1 | 3 | 0 | 0,2308 | +0,2308 |
| C2 | 2 | 0,3103 | 0,4737 | +0,1634 |
| C3, C4, C5 | 2 | 0,3548 | 0,5000 | +0,1452 |

O candidato que coincidia em estrutura (C1) é o que mais perde, porque o primeiro parâmetro sem correspondência é o mais caro. A vantagem de Given de C1 cai de 0,0957 para 0,0283, abaixo de 0,0476, e C2 fica em primeiro por 0,0064.

O mesmo vale para qualquer predicado acrescentado que C1 e C2 não declaram: em D4–D8, C1 e C2 têm sempre 0,8357 e 0,8421. A liderança de C1 em D0 (margem de 0,0160) cai com **qualquer** informação extra que não corresponda a C1.

### G. D0 × D11 — omitir os contatos

`finger_contacts < 2` é idêntico em todos os candidatos. Retirá-lo reduz todos os escores:

| | C1 | C2 | C3 | C4 | C5 |
|---|---:|---:|---:|---:|---:|
| Variação em relação a D0 | −0,0516 | −0,0632 | −0,0938 | −0,0635 | −0,1273 |

Mesmo assim, o Top-1 não muda, porque o atrito, que distingue C1, continua no diagnóstico:
- **C1** compartilha altura e atrito. O S_param passa a 0,6781, porque o J parcial do atrito pesa mais numa média de dois parâmetros. O contato sobra só em C1 e custa β (P = 0,0476), logo S_Given = 0,6305.
- **C2** compartilha só a altura, paga α pelo atrito e β pelo contato: P = 0,5 e S_Given = 0,5.

A margem de C1 até cresce, para 0,0276.

Em C5, o resultado da cláusula seria negativo (0,4737 − 0,5455) e é cortado em 0 pelo `max(0, ·)`. O corte esconde quanto o Given de C5 se afasta do diagnóstico.

### H. D6 × D7 — semântica diferente, mesmo resultado

D6 (`planned_lift_acceleration_m_s2 > 2`) e D7 (`payload_swing_risk == 1`) produzem **o mesmo vetor de escores e o mesmo ranking** (há um teste para isso). O motivo é estrutural: os dois parâmetros só existem em C5, com o mesmo predicado do diagnóstico (J = 1).
- Para C5, os dois casos dão 3 parâmetros compartilhados, 1 só do diagnóstico e 1 só do candidato.
- Para os outros candidatos, os dois casos são um parâmetro a mais que só o diagnóstico declara.

A métrica compara regiões e conjuntos de nomes de parâmetros. Ela não distingue aceleração de risco de oscilação e não interpreta a causa física da situação. A diferença entre D4 e D5, restrita a C4, mostra a mesma coisa: o que conta é quais candidatos declaram o parâmetro.

### Outros casos

- **D1 (atrito ≤ 0,25).** Ampliar a região diagnosticada em direção à de C1 (≤ 0,4) aumenta o J para 0,625, e a margem de C1 sobe para 0,0459. A métrica premia a sobreposição, não a correção do limiar: o limiar diagnosticado de fato (0,1425) dá **menos** similaridade com C1 que o limiar impreciso.
- **D9 e D10 (limiar de altura).** Todos os candidatos têm altura, então não há mudança estrutural, só de J.
  - **D9 (`< 12`):** C3 ganha J = 1 e fica a 0,0041 de C2, a menor distância entre posições vizinhas da bateria.
  - **D10 (`< 20`):** C5 ganha J = 1 e passa C4 nas posições 4 e 5.
  - Nos dois, o Top-1 continua C1, porque o atrito, que só C1 compartilha, continua no diagnóstico.

## 6. Comparação com a reprodução independente

**Resultado da comparação:**
- **Escores:** 49 dos 100 coincidem em 4 casas. Os 51 restantes diferem entre −0,0050 e −0,0012; todos os escores reais ficam abaixo dos da reprodução.
- **Ordem:** o Top-3 e a ordem completa coincidem nas 20 configurações.
- **Contagens:** as da seção 9 da especificação se confirmam: Top-1 muda em 15, ordem do Top-3 em 15, composição do Top-3 em 2, sem empates.

**Causa: os domínios.** Rodando o mesmo código de produção com os domínios da reprodução, **os 100 escores coincidem em 4 casas** (há um teste para isso). Os domínios que diferem são:

| Parâmetro | Repositório | Reprodução | Efeito na bateria |
|---|---|---|---|
| `object_lift_height_cm` | int [0, 100] | float [0, 100] | **Causa todas as diferenças.** Com inteiros, `x < 10` é [0, 9] e `x < 12` é [0, 11], então J(`< 10`, `< 12`) = 9/11 = 0,8182 em vez de 10/12 = 0,8333, e J(`< 10`, `< 20`) = 9/19 = 0,4737 em vez de 0,5. Afeta toda comparação entre limiares de altura diferentes no Given (C3 e C5 sempre; C1, C2 e C4 em D9, D10 e D16–D19) |
| `grasp_alignment_error_cm` | float [0, 100] | float [0, 10] | nenhum: o predicado do diagnóstico é idêntico ao de C3, e J = 1 em qualquer domínio |
| `planned_lift_acceleration_m_s2` | float [0, 20] | float [0, 10] | nenhum, pelo mesmo motivo (idêntico ao de C5) |
| `object_mass` | ausente (o catálogo tem `objects_object_1_mass`) | float [0, 20] | nenhum: nenhum candidato declara massa, então o domínio nunca é consultado; o parâmetro só entra na contagem de Tversky |

**D16 (margem reduzida).** A ordem é a mesma (C5, C1, C2), mas a margem real é 0,0060, o dobro da reprodução (0,0030):
- C5 não muda (0,7351), porque não depende dos domínios divergentes;
- C1 cai de 0,7320 para 0,7291, porque J(`< 20`, `< 10`) cai de 0,5 para 9/19.

A ordenação de D16 não depende do tipo do domínio de altura. Mas, sendo a menor margem da bateria, é a configuração mais sensível a esse tipo de escolha.

## 7. Comportamentos para destacar no artigo

1. **A cadeia de efeitos é estrutural e calculável.** Uma modificação do Given muda o conjunto de parâmetros (penalização de Tversky) ou a região de um parâmetro compartilhado (Jaccard), e só isso altera o escore. Com When e Then fixos, cada troca de posição se reduz a comparar a diferença de S_Given com a diferença fixa de S_Then.
2. **A assimetria α ≫ β decide a maior parte das trocas.** Informação que está no diagnóstico e falta no candidato custa caro; o contrário custa pouco. Logo:
   - acrescentar condições favorece quem as declara e penaliza todos os outros (D4, D5, D12);
   - omitir condições favorece candidatos mais genéricos (D3, D13, D15, D17).
3. **Informação sem correspondência também reordena (D8).** A penalização é uma razão, e o primeiro parâmetro sem correspondência custa mais a quem coincidia em estrutura.
4. **O sentido de um predicado só importa pela sobreposição de regiões (D2).** O efeito depende dos limites do domínio declarado e pode até se inverter.
5. **Nomes não têm semântica para a métrica (D6 = D7).**
6. **O Then de cada candidato funciona como desvantagem fixa.**
   - C2, com o Then idêntico ao do diagnóstico, herda o Top-1 sempre que a vantagem de C1 cai abaixo de 0,0476.
   - C4 nunca entra no Top-3.
   - C5 só chega ao Top-1 com três modificações ao mesmo tempo (D16, D17).
7. **Margens pequenas.** A liderança de C1 em D0 é de 0,0160, e uma única condição a mais não correspondida (D6–D8) a desfaz. As margens grandes (0,10–0,17) aparecem quando o diagnóstico passa a reproduzir a estrutura de outro candidato (D12, D13, D18, D19).
8. **O Retriever não tem limiar de rejeição.** Sempre devolve um Top-1, e o escore mínimo possível é 1/3.

**Consequência operacional, só no nível do ranking.** O DejaVú tenta no máximo os 2 primeiros candidatos (`retry_policy.MAX_ATTEMPTS = 2`):
- C1, o candidato validado fisicamente na RQ1.2 a μ = 0,140, sai dos dois primeiros em 7 configurações (D4, D5, D12, D13, D17, D18, D19).
- Em 8 configurações (D4, D5, D12, D13, D16–D19), o Top-1 é C3 ou C5, que não têm implementação física neste estudo de caso (`CLAUDE.md`, *Not Implemented*).

A RQ2 não executa essas adaptações e nada afirma sobre o resultado físico delas.

## 8. Limitações

- **Uma referência e um catálogo.** A bateria tem um diagnóstico de referência, cinco candidatos e 19 modificações escolhidas à mão. As proporções (15 de 19 etc.) valem só para ela.
- **Só a recuperação é avaliada.** Nenhuma adaptação foi executada, e C3, C4 e C5 não têm implementação física.
- **Predicados sintéticos.** Geometria, desalinhamento, aceleração, oscilação e massa com esse nome não são colunas do dataset de execução, que só tem a massa como `objects.object_1.mass`. O Diagnoser deste estudo de caso não produziria esses predicados. Eles representam imprecisões hipotéticas de um diagnóstico e foram entregues diretamente ao Retriever.
- **Dependência dos domínios.** Os escores dependem dos domínios declarados no catálogo, que foram definidos pelos autores: o tipo inteiro da altura e o limite superior do atrito (seção 5B).
- **Configuração fixa da métrica.** Os pesos são fixos (α = 0,9, β = 0,1, w_p = 1, cláusulas com peso 1), sem análise de sensibilidade a eles. O Jaccard é arredondado a 5 casas.
- **Só o Given varia.** Imprecisões no Then, como a negação feita pelo Identifier, e no When ficam fora do escopo; um When diferente nem passaria pelo filtro.
- **Empates.** Não ocorreram. Se ocorressem, a escolha seguiria a ordem do catálogo.
