# Análise de escorregamento durante `LIFT_OBJECT`

## Objetivo

Esta análise verifica se o cenário `(escorrega_no_final)` já apresentava, durante a subtarefa `LIFT_OBJECT`, evidências de que a preensão se tornaria inadequada e resultaria na perda do objeto durante o transporte.

Foram comparados:

- os CSVs de referência cujos nomes começam com `_`, representando o caminho feliz;
- o arquivo `(escorrega_no_final)_antecipated_scenario_dataset_20260814_000958.csv`, representando o cenário problemático.

Os cinco arquivos de referência são idênticos entre si. Portanto, eles correspondem a uma única trajetória efetiva repetida, e não a cinco observações independentes.

## Conclusão principal

Sim. Há evidência de que o objeto já estava escorregando durante `LIFT_OBJECT`, vários passos antes da perda completa de contato no passo 37.

O indício mais relevante não está isoladamente em `finger_contacts`, pois essa variável permanece igual a 2 durante o lift. A evidência aparece principalmente no deslocamento progressivo do objeto em relação ao efetuador, na menor altura alcançada e na maior inclinação do objeto.

## Diferença de configuração

Entre os parâmetros constantes de configuração dos dois cenários, a diferença encontrada foi:

| Parâmetro | Caminho feliz | Cenário problemático | Alteração |
|---|---:|---:|---:|
| `objects.object_1.lateral_friction` | 0,500 | 0,155 | redução de 69% |

Os demais parâmetros relevantes permaneceram iguais, incluindo massa e dimensões do objeto, atrito rotacional, propriedades da mesa, configuração do robô, posição inicial e posição do alvo.

Isso torna o atrito lateral reduzido o principal candidato para explicar o escorregamento.

## Evidências durante o lift

| Passo | Distância objeto–garra: referência | Distância objeto–garra: falha | Altura referência/falha | `cube_pitch`: referência/falha |
|---:|---:|---:|---:|---:|
| 16 | 0,36 cm | 0,42 cm | 1 / 0 cm | 0,040 / 0,075 rad |
| 17 | 0,37 cm | 0,82 cm | 4 / 3 cm | -0,009 / 0,028 rad |
| 18 | 0,52 cm | 1,18 cm | 7 / 5 cm | 0,001 / 0,040 rad |
| 19 | 0,61 cm | 1,42 cm | 10 / 8 cm | aproximadamente 0 / 0,105 rad |
| 20 | 0,68 cm | 1,63 cm | 13 / 11 cm | 0,004 / 0,157 rad |
| 21 | 0,74 cm | 1,83 cm | 16 / 14 cm | 0,002 / 0,149 rad |
| 22 | 0,75 cm | 1,55 cm | 15 / 14 cm | -0,087 / -0,041 rad |

Considerando toda a subtarefa `LIFT_OBJECT`:

- o deslocamento médio entre objeto e garra foi aproximadamente **2,2 vezes maior** no cenário problemático;
- o deslocamento vertical relativo foi aproximadamente **7,2 vezes maior**;
- a inclinação média do objeto foi aproximadamente **4,4 vezes maior**;
- o objeto permaneceu entre 1 e 2 cm abaixo da altura observada no caminho feliz.

## Evidência de escorregamento dentro da garra

A partir do passo 16, o objeto começa a ficar progressivamente abaixo do efetuador:

- caminho feliz: deslocamento vertical relativo médio de aproximadamente `+0,16 cm`;
- cenário problemático: deslocamento vertical relativo médio de aproximadamente `-1,11 cm`.

Esse comportamento é compatível com um objeto descendo entre os dedos. A garra continua fechada e os sensores ainda registram dois contatos, mas a posição relativa do objeto muda progressivamente.

Consequentemente, `finger_contacts=2` não é suficiente para concluir que a preensão está estável. Essa variável indica a existência de contato físico, mas não garante que o objeto esteja imóvel em relação à garra.

## Possibilidade de antecipação

Retrospectivamente, seria possível sinalizar risco entre os passos 17 e 18, pois nesse intervalo:

- a distância relativa entre objeto e garra passa a ser mais de duas vezes maior que a referência;
- o deslocamento vertical para baixo cresce continuamente;
- a altura atingida fica abaixo da trajetória esperada;
- a inclinação do objeto aumenta;
- a garra continua recebendo comando de fechamento;
- os dois contatos ainda estão ativos.

A evolução da falha pode ser resumida da seguinte forma:

```text
Passo 16: objeto começa a descer em relação à garra
    ↓
Passos 17–21: afastamento e inclinação aumentam
    ↓
Passo 23: transporte começa com a preensão já degradada
    ↓
Passo 37: os dois contatos são perdidos
    ↓
Passos 38–40: objeto se afasta do efetuador e cai
    ↓
Passo 41: sistema registra ERR_23 e sat=False
```

O erro formal aparece somente no passo 41, enquanto os primeiros indícios físicos aparecem no início do lift. Isso representa uma antecipação potencial de aproximadamente 24 passos em relação ao registro de `sat=False`.

## Relação física com o atrito

No caminho feliz, o atrito lateral do objeto é `0,500`. No cenário problemático, ele é `0,155`.

Com menor atrito, o objeto pode permanecer em contato com os dedos e, simultaneamente, deslizar verticalmente. Isso explica por que `finger_contacts` permanece igual a 2 durante o lift, apesar do aumento da distância relativa, da diferença de altura e da inclinação anormal.

A perda completa de contato no passo 37 é, portanto, o estágio final de uma degradação que já era observável durante `LIFT_OBJECT`.

## Parâmetros relevantes para uma decisão antecipada

Uma avaliação explicável de risco de escorregamento poderia considerar conjuntamente:

- `objects.object_1.lateral_friction`: condição física do cenário;
- posição relativa entre `cube_x`, `cube_y`, `cube_z` e `ee_x`, `ee_y`, `ee_z`;
- tendência do deslocamento vertical relativo objeto–garra;
- `object_lift_height_cm`: progresso efetivo da elevação;
- `cube_pitch`, `cube_roll` e `cube_yaw`: inclinação e instabilidade;
- `cube_vx`, `cube_vy` e `cube_vz`: movimento do objeto;
- `finger_contacts`: perda parcial ou completa de contato;
- `action_gripper`: distinção entre queda e liberação comandada;
- `current_subtask`: contexto operacional da observação.

O uso conjunto é importante porque nenhum desses sinais, isoladamente, caracteriza todos os casos de escorregamento.

## Justificativa antecipada possível

> Durante `LIFT_OBJECT`, o objeto apresentou deslocamento relativo à garra aproximadamente 2,2 vezes maior que o comportamento de referência, deslocamento vertical 7,2 vezes maior e inclinação média 4,4 vezes maior. Mesmo com dois contatos ativos e comando de fechamento da garra, o objeto desceu progressivamente em relação ao efetuador. Combinado ao atrito lateral reduzido de 0,500 para 0,155, esse comportamento indica escorregamento gradual e risco elevado de perda da preensão durante o transporte.

## Limitação da análise

Esta conclusão é baseada em uma trajetória efetivamente adequada e uma trajetória problemática. A evidência física é consistente e a comparação é forte porque apenas o atrito lateral de configuração foi alterado, mas ainda não existem amostras independentes suficientes para estabelecer um limiar estatístico robusto e generalizável.

Para transformar os valores observados em regras confiáveis, seriam necessárias várias execuções com diferentes níveis de atrito, condições iniciais e resultados.
