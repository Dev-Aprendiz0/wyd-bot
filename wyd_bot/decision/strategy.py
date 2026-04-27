"""Estratégias de comportamento do bot."""

from __future__ import annotations

import random
import time
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


class ResurrectStrategy(Strategy):
    """Ressurreição automática quando morre."""

    def __init__(self, resurrect_key: str = "enter") -> None:
        self.resurrect_key = resurrect_key
        self._death_time: float = 0.0
        self._wait_before_resurrect: float = 3.0

    @property
    def name(self) -> str:
        return "Resurrect"

    @property
    def priority(self) -> int:
        return 300

    def should_activate(self, state: GameState) -> bool:
        if not state.player.is_alive:
            if self._death_time == 0.0:
                self._death_time = time.time()
            elapsed = time.time() - self._death_time
            return elapsed > self._wait_before_resurrect
        self._death_time = 0.0
        return False

    def execute(self, state: GameState, actions: GameActions) -> None:
        wait = random.uniform(0.5, 1.5)
        time.sleep(wait)
        actions.keyboard.press(self.resurrect_key)
        state.stats.resurrections += 1
        state.last_resurrect_time = time.time()
        self._death_time = 0.0
        logger.info("Tentando ressuscitar (aguardou %.1fs)", wait)


class FleeStrategy(Strategy):
    """Fuga quando HP está crítico."""

    def __init__(self, flee_threshold: float = 0.15) -> None:
        self.flee_threshold = flee_threshold

    @property
    def name(self) -> str:
        return "Flee"

    @property
    def priority(self) -> int:
        return 200

    def should_activate(self, state: GameState) -> bool:
        return (
            state.player.hp_percent < self.flee_threshold
            and state.player.is_in_combat
        )

    def execute(self, state: GameState, actions: GameActions) -> None:
        actions.flee()
        actions.use_hp_potion()
        state.stats.potions_used += 1
        state.stats.hp_potions_used += 1
        state.last_hp_potion_time = time.time()
        logger.warning(
            "HP crítico (%.0f%%) - Fugindo e usando poção!",
            state.player.hp_percent * 100,
        )


class HealStrategy(Strategy):
    """Cura com cooldown inteligente entre poções."""

    POTION_COOLDOWN = 2.0

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
        return 100

    def should_activate(self, state: GameState) -> bool:
        return (
            state.player.hp_percent < self.hp_threshold
            or state.player.mp_percent < self.mp_threshold
        )

    def execute(self, state: GameState, actions: GameActions) -> None:
        if state.player.hp_percent < self.emergency_threshold:
            logger.warning(
                "EMERGÊNCIA! HP: %.0f%%",
                state.player.hp_percent * 100,
            )
            actions.use_hp_potion()
            state.stats.potions_used += 1
            state.stats.hp_potions_used += 1
            state.last_hp_potion_time = time.time()
            return

        if (
            state.player.hp_percent < self.hp_threshold
            and state.time_since_hp_potion > self.POTION_COOLDOWN
        ):
            logger.info(
                "HP baixo (%.0f%%) - Usando poção de HP",
                state.player.hp_percent * 100,
            )
            actions.use_hp_potion()
            state.stats.potions_used += 1
            state.stats.hp_potions_used += 1
            state.last_hp_potion_time = time.time()

        if (
            state.player.mp_percent < self.mp_threshold
            and state.time_since_mp_potion > self.POTION_COOLDOWN
        ):
            logger.info(
                "MP baixo (%.0f%%) - Usando poção de MP",
                state.player.mp_percent * 100,
            )
            actions.use_mp_potion()
            state.stats.potions_used += 1
            state.stats.mp_potions_used += 1
            state.last_mp_potion_time = time.time()


class ReturnToTownStrategy(Strategy):
    """Volta para cidade quando sem poções."""

    def __init__(self, return_key: str = "t") -> None:
        self.return_key = return_key

    @property
    def name(self) -> str:
        return "ReturnToTown"

    @property
    def priority(self) -> int:
        return 90

    def should_activate(self, state: GameState) -> bool:
        return state.is_out_of_potions

    def execute(self, state: GameState, actions: GameActions) -> None:
        logger.warning("Sem poções! Voltando para a cidade.")
        actions.keyboard.press(self.return_key)


class AutoBuffStrategy(Strategy):
    """Usa buffs automaticamente a cada intervalo."""

    def __init__(
        self,
        buff_keys: list[str] | None = None,
        buff_interval: float = 300.0,
    ) -> None:
        self.buff_keys = buff_keys or []
        self.buff_interval = buff_interval

    @property
    def name(self) -> str:
        return "AutoBuff"

    @property
    def priority(self) -> int:
        return 80

    def should_activate(self, state: GameState) -> bool:
        if not self.buff_keys:
            return False
        return state.time_since_buff > self.buff_interval

    def execute(self, state: GameState, actions: GameActions) -> None:
        logger.info("Aplicando buffs (%d buffs)", len(self.buff_keys))
        for key in self.buff_keys:
            actions.keyboard.press(key)
            delay = random.uniform(0.3, 0.8)
            time.sleep(delay)
        state.last_buff_time = time.time()


class FarmStrategy(Strategy):
    """Farm com Tab-targeting, ataque automático e patrulha.

    Funciona em dois modos:
    - Com templates: detecta monstros visualmente e clica neles.
    - Sem templates (padrão): usa Tab para selecionar alvos no jogo
      e ataca com rotação de skills + ataque básico.
    """

    TAB_TARGET_INTERVAL = 3.0

    def __init__(
        self,
        screen_center: tuple[int, int] = (512, 384),
        walk_pattern: str = "mixed",
    ) -> None:
        self.screen_center = screen_center
        self.walk_pattern = walk_pattern
        self._patrol_index: int = 0
        self._last_tab_time: float = 0.0
        self._attack_cycle: int = 0

    @property
    def name(self) -> str:
        return "Farm"

    @property
    def priority(self) -> int:
        return 50

    def should_activate(self, state: GameState) -> bool:
        return True

    def execute(self, state: GameState, actions: GameActions) -> None:
        if state.has_target:
            self._attack_target(state, actions)
        elif state.has_monsters_nearby:
            self._find_and_attack(state, actions)
        else:
            self._tab_and_attack(state, actions)

    def _attack_target(
        self, state: GameState, actions: GameActions
    ) -> None:
        best_skill = actions.get_best_available_skill()
        if best_skill is not None:
            actions.use_skill(best_skill)
            state.stats.skills_used += 1
        else:
            actions.attack()
        state.last_combat_time = time.time()
        delay = random.uniform(0.05, 0.15)
        time.sleep(delay)

    def _find_and_attack(
        self, state: GameState, actions: GameActions
    ) -> None:
        cx, cy = self.screen_center
        monster = state.get_closest_monster(cx, cy)
        if monster:
            ox = random.randint(-3, 3)
            oy = random.randint(-3, 3)
            actions.click_on_target(
                monster.center[0] + ox,
                monster.center[1] + oy,
            )
            state.target = monster
            logger.info(
                "Novo alvo: %s em (%d, %d)",
                monster.label,
                *monster.center,
            )

    def _tab_and_attack(
        self, state: GameState, actions: GameActions
    ) -> None:
        """Modo sem templates: Tab para selecionar alvo e atacar."""
        now = time.time()
        if now - self._last_tab_time > self.TAB_TARGET_INTERVAL:
            actions.select_target()
            self._last_tab_time = now
            delay = random.uniform(0.15, 0.3)
            time.sleep(delay)
            logger.debug("Tab targeting - procurando alvo")

        self._attack_cycle += 1
        best_skill = actions.get_best_available_skill()
        if best_skill is not None:
            actions.use_skill(best_skill)
            state.stats.skills_used += 1
        else:
            actions.attack()

        if self._attack_cycle % 15 == 0:
            self._patrol(state, actions)

    def _patrol(self, state: GameState, actions: GameActions) -> None:
        cx, cy = self.screen_center
        pattern = self.walk_pattern
        if pattern == "mixed":
            pattern = random.choice(
                ["circular", "square", "random"]
            )

        if pattern == "circular":
            actions.walk_circular(cx, cy, radius=150, steps=4)
        elif pattern == "square":
            actions.walk_square(cx, cy, size=150)
        else:
            actions.walk_random(cx, cy, radius=200)

        state.idle_since = time.time()
        logger.debug("Patrulhando (%s)", pattern)


class LootStrategy(Strategy):
    """Coleta itens com prioridade e screenshot de drops raros."""

    def __init__(
        self,
        rare_keywords: list[str] | None = None,
    ) -> None:
        self.rare_keywords = rare_keywords or [
            "legendary",
            "epic",
            "rare",
            "unique",
            "lendario",
            "epico",
            "raro",
            "unico",
        ]

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
            is_rare = any(
                kw in item.label.lower() for kw in self.rare_keywords
            )
            if is_rare:
                state.stats.rare_drops += 1
                logger.info("DROP RARO encontrado: %s!", item.label)
                actions.screenshot_rare_drop(item.label)

            ox = random.randint(-2, 2)
            oy = random.randint(-2, 2)
            actions.click_on_target(
                item.center[0] + ox,
                item.center[1] + oy,
            )
            actions.loot()
            state.stats.record_loot()
            state.last_loot_time = time.time()
            delay = random.uniform(0.15, 0.35)
            time.sleep(delay)
            logger.debug("Loot coletado: %s", item.label)
