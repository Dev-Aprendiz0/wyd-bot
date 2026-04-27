"""Ações de alto nível do jogo WYD."""

from __future__ import annotations

import math
import random
import time
from datetime import datetime
from pathlib import Path

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
        screenshot_dir: str = "screenshots",
    ) -> None:
        self.keyboard = keyboard or KeyboardController()
        self.mouse = mouse or MouseController()
        self.combat = combat_config or CombatConfig()
        self.farm = farm_config or FarmConfig()
        self._screenshot_dir = Path(screenshot_dir)
        self._skill_last_used: dict[int, float] = {}

        for i, key in enumerate(self.combat.skill_keys):
            if i < len(self.combat.skill_cooldowns):
                self.keyboard.set_cooldown(
                    key, self.combat.skill_cooldowns[i]
                )

    def attack(self) -> None:
        """Executa ataque básico com delay humanizado."""
        delay = random.uniform(0.02, 0.08)
        time.sleep(delay)
        self.keyboard.press(self.combat.attack_key)
        logger.debug("Ataque executado")

    def select_target(self) -> None:
        self.keyboard.press(self.combat.target_key)
        logger.debug("Alvo selecionado")

    def use_skill(self, skill_index: int) -> bool:
        """Usa uma skill pelo índice."""
        if skill_index >= len(self.combat.skill_keys):
            return False

        key = self.combat.skill_keys[skill_index]
        remaining = self.keyboard.get_remaining_cooldown(key)
        if remaining > 0:
            return False

        delay = random.uniform(0.03, 0.1)
        time.sleep(delay)
        self.keyboard.press(key)
        self._skill_last_used[skill_index] = time.time()
        logger.info("Skill %d usada (tecla: %s)", skill_index, key)
        return True

    def use_hp_potion(self) -> None:
        self.keyboard.press(self.combat.hp_potion_key)
        logger.info("Poção de HP usada")

    def use_mp_potion(self) -> None:
        self.keyboard.press(self.combat.mp_potion_key)
        logger.info("Poção de MP usada")

    def loot(self) -> None:
        self.keyboard.press(self.farm.loot_key)
        logger.debug("Loot coletado")

    def click_on_target(self, x: int, y: int) -> None:
        self.mouse.click(x, y)
        logger.debug("Clicou no alvo em (%d, %d)", x, y)

    def walk_to(self, x: int, y: int) -> None:
        self.mouse.click(x, y)
        delay = self.farm.walk_delay + random.uniform(-0.1, 0.2)
        time.sleep(max(0.1, delay))
        logger.debug("Andou para (%d, %d)", x, y)

    def walk_circular(
        self,
        center_x: int,
        center_y: int,
        radius: int,
        steps: int = 8,
    ) -> None:
        """Movimento circular com variação aleatória."""
        offset = random.uniform(0, 2 * math.pi)
        for i in range(steps):
            angle = offset + (2 * math.pi * i) / steps
            r = radius + random.randint(-20, 20)
            target_x = int(center_x + r * math.cos(angle))
            target_y = int(center_y + r * math.sin(angle))
            self.walk_to(target_x, target_y)

    def walk_square(
        self,
        center_x: int,
        center_y: int,
        size: int = 150,
    ) -> None:
        """Movimento em padrão quadrado com variação."""
        half = size // 2
        v = random.randint(-15, 15)
        points = [
            (center_x - half + v, center_y - half + v),
            (center_x + half + v, center_y - half - v),
            (center_x + half - v, center_y + half + v),
            (center_x - half - v, center_y + half - v),
        ]
        for px, py in points:
            self.walk_to(px, py)

    def walk_random(
        self,
        center_x: int,
        center_y: int,
        radius: int = 200,
    ) -> None:
        """Movimento aleatório dentro de um raio."""
        steps = random.randint(3, 6)
        for _ in range(steps):
            angle = random.uniform(0, 2 * math.pi)
            r = random.randint(50, radius)
            tx = int(center_x + r * math.cos(angle))
            ty = int(center_y + r * math.sin(angle))
            self.walk_to(tx, ty)

    def flee(self) -> None:
        """Fuga com movimento aleatório para dificultar perseguição."""
        self.keyboard.press(self.combat.flee_key)
        angle = random.uniform(0, 2 * math.pi)
        dist = random.randint(200, 350)
        fx = int(512 + dist * math.cos(angle))
        fy = int(384 + dist * math.sin(angle))
        self.mouse.click(fx, fy)
        logger.warning("Fugindo do combate!")

    def get_best_available_skill(self) -> int | None:
        """Retorna o índice da melhor skill disponível."""
        for i, key in enumerate(self.combat.skill_keys):
            if self.keyboard.get_remaining_cooldown(key) <= 0:
                return i
        return None

    def screenshot_rare_drop(self, item_name: str) -> None:
        """Captura screenshot quando um drop raro é encontrado."""
        try:
            import mss

            self._screenshot_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = "".join(
                c if c.isalnum() else "_" for c in item_name
            )
            filename = f"rare_{timestamp}_{safe_name}.png"
            path = self._screenshot_dir / filename

            with mss.mss() as sct:
                sct.shot(output=str(path))

            logger.info("Screenshot de drop raro salvo: %s", path)
        except Exception:
            logger.exception("Erro ao salvar screenshot de drop raro")
