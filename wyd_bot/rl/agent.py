"""Agente de Reinforcement Learning para WYD.

Base preparada para treinar com stable-baselines3.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from wyd_bot.decision.state import GameState
from wyd_bot.utils.logger import setup_logger

logger = setup_logger("wyd_bot.rl.agent")

try:
    from stable_baselines3 import PPO

    SB3_AVAILABLE = True
except ImportError:
    SB3_AVAILABLE = False


class RLAgent:
    """Agente RL que pode ser treinado e usado para tomar decisões.

    Usa PPO (Proximal Policy Optimization) do stable-baselines3.
    """

    def __init__(self, model_path: str | None = None) -> None:
        """Inicializa o agente.

        Args:
            model_path: Caminho para carregar um modelo treinado.
        """
        self._model: Any = None
        self._is_trained = False

        if model_path and SB3_AVAILABLE:
            self.load(model_path)

    @property
    def is_available(self) -> bool:
        """Verifica se o agente RL está disponível (dependências instaladas)."""
        return SB3_AVAILABLE

    @property
    def is_trained(self) -> bool:
        return self._is_trained

    def state_to_observation(self, state: GameState) -> np.ndarray:
        """Converte GameState para observation do ambiente RL.

        Args:
            state: Estado do jogo.

        Returns:
            Array numpy com 14 dimensões normalizado.
        """
        screen_w, screen_h = 1024, 768
        closest_monster = state.get_closest_monster(screen_w // 2, screen_h // 2)

        if closest_monster:
            dist = (
                (closest_monster.center[0] - screen_w // 2) ** 2
                + (closest_monster.center[1] - screen_h // 2) ** 2
            ) ** 0.5
            max_dist = (screen_w**2 + screen_h**2) ** 0.5
            monster_dist = min(dist / max_dist, 1.0)
            monster_x = closest_monster.center[0] / screen_w
            monster_y = closest_monster.center[1] / screen_h
        else:
            monster_dist = 1.0
            monster_x = 0.5
            monster_y = 0.5

        return np.array(
            [
                state.player.hp_percent,
                state.player.mp_percent,
                float(state.player.is_in_combat),
                float(state.has_target),
                min(len(state.nearby_monsters) / 10.0, 1.0),
                min(len(state.nearby_items) / 10.0, 1.0),
                monster_dist,
                monster_x,
                monster_y,
                1.0,  # skill_1_ready (placeholder)
                1.0,  # skill_2_ready
                1.0,  # skill_3_ready
                1.0,  # skill_4_ready
                min(state.idle_duration / 30.0, 1.0),
            ],
            dtype=np.float32,
        )

    def predict(self, state: GameState) -> int:
        """Prevê a melhor ação dado o estado atual.

        Args:
            state: Estado do jogo.

        Returns:
            Índice da ação (0 a NUM_ACTIONS-1).
        """
        if not self._is_trained or self._model is None:
            return self._heuristic_action(state)

        obs = self.state_to_observation(state)
        action, _ = self._model.predict(obs, deterministic=True)
        return int(action)

    def train(
        self,
        env: Any,
        total_timesteps: int = 100000,
        save_path: str = "models/wyd_ppo",
    ) -> None:
        """Treina o agente.

        Args:
            env: Ambiente Gymnasium.
            total_timesteps: Número total de timesteps de treino.
            save_path: Caminho para salvar o modelo.
        """
        if not SB3_AVAILABLE:
            raise ImportError(
                "stable-baselines3 não instalado. "
                "Instale com: pip install 'wyd-bot[ml]'"
            )

        logger.info("Iniciando treinamento RL (%d timesteps)", total_timesteps)
        self._model = PPO(
            "MlpPolicy",
            env,
            verbose=1,
            learning_rate=3e-4,
            n_steps=2048,
            batch_size=64,
            n_epochs=10,
            gamma=0.99,
            tensorboard_log="logs/tensorboard/",
        )
        self._model.learn(total_timesteps=total_timesteps)
        self._is_trained = True

        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        self._model.save(save_path)
        logger.info("Modelo salvo em: %s", save_path)

    def load(self, model_path: str) -> None:
        """Carrega um modelo treinado."""
        if not SB3_AVAILABLE:
            logger.warning("stable-baselines3 não disponível, usando heurísticas")
            return

        self._model = PPO.load(model_path)
        self._is_trained = True
        logger.info("Modelo carregado de: %s", model_path)

    @staticmethod
    def _heuristic_action(state: GameState) -> int:
        """Ação heurística quando não há modelo treinado."""
        from wyd_bot.rl.environment import (
            ACTION_ATTACK,
            ACTION_FLEE,
            ACTION_HP_POTION,
            ACTION_LOOT,
            ACTION_MP_POTION,
            ACTION_SKILL_1,
            ACTION_TARGET,
            ACTION_WALK_NORTH,
        )

        if state.is_emergency:
            return ACTION_FLEE
        if state.needs_healing:
            return ACTION_HP_POTION
        if state.needs_mp:
            return ACTION_MP_POTION
        if state.has_items_nearby and not state.player.is_in_combat:
            return ACTION_LOOT
        if state.has_target:
            return ACTION_SKILL_1 if state.player.mp_percent > 0.5 else ACTION_ATTACK
        if state.has_monsters_nearby:
            return ACTION_TARGET
        return ACTION_WALK_NORTH
