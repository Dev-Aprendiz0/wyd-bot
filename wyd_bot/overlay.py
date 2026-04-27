"""Overlay visual para monitorar o bot em tempo real.

Exibe informações do estado do bot sobre o jogo usando OpenCV.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import cv2
import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray

from wyd_bot.decision.state import GameState
from wyd_bot.utils.logger import setup_logger

logger = setup_logger("wyd_bot.overlay")

# Cores BGR
GREEN = (0, 255, 0)
RED = (0, 0, 255)
BLUE = (255, 0, 0)
YELLOW = (0, 255, 255)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
ORANGE = (0, 165, 255)


class Overlay:
    """Desenha informações de debug sobre o frame capturado."""

    def __init__(self, show_detections: bool = True, show_stats: bool = True) -> None:
        self.show_detections = show_detections
        self.show_stats = show_stats
        self._window_name = "WYD Bot - Debug"

    def draw(self, frame: NDArray[np.uint8], state: GameState) -> NDArray[np.uint8]:
        """Desenha o overlay sobre o frame.

        Args:
            frame: Frame BGR capturado.
            state: Estado atual do jogo.

        Returns:
            Frame com overlay desenhado.
        """
        display = frame.copy()

        if self.show_detections:
            self._draw_detections(display, state)

        if self.show_stats:
            self._draw_stats(display, state)

        return display

    def show(self, frame: NDArray[np.uint8], state: GameState) -> bool:
        """Mostra o overlay em uma janela OpenCV.

        Args:
            frame: Frame BGR capturado.
            state: Estado atual do jogo.

        Returns:
            False se a janela foi fechada (tecla 'q'), True caso contrário.
        """
        display = self.draw(frame, state)
        cv2.imshow(self._window_name, display)
        key = cv2.waitKey(1) & 0xFF
        return key != ord("q")

    def close(self) -> None:
        """Fecha a janela de overlay."""
        cv2.destroyAllWindows()

    def _draw_detections(self, frame: NDArray[np.uint8], state: GameState) -> None:
        """Desenha retângulos ao redor de detecções."""
        for monster in state.nearby_monsters:
            cv2.rectangle(
                frame,
                (monster.x, monster.y),
                (monster.x + monster.width, monster.y + monster.height),
                RED,
                2,
            )
            cv2.putText(
                frame,
                f"{monster.label} ({monster.confidence:.0%})",
                (monster.x, monster.y - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                RED,
                1,
            )

        for item in state.nearby_items:
            cv2.rectangle(
                frame,
                (item.x, item.y),
                (item.x + item.width, item.y + item.height),
                YELLOW,
                2,
            )
            cv2.putText(
                frame,
                f"{item.label}",
                (item.x, item.y - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                YELLOW,
                1,
            )

        if state.target:
            t = state.target
            cv2.rectangle(
                frame,
                (t.x - 3, t.y - 3),
                (t.x + t.width + 3, t.y + t.height + 3),
                GREEN,
                3,
            )

    def _draw_stats(self, frame: NDArray[np.uint8], state: GameState) -> None:
        """Desenha painel de estatísticas no canto da tela."""
        panel_h = 180
        panel_w = 320
        overlay_region = frame[10 : 10 + panel_h, 10 : 10 + panel_w]
        dark = np.zeros_like(overlay_region)
        cv2.addWeighted(overlay_region, 0.3, dark, 0.7, 0, overlay_region)

        y_offset = 30
        line_height = 22

        self._draw_text(frame, "WYD Bot - Legends of Midgard", 20, y_offset, WHITE, 0.6)
        y_offset += line_height

        hp_pct = state.player.hp_percent
        if hp_pct > 0.5:
            hp_color = GREEN
        elif hp_pct > 0.2:
            hp_color = ORANGE
        else:
            hp_color = RED
        self._draw_bar(frame, 20, y_offset, 200, 14, state.player.hp_percent, hp_color, "HP")
        y_offset += line_height

        self._draw_bar(frame, 20, y_offset, 200, 14, state.player.mp_percent, BLUE, "MP")
        y_offset += line_height

        self._draw_text(frame, f"Modo: {state.mode.name}", 20, y_offset, WHITE, 0.5)
        y_offset += line_height

        kills_loot = f"Kills: {state.kills_count} | Loot: {state.items_looted}"
        self._draw_text(frame, kills_loot, 20, y_offset, WHITE, 0.5)
        y_offset += line_height

        n_mon = len(state.nearby_monsters)
        n_items = len(state.nearby_items)
        entities = f"Monstros: {n_mon} | Itens: {n_items}"
        self._draw_text(frame, entities, 20, y_offset, WHITE, 0.5)
        y_offset += line_height

        mins = state.session_duration / 60
        session_txt = f"Sessão: {mins:.1f}min | Mortes: {state.deaths}"
        self._draw_text(frame, session_txt, 20, y_offset, WHITE, 0.5)

    @staticmethod
    def _draw_text(
        frame: NDArray[np.uint8],
        text: str,
        x: int,
        y: int,
        color: tuple[int, int, int],
        scale: float = 0.5,
    ) -> None:
        cv2.putText(frame, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, scale, BLACK, 2)
        cv2.putText(frame, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, scale, color, 1)

    @staticmethod
    def _draw_bar(
        frame: NDArray[np.uint8],
        x: int,
        y: int,
        width: int,
        height: int,
        percent: float,
        color: tuple[int, int, int],
        label: str,
    ) -> None:
        cv2.rectangle(frame, (x, y), (x + width, y + height), WHITE, 1)
        fill_w = int(width * max(0, min(1, percent)))
        cv2.rectangle(frame, (x, y), (x + fill_w, y + height), color, -1)
        text = f"{label}: {percent:.0%}"
        pos = (x + width + 10, y + height - 2)
        cv2.putText(frame, text, pos, cv2.FONT_HERSHEY_SIMPLEX, 0.4, WHITE, 1)
