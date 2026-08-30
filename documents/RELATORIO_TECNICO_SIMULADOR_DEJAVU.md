# Relatório técnico — Self-Adaptive ARM Simulator e camada DejaVu

**Data da análise:** 25 de agosto de 2026  
**Escopo:** estado atual do repositório, incluindo código-fonte, configurações, cenários ASM, catálogos, datasets, traces, consoles, scripts experimentais e documentação.  
**Objetivo:** explicar como o sistema funciona, o que o simulador robótico permite fazer, como a situação não prevista é produzida e tratada e como avaliar cientificamente o DejaVu.

---

## 1. Resumo executivo

O projeto é um protótipo funcional de um sistema ciberfísico autoadaptativo em três camadas:

1. **Managing System:** simulação física de um braço Franka Panda no PyBullet, executando uma entrega de objeto em cinco subtarefas;
2. **Manager:** laço MAPE-K que monitora percepções, avalia cenários antecipados em um ASM e emite comandos de continuação ou adaptação;
3. **DejaVu:** camada de tratamento de cenários não antecipados, baseada em máquina de estados, diagnóstico por árvore de decisão, busca de casos semelhantes, recomendação de adaptação, avaliação do resultado e evolução do ASM.

O caso principal já presente no repositório é a **perda de aderência do cubo por baixa fricção lateral**. Com `lateral_friction` normal (`0.5`), a sequência termina normalmente. Com valores próximos de `0.13`–`0.14`, o cubo escorrega durante a elevação. O contrato formal de `LIFT_OBJECT` falha e o DejaVu:

- identifica o cenário violado;
- associa a falha à condição `lateral_friction <= 0.1475`, aprendida dos datasets existentes;
- recupera do catálogo o caso “Lift Slip — Low Friction”;
- recomenda `apply_vacuum_assist()`;
- o simulador aumenta a fricção dos dedos, reagarra e reeleva o cubo;
- o avaliador confirma o pós-estado de elevação;
- o evolutor acrescenta ao ASM um cenário específico para baixa fricção.

Há evidência concreta desse fluxo nos traces de 17/08/2026. Portanto, o projeto já demonstra o ciclo conceitual completo **detectar → identificar → diagnosticar → reutilizar → adaptar → avaliar → evoluir**.

Entretanto, ainda não é seguro tratá-lo como uma plataforma experimental madura. Os principais bloqueios são:

- o ASM evoluído usa `lateral_friction`, mas o Manager não fornece essa variável ao avaliador do ASM;
- a evolução não é atômica nem idempotente e a máquina Sismic não é regenerada automaticamente;
- a tarefa de elevação termina pela altura do efetuador, não pela altura real do cubo;
- a detecção ocorre apenas na fronteira entre fases, embora os sinais físicos indiquem o deslizamento antes;
- os experimentos existentes não garantem independência, sementes, reinicialização das três camadas ou validação estatística;
- os ambientes Python e o `requirements.txt` não reproduzem atualmente toda a execução;
- obstáculos são manipuláveis e percebidos, mas ainda não participam do caso adaptativo nem de um planejador de desvio.

Minha avaliação é: **o repositório é um bom demonstrador de pesquisa para a arquitetura DejaVu, mas precisa de correções de consistência, reprodutibilidade e validade experimental antes de sustentar conclusões fortes sobre eficácia de SAS/CPS**.

---

## 2. Como a análise foi realizada

Foram inspecionados os cinco processos da solução, seus arquivos de configuração, todos os módulos Python do repositório, os documentos técnicos, os datasets de treinamento e os traces persistidos. Ao todo, 111 arquivos Python passaram por validação sintática via AST.

Também foram feitos testes isolados usando o ambiente `temp_dejavu`, que contém as dependências necessárias:

- replay do caminho nominal;
- replay de falha durante elevação;
- replay de falha tardia;
- reprodução direta da regra aprendida pelo diagnosticador;
- reprodução do ranking do adaptador por similaridade;
- testes do comportamento do avaliador e do evolutor sobre cópias temporárias.

Não foi reexecutada a aplicação gráfica integrada inteira. A `.venv` usada pelo launcher não contém várias dependências de runtime. Assim, este relatório combina análise estática integral com replay e testes isolados dos artefatos reais, sem afirmar uma nova execução ponta a ponta da GUI.

---

## 3. Arquitetura executável

```text
┌───────────────────────────────────────────────────────────────────────┐
│ 2-managing — Managed System / PyBullet (HTTP :8000)                  │
│ Panda + cubo + mesa + sensores + controlador de subtarefas           │
└─────────────────────────┬─────────────────────────────────────────────┘
                          │ percepção, uma vez por passo
                          ▼ WebSocket
┌───────────────────────────────────────────────────────────────────────┐
│ 1-manager — Managing System / MAPE-K (HTTP :8001)                    │
│ Monitor → Analyzer/ASM → Planner → Executor                           │
└─────────────────────────┬─────────────────────────────────────────────┘
                          │ checkpoint síncrono
                          ▼ WebSocket
┌───────────────────────────────────────────────────────────────────────┐
│ 3-dejavu — meta-adaptação (HTTP :8002)                               │
│ monitor → identificar → diagnosticar → buscar → recomendar           │
│ → avaliar → evoluir                                                   │
└─────────────────────────┬─────────────────────────────────────────────┘
                          │ adaptação recomendada
                          ▼
                   Manager → PUT /task → Managing
```

Os consoles são auxiliares:

- `0-console`: edição/visualização do ASM e inicialização dos três processos;
- `4-dejavu-console`: configuração e visualização da máquina de estados e do catálogo.

### 3.1 Sincronização

Cada passo do simulador envia uma percepção ao Manager e aguarda resposta por até cinco segundos. O Manager consulta o DejaVu antes de devolver o comando. Essa sincronização facilita traces determinísticos, mas acopla a taxa da física à latência das duas camadas de controle.

Se o DejaVu estiver indisponível, o Manager continua operando de forma degradada com seus cenários antecipados. Essa é uma propriedade útil de tolerância a falha arquitetural.

### 3.2 Prioridade de decisão

O Manager possui duas adaptações antecipadas próprias:

- `RETRY_GRASP`: contato insuficiente e menos de três tentativas;
- `SAFE_ABORT`: contato insuficiente após três tentativas.

Uma adaptação proposta pelo DejaVu tem prioridade quando ele declara cenário não antecipado e devolve uma ação, desde que o objetivo interno do ASM não esteja marcado como violado. Caso contrário, permanece a decisão local do MAPE-K.

---

## 4. O que o simulador robótico faz

### 4.1 Caso executado por padrão

O `main.py` do Managing cria sempre uma `ObjectDeliverySequence`:

```text
APPROACH_OBJECT
  → GRASP_OBJECT
  → LIFT_OBJECT
  → TRANSPORT_OBJECT
  → PLACE_OBJECT
  → FINAL
```

O controle é procedural, não aprendizado por reforço. As ações normalizadas comandam deslocamentos cartesianos do efetuador (`dx`, `dy`, `dz`) e abertura/fechamento da garra. A recompensa exposta pelo ambiente é essencialmente uma métrica de distância; não existe agente aprendendo uma política no fluxo atual.

### 4.2 Capacidades implementadas

O código inclui tarefas de:

- alcançar uma posição (`REACH`);
- empurrar (`PUSH`);
- pegar e colocar (`PICK_AND_PLACE`);
- manter posição (`HOLD`);
- controle manual e por API;
- entrega sequencial de objeto;
- tentar a pegada novamente;
- abortar de forma segura;
- aplicar assistência por “vácuo”.

Também existem APIs para:

- mover, adicionar e remover obstáculos;
- mover o objeto;
- mover a base do robô;
- mover o alvo e escolher modo de objetivo;
- configurar waypoints.

### 4.3 Sensoriamento disponível

As percepções incluem:

- posição e velocidade do efetuador;
- abertura da garra;
- posição, orientação e velocidade do cubo;
- juntas do robô;
- contatos físicos reais de cada dedo, consultados no PyBullet;
- interseção em XY do trajeto com obstáculos;
- parâmetros estáticos, como massa, tamanho e fricção.

Esses sinais são suficientes para construir detectores físicos melhores do que o atual, em particular um detector online de deslizamento.

### 4.4 Limites atuais da parte robótica

1. **Elevação mede o elemento errado.** `LiftObjectTask.done()` usa a altura do efetuador. O efetuador pode subir sem o cubo, fazendo o Managing avançar para transporte mesmo após uma pegada perdida.
2. **Obstáculos não têm comportamento associado.** Eles podem ser inseridos e são percebidos, mas não existe planejamento de trajetória, desvio, cenário ASM ou adaptação conectada a essa percepção.
3. **“Vácuo” é uma abstração.** A adaptação aumenta a fricção lateral dos dedos para `3.0`, desce, reagarra e reeleva. Não há ventosa ou força de sucção modelada.
4. **A fricção elevada não é restaurada.** Isso contamina fases ou episódios posteriores e compromete independência experimental.
5. **Múltiplos alvos não funcionam no fluxo atual.** Após a primeira colocação, `_seq_done` permanece verdadeiro; por isso o experimento com quatro posições de alvo tende a não executar quatro entregas.
6. **A fábrica está incompleta.** Existe uma tarefa terminal, mas `_make_task` não contém seu caso.
7. **API e documentação divergem.** O endpoint de tarefa hoje espera comandos `continue`, `adapt` ou `transition`; o formato antigo `{strategy: ...}` documentado é ignorado.

---

## 5. Modelo ASM e cenários antecipados

O ASM representa contratos no padrão **Given–When–Then**, além de uma ação `Do` em cenários adaptativos/evolutivos.

| Fase | Given relevante | When | Then esperado |
|---|---|---|---|
| Aproximar | objeto disponível, garra aberta | tarefa iniciada | distância efetuador–objeto ≤ 2 cm |
| Agarrar | garra aberta | distância ≤ 2 cm | `grasp_completed == 1` |
| Elevar | dois contatos | pegada concluída | cubo ≥ 10 cm e dois contatos |
| Transportar | dois contatos | cubo ≥ 10 cm | distância ao alvo ≤ 5 cm, altura e contatos mantidos |
| Colocar | altura e contatos válidos | distância ≤ 5 cm | distância ≤ 5 cm e garra aberta |

Há ainda os dois cenários adaptativos antecipados de nova tentativa e aborto seguro.

### 5.1 Fragilidades semânticas

- `object_available` e `task_started` são fixados em `1`, em vez de derivados do mundo.
- `grasp_completed` é inferido principalmente pela largura da garra; uma garra fechada e vazia pode ser classificada como pegada concluída.
- Os contatos físicos são outra variável, criando possível incoerência entre “pegada” e “contato”.
- O Manager avança a fase do ASM quando `current_subtask` muda, mesmo que o `Then` anterior não tenha sido satisfeito; ele apenas registra o aviso.
- Tentativas de pegada e alguns estados do monitor não são reinicializados claramente entre episódios.

A camada DejaVu acaba compensando parte dessa permissividade: o Managing já mudou para a próxima subtarefa, mas a máquina formal ainda valida o pós-estado da ação anterior.

---

## 6. Onde e como a situação não prevista é criada

O ponto de injeção recomendado pelo próprio caso é:

`2-managing/configs/environments/environment.yaml`

Parâmetro:

```yaml
objects:
  object_1:
    lateral_friction: 0.5
```

- `0.5`: caminho nominal nos dados existentes;
- aproximadamente `0.13`–`0.14`: deslizamento durante `LIFT_OBJECT` nos traces atuais;
- `0.155`: execução histórica em que a violação formal aparece mais tarde, próxima da colocação.

Esses números não são constantes universais. Dependem da massa, tamanho, velocidade, configuração do solver, fricção dos dedos, pose e versão do simulador. Há comentários conflitantes no repositório citando `0.120`, `0.124`, `0.125`, `0.126`, `0.130` e `0.155`; portanto, a fronteira deve ser tratada como variável experimental.

A fricção é lida na criação do corpo físico. Alterar o YAML durante uma execução não atualiza o PyBullet. É necessário reiniciar o Managing — e, para um ensaio independente, reiniciar as três camadas.

---

## 7. Linha do tempo real do caso de baixa fricção

### 7.1 Caminho nominal

Os cinco datasets `happy_path` existentes têm:

- `lateral_friction = 0.5`;
- 69 passos;
- nenhuma observação `sat == false`.

Os cinco arquivos são byte a byte idênticos. Eles comprovam determinismo do caso salvo, mas não equivalem a cinco replicações independentes.

### 7.2 Falha durante elevação

Nos datasets com fricção `0.13` ou `0.14`:

1. o braço aproxima e fecha a garra;
2. o efetuador começa a subir;
3. o cubo desliza em relação aos dedos;
4. a tarefa local considera a elevação concluída pela altura do efetuador;
5. o Managing muda para `TRANSPORT_OBJECT`;
6. ao processar o evento formal `lift_object()`, o DejaVu verifica o `Then` da elevação;
7. altura real e/ou contatos do cubo são inválidos;
8. a máquina entra em `ERR_19` e produz `sat = false`.

Nos traces analisados, a primeira violação ocorre no **passo 23**. Portanto:

> A falha física pertence a `LIFT_OBJECT`, embora a percepção que dispara a verificação já informe `TRANSPORT_OBJECT`.

Essa diferença é essencial ao rotular datasets e ao explicar o comportamento.

### 7.3 Sinais físicos antecipados

A documentação e os dados do caso mostram que o escorregamento poderia ser percebido antes da violação formal por:

- aumento da distância relativa cubo–efetuador;
- divergência vertical entre cubo e efetuador;
- inclinação crescente do cubo;
- velocidade relativa com a garra fechada;
- perda parcial ou total de contato.

No estudo salvo, sinais surgem por volta dos passos 17–18, enquanto uma violação tardia apareceu no passo 41. Isso sugere margem de aproximadamente 24 passos para detecção proativa. Contar apenas `finger_contacts == 2` não basta, porque o objeto pode deslizar mantendo contato momentâneo.

---

## 8. Funcionamento detalhado do DejaVu

### 8.1 Monitor formal

O ASM é convertido em uma máquina Sismic. Cada cenário segue aproximadamente:

```text
estado anterior
  → PHI Given
  → espera da ação S
  → PHI Then
  → S concluído, se SAT
  → ERR, se UNSAT
```

Eventos de ação são sintetizados quando `current_subtask` muda. Há um ajuste de temporização/rewind para que o pós-estado seja verificado na percepção correta.

Os estados `ERR` são terminais. Depois da primeira violação, o monitor continua retornando UNSAT nos passos restantes. O pipeline pesado roda apenas uma vez, protegido por um marcador de cenário identificado.

### 8.2 Identificação

O identificador recupera o cenário cuja pós-condição falhou e cria uma descrição não antecipada. No caso observado:

```text
name: LIFT_OBJECT_unanticipated
given: (object_lift_height_cm < 10) AND (finger_contacts < 2)
when:  grasp_completed == 1
then:  pós-condição original de LIFT_OBJECT
```

Limitação lógica: para negar uma conjunção, o complemento geral seria uma disjunção. O código nega cada cláusula falsa e as une com `AND`, descrevendo a observação concreta, mas não todo o espaço de violação. O parser também depende de ` AND ` em caixa alta.

### 8.3 Diagnóstico

O diagnosticador:

1. carrega os CSVs históricos;
2. resume cada execução por parâmetros estáticos da primeira linha;
3. rotula a execução como falha se qualquer linha teve `sat = false`;
4. treina uma árvore de decisão de profundidade máxima 3;
5. extrai a condição que separa falhas e sucessos;
6. acrescenta essa condição ao cenário identificado.

Com os dados atuais, o resultado reproduzido foi:

```text
lateral_friction <= 0.1475
```

Esse valor é o ponto médio aprendido entre amostras próximas, não uma lei física. Não há conjunto de teste, validação cruzada, intervalo de confiança, controle de duplicatas ou teste fora da distribuição. Se houver múltiplas folhas positivas, o código as combina com `AND`, quando caminhos alternativos normalmente deveriam ser unidos por `OR`.

### 8.4 Similaridade e recuperação de caso

O adaptador compara o cenário diagnosticado com o catálogo usando uma composição de Jaccard condicional e penalidade de Tversky. O ranking reproduzido foi:

| Posição | Caso do catálogo | Similaridade |
|---:|---|---:|
| 1 | Lift Slip — Low Friction | 0.92986 |
| 2 | Parallel Gripper Contact Loss | 0.89655 |
| 3 | Lightweight Object Height | 0.73125 |
| 4 | Grip Pressure | 0.61494 |
| 5 | Motor Overload | 0.50000 |
| 6 | Vacuum Loss | 0.33333 |

O recomendador escolhe sempre o primeiro. Não existe limiar mínimo, rejeição por baixa confiança, verificação de que a ação é executável nem comparação semântica do `Do`. O `When` comum entre casos também contribui uma parcela constante relevante para a pontuação. Consequentemente, a métrica é útil como ranking demonstrativo, mas não deve ser interpretada como probabilidade de sucesso.

### 8.5 Adaptação

O caso vencedor recomenda:

```text
apply_vacuum_assist()
```

O Manager envia a ação ao Managing. `VacuumAssistTask`:

1. aumenta a fricção dos dedos para `3.0`;
2. desce até o cubo;
3. fecha a garra novamente;
4. eleva;
5. retorna para `TRANSPORT_OBJECT`.

No trace de sucesso, a adaptação ocupa aproximadamente os passos 24–34 e a sequência é retomada no passo 35.

Somente essa ação do catálogo possui implementação concreta no simulador. Se outro candidato alcançar o primeiro lugar, o Manager pode registrar ação desconhecida e não efetivar a recomendação.

### 8.6 Avaliação

Depois que a subtarefa adaptativa termina, o avaliador verifica o `Then` original de `LIFT_OBJECT`. No trace, o primeiro passo pós-adaptação satisfaz altura e contatos, sendo marcado como sucesso.

Isso prova recuperação do contrato local, mas não prova:

- estabilidade da pegada por vários passos;
- conclusão do transporte;
- colocação correta;
- ausência de colisões ou efeitos colaterais;
- restauração dos parâmetros físicos.

O timeout também só avança depois que o sistema sai da subtarefa adaptativa. Se ela ficar travada, o avaliador pode esperar indefinidamente.

### 8.7 Evolução

Após avaliação positiva, o evolutor divide o cenário de elevação em duas regiões:

```text
Cenário antigo:
finger_contacts >= 2 AND lateral_friction > 0.1475

Novo cenário evolutivo:
finger_contacts >= 2 AND lateral_friction <= 0.1475
do: apply_vacuum_assist()
```

Conceitualmente, isso transforma conhecimento episódico em conhecimento arquitetural persistente: numa execução futura de baixa fricção, a condição deveria ser antecipada pelo Manager.

Na implementação atual há quatro problemas críticos:

1. `SystemState.to_eval_dict()` do Manager não expõe `lateral_friction`; os dois cenários evoluídos passam a falhar na avaliação após reinício.
2. O JSON é sobrescrito diretamente, sem arquivo temporário, validação transacional ou backup.
3. Repetir a evolução duplica condições e transições; testes em cópia produziram `lateral_friction > 0.1475` repetido e quatro transições de entrada.
4. A máquina Sismic do DejaVu não é regenerada nem recarregada automaticamente. É preciso regenerá-la e reiniciar as camadas relevantes.

Além disso, o gerador reconhece explicitamente o tipo `adaptive`, mas trata `evolutionary` como um cenário de domínio comum. Isso deve ser uma escolha consciente e testada, não um efeito implícito.

---

## 9. Evidências preservadas no repositório

### 9.1 Datasets

Foram encontrados dez CSVs úteis:

- cinco caminhos nominais, fricção `0.5`, 69 linhas, zero UNSAT;
- uma falha tardia, fricção `0.155`, 73 linhas, primeira violação no passo 41;
- uma falha de elevação, fricção `0.14`, primeira violação no passo 23;
- três falhas de elevação, fricção `0.13`, aproximadamente 69–70 linhas, primeira violação no passo 23.

Cinco arquivos nominais são idênticos entre si, e pelo menos dois arquivos de falha `0.13` também são idênticos. Eles não devem ser tratados como evidência estatística independente.

### 9.2 Traces de sucesso do pipeline

O conjunto de traces de 17/08/2026 documenta:

- `3-dejavu/output/arm/traces/trace_20260817_012125.log`: identificação, diagnóstico, ranking, recomendação, avaliação e evolução;
- `1-manager/traces/trace_20260817_012123.log`: transição para transporte, resposta do DejaVu e envio da adaptação;
- `2-managing/traces/trace_20260817_012124.log`: execução de `VACUUM_ASSIST` e retomada da sequência.

Há traces históricos mais antigos com erros como acesso a `.columns` em `None` e falhas de parsing de expressões. Eles mostram que o pipeline evoluiu, mas também reforçam a necessidade de testes de regressão.

### 9.3 Resultados dos replays desta análise

| Entrada | Primeira violação reproduzida |
|---|---|
| Caminho nominal | nenhuma |
| Escorregamento na elevação | passo 23, `ERR_19`, percepção já em `TRANSPORT_OBJECT` |
| Escorregamento tardio | passo 41, `ERR_23`, percepção em `PLACE_OBJECT` |

O diagnóstico `lateral_friction <= 0.1475` e o ranking de similaridade acima também foram reproduzidos diretamente.

---

## 10. Como exercitar o DejaVu manualmente

Antes do ensaio, é necessário corrigir ou recriar o ambiente Python. O `requirements.txt` atual não lista várias dependências centrais, embora o README apresente comandos manuais mais completos. A `.venv` acionada pelos launchers está incompleta no estado analisado.

### 10.1 Preparação recomendada

1. Faça uma cópia de `1-manager/configs/asm/asm.json`; a evolução o modifica em disco.
2. Use uma única versão compatível de Python e instale PyBullet, panda-gym, Gymnasium, FastAPI, Uvicorn, NumPy, SciPy, PyYAML, pandas, scikit-learn, SymPy, Sismic, wrapt, pyparsing, websockets, Streamlit, streamlit-agraph e Graphviz.
3. Confirme que não há processos antigos usando as portas 8000, 8001, 8002, 8501 e 8502.
4. Gere a máquina do DejaVu a partir do ASM que será usado no ensaio.
5. Para resultados limpos, reinicie Managing, Manager e DejaVu a cada execução.

### 10.2 Ensaio A — baseline nominal

1. Defina `lateral_friction: 0.5` em `environment.yaml`.
2. Inicie Managing, Manager e DejaVu. O console ASM também pode iniciar os três processos; o `start.bat` inicia somente os consoles.
3. Espere a sequência alcançar `FINAL`.
4. Verifique que não houve `sat = false`.
5. Preserve o CSV e os três traces com um identificador único de execução.

### 10.3 Ensaio B — situação não prevista

1. Restaure o mesmo ASM do baseline.
2. Altere apenas `lateral_friction` para `0.13` ou `0.14`.
3. Reinicie as três camadas.
4. Observe o escorregamento durante a subida.
5. Espere uma violação de `LIFT_OBJECT` por volta da transição para transporte.
6. Confirme no trace do DejaVu:
   - cenário identificado;
   - condição diagnosticada;
   - ranking de casos;
   - seleção de `apply_vacuum_assist()`;
   - início da avaliação;
   - resultado da avaliação;
   - alteração proposta/aplicada ao ASM.
7. Confirme no Managing a execução de `VACUUM_ASSIST` e a retomada de `TRANSPORT_OBJECT`.
8. Não considere o ensaio bem-sucedido apenas porque o avaliador local retornou sucesso; confira também a colocação final do cubo.

### 10.4 Ensaio C — conhecimento evoluído

Este ensaio só deve ser usado após corrigir a ausência de `lateral_friction` no estado avaliável do Manager e tornar a evolução consistente.

1. Regere a máquina Sismic a partir do ASM evoluído.
2. Reinicie Manager e DejaVu para eliminar estado residual.
3. Execute novamente com fricção baixa.
4. O comportamento esperado é que o novo cenário seja reconhecido como conhecimento antecipado/evolutivo, e não novamente como descoberta não antecipada.
5. Verifique se a adaptação ocorre antes da falha física e se a execução completa termina com o cubo no alvo.

---

## 11. Protocolo experimental recomendado

Uma avaliação defensável deve separar três perguntas:

1. **Detecção:** o sistema percebe corretamente uma situação não antecipada?
2. **Adaptação:** a resposta recupera o objetivo do sistema?
3. **Evolução:** o conhecimento persistido evita a recorrência da mesma surpresa sem introduzir regressões?

### 11.1 Tratamentos

Compare pelo menos:

| Grupo | DejaVu | Evolução | Finalidade |
|---|---:|---:|---|
| Controle | não | não | medir comportamento físico sem recuperação |
| Adaptação | sim | não/persistência descartada | medir recuperação episódica |
| Evolução | sim | sim | medir benefício em execuções futuras |
| Oráculo opcional | adaptação conhecida | não | limite superior para tempo/sucesso da resposta |

### 11.2 Variáveis experimentais

Comece com uma varredura de fricção, por exemplo:

```text
0.10, 0.12, 0.13, 0.14, 0.145, 0.15, 0.155, 0.20, 0.50
```

Depois amplie para:

- massa e tamanho do cubo;
- pose inicial e distância de transporte;
- velocidade do braço;
- fricção dos dedos e da mesa;
- ruído/atraso de percepção;
- perda temporária de comunicação;
- obstáculos, somente depois de implementar planejamento e contratos correspondentes.

Use ao menos 20–30 sementes por combinação se a intenção for inferência quantitativa. Caso a simulação permaneça determinística, introduza perturbações controladas e registre a semente; repetir arquivos idênticos não aumenta evidência.

### 11.3 Rotulagem temporal

Registre separadamente:

- início físico do deslizamento;
- perda de um e de dois contatos;
- primeira divergência vertical cubo–efetuador;
- primeira inclinação anormal;
- transição da subtarefa;
- primeira violação formal;
- início e fim da adaptação;
- recuperação sustentada;
- sucesso ou falha da entrega completa.

Uma possível definição de início físico é a combinação de garra fechada com crescimento persistente, por `k` passos, da distância relativa ou de `cube_z - ee_z`, apoiada por inclinação/velocidade relativa. Os limiares devem ser calibrados em dados nominais e depois congelados para o teste.

### 11.4 Métricas

**Detecção**

- precisão, recall e F1;
- taxa de falso positivo no caminho nominal;
- latência entre início físico e detecção formal;
- proporção de falhas detectadas antes da perda irreversível.

**Diagnóstico e recuperação de caso**

- acurácia e estabilidade da regra aprendida;
- variação do limiar entre folds/sementes;
- top-1, top-k e Mean Reciprocal Rank do caso correto;
- taxa de rejeição correta quando nenhum caso é aplicável;
- taxa de recomendações realmente executáveis.

**Adaptação**

- recuperação sustentada da pegada;
- sucesso da entrega ponta a ponta;
- passos/tempo até recuperação;
- distância percorrida e proxy de energia;
- colisões, quedas e violações de segurança;
- efeitos residuais, como fricção não restaurada.

**Evolução**

- reconhecimento antecipado na segunda exposição;
- redução de latência e aumento da taxa de sucesso;
- ausência de regressão nos casos de fricção normal;
- validade, idempotência e reversibilidade do ASM gerado;
- consistência entre ASM do Manager e máquina do DejaVu.

### 11.5 Separação dos dados

- deduplicate os CSVs atuais;
- separe por execução, nunca por linha, para evitar vazamento temporal;
- use níveis de fricção e sementes não vistos no teste;
- reserve testes fora da distribuição, por exemplo alteração conjunta de massa e fricção;
- mantenha um ASM limpo por replicação;
- registre versão do código, configuração, semente, ambiente Python e hash dos artefatos.

---

## 12. Problemas do executor de experimentos atual

`5-experiments/build_simulations.py` e `execute_simulations.py` não são suficientes para o protocolo acima:

- o executor aponta para `2-managing/managing/main.py`, que não existe; o caminho atual é `2-managing/src/main.py`;
- apenas o Managing é iniciado, sem garantir Manager e DejaVu limpos;
- as execuções tendem a reutilizar `episode = 1`, dificultando o reset do DejaVu;
- o Manager também conserva estado de monitor/evaluator entre episódios;
- o gerador anuncia headless, mas configura renderização humana;
- as configurações incluem quatro alvos, incompatíveis com o estado terminal atual da sequência;
- o script remove e recria a pasta de simulações, o que exige cuidado com configurações versionadas.

O executor deve orquestrar os três processos ou usar endpoints explícitos de reset, gerar `run_id` único, aguardar health checks, encerrar processos de forma controlada e preservar logs por execução.

---

## 13. Riscos técnicos e lacunas de validade

### Críticos — corrigir antes de avaliar evolução

1. Expor `lateral_friction` em `SystemState.to_eval_dict()` e no contrato de parâmetros monitorados.
2. Tornar a evolução transacional: copiar, modificar, validar, gravar em arquivo temporário, substituir atomicamente e manter backup.
3. Tornar a evolução idempotente e impedir duplicação de condições/cenários/transições.
4. Regenerar e recarregar a máquina Sismic após evolução, ou exigir reinício controlado e verificável.
5. Reinicializar Manager, DejaVu, monitor, tentativas e parâmetros físicos por `run_id`/episódio.
6. Corrigir `LiftObjectTask.done()` para validar o cubo, não somente o efetuador.

### Altos — corrigir antes de alegar robustez

7. Fazer o timeout avançar também enquanto a adaptação estiver ativa.
8. Exigir sucesso sustentado e entrega completa na avaliação, não um único tick do pós-estado local.
9. Restaurar a fricção dos dedos após a adaptação.
10. Definir recuperação formal após `ERR`; hoje a máquina permanece terminalmente UNSAT.
11. Implementar limiar de similaridade, opção “nenhum caso aplicável” e filtro de ações executáveis.
12. Corrigir composição lógica de folhas da árvore e adicionar validação cruzada/confiança.
13. Substituir `eval` irrestrito por interpretador seguro e validar expressões/esquemas.

### Médios — engenharia e comunicação

14. Corrigir `requirements.txt` e adotar lockfile/ambiente único reproduzível.
15. Adicionar testes unitários, de contrato, replay e integração.
16. Corrigir executor experimental, múltiplos alvos e fábrica de tarefas.
17. Alinhar README, comentários de limiar, endpoints e estado real de implementação.
18. Completar as telas de similaridades e cenários verificados, hoje essencialmente stubs.
19. Integrar obstáculos a cenários e planejamento antes de apresentá-los como capacidade adaptativa.

---

## 14. Roadmap sugerido

### Etapa 1 — baseline reproduzível

- consolidar dependências;
- adicionar health checks e `run_id`;
- corrigir reinicialização e executor;
- criar testes de replay para os três datasets representativos;
- congelar configurações e sementes.

### Etapa 2 — correção semântica

- alinhar conclusão das tarefas aos pós-estados físicos;
- disponibilizar todos os parâmetros usados pelo ASM;
- corrigir evaluator e evolução transacional/idempotente;
- regenerar o monitor automaticamente;
- restaurar parâmetros após adaptações.

### Etapa 3 — avaliação do DejaVu

- produzir dados independentes;
- executar tratamentos controle/adaptação/evolução;
- medir detecção, diagnóstico, recuperação e regressão;
- relatar incerteza estatística e casos de falha.

### Etapa 4 — detecção proativa e novos casos

- criar detector de deslizamento durante a elevação;
- comparar detecção reativa por contrato com detecção preditiva física;
- introduzir massa, velocidade, ruído e comunicação como perturbações;
- somente então implementar o caso de obstáculos com planner e contratos próprios.

---

## 15. Leitura como pesquisa em SAS, CPS e robótica

### Contribuição demonstrada

O projeto materializa uma separação interessante entre:

- **controle do sistema físico**, no Managing;
- **adaptação antecipada**, no MAPE-K/ASM;
- **meta-adaptação para o desconhecido**, no DejaVu;
- **memória de longo prazo**, nos datasets, catálogo e evolução do ASM.

O caso de escorregamento é adequado para CPS porque liga uma perturbação física contínua — fricção — a sintomas observáveis, violação de contrato discreto, adaptação do controlador e alteração do modelo de conhecimento.

### O que ainda precisa ser demonstrado

Para sustentar que o sistema é verdadeiramente autoadaptativo e evolutivo, não basta mostrar um trace de sucesso. É necessário demonstrar:

- detecção correta em uma região de condições e não apenas numa execução;
- ausência de falsos positivos nominais;
- ação apropriada e segura;
- sucesso ponta a ponta, e não somente pós-condição local;
- ganho mensurável na segunda exposição após evolução;
- ausência de regressão após alterar o ASM;
- consistência e auditabilidade do conhecimento gerado.

Assim, a formulação científica mais precisa hoje é:

> O repositório implementa uma prova de conceito integrada de tratamento de cenários não antecipados em um braço robótico simulado, com evidência de recuperação e evolução em um caso de baixa fricção, mas ainda sem a infraestrutura e a amostragem necessárias para validar robustez, generalização e segurança.

---

## 16. Perguntas de pesquisa possíveis

1. Quanto antes um detector multimodal de deslizamento identifica a falha em comparação com a violação Given–When–Then na fronteira de fase?
2. A recuperação baseada em similaridade supera uma política fixa de retry/abort em taxa de sucesso e custo?
3. O cenário evoluído reduz latência e falhas numa segunda exposição sem degradar o caminho nominal?
4. Quão estável é a condição diagnosticada sob variações de massa, semente, velocidade e ruído?
5. Qual limiar de similaridade equilibra cobertura e recomendações incorretas?
6. Avaliação local de pós-condição prediz sucesso global da missão?
7. Como garantir evolução segura do modelo em runtime por validação, rollback e invariantes?

---

## 17. Contexto compacto para fornecer a outro ChatGPT

O texto abaixo pode ser copiado como contexto inicial para uma discussão de avaliação:

```text
Tenho um protótipo de sistema ciberfísico autoadaptativo com um Franka Panda em
PyBullet. O Managing executa APPROACH → GRASP → LIFT → TRANSPORT → PLACE. Um
Manager MAPE-K avalia cenários Given–When–Then de um ASM. Uma camada DejaVu
mantém uma máquina Sismic e, ao encontrar UNSAT, identifica o cenário, aprende
uma condição a partir de datasets por árvore de decisão, compara o caso com um
catálogo por similaridade, recomenda uma adaptação, avalia seu pós-estado e
evolui o ASM.

O caso estudado reduz lateral_friction do cubo de 0.5 para aproximadamente
0.13–0.14. O cubo desliza em LIFT, mas a tarefa local termina pela altura do
efetuador e muda para TRANSPORT. No passo 23, o DejaVu valida lift_object(),
entra em ERR_19 e diagnostica lateral_friction <= 0.1475. O catálogo ranqueia
“Lift Slip — Low Friction” com 0.92986 e recomenda apply_vacuum_assist(). A
adaptação eleva a fricção dos dedos para 3.0, reagarra, reeleva e retorna ao
transporte. O avaliador confirma o Then local e o evolutor cria uma região de
baixa fricção no ASM.

Limitações críticas: lateral_friction não é fornecida pelo Manager ao ASM
evoluído; evolução não é atômica/idempotente; Sismic não é regenerado
automaticamente; ERR é terminal; avaliação verifica um tick local, não a
entrega; timeout não avança durante adaptação; fricção dos dedos não é
restaurada; datasets têm muitas duplicatas; árvore não tem validação; ranking
sempre escolhe top-1 sem limiar; obstáculos não estão integrados ao controle;
executor experimental não reinicia corretamente as três camadas.

Quero propor uma avaliação rigorosa separando detecção, diagnóstico/recuperação,
adaptação e evolução. Compare controle sem DejaVu, adaptação episódica, evolução
persistente e opcionalmente um oráculo. Faça varredura de fricção com 20–30
sementes, depois varie massa, velocidade e ruído. Meça precisão/recall/FPR,
latência desde o início físico do slip, top-k/MRR, taxa de ação executável,
recuperação sustentada, sucesso ponta a ponta, custo/tempo, segurança,
idempotência do ASM e regressão nominal. Separe datasets por execução, elimine
duplicatas e teste níveis/condições fora da distribuição.

Ajude-me a transformar isso em perguntas de pesquisa, hipóteses, desenho
experimental, variáveis, métricas, análise estatística, ameaças à validade e
critérios de aceitação.
```

---

## 18. Conclusão

O melhor caminho para exercitar o DejaVu é manter o foco no caso já implementado de baixa fricção. Ele tem causalidade física compreensível, dados e traces existentes, contrato formal violável, caso semelhante no catálogo, adaptação executável e mecanismo de evolução.

Antes de ampliar para obstáculos ou outros imprevistos, a prioridade deve ser tornar esse único caso reproduzível e semanticamente consistente. Corrigidos o estado fornecido ao ASM, a conclusão física da elevação, a reinicialização experimental e a evolução segura, o projeto passa a oferecer uma base muito mais sólida para comparar detecção reativa, detecção proativa, adaptação episódica e aprendizado/evolução entre execuções.
