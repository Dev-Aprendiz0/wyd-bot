"""Ações de alto nível do jogo WYD."""

from __future__ import annotations

import math
import time

from wyd_bot.automation.keyboard import KeyboardController
from wyd_bot.automation.mouse import MouseController
from wyd_bot.utils.config import CombatConfig, FarmConfig
from wyd_bot.utils.logger import setup_logger

logger = setup_logger("wyd_bot.automation.actions")


class GameActions:
    """Ações de alto nível para controlar o personagem no WYD."""

    def __init__(
        self,
        keyboard: KeyboardController | None = None,
        mouse: MouseController | None = None,
        combat_config: CombatConfig | None = None,
        farm_config: FarmConfig | None = None,
    ) -> None:
        self.keyboard = keyboard or KeyboardController()
        self.mouse = mouse or MouseController()
        self.combat = combat_config or CombatConfig()
        self.farm = farm_config or FarmConfig()
        self._skill_last_used: dict[int, float] = {}

        for i, key in enumerate(self.combat.skill_keys):
            if i < len(self.combat.skill_cooldowns):
                self.keyboard.set_cooldown(key, self.combat.skill_cooldowns[i])

    def attack(self) -> None:
        """Executa ataque básico."""
        self.keyboard.press(self.combat.attack_key)
        logger.debug("Ataque executado")

    def select_target(self) -> None:
        """Seleciona o próximo alvo."""
        self.keyboard.press(self.combat.target_key)
        logger.debug("Alvo selecionado")

    def use_skill(self, skill_index: int) -> bool:
        """Usa uma skill pelo índice.

        Args:
            skill_index: Índice da skill (0-based).

        Returns:
            True se a skill foi usada, False se em cooldown.
        """
        if skill_index >= len(self.combat.skill_keys):
            return False

        key = self.combat.skill_keys[skill_index]
        remaining = self.keyboard.get_remaining_cooldown(key)
        if remaining > 0:
            logger.debug("Skill %d em cooldown (%.1fs restante)", skill_index, remaining)
            return False

        self.keyboard.press(key)
        self._skill_last_used[skill_index] = time.time()
        logger.info("Skill %d usada (tecla: %s)", skill_index, key)
        return True

    def use_hp_potion(self) -> None:
        """Usa poção de HP."""
        self.keyboard.press(self.combat.hp_potion_key)
        logger.info("Poção de HP usada")

    def use_mp_potion(self) -> None:
        """Usa poção de MP."""
        self.keyboard.press(self.combat.mp_potion_key)
        logger.info("Poção de MP usada")

    def loot(self) -> None:
        """Coleta itens do chão."""
        self.keyboard.press(self.farm.loot_key)
        logger.debug("Loot coletado")

    def click_on_target(self, x: int, y: int) -> None:
        """Clica em um alvo na tela.

        Args:
            x: Coordenada X do alvo.
            y: Coordenada Y do alvo.
        """
        self.mouse.click(x, y)
        logger.debug("Clicou no alvo em (%d, %d)", x, y)

    def walk_to(self, x: int, y: int) -> None:
        """Move o personagem clicando no chão.

        Args:
            x: Coordenada X do destino na tela.
            y: Coordenada Y do destino na tela.
        """
        self.mouse.click(x, y)
        time.sleep(self.farm.walk_delay)
        logger.debug("Andou para (%d, %d)", x, y)

    def walk_circular(self, center_x: int, center_y: int, radius: int, steps: int = 8) -> None:
        """Move o personagem em padrão circular.

        Args:
            center_x: Centro X da rotação.
            center_y: Centro Y da rotação.
            radius: Raio do movimento.
            steps: Número de pontos no círculo.
        """
        for i in range(steps):
            angle = (2 * math.pi * i) / steps
            target_x = int(center_x + radius * math.cos(angle))
            target_y = int(center_y + radius * math.sin(angle))
            self.walk_to(target_x, target_y)
            time.sleep(self.farm.walk_delay)

    def flee(self) -> None:
        """Tenta fugir do combate."""
        self.keyboard.press(self.combat.flee_key)
        logger.warning("Fugindo do combate!")

    def get_best_available_skill(self) -> int | None:
        """Retorna o índice da melhor skill disponível (sem cooldown).

        Returns:
            Índice da skill ou None se todas estão em cooldown.
        """
        for i, key in enumerate(self.combat.skill_keys):
            if self.keyboard.get_remaining_cooldown(key) <= 0:
                return i
        return None
