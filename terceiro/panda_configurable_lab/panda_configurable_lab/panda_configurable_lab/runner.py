from __future__ import annotations

from typing import Any, Dict

import numpy as np
import pybullet_data

from panda_gym.envs.robots.panda import Panda
from panda_gym.envs.tasks.reach        import Reach
from panda_gym.envs.tasks.push         import Push
from panda_gym.envs.tasks.slide        import Slide
from panda_gym.envs.tasks.pick_and_place import PickAndPlace
from panda_gym.envs.tasks.stack        import Stack
from panda_gym.envs.tasks.flip         import Flip

import time
from pathlib import Path
import yaml

from .env_factory import make_configurable_env
from .logger import ExperimentLogger
from .policies import SimplePolicy


# Mapeamento nome amigável → classe da task padrão do panda-gym.
# A task customizável (ConfigurableTask) é criada por make_configurable_env
# e não aparece aqui — ela é o ponto de partida, não um destino de troca.
TASK_CLASS_MAP: Dict[str, type] = {
    "reach":           Reach,
    "push":            Push,
    "slide":           Slide,
    "pick_and_place":  PickAndPlace,
    "stack":           Stack,
    "flip":            Flip,
}


class ExperimentRunner:
    def __init__(self, config: Dict[str, Any]):
        self.experiment_config  = config.get("experiment", {})
        self.logging_config     = config.get("logging", {})
        self.simulation_config  = config.get("simulation", {})
        self.step_delay         = float(self.simulation_config.get("step_delay", 1.0))
        self.verbose            = bool(self.simulation_config.get("verbose", False))
        self.runtime_config     = config.get("runtime", {})

        # guarda quais comandos já foram aplicados
        self.applied_runtime_commands = set()

        # sinaliza que o env foi trocado por change_task e precisa de reset
        self._env_reset_needed = False

        config_dir = Path(config.get("_config_dir", "."))

        # Resolve o caminho do arquivo de comandos
        command_file = self.runtime_config.get("command_file")
        self.command_file = config_dir / command_file if command_file else None

        # Resolve o caminho do arquivo de goals
        goal_file = self.runtime_config.get("goal_file")
        self.goal_file = config_dir / goal_file if goal_file else None

        self.poll_every_steps = int(self.runtime_config.get("poll_every_steps", 1))

        # Carrega commands file antecipadamente para extrair policy e task iniciais.
        commands_data = self._load_commands_data()

        # policy: commands file tem prioridade; env file é fallback para compat.
        policy_from_commands = commands_data.get("policy", {})
        policy_from_env      = config.get("policy", {})
        effective_policy     = {**policy_from_env, **policy_from_commands}

        # task: commands file tem prioridade; env file é fallback para compat.
        task_from_commands = commands_data.get("task", {})
        task_from_env      = config.get("task", {})
        effective_task     = {**task_from_env, **task_from_commands}

        # goals: goals file tem prioridade; env file é fallback para compat.
        goals_data          = self._load_goals_data()
        goals_from_file     = goals_data.get("initial", {})
        goals_from_env      = config.get("goals", {})
        effective_goals     = goals_from_file if goals_from_file else goals_from_env

        # Monta config final fundindo as fontes
        self.config = {**config, "task": effective_task, "policy": effective_policy, "goals": effective_goals}

        self.env = make_configurable_env(self.config)

        self.policy = SimplePolicy(
            name=effective_policy.get("name", "random"),
            gain=float(effective_policy.get("gain", 5.0)),
        )

        self.logger = ExperimentLogger(
            output_dir=self.logging_config.get(
                "output_dir",
                f"results/{self.experiment_config.get('name', 'experiment')}",
            )
        )

    def run(self) -> Dict[str, Any]:
        seed = int(self.experiment_config.get("seed", 42))
        episodes = int(self.experiment_config.get("episodes", 1))
        max_steps = int(self.experiment_config.get("max_steps", 100))

        print(f"[PandaConfigurableLab] Experimento: {self.experiment_config.get('name')}")
        print(f"[PandaConfigurableLab] Episódios: {episodes}")
        print(f"[PandaConfigurableLab] Max steps: {max_steps}")
        print(f"[PandaConfigurableLab] Política: {self.policy.name}")

        for episode in range(episodes):
            self._run_episode(episode=episode, seed=seed + episode, max_steps=max_steps)

        self.logger.flush()
        self.env.close()

        output_dir = self.logger.output_dir.as_posix()

        print(f"[PandaConfigurableLab] Finalizado. Resultados em: {output_dir}")

        return {
            "episodes": episodes,
            "output_dir": output_dir,
        }

    def _run_episode(self, episode: int, seed: int, max_steps: int) -> None:
        observation, info = self.env.reset(seed=seed)
        self.policy.reset_phase()   # reinicia estado da pick_and_place state machine

        final_reward = None
        final_success = False
        final_distance = None
        steps_executed = 0

        for step in range(max_steps):
            self._apply_runtime_commands(episode, step)

            # change_task fechou o env antigo e criou um novo: faz reset antes de agir
            if self._env_reset_needed:
                self._env_reset_needed = False
                observation, _ = self.env.reset()
                continue

            # Garante que a política vê o desired_goal atualizado no mesmo step
            # em que o comando foi aplicado (sem esperar o próximo env.step)
            observation = self._refresh_desired_goal(observation)

            action = self.policy.act(self.env, observation)

            next_observation, reward, terminated, truncated, info = self.env.step(action)
            
            if self.step_delay > 0 and self.policy.name != "manual":
                time.sleep(self.step_delay)

            achieved = next_observation.get("achieved_goal")
            desired = next_observation.get("desired_goal")
            distance_to_goal = self._distance(achieved, desired)

            record = {
                "episode": episode,
                "step": step,
                "action": action,
                "reward": float(reward),
                "terminated": bool(terminated),
                "truncated": bool(truncated),
                "achieved_goal": achieved,
                "desired_goal": desired,
                "distance_to_goal": distance_to_goal,
                "is_success": bool(info.get("is_success", False)) if isinstance(info, dict) else False,
                "observation": next_observation.get("observation") if isinstance(next_observation, dict) else next_observation,
                "info": info,
            }

            self.logger.log_step(record)

            if self.verbose:
                print(
                    f"[ep={episode} step={step:3d}]"
                    f"  reward={reward:.4f}"
                    f"  terminated={terminated}"
                    f"  truncated={truncated}"
                    f"  success={record['is_success']}"
                    f"  dist={distance_to_goal:.4f}"
                    f"\n    action       = {np.round(action, 3).tolist()}"
                    f"\n    achieved_goal= {np.round(achieved, 3).tolist() if achieved is not None else None}"
                    f"\n    desired_goal = {np.round(desired, 3).tolist() if desired is not None else None}"
                    f"\n    observation  = {np.round(record['observation'], 3).tolist() if record['observation'] is not None else None}"
                    f"\n    info         = {info}"
                )

            final_reward = float(reward)
            final_success = bool(info.get("is_success", False)) if isinstance(info, dict) else False
            final_distance = distance_to_goal
            steps_executed = step + 1

            observation = next_observation

            if terminated or truncated:
                break

        summary = {
            "episode": episode,
            "seed": seed,
            "steps": steps_executed,
            "final_reward": final_reward,
            "final_success": final_success,
            "final_distance_to_goal": final_distance,
        }

        self.logger.add_summary(summary)

        print(
            f"[PandaConfigurableLab] Episódio {episode}: "
            f"steps={steps_executed}, "
            f"reward={final_reward}, "
            f"success={final_success}, "
            f"distance={final_distance}"
        )

    def _refresh_desired_goal(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Atualiza desired_goal na observation com o valor atual de task.goal.

        Necessário porque observation vem do env.step() anterior — sem isso,
        a política só veria o novo goal no step seguinte ao comando.
        """
        if not isinstance(observation, dict):
            return observation

        task = getattr(self.env, "task", None)
        if task is None:
            task = getattr(getattr(self.env, "unwrapped", None), "task", None)
        if task is None:
            return observation

        new_goal = task.get_goal()
        if np.array_equal(observation.get("desired_goal"), new_goal):
            return observation  # nada mudou, evita cópia desnecessária

        return {**observation, "desired_goal": new_goal}

    @staticmethod
    def _distance(achieved: Any, desired: Any) -> float | None:
        if achieved is None or desired is None:
            return None

        achieved_arr = np.asarray(achieved, dtype=float)
        desired_arr = np.asarray(desired, dtype=float)

        if achieved_arr.shape != desired_arr.shape:
            return None

        return float(np.linalg.norm(achieved_arr - desired_arr))
    
    def _load_commands_data(self) -> Dict[str, Any]:
        """Lê o commands file e retorna o conteúdo bruto (sem filtrar por enabled/id)."""
        if self.command_file is None or not self.command_file.exists():
            return {}
        try:
            with self.command_file.open("r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return {}

    def _load_goals_data(self) -> Dict[str, Any]:
        """Lê o goals file e retorna o conteúdo bruto."""
        if self.goal_file is None or not self.goal_file.exists():
            return {}
        try:
            with self.goal_file.open("r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return {}

    def _apply_runtime_commands(self, episode: int, step: int) -> None:
        """
        Lê comandos de runtime a partir de um YAML externo.

        O usuário pode editar esse arquivo enquanto a simulação está rodando.
        """
        if self.command_file is None:
            return

        if step % self.poll_every_steps != 0:
            return

        if not self.command_file.exists():
            return

        try:
            with self.command_file.open("r", encoding="utf-8") as file:
                data = yaml.safe_load(file) or {}
        except Exception as exc:
            self.logger.log_event(
                {
                    "episode": episode,
                    "step": step,
                    "operation": "read_runtime_commands",
                    "status": "failed",
                    "message": str(exc),
                }
            )
            return

        commands = list(data.get("commands", []) or [])

        # Injeta as mudanças de goal do goals file como change_goal commands
        if self.goal_file and self.goal_file.exists():
            try:
                with self.goal_file.open("r", encoding="utf-8") as gf:
                    goals_data = yaml.safe_load(gf) or {}
                for change in goals_data.get("changes", []) or []:
                    commands.append({**change, "operation": "change_goal"})
            except Exception:
                pass

        for command in commands:
            if not command.get("enabled", False):
                continue

            command_id = str(command.get("id", f"command_{len(self.applied_runtime_commands)}"))

            if command_id in self.applied_runtime_commands:
                continue

            if "at_episode" in command and int(command["at_episode"]) != episode:
                continue

            if "at_step" in command and int(command["at_step"]) != step:
                continue

            operation = command.get("operation")

            event = {
                "episode": episode,
                "step": step,
                "command_id": command_id,
                "operation": operation,
                "status": "pending",
                "command": command,
            }

            try:
                if operation == "change_goal":
                    self._change_goal(command)
                    event["status"] = "applied"

                elif operation == "change_task":
                    self._change_task(command)
                    event["status"] = "applied"

                elif operation == "change_task_mode":
                    self._change_task_mode(command)
                    event["status"] = "applied"

                elif operation == "run_script":
                    self._run_script(command)
                    event["status"] = "applied"

                else:
                    raise ValueError(f"Operação não suportada: {operation}")

            except Exception as exc:
                event["status"] = "failed"
                event["message"] = str(exc)

            self.logger.log_event(event)
            self.applied_runtime_commands.add(command_id)

            print(
                f"[RuntimeCommand] step={step} "
                f"id={command_id} "
                f"operation={operation} "
                f"status={event['status']}"
            )


    def _change_task(self, command: Dict[str, Any]) -> None:
        """
        Troca a task em tempo de execução SEM fechar a janela do PyBullet.

        Estratégia:
          1. Chama resetSimulation() para limpar todos os corpos da física,
             mantendo a conexão GUI aberta (a janela NÃO fecha).
          2. Restaura as configurações de física (gravidade, timestep).
          3. Recria o robô Panda e a nova task usando o MESMO objeto sim.
          4. Faz hot-swap de env.robot e env.task no lugar.
          5. Sinaliza o loop para fazer env.reset() antes da próxima ação.

        Comando YAML:
            operation: change_task
            task: reach | push | slide | pick_and_place | stack | flip
            policy: greedy_goal | greedy_push | random | hold  (opcional)
            reward_type: dense | sparse                         (opcional, padrão: sparse)
        """
        task_name = str(command.get("task", "")).lower().replace("-", "_").replace(" ", "_")
        task_class = TASK_CLASS_MAP.get(task_name)

        if task_class is None:
            raise ValueError(
                f"Task '{task_name}' não reconhecida. "
                f"Opções: {sorted(TASK_CLASS_MAP)}"
            )

        reward_type = str(command.get("reward_type", "sparse"))

        # ── 1. Acessa o PyBullet compartilhado ───────────────────────────────
        sim = self.env.sim

        # ── 2. Limpa todos os corpos; a janela GUI permanece aberta ──────────
        sim.physics_client.resetSimulation()
        sim._bodies_idx.clear()

        # ── 3. Restaura configurações de física apagadas pelo reset ──────────
        sim.physics_client.setTimeStep(sim.timestep)
        sim.physics_client.setAdditionalSearchPath(pybullet_data.getDataPath())
        sim.physics_client.setGravity(0, 0, -9.81)

        # ── 4. Recria o robô no mesmo sim (recarrega o URDF) ─────────────────
        robot_config = self.config.get("robot", {})
        new_robot = Panda(
            sim=sim,
            block_gripper=bool(robot_config.get("block_gripper", True)),
            base_position=np.array(robot_config.get("base_position", [-0.6, 0.0, 0.0]), dtype=float),
            control_type=str(robot_config.get("control_type", "ee")),
        )

        # ── 5. Cria a nova task no mesmo sim ─────────────────────────────────
        # Reach é a única task que precisa de get_ee_position (para gerar o goal)
        if task_class is Reach:
            new_task = Reach(
                sim=sim,
                get_ee_position=new_robot.get_ee_position,
                reward_type=reward_type,
            )
        else:
            new_task = task_class(sim=sim, reward_type=reward_type)

        # ── 6. Hot-swap: substitui robô e task sem recriar o env ─────────────
        self.env.robot = new_robot
        self.env.task  = new_task

        # ── 7. Troca a política se solicitado ─────────────────────────────────
        new_policy = command.get("policy")
        if new_policy:
            self.policy.name = str(new_policy)

        # Sinaliza o loop: buscar nova observation antes de agir
        self._env_reset_needed = True

    def _run_script(self, command: Dict[str, Any]) -> None:
        """
        Carrega e executa uma sequência de ações primitivas.

        O script é definido diretamente no comando YAML como uma lista de passos,
        cada um com um vetor de ação e a quantidade de steps que deve ser mantido.

        Quando o script termina, a política volta para policy_after (padrão: "hold").

        Comando YAML:
            operation: run_script
            policy_after: "greedy_push"   (opcional, padrão: hold)
            script:
              - action: [dx, dy, dz, gripper]
                steps: N
              - action: [...]
                steps: N
        """
        script       = command.get("script", [])
        policy_after = str(command.get("policy_after", "hold"))

        if not script:
            raise ValueError("run_script: campo 'script' ausente ou vazio.")

        self.policy.load_script(script, policy_after=policy_after)

    def _change_task_mode(self, command: Dict[str, Any]) -> None:
        """
        Muda o comportamento da task NO MESMO fluxo físico, sem reset da cena.

        Ao contrário de change_task (que reinicia o PyBullet), este comando
        apenas altera o goal e/ou a política, mantendo cubo, robô e físicas
        exatamente onde estão.

        Ideal para transições do tipo:
          push → pick_and_place  (cubo continua no lugar, robô continua onde está)

        Comando YAML:
            operation: change_task_mode
            target_object: "cube_1"         (opcional: muda o goal)
            position: [x, y, z]             (opcional: nova posição do goal, pode ser no ar)
            tolerance: 0.05                  (opcional)
            visual_marker: true              (opcional)
            policy: "greedy_pick_and_place"  (opcional: muda a política)
        """
        # Muda o goal se uma nova posição foi especificada
        if "position" in command and "target_object" in command:
            self._change_goal(command)

        # Muda a política e reinicia o estado de fase se necessário
        new_policy = command.get("policy")
        if new_policy:
            self.policy.name = str(new_policy)
            self.policy.reset_phase()

    def _change_goal(self, command: Dict[str, Any]) -> None:
        """
        Aplica mudança de goal na task atual.
        """
        task = getattr(self.env, "task", None)

        if task is None:
            unwrapped = getattr(self.env, "unwrapped", None)
            task = getattr(unwrapped, "task", None)

        if task is None:
            raise AttributeError("Não foi possível acessar a task atual do ambiente.")

        if not hasattr(task, "set_goal_for_object"):
            raise AttributeError("A task atual não suporta set_goal_for_object().")

        task.set_goal_for_object(
            object_name=command["target_object"],
            position=command["position"],
            tolerance=command.get("tolerance"),
            visual_marker=bool(command.get("visual_marker", True)),
        )
