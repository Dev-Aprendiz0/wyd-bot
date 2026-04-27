"""Módulo de controle de teclado."""

from __future__ import annotations

import time

import pyautogui

from wyd_bot.utils.logger import setup_logger

logger = setup_logger("wyd_bot.automation.keyboard")

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05


class KeyboardController:
    """Controlador de teclado para o jogo."""

    def __init__(self, key_delay: float = 0.05, hold_duration: float = 0.1) -> None:
        """Inicializa o controlador de teclado.

        Args:
            key_delay: Delay entre pressionamentos de tecla.
            hold_duration: Duração do pressionamento.
        """
        self.key_delay = key_delay
        self.hold_duration = hold_duration
        self._last_key_time: dict[str, float] = {}
        self._cooldowns: dict[str, float] = {}

    def press(self, key: str) -> None:
        """Pressiona e solta uma tecla.

        Args:
            key: Nome da tecla (ex: 'space', 'f1', 'a').
        """
        if not self._can_press(key):
            return

        pyautogui.press(key)
        self._last_key_time[key] = time.time()
        logger.debug("Tecla pressionada: %s", key)

    def hold(self, key: str, duration: float | None = None) -> None:
        """Segura uma tecla por um tempo.

        Args:
            key: Nome da tecla.
            duration: Duração em segundos (usa hold_duration padrão se None).
        """
        dur = duration or self.hold_duration
        pyautogui.keyDown(key)
        time.sleep(dur)
        pyautogui.keyUp(key)
        self._last_key_time[key] = time.time()
        logger.debug("Tecla segurada: %s por %.2fs", key, dur)

    def combo(self, *keys: str) -> None:
        """Pressiona uma combinação de teclas.

        Args:
            keys: Sequência de teclas (ex: 'ctrl', 'a').
        """
        pyautogui.hotkey(*keys)
        logger.debug("Combo: %s", "+".join(keys))

    def type_text(self, text: str, interval: float = 0.05) -> None:
        """Digita um texto caractere por caractere.

        Args:
            text: Texto a digitar.
            interval: Intervalo entre caracteres.
        """
        pyautogui.typewrite(text, interval=interval)
        logger.debug("Texto digitado: %s", text[:20])

    def set_cooldown(self, key: str, cooldown: float) -> None:
        """Define cooldown para uma tecla (útil para skills).

        Args:
            key: Nome da tecla.
            cooldown: Tempo de cooldown em segundos.
        """
        self._cooldowns[key] = cooldown

    def _can_press(self, key: str) -> bool:
        """Verifica se a tecla pode ser pressionada (respeitando cooldown)."""
        if key not in self._cooldowns:
            return True

        last_time = self._last_key_time.get(key, 0)
        elapsed = time.time() - last_time
        return elapsed >= self._cooldowns[key]

    def get_remaining_cooldown(self, key: str) -> float:
        """Retorna o tempo restante de cooldown de uma tecla."""
        if key not in self._cooldowns:
            return 0.0

        last_time = self._last_key_time.get(key, 0)
        elapsed = time.time() - last_time
        remaining = self._cooldowns[key] - elapsed
        return max(0.0, remaining)
