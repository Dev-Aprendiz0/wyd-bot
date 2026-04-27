"""Overlay visual para monitorar o bot em tempo real."""

from __future__ import annotations

from typing import TYPE_CHECKING

import cv2
import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray

from wyd_bot.decision.state import GameState
from wyd_bot.utils.logger import setup_logger

logger = setup_logger("wyd_bot.overlay")

GREEN = (0, 255, 0)
RED = (0, 0, 255)
BLUE = (255, 0, 0)
YELLOW = (0, 255, 255)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
ORANGE = (0, 165, 255)
CYAN = (255, 255, 0)


class Overlay:
    """Desenha informações de debug sobre o frame capturado."""

    def __init__(
        self,
        show_detections: bool = True,
        show_stats: bool = True,
    ) -> None:
        self.show_detections = show_detections
        self.show_stats = show_stats
        self._window_name = "WYD Bot - Debug"

    def draw(
        self,
        frame: NDArray[np.uint8],
        state: GameState,
    ) -> NDArray[np.uint8]:
        display = frame.copy()
        if self.show_detections:
            self._draw_detections(display, state)
        if self.show_stats:
            self._draw_stats(display, state)
        return display

    def show(
        self,
        frame: NDArray[np.uint8],
        state: GameState,
    ) -> bool:
        display = self.draw(frame, state)
        cv2.imshow(self._window_name, display)
        key = cv2.waitKey(1) & 0xFF
        return key != ord("q")

    def close(self) -> None:
        cv2.destroyAllWindows()

    def _draw_detections(
        self,
        frame: NDArray[np.uint8],
        state: GameState,
    ) -> None:
        for monster in state.nearby_monsters:
            cv2.rectangle(
                frame,
                (monster.x, monster.y),
                (monster.x + monster.width, monster.y + monster.height),
                RED,
                2,
            )
            label = f"{monster.label} ({monster.confidence:.0%})"
            cv2.putText(
                frame,
                label,
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

    def _draw_stats(
        self,
        frame: NDArray[np.uint8],
        state: GameState,
    ) -> None:
        panel_h = 240
        panel_w = 340
        overlay_region = frame[10 : 10 + panel_h, 10 : 10 + panel_w]
        dark = np.zeros_like(overlay_region)
        cv2.addWeighted(overlay_region, 0.3, dark, 0.7, 0, overlay_region)

        y_offset = 30
        lh = 22

        self._draw_text(
            frame, "WYD Bot - Legends of Midgard", 20, y_offset, WHITE, 0.6
        )
        y_offset += lh

        hp_pct = state.player.hp_percent
        if hp_pct > 0.5:
            hp_color = GREEN
        elif hp_pct > 0.2:
            hp_color = ORANGE
        else:
            hp_color = RED
        self._draw_bar(
            frame, 20, y_offset, 200, 14,
            state.player.hp_percent, hp_color, "HP",
        )
        y_offset += lh

        self._draw_bar(
            frame, 20, y_offset, 200, 14,
            state.player.mp_percent, BLUE, "MP",
        )
        y_offset += lh

        mode_txt = f"Modo: {state.mode.name}"
        self._draw_text(frame, mode_txt, 20, y_offset, WHITE, 0.5)
        y_offset += lh

        kph = state.stats.kills_per_hour()
        kills_txt = (
            f"Kills: {state.stats.kills_count} ({kph:.0f}/h)"
        )
        self._draw_text(frame, kills_txt, 20, y_offset, WHITE, 0.5)
        y_offset += lh

        lph = state.stats.loot_per_hour()
        loot_txt = (
            f"Loot: {state.stats.items_looted} ({lph:.0f}/h)"
        )
        self._draw_text(frame, loot_txt, 20, y_offset, WHITE, 0.5)
        y_offset += lh

        n_mon = len(state.nearby_monsters)
        n_items = len(state.nearby_items)
        entities = f"Monstros: {n_mon} | Itens: {n_items}"
        self._draw_text(frame, entities, 20, y_offset, WHITE, 0.5)
        y_offset += lh

        pot_txt = (
            f"Poções: {state.stats.potions_used} "
            f"(HP:{state.stats.hp_potions_used} "
            f"MP:{state.stats.mp_potions_used})"
        )
        self._draw_text(frame, pot_txt, 20, y_offset, WHITE, 0.5)
        y_offset += lh

        mins = state.session_duration / 60
        session_txt = (
            f"Sessão: {mins:.1f}min | "
            f"Mortes: {state.stats.deaths}"
        )
        self._draw_text(frame, session_txt, 20, y_offset, WHITE, 0.5)

        if state.stats.rare_drops > 0:
            y_offset += lh
            rare_txt = f"Drops raros: {state.stats.rare_drops}"
            self._draw_text(frame, rare_txt, 20, y_offset, CYAN, 0.5)

    @staticmethod
    def _draw_text(
        frame: NDArray[np.uint8],
        text: str,
        x: int,
        y: int,
        color: tuple[int, int, int],
        scale: float = 0.5,
    ) -> None:
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(frame, text, (x, y), font, scale, BLACK, 2)
        cv2.putText(frame, text, (x, y), font, scale, color, 1)

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
        cv2.rectangle(
            frame, (x, y), (x + width, y + height), WHITE, 1
        )
        fill_w = int(width * max(0, min(1, percent)))
        cv2.rectangle(
            frame, (x, y), (x + fill_w, y + height), color, -1
        )
        text = f"{label}: {percent:.0%}"
        pos = (x + width + 10, y + height - 2)
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(frame, text, pos, font, 0.4, WHITE, 1)
