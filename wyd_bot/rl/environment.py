"""Ambiente de Reinforcement Learning para WYD.

Este módulo define o ambiente no formato Gymnasium para treinar agentes RL.
É uma base preparada para expansão futura - requer que o jogo esteja rodando
e o módulo de visão esteja calibrado.

Uso futuro:
    from stable_baselines3 import PPO
    from wyd_bot.rl.environment import WYDEnvironment

    env = WYDEnvironment(config)
    model = PPO("MlpPolicy", env, verbose=1)
    model.learn(total_timesteps=100000)
"""

from __future__ import annotations

from typing import Any

import numpy as np

try:
    import gymnasium as gym
    from gymnasium import spaces

    GYM_AVAILABLE = True
except ImportError:
    GYM_AVAILABLE = False

from wyd_bot.utils.logger import setup_logger

logger = setup_logger("wyd_bot.rl.environment")


# Ações disponíveis no jogo
ACTION_ATTACK = 0
ACTION_SKILL_1 = 1
ACTION_SKILL_2 = 2
ACTION_SKILL_3 = 3
ACTION_SKILL_4 = 4
ACTION_HP_POTION = 5
ACTION_MP_POTION = 6
ACTION_LOOT = 7
ACTION_WALK_NORTH = 8
ACTION_WALK_SOUTH = 9
ACTION_WALK_EAST = 10
ACTION_WALK_WEST = 11
ACTION_TARGET = 12
ACTION_FLEE = 13
NUM_ACTIONS = 14


def create_wyd_environment(config: dict[str, Any] | None = None) -> Any:
    """Factory function para criar o ambiente WYD.

    Args:
        config: Configuração opcional do ambiente.

    Returns:
        Instância do WYDEnvironment se gymnasium disponível.

    Raises:
        ImportError: Se gymnasium não estiver instalado.
    """
    if not GYM_AVAILABLE:
        raise ImportError(
            "gymnasium não está instalado. "
            "Instale com: pip install 'wyd-bot[ml]'"
        )
    return WYDEnvironment(config)


if GYM_AVAILABLE:

    class WYDEnvironment(gym.Env):  # type: ignore[misc]
        """Ambiente Gymnasium para treinar agentes RL no WYD.

        Observation space (14 dimensões):
            [0] hp_percent (0-1)
            [1] mp_percent (0-1)
            [2] is_in_combat (0/1)
            [3] has_target (0/1)
            [4] num_monsters_nearby (0-10, normalizado)
            [5] num_items_nearby (0-10, normalizado)
            [6] closest_monster_distance (0-1, normalizado)
            [7] closest_monster_x (0-1, normalizado)
            [8] closest_monster_y (0-1, normalizado)
            [9] skill_1_ready (0/1)
            [10] skill_2_ready (0/1)
            [11] skill_3_ready (0/1)
            [12] skill_4_ready (0/1)
            [13] idle_time (0-1, normalizado)

        Action space (14 ações discretas):
            0: Ataque básico
            1-4: Skills 1-4
            5: Poção HP
            6: Poção MP
            7: Loot
            8-11: Andar N/S/E/W
            12: Selecionar alvo
            13: Fugir
        """

        metadata = {"render_modes": ["human"]}

        def __init__(self, config: dict[str, Any] | None = None) -> None:
            super().__init__()
            self.config = config or {}

            self.observation_space = spaces.Box(
                low=0.0,
                high=1.0,
                shape=(14,),
                dtype=np.float32,
            )
            self.action_space = spaces.Discrete(NUM_ACTIONS)

            self._step_count = 0
            self._total_reward = 0.0
            self._state = np.zeros(14, dtype=np.float32)

            logger.info("Ambiente WYD RL inicializado")

        def reset(
            self,
            *,
            seed: int | None = None,
            options: dict[str, Any] | None = None,
        ) -> tuple[np.ndarray, dict[str, Any]]:
            """Reseta o ambiente para um novo episódio."""
            super().reset(seed=seed)
            self._step_count = 0
            self._total_reward = 0.0

            self._state = np.array(
                [
                    1.0,   # hp
                    1.0,   # mp
                    0.0,   # in_combat
                    0.0,   # has_target
                    0.0,   # monsters
                    0.0,   # items
                    1.0,   # monster_distance
                    0.5,   # monster_x
                    0.5,   # monster_y
                    1.0,   # skill_1
                    1.0,   # skill_2
                    1.0,   # skill_3
                    1.0,   # skill_4
                    0.0,   # idle_time
                ],
                dtype=np.float32,
            )

            return self._state.copy(), {}

        def step(
            self, action: int
        ) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
            """Executa uma ação no ambiente.

            Returns:
                observation, reward, terminated, truncated, info
            """
            self._step_count += 1
            reward = self._compute_reward(action)
            self._total_reward += reward

            terminated = self._state[0] <= 0.0  # HP = 0
            truncated = self._step_count >= self.config.get("max_steps", 10000)

            info = {
                "step": self._step_count,
                "total_reward": self._total_reward,
                "hp": float(self._state[0]),
                "mp": float(self._state[1]),
            }

            return self._state.copy(), reward, terminated, truncated, info

        def _compute_reward(self, action: int) -> float:
            """Calcula a recompensa baseada na ação e estado."""
            reward = 0.0
            hp = self._state[0]
            mp = self._state[1]
            in_combat = self._state[2] > 0.5
            has_target = self._state[3] > 0.5

            if action == ACTION_ATTACK and has_target:
                reward += 1.0
            elif action == ACTION_ATTACK and not has_target:
                reward -= 0.5

            if action in (ACTION_SKILL_1, ACTION_SKILL_2, ACTION_SKILL_3, ACTION_SKILL_4):
                skill_idx = action - ACTION_SKILL_1 + 9
                if self._state[skill_idx] > 0.5 and has_target:
                    reward += 2.0
                else:
                    reward -= 0.3

            if action == ACTION_HP_POTION:
                if hp < 0.5:
                    reward += 3.0
                else:
                    reward -= 1.0

            if action == ACTION_MP_POTION:
                if mp < 0.3:
                    reward += 2.0
                else:
                    reward -= 1.0

            if action == ACTION_LOOT and self._state[5] > 0:
                reward += 1.5

            if action == ACTION_FLEE:
                if hp < 0.2 and in_combat:
                    reward += 5.0
                else:
                    reward -= 2.0

            reward -= 0.01  # penalidade por tempo

            return reward

        def render(self) -> None:
            """Renderiza informações do ambiente."""
            logger.info(
                "Step %d | HP: %.0f%% | MP: %.0f%% | Reward: %.2f",
                self._step_count,
                self._state[0] * 100,
                self._state[1] * 100,
                self._total_reward,
            )
