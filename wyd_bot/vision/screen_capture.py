"""Módulo de captura de tela em tempo real."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import mss
import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray

from wyd_bot.utils.logger import setup_logger

logger = setup_logger("wyd_bot.vision.capture")


class ScreenCapture:
    """Captura frames da tela do jogo usando mss (rápido e cross-platform)."""

    def __init__(
        self,
        monitor_index: int = 1,
        region: tuple[int, int, int, int] | None = None,
        target_fps: int = 10,
    ) -> None:
        """Inicializa o capturador de tela.

        Args:
            monitor_index: Índice do monitor (1 = principal).
            region: Região específica (x, y, width, height) ou None para tela toda.
            target_fps: FPS alvo para captura.
        """
        self.monitor_index = monitor_index
        self.region = region
        self.target_fps = target_fps
        self.frame_interval = 1.0 / target_fps
        self._sct: mss.mss | None = None
        self._last_capture_time: float = 0
        self._frame_count: int = 0
        self._fps_timer: float = 0
        self._current_fps: float = 0

    def start(self) -> None:
        """Inicializa o contexto de captura."""
        self._sct = mss.mss()
        self._fps_timer = time.time()
        logger.info(
            "Captura de tela iniciada (monitor=%d, fps_alvo=%d)",
            self.monitor_index,
            self.target_fps,
        )

    def stop(self) -> None:
        """Fecha o contexto de captura."""
        if self._sct:
            self._sct.close()
            self._sct = None
        logger.info("Captura de tela parada")

    def capture_frame(self) -> NDArray[np.uint8]:
        """Captura um frame da tela.

        Returns:
            Frame como array numpy BGR (compatível com OpenCV).
        """
        if self._sct is None:
            self.start()
            assert self._sct is not None

        now = time.time()
        elapsed = now - self._last_capture_time
        if elapsed < self.frame_interval:
            time.sleep(self.frame_interval - elapsed)

        if self.region:
            monitor = {
                "left": self.region[0],
                "top": self.region[1],
                "width": self.region[2],
                "height": self.region[3],
            }
        else:
            monitor = self._sct.monitors[self.monitor_index]

        screenshot = self._sct.grab(monitor)
        frame = np.array(screenshot, dtype=np.uint8)
        frame = frame[:, :, :3]  # Remove canal alpha (BGRA -> BGR)

        self._last_capture_time = time.time()
        self._frame_count += 1

        if now - self._fps_timer >= 1.0:
            self._current_fps = self._frame_count / (now - self._fps_timer)
            self._frame_count = 0
            self._fps_timer = now

        return frame

    def capture_region(self, x: int, y: int, width: int, height: int) -> NDArray[np.uint8]:
        """Captura uma região específica da tela.

        Args:
            x: Coordenada X do canto superior esquerdo.
            y: Coordenada Y do canto superior esquerdo.
            width: Largura da região.
            height: Altura da região.

        Returns:
            Frame da região como array numpy BGR.
        """
        if self._sct is None:
            self.start()
            assert self._sct is not None

        monitor = {"left": x, "top": y, "width": width, "height": height}
        screenshot = self._sct.grab(monitor)
        frame = np.array(screenshot, dtype=np.uint8)
        return frame[:, :, :3]

    @property
    def fps(self) -> float:
        """Retorna o FPS atual de captura."""
        return self._current_fps

    def __enter__(self) -> ScreenCapture:
        self.start()
        return self

    def __exit__(self, *args: object) -> None:
        self.stop()
