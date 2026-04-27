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
    RESURRECTING = auto()
    BUFFING = auto()
    RETURNING_TO_TOWN = auto()
    DISCONNECTED = auto()


@dataclass
class PlayerStatus:
    """Status atual do jogador."""

    hp_percent: float = 1.0
    mp_percent: float = 1.0
    is_alive: bool = True
    is_in_combat: bool = False
    position_x: int = 0
    position_y: int = 0
    level: int = 0


@dataclass
class SessionStats:
    """Estatísticas detalhadas da sessão de farm."""

    kills_count: int = 0
    items_looted: int = 0
    potions_used: int = 0
    hp_potions_used: int = 0
    mp_potions_used: int = 0
    deaths: int = 0
    resurrections: int = 0
    skills_used: int = 0
    rare_drops: int = 0
    disconnections: int = 0
    _kills_history: list[float] = field(default_factory=list)
    _loot_history: list[float] = field(default_factory=list)

    def record_kill(self) -> None:
        self.kills_count += 1
        self._kills_history.append(time.time())

    def record_loot(self) -> None:
        self.items_looted += 1
        self._loot_history.append(time.time())

    def kills_per_hour(self) -> float:
        """Calcula kills por hora baseado no último período."""
        now = time.time()
        one_hour_ago = now - 3600
        recent = [t for t in self._kills_history if t > one_hour_ago]
        if not recent:
            return 0.0
        elapsed = now - recent[0]
        if elapsed < 1:
            return 0.0
        return len(recent) / (elapsed / 3600)

    def loot_per_hour(self) -> float:
        """Calcula loot por hora baseado no último período."""
        now = time.time()
        one_hour_ago = now - 3600
        recent = [t for t in self._loot_history if t > one_hour_ago]
        if not recent:
            return 0.0
        elapsed = now - recent[0]
        if elapsed < 1:
            return 0.0
        return len(recent) / (elapsed / 3600)


@dataclass
class GameState:
    """Representa o estado completo do jogo num dado momento."""

    player: PlayerStatus = field(default_factory=PlayerStatus)
    stats: SessionStats = field(default_factory=SessionStats)
    mode: BotMode = BotMode.IDLE
    nearby_monsters: list[Detection] = field(default_factory=list)
    nearby_items: list[Detection] = field(default_factory=list)
    nearby_hp_bars: list[Detection] = field(default_factory=list)
    target: Detection | None = None
    last_combat_time: float = 0.0
    last_loot_time: float = 0.0
    last_heal_time: float = 0.0
    last_action_time: float = 0.0
    last_hp_potion_time: float = 0.0
    last_mp_potion_time: float = 0.0
    last_buff_time: float = 0.0
    last_resurrect_time: float = 0.0
    idle_since: float = field(default_factory=time.time)
    session_start: float = field(default_factory=time.time)
    potions_remaining: int = -1  # -1 = desconhecido
    is_disconnected: bool = False

    @property
    def kills_count(self) -> int:
        return self.stats.kills_count

    @property
    def items_looted(self) -> int:
        return self.stats.items_looted

    @property
    def potions_used(self) -> int:
        return self.stats.potions_used

    @property
    def deaths(self) -> int:
        return self.stats.deaths

    @deaths.setter
    def deaths(self, value: int) -> None:
        self.stats.deaths = value

    @property
    def idle_duration(self) -> float:
        return time.time() - self.idle_since

    @property
    def time_since_combat(self) -> float:
        if self.last_combat_time == 0:
            return float("inf")
        return time.time() - self.last_combat_time

    @property
    def time_since_hp_potion(self) -> float:
        if self.last_hp_potion_time == 0:
            return float("inf")
        return time.time() - self.last_hp_potion_time

    @property
    def time_since_mp_potion(self) -> float:
        if self.last_mp_potion_time == 0:
            return float("inf")
        return time.time() - self.last_mp_potion_time

    @property
    def time_since_buff(self) -> float:
        if self.last_buff_time == 0:
            return float("inf")
        return time.time() - self.last_buff_time

    @property
    def session_duration(self) -> float:
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
        return self.player.hp_percent < 0.5

    @property
    def needs_mp(self) -> bool:
        return self.player.mp_percent < 0.3

    @property
    def is_emergency(self) -> bool:
        return self.player.hp_percent < 0.2

    @property
    def is_out_of_potions(self) -> bool:
        return self.potions_remaining == 0

    def get_closest_monster(
        self, ref_x: int, ref_y: int
    ) -> Detection | None:
        if not self.nearby_monsters:
            return None
        return min(
            self.nearby_monsters,
            key=lambda m: (
                (m.center[0] - ref_x) ** 2 + (m.center[1] - ref_y) ** 2
            ),
        )

    def get_weakest_monster(self) -> Detection | None:
        """Retorna o monstro com menor confiança (proxy para HP baixo)."""
        if not self.nearby_monsters:
            return None
        return min(self.nearby_monsters, key=lambda m: m.confidence)

    def get_closest_item(
        self, ref_x: int, ref_y: int
    ) -> Detection | None:
        if not self.nearby_items:
            return None
        return min(
            self.nearby_items,
            key=lambda i: (
                (i.center[0] - ref_x) ** 2 + (i.center[1] - ref_y) ** 2
            ),
        )

    def get_stats_summary(self) -> str:
        minutes = self.session_duration / 60
        kph = self.stats.kills_per_hour()
        return (
            f"Sessão: {minutes:.1f}min | "
            f"HP: {self.player.hp_percent:.0%} | "
            f"MP: {self.player.mp_percent:.0%} | "
            f"Kills: {self.stats.kills_count} ({kph:.0f}/h) | "
            f"Loot: {self.stats.items_looted} | "
            f"Poções: {self.stats.potions_used} | "
            f"Mortes: {self.stats.deaths}"
        )
