# Dicionário de Parâmetros do Arquivo de Trace

Este documento explica cada campo presente nos arquivos de log gerados pelo simulador de braço robótico. Os arquivos de trace registram, a cada instante (chamado de "step"), o estado completo da simulação: onde o robô está, o que está fazendo, o que está vendo e se conseguiu completar a tarefa.

---

## Estrutura geral de um bloco de log

Cada bloco começa com uma linha separadora e o cabeçalho:

```
────────────────────────────────────────────
 Ep  1 | Step   5
────────────────────────────────────────────
```

---

## Cabeçalho do bloco

### `Ep` — Episódio
**O que é:** Número da tentativa atual.

O simulador pode rodar a mesma tarefa várias vezes seguidas (chamadas de "episódios"). A cada novo episódio, tudo é reiniciado — o robô volta à posição inicial, o cubo é recolocado, e o robô tenta novamente do zero.

**Exemplo:** `Ep  1` = primeira tentativa.

---

### `Step` — Passo
**O que é:** Número do instante dentro do episódio atual.

Dentro de cada episódio, o tempo avança em "passos" discretos. A cada passo, o robô recebe uma nova instrução de movimento e o estado inteiro é registrado. É como um frame de um filme — cada passo é um quadro.

**Exemplo:** `Step   5` = quinto instante desta tentativa.

---

## Campos de controle

### `Task` — Tarefa atual
**O que é:** O nome da estratégia que o robô está executando naquele momento.

O robô pode ser instruído a fazer diferentes tipos de movimento. O campo `Task` diz qual está ativo:

| Valor | Significado |
|---|---|
| `PUSH` | Empurrar o cubo até o destino |
| `PICK_AND_PLACE` | Pegar o cubo com a garra e depositá-lo no destino |
| `REACH` | Apenas mover a garra até uma posição, sem pegar nada |
| `HOLD` | Segurar o cubo parado, sem se mover |
| `MANUAL` | Controle manual via teclado |
| `API_TASK` | Tarefa enviada por um sistema externo via API |
| `SCRIPTED_TASK.<nome>` | Sequência de movimentos pré-programada com aquele nome |

---

### `Action` — Ação executada
**O que é:** O comando de movimento enviado ao braço robótico neste passo.

Formato: `[x, y, z, garra]`

- Os três primeiros valores (`x`, `y`, `z`) indicam para onde a extremidade do braço deve se mover — pense como joystick: negativo = recua/desce/vai para a esquerda; positivo = avança/sobe/vai para a direita.
- O quarto valor (`garra`) controla a abertura ou fechamento da garra: positivo = abrir, negativo = fechar.
- Os valores vão de `-1.0` a `+1.0` (intensidade máxima em cada direção).

**Exemplo:** `[-0.603, +0.000, -0.798, +0.000]` = braço movendo para trás e para baixo, garra sem movimento.

---

## Posição e movimento do braço

### `EE posição` — Posição da extremidade do braço
**O que é:** Onde está a ponta do braço (a garra) no espaço tridimensional.

"EE" significa *End-Effector* — o ponto mais extremo do braço, onde a garra fica. As coordenadas seguem um sistema de eixos:
- `x`: eixo horizontal de frente para trás (negativo = mais atrás, positivo = mais à frente)
- `y`: eixo horizontal de esquerda para direita
- `z`: eixo vertical (negativo = abaixo, positivo = acima)

Todas as medidas são em **metros**.

**Exemplo:** `[+0.025, +0.000, +0.168]` = garra está 2,5 cm à frente do centro, alinhada no eixo lateral, e a 16,8 cm de altura.

---

### `EE velocidade` — Velocidade da extremidade do braço
**O que é:** Com que velocidade e em que direção a garra está se movendo neste instante.

Mesmo formato que a posição (`[x, y, z]`), mas agora os valores representam metros por segundo em cada eixo. Valores próximos de zero indicam que o braço está quase parado naquele eixo.

**Exemplo:** `[-0.518, -0.000, -0.882]` = garra se movendo para trás a 0,52 m/s e descendo a 0,88 m/s.

---

### `Garra` — Abertura da garra
**O que é:** A distância entre os dois dedos da garra, seguida do seu estado interpretado.

Medida em **metros**. O estado é calculado automaticamente:

| Estado | Condição | Significado |
|---|---|---|
| `FECHADA` | abertura < 1 cm | Os dedos estão completamente fechados |
| `AGARRADA` | abertura ≈ tamanho do objeto | Os dedos envolvem o objeto (preso) |
| `ABERTA` | abertura > tamanho do objeto | Os dedos estão abertos, sem segurar nada |

**Exemplo:** `0.000 m  (FECHADA)` = garra completamente fechada.

---

### `Juntas ângulos` — Ângulos das 7 juntas do braço
**O que é:** O ângulo de rotação de cada articulação do braço robótico, em radianos.

O braço tem 7 articulações (como os ombros, cotovelo e pulso de um braço humano). Cada valor corresponde a uma junta, da base até a ponta. Radianos é uma unidade de ângulo: 0 = reto, ±3,14 = posição extrema.

**Exemplo:** `[-0.00, +0.42, +0.00, -1.93, -0.00, +2.36, +0.79]`

---

### `Juntas veloc.` — Velocidades angulares das juntas
**O que é:** Com que velocidade cada junta está girando neste instante, em radianos por segundo.

Segue a mesma ordem das 7 juntas. Valores próximos de zero indicam que a junta está parada.

**Exemplo:** `[-0.00, +0.59, +0.00, -1.37, -0.01, +0.75, -0.03]`

---

## O cubo (objeto manipulável)

### `Cubo posição` — Posição do cubo
**O que é:** Onde o cubo está no espaço tridimensional, em metros.

O cubo é o objeto que o robô deve mover até o destino. As coordenadas usam o mesmo sistema de eixos da posição da garra.

**Exemplo:** `[+0.030, +0.000, +0.020]` = cubo a 3 cm à frente, centralizado lateralmente, e a 2 cm de altura (em cima da mesa).

---

### `Cubo rotação` — Rotação do cubo
**O que é:** O ângulo de inclinação do cubo nos três eixos, em radianos.

Apresentado como `(roll/pitch/yaw)`:
- **roll**: inclinação lateral (como uma moeda rolando)
- **pitch**: inclinação de frente para trás (como um barco no mar)
- **yaw**: rotação horizontal (como uma bússola girando)

Valores próximos de zero indicam que o cubo está plano/alinhado.

**Exemplo:** `[+0.000, -0.000, -0.000]` = cubo perfeitamente plano, sem inclinação.

---

### `Cubo vel.linear` — Velocidade linear do cubo
**O que é:** Com que velocidade o cubo está se deslocando, em metros por segundo.

Indica se o cubo está parado ou em movimento, e em qual direção. Surge quando o robô empurra ou solta o cubo.

**Exemplo:** `[-0.000, +0.000, -0.000]` = cubo estacionário.

---

## Distâncias e desempenho

### `Dist EE→Cubo` — Distância da garra ao cubo
**O que é:** A distância em linha reta entre a ponta do braço (garra) e o centro do cubo, em metros.

Quanto menor esse valor, mais próxima a garra está do cubo. Quando chega a zero (ou próximo), o robô está em contato com o objeto.

**Exemplo:** `0.1484 m` = garra está a quase 15 cm do cubo.

---

### `Dist Cubo→target` — Distância do cubo ao destino
**O que é:** A distância em linha reta entre o cubo e o ponto de destino (goal), em metros.

Essa é a medida principal de progresso da tarefa: quando ela chega próxima de zero, o robô completou o objetivo. O threshold configurado é de **5 cm** — se o cubo estiver a menos de 5 cm do alvo, conta como sucesso.

**Exemplo:** `0.1200 m` = cubo ainda está a 12 cm do destino.

---

### `Reward` — Recompensa
**O que é:** Uma pontuação numérica que indica o quão bem o robô está indo neste passo.

É um valor negativo que representa a distância do cubo ao alvo, multiplicada por -1. Quanto mais próximo de zero, melhor:
- `0.0` = cubo está exatamente no destino (máxima recompensa)
- `-0.12` = cubo está a 12 cm do destino

Esse valor é usado pelo sistema de aprendizado para ensinar o robô a melhorar ao longo do tempo.

**Exemplo:** `-0.1200` = cubo ainda está 12 cm longe.

---

### `Sucesso` — Tarefa concluída
**O que é:** Indica se o robô atingiu o objetivo neste passo.

- `True` = cubo chegou ao destino dentro da margem de tolerância (5 cm)
- `False` = objetivo ainda não foi alcançado

**Exemplo:** `False` = tarefa ainda em andamento.

---

## Obstáculos

### `Obstáculo caminho` — Há obstáculo no caminho direto?
**O que é:** Indica se existe algum objeto físico bloqueando a linha reta entre o cubo e o destino.

O sistema analisa o espaço 2D (visto de cima) e verifica se algum obstáculo intercepta o trajeto direto cubo → destino.

- `SIM` = há pelo menos um obstáculo no caminho
- `nao` = caminho livre

O `count` ao lado informa quantos obstáculos estão bloqueando.

**Exemplo:** `SIM  (count: 1)` = um obstáculo está no caminho direto.

---

### `Obstáculo [nome]` — Dados de cada obstáculo
**O que é:** Informações físicas de cada obstáculo presente na cena.

| Sub-campo | Significado |
|---|---|
| `tipo` | Formato do objeto (`box` = caixa retangular) |
| `massa` | Peso em kg. `0.0` = objeto fixo, não se move |
| `tamanho` | Dimensões em metros: `[largura_x, largura_y, altura_z]` |

**Exemplo:** `tipo=box  massa=0.0 kg  tamanho=[0.02, 0.30, 0.5]` = parede fina (2 cm) e larga (30 cm), com 50 cm de altura, fixada no chão.

---

## Objetos

### `Objeto [nome]` — Dados de cada objeto manipulável
**O que é:** Informações físicas dos objetos que o robô pode pegar ou empurrar (geralmente o cubo).

Mesma estrutura do obstáculo, mas com objetos que podem ser movidos.

| Sub-campo | Significado |
|---|---|
| `tipo` | Formato do objeto |
| `massa` | Peso em kg |
| `tamanho` | Dimensões em metros `[x, y, z]` |

**Exemplo:** `tipo=box  massa=1.0 kg  tamanho=[0.04, 0.04, 0.04]` = cubo de 4×4×4 cm com 1 kg.

---

## Destino (goal)

### `Target (nome)` — Posição do destino ativo
**O que é:** As coordenadas do ponto que o cubo deve alcançar.

O nome entre parênteses identifica qual destino está ativo no momento (pode haver vários destinos em sequência). A posição usa o mesmo sistema de coordenadas `[x, y, z]`.

**Exemplo:** `Target (target): [+0.150, +0.000, +0.020]` = destino está a 15 cm à frente, centralizado, e sobre a mesa.

---

### `Target goal` — Configuração completa dos destinos
**O que é:** A lista de todos os destinos possíveis e o modo de funcionamento dos objetivos.

Contém:
- **`type` / `mode`**: como os destinos são usados:
  - `goal_sequence` = o robô deve visitar os destinos nesta ordem exata
  - `goal_options` = basta chegar em qualquer um dos destinos
  - `goal_set` = deve visitar todos, mas em qualquer ordem
- **`targets`**: lista de destinos com nome e posição de cada um

**Exemplo:**
```
type: goal_sequence
targets: [target, target_1, target_2, target_3]
```
= robô deve levar o cubo a 4 pontos em sequência.

---

## Ambiente físico

### `Mesa` — Dimensões da mesa
**O que é:** As medidas físicas da superfície onde o robô e os objetos estão posicionados.

| Sub-campo | Significado |
|---|---|
| Primeiro valor | Comprimento (eixo X) em metros |
| Segundo valor | Largura (eixo Y) em metros |
| Terceiro valor | Altura (eixo Z) em metros |
| `offset_x` | Deslocamento horizontal da mesa em relação ao robô |

**Exemplo:** `1.1x0.7x0.4 m  offset_x=-0.3` = mesa de 1,1 m × 0,7 m, com 40 cm de altura, deslocada 30 cm para trás em relação à base do robô.

---

## Configuração do robô

### `Robô config` — Parâmetros de controle do robô
**O que é:** Como o robô está configurado para se mover e operar a garra.

| Sub-campo | Valor possível | Significado |
|---|---|---|
| `control` | `ee` | Controle direto da ponta do braço (*end-effector*): a ação move a garra diretamente no espaço 3D |
| `block_gripper` | `True` | Garra travada — não abre nem fecha durante a execução |
| `block_gripper` | `False` | Garra livre — pode abrir e fechar conforme a tarefa |
| `base` | `[x, y, z]` | Posição fixa da base do robô no mundo |

**Exemplo:** `control=ee  block_gripper=False  base=[-0.6, 0.0, 0.05]` = robô com garra livre, controlado pela ponta, fixado 60 cm atrás do centro da mesa.

---

## Scripts

### `Scripts` — Sequências de movimento disponíveis
**O que é:** Lista de roteiros de movimentos pré-programados carregados para esta simulação.

Cada script é uma sequência de tarefas com nome. Eles podem ser ativados dinamicamente durante a execução para trocar o comportamento do robô sem reiniciar a simulação.

**Exemplo:** `['script_1', 'reach_only', 'left_right']` = três scripts disponíveis: um genérico, um que só alcança objetos, e um que alterna esquerda-direita.

---

## Resumo rápido dos campos

| Campo | Unidade | Frequência de atualização |
|---|---|---|
| `Ep` | número inteiro | A cada reinício |
| `Step` | número inteiro | A cada passo |
| `Task` | texto | Quando muda a estratégia |
| `Action` | adimensional (-1 a +1) | A cada passo |
| `EE posição` | metros | A cada passo |
| `EE velocidade` | metros/segundo | A cada passo |
| `Garra` | metros | A cada passo |
| `Cubo posição` | metros | A cada passo |
| `Cubo rotação` | radianos | A cada passo |
| `Cubo vel.linear` | metros/segundo | A cada passo |
| `Target posição` | metros | Quando o alvo muda |
| `Dist EE→Cubo` | metros | A cada passo |
| `Dist Cubo→target` | metros | A cada passo |
| `Reward` | adimensional | A cada passo |
| `Sucesso` | True/False | A cada passo |
| `Obstáculo caminho` | Sim/Não + contagem | A cada passo |
| `Juntas ângulos` | radianos (7 valores) | A cada passo |
| `Juntas veloc.` | radianos/segundo (7 valores) | A cada passo |
| `Mesa` | metros | Fixo por simulação |
| `Robô config` | misto | Fixo por simulação |
| `Scripts` | lista de nomes | Fixo por simulação |
| `Target goal` | estrutura | Quando o alvo muda |
| `Objetos` | estrutura | Quando objetos mudam |
| `Obstáculos` | estrutura | Quando obstáculos mudam |