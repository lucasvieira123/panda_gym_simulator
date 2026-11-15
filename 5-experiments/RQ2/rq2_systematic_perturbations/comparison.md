# Bateria A × Bateria B — comparação crítica

> **Revisão de 2026-11-12.** Depois de uma revisão crítica, foram corrigidos:
> - o critério de validade das inversões (seção 1);
> - o alcance da estabilidade do Top-3 (seção 4 e recomendação);
> - a análise da convenção de inteiros, que agora compara implementação e especificação (seção "Implementação × especificação");
> - as limitações.
>
> Os números das baterias não mudaram. Os detalhes estão no adendo de `exploration/selection_rationale.md` e em `review/`.

**Fontes dos números:**
- **Bateria A:** `../output/`, com a numeração do artigo dada por `../figures/rq2_similarity_plotly_labels.csv`. A Bateria A não foi executada de novo.
- **Bateria B:** `output/` e `exploration/`.

**Uma ressalva:** escolhi os casos da Bateria B já conhecendo os resultados da A. Oito das 19 configurações modificadas da B repetem configurações da A com os mesmos cinco escores:

| B | A |
|---|---|
| B1 | D5 |
| B2 | D6 |
| B3 | D7 (e D8) |
| B4 | D11 |
| B5 | D3 |
| B6 | D4 |
| B9 | D2 |
| B8 | idêntico a D0 |

B7, B10–B19 são novas.

## Visão geral

| | Bateria A | Bateria B |
|---|---|---|
| Configurações modificadas | 19 (11 isoladas, 8 combinadas) | 19 (15 isoladas, 4 combinadas) |
| Como foram escolhidas | caso a caso, por tema (atrito, contato, geometria, dinâmica, altura) | taxonomia de 4 categorias, critérios declarados antes dos escores, 130 perturbações exploradas com motivo de exclusão |
| Intensidade | não definida | distância de Jaccard medida com a função do Retriever |
| Direção dos limiares | só permissiva (atrito 0,25; altura 12 e 20) | restritiva e permissiva, com o mesmo alvo |
| Limiares iguais aos de um candidato | altura < 12 (= C3) e < 20 (= C5) | nenhum (controle `coincides_with_candidate`) |
| Combinações | 2 a 4 mudanças, agrupadas por candidato (geometria → C3, dinâmica → C5) | ordem 2, a partir de casos isolados da própria bateria |
| Given idêntico ao de um candidato | D3 (C2), D15 (C3), D19 (C5) | só B5 (C2), que é a omissão isolada do atrito |
| Top-1 muda | 15/19 | 11/19 |
| Conjunto do Top-2 (tentativas) muda | 8/19 | 4/19 (B1, B2, B16, B19) |
| Composição do Top-3 muda | 2/19 (D18, D19) | **0/19**, e 0 nas 128 perturbações exploradas com escore (no máximo duas modificações simultâneas) |
| C1 entre os dois primeiros / no Top-3 | 12/19 / 18/19 | 16/19 / 19/19 |
| Trocas de Top-1 com margem < 0,01 | 5 de 15 | 3 de 11 (B3, B4, B9) |
| τ de Kendall vs referência (mediana / mínimo) | 0,6 / −0,2 | 0,8 / 0,4 |
| Escore do primeiro colocado | 0,735–1,000 | 0,831–1,000 |

## 1. Cobertura das categorias de imprecisão

**Na A**, a cobertura é desigual:
- 5 adições e 2 omissões. Não há omissão da altura;
- 1 inversão de operador;
- 3 mudanças de limiar, todas na direção permissiva.

**Na B:**
- **Categorias:** as quatro aparecem de forma explícita, e as omissões cobrem os três parâmetros de B0.
- **Classes de parâmetro:** as adições cobrem quatro, em comparação controlada: compartilhado por dois, específico de C3, específico de C5 e ausente.
- **Limiares:** aparecem nas duas direções, e o atrito em duas intensidades.

**A categoria C é pobre neste exemplar, nas duas baterias, por causa da origem das imprecisões.**
- **Nenhuma inversão é uma contradição lógica.**
- **Altura e contatos.** O Identifier escreve esses predicados negando uma cláusula do Then que a observação violou, e a negação sempre admite o valor observado (altura 1, contatos 0).
  - Uma inversão que exclui esse valor (`>`, `>=`, `==`) não pode vir do Identifier, por mais impreciso que seja o ASM.
  - `finger_contacts > 2` também é inviável na aplicação: o sensor produz só 0–2.
- **Atrito.** Vem do caminho da árvore do Diagnoser. Um valor errado da feature leva ao ramo oposto, então a inversão é plausível, embora exclua o atrito observado (0,14).
  - B10 e B11 também excluem esse valor.
- **Resultado:** a única inversão plausível é a do atrito (B9). B8 (só a fronteira, d = 0) funciona como controle e não muda nada.
- **As inversões excluídas não escondem efeitos.** Elas receberam escore na exploração, e em todas C1 continua em primeiro e o Top-3 não muda.

## 2. Sensibilidade dos escores

A B separa dois mecanismos que a A mistura.

**Região (Jaccard).**
- **Atrito.** Só C1 representa o atrito, então mudar a região dele altera **apenas** o escore de C1. O efeito vai de −0,030 (B11) a +0,038 (B13).
- **Altura.** É compartilhada, então mudar a região dela altera todos os candidatos:
  - nas duas direções, cai o escore de C1, C2 e C4, cujo predicado é `< 10`;
  - na direção permissiva, o efeito depende do limiar de cada candidato. C5 (`< 20`) sobe. C3 (`< 12`) sobe com `< 13` (exploração) e cai com `< 19` (B15), quando o limiar ultrapassa o dele.

**Estrutura (Tversky).**
- **Ausente da referência.** Qualquer parâmetro que C1 e C2 não têm reduz C1 em 0,077 e C2 em 0,054, seja qual for o parâmetro: B1–B4 dão os mesmos escores para C1 e C2.
- **Representado por um candidato.** Se algum candidato tem o parâmetro adicionado, só esse candidato ganha.
- **Na A**, essa invariância ficou escondida em três casos (D7, D8, D11) que pareciam efeitos diferentes.

## 3. Primeira posição

**Na B, a troca do Top-1 segue regras simples, determinadas pela classe do parâmetro e pela direção da mudança:**

| Perturbação | Troca o Top-1? |
|---|---|
| Qualquer adição | sempre (4/4) |
| Omissão do atrito (parâmetro distintivo) | sim |
| Omissão de parâmetro compartilhado | não (0/2) |
| Redução da sobreposição de C1 no atrito com intensidade ≥ 0,5 (B9, B11; e ED13 na exploração) | sim |
| Mesma redução com intensidade 0,25 (B10) | não |
| Atrito na direção permissiva | nunca |
| Limiar da altura, nas duas direções, nas três intensidades exploradas | nunca |
| Combinações | sempre (4/4) |

**A margem pequena de B0 (0,016) explica boa parte disso:** uma troca acontece quando C1 perde mais de 0,016 em relação a C2.

**Na A**, 15 trocas em 19 refletem tanto essa margem quanto a escolha dos casos. Por exemplo, todas as combinações da A incluem adições, e toda adição já troca o Top-1.

## 4. Estabilidade do Top-2 e do Top-3

- **Top-3 na B.** C1, C2 e C3 ficam no Top-3 em todas as configurações e nas 128 perturbações exploradas com escore, inclusive os 81 pares. **Essa estabilidade vale só para o que foi explorado:** no máximo duas modificações simultâneas (três, nas adições múltiplas de parâmetros ausentes).
- **Top-3 na A.** As duas mudanças (D18, D19) aparecem com três e quatro modificações orientadas a C5: os dois parâmetros de C5, o limiar de altura igual ao de C5 e, em D19, a omissão do atrito.
- **Três modificações podem mudar o Top-3 sem convergir para um candidato.** Uma checagem exploratória, fora da bateria, testou as 214 combinações de três perturbações isoladas da B que tocam parâmetros diferentes (`review/order3_combinations.csv`). **Uma delas muda o Top-3:**
  - **A combinação:** B3 + B6 + B15 (aceleração, omissão dos contatos, altura < 19).
  - **O resultado:** C1 > C5 > C2 > C3 > C4.
  - **Por que acontece:** o Given de C2, C3 e C4 é cortado em zero (`max(·, 0)`), e entre eles a ordem passa a depender só do Then.
  - **Margem que decide a composição:** é a distância entre o 3º e o 4º colocado, 0,0196.
  - **Com cardinalidade discreta para inteiros:** a mudança se mantém.
- **Alcance dessa checagem.** Ela mostra que a mudança existe, não com que frequência ocorre: cobre apenas os operadores da bateria.
- **O que se pode afirmar:**
  - com uma ou duas modificações, o Top-3 foi estável em tudo o que exploramos;
  - com três ou mais, pode mudar, quando o Given de vários candidatos chega a zero e um candidato representa as condições adicionadas;
  - a Bateria A chegou a esse regime com combinações orientadas a C5.
- **A afirmação "o Top-3 muda em 2 de 19" diz respeito a configurações de três e quatro modificações**, e não ao efeito de imprecisões isoladas.
- **Top-2 (as tentativas permitidas pelo retry).** Muda em 4/19 na B e em 8/19 na A. Na B, as quatro mudanças envolvem adições representadas por C3 (B1, B2, B16, B19).

## 5. Direção e intensidade

Só a B permite responder.

**Direção (atrito).** Com a mesma intensidade, direções opostas dão efeitos de sinal oposto em C1:

| | d = 0,25 | d = 0,50 | d = 0,75 |
|---|---|---|---|
| Restritivo | −0,010 | −0,020 | −0,030 |
| Permissivo | +0,013 | +0,040 | +0,038 |

A região de C1 (`≤ 0,4`) contém a de B0, por isso o aumento é favorável até o limiar de C1.

**Intensidade.**
- **Restritivo:** o efeito cresce de forma monótona com a intensidade, e o Top-1 troca a partir de 0,5.
- **Permissivo:** não é monótono. O máximo fica perto de 0,4, o limiar de C1, e depois o efeito cai.

**A distância de Jaccard não prevê o impacto no ranking entre parâmetros.** Com d = 0,5, o atrito restritivo troca o Top-1, e a altura, nas duas direções, não troca. O que decide é **quais candidatos representam o parâmetro**.

**Diluição.** Uma mudança na altura afeta menos C1 do que C2: C1 faz a média sobre 3 parâmetros compartilhados, e C2 sobre 2. Por isso, a margem de C1 cresce nas duas direções (0,041 e 0,044).

**Medida das intensidades.** As intensidades da altura estão na medida do Retriever:
- B14 tem d = 0,444, e B15 tem d = 0,500;
- com cardinalidade discreta, seriam 0,400 e 0,474;
- "o mesmo alvo nas duas direções" vale, portanto, na medida do Retriever.

## 6. Interações nas combinações

| | Componentes | Top-1 conjunto (componentes) | Resíduo (conjunto − soma), máx. em módulo |
|---|---|---|---|
| B16 | B2 + B3 | C3 (C3, C2) | 0,029 |
| B17 | B5 + B6 | C2 (C2, C1) | 0,033 |
| B18 | B4 + B5 | C2 (C2, C2) | 0,049 |
| B19 | B1 + B12 | C3 (C3, C1) | **0** |

- **B19 é exatamente aditiva.** Quando o conjunto de parâmetros compartilhados não muda, o termo de região (média dos Jaccard) e o termo estrutural (penalidade) entram separados no escore.
- **Adições e omissões combinadas não são aditivas.** A razão de Tversky não é linear, e a omissão muda o denominador da média.
- **Em B18, C2 fica com o mesmo escore de B0:** trocar um parâmetro que C2 não tem (o atrito) por outro que ele também não tem (a massa) mantém a penalidade.
- **Em todas as combinações, o Top-1 conjunto é o Top-1 de um dos componentes.**
- **A A não analisou interações.** Seus dados até permitiriam, porque cada modificação M1–M11 existe como caso isolado. Mas as combinações de 3 e 4 mudanças misturam vários termos, e o resíduo em relação à soma dos efeitos isolados fica menos interpretável do que em pares.

## 7. Clareza entre perturbação e resultado

**Na B, cada configuração isola uma variável de desenho.** Os efeitos se explicam por três fatores:
- quais candidatos representam o parâmetro;
- se o parâmetro afetado é compartilhado, distintivo ou ausente;
- a direção da mudança de região.

**As categorias também se ligam aos componentes do DejaVú:**
- a altura e os contatos vêm do Identifier;
- o atrito e as condições adicionadas vêm do Diagnoser.

**Na A, a explicação é caso a caso, e alguns efeitos aparentes são artefatos do desenho:**
- D7, D8 e D11 são o mesmo efeito estrutural;
- as mudanças de Top-3 vêm de combinações de três e quatro modificações orientadas a C5.

## 8. Complexidade para o artigo

A B exige explicar, além do que a A explica:
- a taxonomia;
- a medida de intensidade (distância de Jaccard entre a região original e a modificada);
- uma tabela das 19 configurações.

Em troca, o texto de resultados pode seguir as categorias, com uma regra por categoria, em vez de uma narrativa caso a caso. Na prática, fica mais curto e mais fácil de defender.

**O custo da troca:** refazer a figura, a tabela e o texto da RQ2, que já estavam prontos para a A.

## Limitações da Bateria B

- **Uma referência, um catálogo, um exemplar.** O experimento é determinístico; não há teste estatístico, e não deve haver.
- **Margem da referência.** Como a margem de B0 é 0,016, as trocas de Top-1 medem sobretudo se C1 perde mais de 0,016 em relação a C2.
- **Adições.** Usam o predicado do candidato que representa o parâmetro (Jaccard 1), para isolar o efeito estrutural. O efeito de região das condições adicionadas não foi estudado.
- **Categoria C.** Limitada ao atrito, pela origem das imprecisões; B8 é um controle sem efeito.
- **Inconsistência com a observação.** B9, B10 e B11 excluem o atrito observado (0,14). Ficam na bateria porque são imprecisões plausíveis do Diagnoser, e isso fica declarado.
- **Limiares de `finger_contacts`.** Ficaram fora:
  - o limiar restritivo (`< 1`) tem região de comprimento zero na medida do Retriever;
  - os permissivos admitem o resultado esperado, e acima de `< 3` também valores que o sensor não produz (só produz 0–2).
- **Número de modificações simultâneas.** A bateria vai até duas, e a estabilidade do Top-3 só vale até aí (seção 4).
- **Convenção de inteiros.** Os escores e as intensidades seguem a medida do Retriever. Os rankings não dependem dela (seção seguinte).
- **Seleção não cega.** Foi feita conhecendo a Bateria A.
- **Eixo Y da figura de 0,4 a 1.** Todos os escores ficam entre 0,46 e 1,00, e o script confere que nenhum ponto cai fora do eixo.

## Implementação × especificação

> **Não tive acesso ao texto do manuscrito.** A comparação parte do que você descreveu: a especificação distingue domínios contínuos de discretos, o que pressupõe a cardinalidade dos valores admitidos como medida das regiões discretas. A seção 2 de `../analysis.md` da Bateria A dizia que as equações 5.1–5.4 "correspondem à implementação" e tratava a medida como detalhe do código. **Essa afirmação não se sustenta.**

**Onde a implementação diverge da especificação** (`_get_relational_expression_region` e `_calculate_jaccard_similarity`):

1. **Medida das regiões inteiras.** O Retriever mede uma região inteira pelo comprimento entre o menor e o maior valor admitido, e não pela cardinalidade. `x < 10` no domínio 0–100 mede 9, e não 10. É uma divergência de definição, não de redação, e tem duas consequências:
   - todo Jaccard entre limiares inteiros diferentes sai enviesado: J(`< 10`, `< 12`) = 9/11 em vez de 10/12;
   - uma região de um único valor mede 0, e seu Jaccard é 0 até consigo mesma. Isso viola J(A, A) = 1.
2. **Igualdade contra intervalo.** O Retriever conta a interseção como 1 (uma contagem) e a divide por um comprimento.
   - Em domínio inteiro, isso dá 1/(n − 1) em vez de 1/n. Por exemplo, `finger_contacts == 1` contra `< 2` dá 1 em vez de 1/2.
   - Em domínio contínuo, dá valores acima de 1: `lateral_friction == 0.1425` contra `<= 0.1425` dá 7,0. **Isso diverge de qualquer definição de Jaccard, seja qual for a medida.**
3. **União.** É a envoltória dos intervalos, e não a união dos conjuntos. Isso só faz diferença para regiões divididas (`!=`).

**Efeito nos resultados da RQ2:**
- **Divergências 2 e 3:** não ocorrem em nenhuma configuração das duas baterias. Nelas, o Retriever só comparou pares intervalo/intervalo e igualdade/igualdade (`review/metric_pairs.csv`).
- **Divergência 1:** afeta os escores, mas não os rankings. Recalculando com cardinalidade discreta (`review/integer_convention_*.csv`):
  - nenhum ranking muda, nas 20 configurações de nenhuma das duas baterias;
  - a maior diferença de escore é 0,0092 na B e 0,0051 na A;
  - a margem mais afetada é a de D18 da A: cai de 0,0060 para 0,0034, com o mesmo Top-1.

**Conclusão.** Há uma divergência de definição entre a especificação e a implementação. Ela não é material para os resultados da RQ2, mas é material para a métrica em geral: com regiões inteiras de um único valor ou igualdades contra intervalos, que outros catálogos podem conter, o Retriever produz valores que contradizem a definição de Jaccard.

**O que fazer** (decisão de vocês, fora do escopo desta bateria):
- **ou** corrigir a implementação e rodar de novo, para confirmar que os resultados se mantêm;
- **ou** declarar a convenção da implementação no artigo, junto com a análise de sensibilidade.

Corrigir a métrica mudaria o código de produção, que a RQ2 se comprometeu a não alterar.

**Nome do parâmetro de massa.** A Bateria A usa `object_mass`, que não está nos `monitored_parameters`; o nome do catálogo é `objects_object_1_mass`. Os escores não mudam, porque nenhum candidato tem o parâmetro (B4 = D11). Ao adotar a B, o artigo deve usar `objects_object_1_mass`.

## Recomendação

**Substituir a Bateria A pela B como avaliação principal da RQ2.** A B não é melhor por trocar mais o ranking; ela troca menos. É melhor porque:

1. **É mais defensável:** critérios declarados antes dos escores, intensidade medida com a métrica do próprio Retriever, nenhum limiar ajustado a um candidato, e as exclusões registradas;
2. **Atribui os efeitos com mais clareza:** separa região de estrutura, parâmetro compartilhado de distintivo, e direção de intensidade;
3. **Situa corretamente a conclusão da A sobre o Top-3:** as mudanças vêm de configurações com três e quatro modificações, e não de imprecisões isoladas ou em pares.

Com a B, a resposta à RQ2 fica assim:
- **Top-3:** com uma ou duas modificações simultâneas, a composição não muda em nenhuma das perturbações exploradas.
- **Top-1:** muda conforme a classe do parâmetro afetado e a direção da mudança, muitas vezes por margens pequenas.
- **Conjunto das duas tentativas:** muda em 4 de 19.
- **Com três modificações:** o Top-3 pode mudar, como mostram a checagem exploratória de ordem 3 e a Bateria A.

Essa última parte entra como limite declarado do alcance, e não como frequência.

**Os casos de convergência da A** (D15, D19, D18) podem entrar como **análise complementar, rotulada como tal**. Apresentá-los como parte da avaliação de robustez a imprecisões isoladas seria enganoso.
