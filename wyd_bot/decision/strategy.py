"""Estratégias de comportamento do bot."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wyd_bot.automation.actions import GameActions
    from wyd_bot.decision.state import GameState

from wyd_bot.utils.logger import setup_logger

logger = setup_logger("wyd_bot.decision.strategy")


class Strategy(ABC):
    """Classe base para estratégias de comportamento."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Nome da estratégia."""

    @abstractmethod
    def should_activate(self, state: GameState) -> bool:
        """Verifica se esta estratégia deve ser ativada."""

    @abstractmethod
    def execute(self, state: GameState, actions: GameActions) -> None:
        """Executa a estratégia."""

    @property
    @abstractmethod
    def priority(self) -> int:
        """Prioridade da estratégia (maior = mais prioritário)."""


class HealStrategy(Strategy):
    """Estratégia de cura - usa poções quando HP/MP está baixo."""

    def __init__(
        self,
        hp_threshold: float = 0.5,
        mp_threshold: float = 0.3,
        emergency_threshold: float = 0.2,
    ) -> None:
        self.hp_threshold = hp_threshold
        self.mp_threshold = mp_threshold
        self.emergency_threshold = emergency_threshold

    @property
    def name(self) -> str:
        return "Heal"

    @property
    def priority(self) -> int:
        return 100  # Maior prioridade

    def should_activate(self, state: GameState) -> bool:
        return (
            state.player.hp_percent < self.hp_threshold
            or state.player.mp_percent < self.mp_threshold
        )

    def execute(self, state: GameState, actions: GameActions) -> None:
        if state.player.hp_percent < self.emergency_threshold:
            logger.warning(
                "EMERGÊNCIA! HP: %.0f%% - Usando poção urgente",
                state.player.hp_percent * 100,
            )
            actions.use_hp_potion()
            state.potions_used += 1
            return

        if state.player.hp_percent < self.hp_threshold:
            logger.info("HP baixo (%.0f%%) - Usando poção de HP", state.player.hp_percent * 100)
            actions.use_hp_potion()
            state.potions_used += 1

        if state.player.mp_percent < self.mp_threshold:
            logger.info("MP baixo (%.0f%%) - Usando poção de MP", state.player.mp_percent * 100)
            actions.use_mp_potion()
            state.potions_used += 1


class FarmStrategy(Strategy):
    """Estratégia de farm - ataca monstros e coleta drops."""

    def __init__(self, screen_center: tuple[int, int] = (512, 384)) -> None:
        self.screen_center = screen_center

    @property
    def name(self) -> str:
        return "Farm"

    @property
    def priority(self) -> int:
        return 50

    def should_activate(self, state: GameState) -> bool:
        return state.has_monsters_nearby or not state.has_target

    def execute(self, state: GameState, actions: GameActions) -> None:
        if state.has_target:
            self._attack_target(state, actions)
        elif state.has_monsters_nearby:
            self._find_and_attack(state, actions)
        else:
            self._patrol(state, actions)

    def _attack_target(self, state: GameState, actions: GameActions) -> None:
        """Ataca o alvo atual usando skills e ataque básico."""
        best_skill = actions.get_best_available_skill()
        if best_skill is not None:
            actions.use_skill(best_skill)
        else:
            actions.attack()
        state.last_combat_time = __import__("time").time()

    def _find_and_attack(self, state: GameState, actions: GameActions) -> None:
        """Encontra o monstro mais próximo e ataca."""
        cx, cy = self.screen_center
        monster = state.get_closest_monster(cx, cy)
        if monster:
            actions.click_on_target(monster.center[0], monster.center[1])
            state.target = monster
            logger.info("Novo alvo: %s em (%d, %d)", monster.label, *monster.center)

    def _patrol(self, state: GameState, actions: GameActions) -> None:
        """Patrulha a área quando não há monstros."""
        if state.idle_duration > 5.0:
            cx, cy = self.screen_center
            actions.walk_circular(cx, cy, radius=150, steps=4)
            state.idle_since = __import__("time").time()
            logger.debug("Patrulhando área")


class LootStrategy(Strategy):
    """Estratégia de loot - coleta itens do chão."""

    @property
    def name(self) -> str:
        return "Loot"

    @property
    def priority(self) -> int:
        return 75

    def should_activate(self, state: GameState) -> bool:
        return state.has_items_nearby and not state.player.is_in_combat

    def execute(self, state: GameState, actions: GameActions) -> None:
        for item in state.nearby_items[:5]:
            actions.click_on_target(item.center[0], item.center[1])
            actions.loot()
            state.items_looted += 1
            logger.info("Item coletado: %s", item.label)

        state.last_loot_time = __import__("time").time()


class FleeStrategy(Strategy):
    """Estratégia de fuga - foge quando HP está criticamente baixo."""

    def __init__(self, flee_threshold: float = 0.15) -> None:
        self.flee_threshold = flee_threshold

    @property
    def name(self) -> str:
        return "Flee"

    @property
    def priority(self) -> int:
        return 200  # Prioridade máxima

    def should_activate(self, state: GameState) -> bool:
        return state.player.hp_percent < self.flee_threshold and state.player.is_in_combat

    def execute(self, state: GameState, actions: GameActions) -> None:
        logger.warning("FUGINDO! HP: %.0f%%", state.player.hp_percent * 100)
        actions.flee()
        actions.use_hp_potion()
        state.potions_used += 1
