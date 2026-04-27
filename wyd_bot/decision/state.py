"""Estado do jogo - representação central do estado atual."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto

from wyd_bot.vision.detector import Detection


class BotMode(Enum):
    """Modos de operação do bot."""

    IDLE = auto()
    FARMING = auto()
    COMBAT = auto()
    HEALING = auto()
    LOOTING = auto()
    FLEEING = auto()
    WALKING = auto()
    DEAD = auto()


@dataclass
class PlayerStatus:
    """Status atual do jogador."""

    hp_percent: float = 1.0
    mp_percent: float = 1.0
    is_alive: bool = True
    is_in_combat: bool = False
    position_x: int = 0
    position_y: int = 0


@dataclass
class GameState:
    """Representa o estado completo do jogo num dado momento.

    Centraliza todas as informações que os módulos de decisão precisam.
    """

    player: PlayerStatus = field(default_factory=PlayerStatus)
    mode: BotMode = BotMode.IDLE
    nearby_monsters: list[Detection] = field(default_factory=list)
    nearby_items: list[Detection] = field(default_factory=list)
    nearby_hp_bars: list[Detection] = field(default_factory=list)
    target: Detection | None = None
    last_combat_time: float = 0.0
    last_loot_time: float = 0.0
    last_heal_time: float = 0.0
    last_action_time: float = 0.0
    idle_since: float = field(default_factory=time.time)
    kills_count: int = 0
    items_looted: int = 0
    potions_used: int = 0
    deaths: int = 0
    session_start: float = field(default_factory=time.time)

    @property
    def idle_duration(self) -> float:
        """Tempo em segundos que o bot está idle."""
        return time.time() - self.idle_since

    @property
    def time_since_combat(self) -> float:
        """Tempo desde o último combate."""
        if self.last_combat_time == 0:
            return float("inf")
        return time.time() - self.last_combat_time

    @property
    def session_duration(self) -> float:
        """Duração da sessão em segundos."""
        return time.time() - self.session_start

    @property
    def has_target(self) -> bool:
        return self.target is not None

    @property
    def has_monsters_nearby(self) -> bool:
        return len(self.nearby_monsters) > 0

    @property
    def has_items_nearby(self) -> bool:
        return len(self.nearby_items) > 0

    @property
    def needs_healing(self) -> bool:
        """Verifica se precisa de cura (HP abaixo de 50%)."""
        return self.player.hp_percent < 0.5

    @property
    def needs_mp(self) -> bool:
        """Verifica se precisa de MP (abaixo de 30%)."""
        return self.player.mp_percent < 0.3

    @property
    def is_emergency(self) -> bool:
        """Verifica se está em emergência (HP muito baixo)."""
        return self.player.hp_percent < 0.2

    def get_closest_monster(self, ref_x: int, ref_y: int) -> Detection | None:
        """Retorna o monstro mais próximo de um ponto de referência."""
        if not self.nearby_monsters:
            return None
        return min(
            self.nearby_monsters,
            key=lambda m: ((m.center[0] - ref_x) ** 2 + (m.center[1] - ref_y) ** 2),
        )

    def get_closest_item(self, ref_x: int, ref_y: int) -> Detection | None:
        """Retorna o item mais próximo de um ponto de referência."""
        if not self.nearby_items:
            return None
        return min(
            self.nearby_items,
            key=lambda i: ((i.center[0] - ref_x) ** 2 + (i.center[1] - ref_y) ** 2),
        )

    def get_stats_summary(self) -> str:
        """Retorna resumo das estatísticas da sessão."""
        minutes = self.session_duration / 60
        return (
            f"Sessão: {minutes:.1f}min | "
            f"HP: {self.player.hp_percent:.0%} | MP: {self.player.mp_percent:.0%} | "
            f"Kills: {self.kills_count} | Loot: {self.items_looted} | "
            f"Poções: {self.potions_used} | Mortes: {self.deaths}"
        )
