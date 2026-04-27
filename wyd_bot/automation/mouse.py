"""Módulo de controle de mouse."""

from __future__ import annotations

import random
import time

import pyautogui

from wyd_bot.utils.logger import setup_logger

logger = setup_logger("wyd_bot.automation.mouse")


class MouseController:
    """Controlador de mouse com movimentos humanizados."""

    def __init__(
        self,
        move_duration: float = 0.2,
        click_delay: float = 0.05,
        humanize: bool = True,
    ) -> None:
        """Inicializa o controlador de mouse.

        Args:
            move_duration: Duração do movimento do mouse.
            click_delay: Delay entre cliques.
            humanize: Se True, adiciona variações aleatórias para parecer humano.
        """
        self.move_duration = move_duration
        self.click_delay = click_delay
        self.humanize = humanize

    def move_to(self, x: int, y: int) -> None:
        """Move o mouse para uma posição.

        Args:
            x: Coordenada X.
            y: Coordenada Y.
        """
        target_x, target_y = self._humanize_position(x, y)
        duration = self._humanize_duration(self.move_duration)
        pyautogui.moveTo(target_x, target_y, duration=duration)
        logger.debug("Mouse movido para (%d, %d)", target_x, target_y)

    def click(self, x: int | None = None, y: int | None = None, button: str = "left") -> None:
        """Clica em uma posição.

        Args:
            x: Coordenada X (None = posição atual).
            y: Coordenada Y (None = posição atual).
            button: Botão do mouse ('left', 'right', 'middle').
        """
        if x is not None and y is not None:
            self.move_to(x, y)
            time.sleep(self._humanize_duration(self.click_delay))

        pyautogui.click(button=button)
        logger.debug("Clique %s em (%s, %s)", button, x, y)

    def double_click(self, x: int | None = None, y: int | None = None) -> None:
        """Duplo clique em uma posição."""
        if x is not None and y is not None:
            self.move_to(x, y)
            time.sleep(self._humanize_duration(self.click_delay))

        pyautogui.doubleClick()
        logger.debug("Duplo clique em (%s, %s)", x, y)

    def right_click(self, x: int | None = None, y: int | None = None) -> None:
        """Clique direito em uma posição."""
        self.click(x, y, button="right")

    def drag_to(self, start_x: int, start_y: int, end_x: int, end_y: int) -> None:
        """Arrasta o mouse de uma posição para outra.

        Args:
            start_x: X inicial.
            start_y: Y inicial.
            end_x: X final.
            end_y: Y final.
        """
        self.move_to(start_x, start_y)
        time.sleep(0.1)
        duration = self._humanize_duration(self.move_duration * 2)
        pyautogui.drag(end_x - start_x, end_y - start_y, duration=duration)
        logger.debug("Drag de (%d,%d) para (%d,%d)", start_x, start_y, end_x, end_y)

    def scroll(self, clicks: int, x: int | None = None, y: int | None = None) -> None:
        """Rola o scroll do mouse.

        Args:
            clicks: Número de cliques de scroll (positivo = cima, negativo = baixo).
            x: Coordenada X (None = posição atual).
            y: Coordenada Y (None = posição atual).
        """
        if x is not None and y is not None:
            self.move_to(x, y)
        pyautogui.scroll(clicks)
        logger.debug("Scroll %d em (%s, %s)", clicks, x, y)

    def get_position(self) -> tuple[int, int]:
        """Retorna a posição atual do mouse."""
        pos = pyautogui.position()
        return (pos.x, pos.y)

    def _humanize_position(self, x: int, y: int) -> tuple[int, int]:
        """Adiciona variação aleatória à posição."""
        if not self.humanize:
            return (x, y)
        offset_x = random.randint(-3, 3)
        offset_y = random.randint(-3, 3)
        return (x + offset_x, y + offset_y)

    def _humanize_duration(self, base_duration: float) -> float:
        """Adiciona variação aleatória à duração."""
        if not self.humanize:
            return base_duration
        variation = base_duration * 0.3
        return base_duration + random.uniform(-variation, variation)
