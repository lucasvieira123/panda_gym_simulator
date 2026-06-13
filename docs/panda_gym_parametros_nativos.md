# Parâmetros nativos do panda_gym

Tudo o que pode ser lido sem criar nenhum Sensor.
Fontes: `obs` dict, objeto `robot` (classe Panda), objeto `sim` (classe PyBullet).

---

## 1. `obs` — retornado por `env.step()` / `env.reset()`

| Chave | Índices / conteúdo | Tipo |
|---|---|---|
| `obs["observation"]` | `[0:3]` posição do EE (x, y, z) | `ndarray` |
| `obs["observation"]` | `[3:6]` velocidade linear do EE (vx, vy, vz) | `ndarray` |
| `obs["observation"]` | `[6]` abertura da garra (fingers_width, metros) | `float` |
| `obs["observation"]` | `[7:10]` posição do cubo (x, y, z) | `ndarray` |
| `obs["achieved_goal"]` | posição atual do cubo (igual a obs[7:10]) | `ndarray (3,)` |
| `obs["desired_goal"]` | posição do target (goal) | `ndarray (3,)` |

---

## 2. `robot` — objeto da classe `Panda`

| Método | Retorno | Descrição |
|---|---|---|
| `robot.get_ee_position()` | `ndarray (x, y, z)` | Posição do end-effector |
| `robot.get_ee_velocity()` | `ndarray (vx, vy, vz)` | Velocidade linear do EE |
| `robot.get_ee_orientation()` | `ndarray (x, y, z, w)` | Orientação do EE (quaternion) |
| `robot.get_joint_angle(i)` | `float` | Ângulo da junta i — i: 0..6 |
| `robot.get_joint_velocity(i)` | `float` | Velocidade da junta i — i: 0..6 |
| `robot.get_fingers_width()` | `float` metros | Abertura total da garra |

---

## 3. `sim` — objeto da classe `PyBullet`

O `sim` aceita qualquer corpo registrado pelo nome (`"panda"`, `"cube_1"`, `"table"`, nome de obstáculo, etc.).

### 3.1 Base (corpo inteiro)

| Método | Retorno | Descrição |
|---|---|---|
| `sim.get_base_position(body)` | `ndarray (x, y, z)` | Posição do centro de massa |
| `sim.get_base_orientation(body)` | `ndarray (x, y, z, w)` | Orientação em quaternion |
| `sim.get_base_rotation(body, type="euler")` | `ndarray (roll, pitch, yaw)` | Rotação em euler ou quaternion |
| `sim.get_base_velocity(body)` | `ndarray (vx, vy, vz)` | Velocidade linear |
| `sim.get_base_angular_velocity(body)` | `ndarray (wx, wy, wz)` | Velocidade angular |

### 3.2 Link (elo específico do corpo — por índice)

Útil para ler posição/velocidade de cada elo do braço Panda (ombro, cotovelo, pulso, etc.).

| Método | Retorno | Descrição |
|---|---|---|
| `sim.get_link_position(body, link)` | `ndarray (x, y, z)` | Posição do link |
| `sim.get_link_orientation(body, link)` | `ndarray (x, y, z, w)` | Orientação do link |
| `sim.get_link_velocity(body, link)` | `ndarray (vx, vy, vz)` | Velocidade linear do link |
| `sim.get_link_angular_velocity(body, link)` | `ndarray (wx, wy, wz)` | Velocidade angular do link |

### 3.3 Joint (junta específica do corpo — por índice)

| Método | Retorno | Descrição |
|---|---|---|
| `sim.get_joint_angle(body, joint)` | `float` | Ângulo da junta |
| `sim.get_joint_velocity(body, joint)` | `float` | Velocidade da junta |

---

## 4. Corpos registrados no `sim` (nomes válidos)

| Nome | Tipo | Origem |
|---|---|---|
| `"panda"` | Robô Franka Panda | carregado pelo `setup_environment` |
| `"cube_1"` | Objeto manipulável | carregado pelo task |
| `"table"` | Mesa | carregado pelo task |
| `"plane"` | Chão | carregado pelo task |
| `"target"` | Marcador visual do goal | carregado pelo task |
| `"<nome do obstáculo>"` | Obstáculo customizado | carregado via `environment_*.yaml` |

---

## 5. Links do braço Panda (índices)

| Índice | Elo |
|---|---|
| 0 | panda_link0 (base) |
| 1 | panda_link1 |
| 2 | panda_link2 |
| 3 | panda_link3 |
| 4 | panda_link4 |
| 5 | panda_link5 |
| 6 | panda_link6 |
| 7 | panda_link7 (pulso) |
| 8 | panda_hand |
| 9 | panda_leftfinger |
| 10 | panda_rightfinger |

---

## 6. O que ainda não coletamos (candidatos a Sensor)

| Parâmetro | Como obter |
|---|---|
| Velocidade angular do cubo | `sim.get_base_angular_velocity("cube_1")` |
| Orientação do EE em quaternion | `robot.get_ee_orientation()` |
| Posição de cada elo do braço | `sim.get_link_position("panda", link)` para link 0..10 |
| Velocidade de cada elo do braço | `sim.get_link_velocity("panda", link)` |
| Velocidade angular de cada elo | `sim.get_link_angular_velocity("panda", link)` |
| Orientação dos obstáculos | `sim.get_base_rotation("<nome>")` |
| Velocidade angular dos obstáculos | `sim.get_base_angular_velocity("<nome>")` |