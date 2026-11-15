# Bateria B — critérios e seleção

Este documento foi escrito **antes** do cálculo de qualquer escore da Bateria B. A ordem foi esta:

1. `explore_perturbations.py --design-only` gerou as 130 perturbações exploradas e a seleção;
2. este documento foi escrito;
3. só então os escores foram calculados.

A seleção está declarada em `scripts/perturbations.py` (`SELECTION`) e depende apenas dos atributos de desenho: categoria, classe do parâmetro, intensidade, direção, validade e plausibilidade. Nenhuma função de seleção recebe escores.

**Limitação desta garantia.** Quem fez a seleção conhecia os resultados da Bateria A, e várias perturbações isoladas da B repetem configurações da A (ver `comparison.md`). Desconhecer os resultados só vale, de fato, para as configurações novas: limiares, operadores, omissão da altura e as quatro combinações.

## Referência e restrições

- **B0 = D0 da Bateria A.**
  - **Given:** `object_lift_height_cm < 10 AND finger_contacts < 2 AND lateral_friction <= 0.1425`
  - **When:** `grasp_completed == 1`
  - **Then:** `object_lift_height_cm >= 10 AND finger_contacts >= 2`
- **Só o Given muda**, e cada configuração é derivada de B0 de forma independente.
- **Retriever de produção:** catálogo, pesos (parâmetros 1,0; cláusulas 1,0/1,0/1,0) e Tversky α = 0,9, β = 0,1, como estão em `3-dejavu/configs/`.

## Como o Retriever restringe o desenho

Lido em `3-dejavu/src/similarity/dejavu_similarity.py`:

- **Jaccard dos predicados.** É calculado sobre a região admissível de cada predicado, dentro do domínio do catálogo.
  - Inteiros são medidos como comprimento contínuo: `x < 10` com domínio 0–100 vira [0, 9], de comprimento 9. Por isso `finger_contacts < 1` vira [0, 0], de comprimento zero, e tem Jaccard 0 até consigo mesmo.
  - Uma igualdade (`==`) contra um intervalo conta como comprimento 1. Em domínio contínuo, isso leva a valores acima de 1 (`lateral_friction == 0.1425` dá 7,0).
  - A união é a envoltória dos dois intervalos.
- **Penalidade estrutural.** É 1 − Tversky(parâmetros do diagnóstico, parâmetros do candidato). O α pesa os parâmetros que só o diagnóstico tem; o β, os que só o candidato tem.
- **Escore da cláusula.** É `max(média dos Jaccard dos parâmetros compartilhados − penalidade, 0)`.
- **Escore global.** É a média das três cláusulas. O When é igual em todos os candidatos depois do filtro, e o Then de cada candidato fica constante na bateria.
- **Ordenação.** Por escore, decrescente; o sort é estável, então um empate é resolvido pela ordem do catálogo.

## Classes de parâmetros (candidatos C1–C5, que passam pelo filtro de When)

| Parâmetro | Classe | Quem escreve no Given |
|---|---|---|
| `object_lift_height_cm` | compartilhado por todos | Identifier (Then violado negado) |
| `finger_contacts` | compartilhado por todos | Identifier |
| `lateral_friction` | específico de C1 | Diagnoser (caminho da árvore) |
| `object_shape_irregular` | compartilhado por C3 e C4 | Diagnoser |
| `grasp_alignment_error_cm` | específico de C3 | Diagnoser |
| `underwater_current_speed_cm_s` | específico de C4 | Diagnoser |
| `planned_lift_acceleration_m_s2`, `payload_swing_risk` | específicos de C5 | Diagnoser |
| `objects_object_1_mass`, `grasp_attempts` | ausentes do catálogo | Diagnoser |
| `grip_pressure` | ausente dos candidatos aplicáveis (só aparece em C7, excluído pelo When) | Diagnoser |

## Operadores explorados

**A — Adição.** São oito adições isoladas e três adições múltiplas da mesma classe (2 a 3 condições).
- Para um parâmetro representado por algum candidato, o predicado adicionado é o do candidato. Assim, a adição isola o efeito estrutural (a presença do parâmetro) do efeito de sobreposição, que as categorias C e D estudam.
- Para um parâmetro ausente, o predicado só precisa ser plausível: ele nunca é pareado, então o valor não altera nenhum escore.

**B — Omissão.** As três omissões isoladas e a omissão total. A omissão total é inválida, porque deixa o Given vazio. As omissões em pares entram como combinações.

**C — Operador.** Para cada predicado de B0, o mesmo valor com cada um dos outros cinco operadores, mais duas reescritas equivalentes, que servem de controle. A validade semântica tem quatro regras:
- um Given que só admite estados em que o Then esperado já vale **contradiz a violação** e é inválido. Isso descarta todas as inversões de altura e contatos;
- `!=` e igualdade em parâmetro contínuo são inválidos;
- um Given que admite parte dos estados do Then é válido, mas marcado como **excessivamente geral**;
- por essas regras, a única inversão válida é a do atrito.

**D — Limiar.**
- **Intensidade:** é a distância de Jaccard `1 − J(região original, região modificada)`, calculada com a função do próprio Retriever.
- **Atrito e altura:** os alvos 0,25, 0,50 e 0,75 foram explorados nas duas direções.
  - No atrito, que é contínuo, o limiar é calculado exatamente e arredondado em 4 casas.
  - Na altura, que é inteira, vale o inteiro mais próximo do alvo; num empate, a mudança menos extrema.
- **Contatos:** como o domínio é 0–5, foram explorados todos os limiares inteiros.
- **Nenhum limiar foi escolhido por coincidir com um candidato.** A coluna `coincides_with_candidate` registra esse controle.

**Combinações.** Todos os pares das 15 perturbações isoladas selecionadas, desde que não toquem o mesmo parâmetro: são 81 pares.

## Critérios de seleção (declarados antes dos escores)

1. Cobertura das quatro categorias.
2. Intensidades diferentes onde há gradação: limiar do atrito em baixa e alta intensidade, operador do atrito na mínima e na máxima.
3. Direções opostas com o mesmo alvo de intensidade: atrito restritivo × permissivo em 0,25 e 0,75, altura restritiva × permissiva em 0,5.
4. Comparações controladas entre classes de parâmetro: compartilhado por todos, compartilhado por dois, específico de um candidato, ausente.
5. Plausibilidade no exemplar: um braço de pick-and-place sobre mesa.
6. Casos isolados que expliquem efeitos específicos.
7. Combinações de ordem 2, formadas só por perturbações isoladas da própria bateria, para comparar o efeito conjunto com a soma dos efeitos isolados.
8. Sem redundância: um representante por classe e por papel no desenho.

**Fica excluído:** o que é inválido, implausível ou artefato da métrica (região de comprimento zero, Jaccard acima de 1). As reescritas equivalentes ficam só na exploração, como controle.

Mudança de Top-1, de Top-3 ou o tamanho da diferença de similaridade **não** entram em nenhum critério.

## Bateria B

| ID | Categoria | Perturbação aplicada a B0 | Intensidade | Justificativa |
|---|---|---|---|---|
| B0 | — | referência | — | D0 da Bateria A |
| B1 | A | + `object_shape_irregular == 1` | 1 parâmetro | compartilhado por dois candidatos (C3, C4) |
| B2 | A | + `grasp_alignment_error_cm > 1` | 1 parâmetro | específico de C3, cujo Then é próximo do de B0 |
| B3 | A | + `planned_lift_acceleration_m_s2 > 2` | 1 parâmetro | específico de C5, cujo Then difere do de B0 |
| B4 | A | + `objects_object_1_mass > 0.5` | 1 parâmetro | ausente de todos: penalidade sem correspondência |
| B5 | B | − `lateral_friction` | 1 parâmetro | o único parâmetro que distingue um candidato (C1) |
| B6 | B | − `finger_contacts` | 1 parâmetro | compartilhado por todos |
| B7 | B | − `object_lift_height_cm` | 1 parâmetro | o outro compartilhado, para comparar com B6 |
| B8 | C | `<=` → `<` no atrito | d = 0,000 | intensidade mínima (só a fronteira); controle |
| B9 | C | `<=` → `>` no atrito | d = 1,000 | intensidade máxima (região complementar) |
| B10 | D | atrito ≤ 0,1069 | d = 0,250, restritivo | baixa |
| B11 | D | atrito ≤ 0,0356 | d = 0,750, restritivo | alta |
| B12 | D | atrito ≤ 0,19 | d = 0,250, permissivo | baixa, direção oposta de B10 |
| B13 | D | atrito ≤ 0,57 | d = 0,750, permissivo | alta, direção oposta de B11 |
| B14 | D | altura < 6 | d = 0,444, restritivo | parâmetro compartilhado, intensidade intermediária |
| B15 | D | altura < 19 | d = 0,500, permissivo (excessivamente geral) | direção oposta de B14 |
| B16 | A+A | B2 + B3 | 2 mudanças | adições ligadas a candidatos diferentes (C3 e C5) |
| B17 | B+B | B5 + B6 | 2 mudanças | omissão de um parâmetro distintivo e de um compartilhado |
| B18 | A+B | B5 + B4 | 2 mudanças | a condição distintiva trocada por uma não informativa |
| B19 | A+D | B12 + B1 | 2 mudanças | mudança de região no parâmetro de C1 com mudança estrutural para C3/C4 |

**Decisões que não decorrem dos critérios, por isso registradas aqui:**
- **B17 usa a omissão dos contatos, e não a da altura.** Os dois parâmetros têm o mesmo papel no desenho (compartilhados, vindos do Identifier); a escolha entre eles é arbitrária, e o par com a altura fica na exploração.
- **B19 usa a intensidade baixa do atrito permissivo.** Ela é a mudança de limiar mais moderada que aumenta a região; a combinação com a intensidade alta fica na exploração.
- **B8 é um controle.** O desenho já mostra que ele é equivalente a B0 sob a métrica (d = 0). Ele fica na bateria para documentar a intensidade mínima da categoria C, que é a única gradação possível de operador válido neste exemplar.

## Excluídos e motivos

Cada perturbação explorada fora da bateria tem o motivo da exclusão em `exploratory_diagnoses.csv`, na coluna `exclusion_reason`. Em resumo:

- **11 inválidas:**
  - inversões de altura e contatos, que contradizem a violação;
  - `!=`;
  - igualdade em parâmetro contínuo;
  - Given vazio.
- **Uma implausível:** a corrente de água, do candidato C4.
- **Um artefato da métrica:** `finger_contacts < 1`.
- **Redundantes:**
  - `>=` no atrito, igual a `>` sob a métrica;
  - adições da mesma classe: balanço, tentativas de preensão, pressão de preensão;
  - adições múltiplas da mesma classe;
  - intensidades intermediárias.
- **Papel já coberto por outro caso:**
  - `<=` em parâmetros inteiros, que equivale a uma mudança de limiar;
  - limiares de contatos, já representados pelos da altura;
  - as reescritas equivalentes, mantidas só como controle;
  - os pares que não estão entre as quatro combinações declaradas.

---

# Adendo (2026-11-12): correções posteriores à revisão

O texto acima é o documento original, escrito antes dos escores, e não foi alterado. Este adendo registra as correções feitas depois de uma revisão crítica.

**O que não mudou:**
- as 20 configurações da bateria;
- os escores e rankings: `output/similarity_scores.csv`, `rankings.csv`, `interactions.csv` e `summary.json` ficaram idênticos byte a byte;
- a figura.

**O que mudou:**
- os rótulos de validade e os motivos de exclusão, em `exploratory_diagnoses.csv`;
- a justificativa de B9 em `SELECTION`;
- as colunas de avaliação de `output/selected_diagnoses.csv`;
- o conjunto de perturbações exploradas que recebem escore.

As verificações estão em `review/` (ver o README).

## A1. Validade das perturbações: cada predicado avaliado contra a violação que representa

**O critério original estava errado.** Ele marcava como "inválidas, por contradizerem a violação" as inversões dos predicados de altura e de contatos, usando como regra geral que o Given só admite estados do Then. Essa regra mistura coisas diferentes:
- inverter um predicado não faz todas as cláusulas do Then valerem;
- nenhuma das perturbações exploradas é uma contradição lógica.

**O critério novo avalia cada predicado escrito pela perturbação em seis dimensões** (`scripts/perturbations.py`, `assess_predicate`):

| Dimensão | Pergunta |
|---|---|
| Satisfatibilidade | o predicado admite algum valor do domínio do catálogo? |
| Consistência com a observação | o predicado admite o valor observado na violação? (registrado em `../inputs/d0_source/events_*.jsonl`: altura 1, contatos 0, atrito 0,14, `grasp_attempts` 1) |
| Relação com a violação representada | só para os predicados que o Identifier escreve (altura e contatos): comparado com a violação da cláusula do Then que ele nega, o predicado admite os mesmos estados, menos estados, também estados que não a violam, ou nenhum estado que a viole? |
| Viabilidade na aplicação | o predicado admite algum valor que o sistema gerenciado produz? (o sensor da garra de dois dedos produz `finger_contacts` ∈ {0, 1, 2}; o catálogo declara 0–5) |
| Mensurabilidade | o Jaccard do Retriever mede o predicado como deveria? |
| Origem e plausibilidade | o componente que escreve o predicado poderia produzi-lo como imprecisão? |

**Exclusões explicadas por origem e plausibilidade:**

- **Inversões de altura e contatos (`>`, `>=`, `==`).** Origem implausível.
  - O Identifier escreve esses predicados negando uma cláusula do Then que a observação violou. A negação de uma cláusula violada sempre admite o valor observado.
  - Portanto, nenhum Then, por mais impreciso que seja o ASM, gera um predicado de altura ou de contatos que exclua o valor observado (altura 1, contatos 0).
  - `finger_contacts > 2` também é inviável na aplicação.
- **Mudanças de limiar desses mesmos predicados (B14, B15) e `<=` com o mesmo valor.** São plausíveis: vêm de um limiar ou operador impreciso no Then do ASM e continuam admitindo o valor observado.
- **`!=` (três casos).** Não são contradições. Ficaram de fora por não serem informativos (admitem todos os valores menos um); além disso, o Retriever mede a região dividida pela envoltória.
- **`lateral_friction == 0.1425`.** Não é mensurável: o Retriever conta a igualdade como comprimento 1 num domínio contínuo, e o Jaccard dá 7,0.
- **Omissão total.** Continua fora: um Given vazio não é um cenário.

**Configurações da bateria inconsistentes com a observação.** Ficam na bateria, agora documentadas:

| Configuração | Predicado | Atrito observado |
|---|---|---|
| B9 | `lateral_friction > 0.1425` | 0,14 |
| B10 | `<= 0.1069` | 0,14 |
| B11 | `<= 0.0356` | 0,14 |

O documento original só tratava B9; B10 e B11 têm a mesma inconsistência. Os três são plausíveis como imprecisão do Diagnoser: a condição é o caminho da árvore para o run corrente, e um valor errado da feature leva a outro ramo ou a outro limiar. A justificativa de B9 em `SELECTION` foi corrigida nesse sentido.

**Na exploração**, `grasp_attempts > 1` (EA07) também exclui o valor observado (1). Ele estava e continua fora da bateria por redundância de classe.

**Efeito na exploração.** Passam a receber escore todas as perturbações satisfatíveis que o Retriever consegue medir: 128 das 130 (antes eram 119). As 9 novas (as inversões e os `!=`) não mudam o Top-3, e nas inversões de altura e contatos C1 continua em primeiro. Os escores das 119 anteriores não mudaram.

## A2. Parâmetros inteiros: convenção do Retriever e sensibilidade

**Como o Retriever mede uma região inteira.** Pelo comprimento entre o menor e o maior valor admitido: `x < 10` no domínio 0–100 vira [0, 9], de comprimento 9, embora sejam 10 valores. Consequências:
- uma região de um único valor tem comprimento 0 e Jaccard 0 até consigo mesma;
- uma igualdade contra um intervalo conta como 1 (uma contagem) sobre um comprimento;
- a união de duas regiões é a envoltória delas.

**Nesta bateria:**
- o Retriever só comparou pares intervalo/intervalo (366) e igualdade/igualdade (104);
- nenhum par envolve região de comprimento zero nem Jaccard acima de 1;
- na exploração, os pares igualdade/intervalo vêm só das inversões excluídas (EC04, EC10), e a região de comprimento zero só de ED07.

**Sensibilidade.** Recalculei as Baterias A e B com cardinalidade discreta (|A ∩ B| / |A ∪ B| sobre os inteiros admitidos), mantendo o resto da métrica (`review/integer_convention_*.csv`):
- **nenhum ranking muda**, em nenhuma das 20 configurações de cada bateria;
- a maior diferença de escore é 0,0092 na B (B17) e 0,0051 na A;
- a menor margem afetada é a de D18 da A, que cai de 0,0060 para 0,0034, com o mesmo Top-1.

As intensidades de altura da B estão na medida do Retriever:

| Configuração | Medida do Retriever | Cardinalidade discreta |
|---|---|---|
| B14 | d = 0,444 | d = 0,400 |
| B15 | d = 0,500 | d = 0,474 |

A medida do Retriever é uma convenção da implementação, e não do texto da especificação; a divergência está tratada em `../comparison.md`.

## A3. Alcance da estabilidade do Top-3

**A estabilidade do Top-3 vale para as perturbações exploradas**, que têm no máximo duas modificações simultâneas (as adições múltiplas de parâmetros ausentes chegam a três).

**Combinações de ordem 3 (`review/order3_combinations.csv`).** A checagem cobre as 214 combinações de três perturbações isoladas da bateria que tocam três parâmetros diferentes. Fica de fora B5 + B6 + B7, que deixa o Given vazio.
- **Uma delas muda o Top-3:** B3 + B6 + B15, que dá C1 > C5 > C2 > C3 > C4.
- **Com cardinalidade discreta, a mudança se mantém:** a ordem é a mesma.
- **A margem que decide a composição** é a distância entre o 3º (C2) e o 4º colocado (C3): 0,0196 na medida do Retriever e 0,0195 com cardinalidade discreta.
- **Os 0,0025 citados na revisão** são a distância entre C5 e C2 (2º e 3º lugares), ou seja, a ordem dentro do Top-3; com cardinalidade discreta, ela vai a 0,0034.
- **Mecanismo:** a similaridade do Given de C2, C3 e C4 é cortada em zero (`max(·, 0)`), e entre eles a ordem passa a depender só do Then.

**Esta checagem não faz parte da bateria.** Ela é exaustiva só para os operadores da bateria e mostra que a mudança é possível com três modificações; "1 em 214" não é uma estimativa de frequência. A configuração não foi acrescentada à bateria, porque escolhê-la por mudar o Top-3 seria seleção pelo resultado.

## A4. Nome do parâmetro de massa

A Bateria A usa `object_mass`, que não está nos `monitored_parameters`. A B usa `objects_object_1_mass`, que está. Como nenhum candidato tem o parâmetro, ele nunca é pareado, e o Tversky só conta nomes: B4 e D11 da A dão os mesmos cinco escores. Ao adotar a B, o artigo deve usar `objects_object_1_mass`.
