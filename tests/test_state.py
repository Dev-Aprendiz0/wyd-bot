"""Testes para o módulo de estado do jogo."""

import time

from wyd_bot.decision.state import (
    BotMode,
    GameState,
    PlayerStatus,
    SessionStats,
)
from wyd_bot.vision.detector import Detection


def test_player_status_defaults():
    player = PlayerStatus()
    assert player.hp_percent == 1.0
    assert player.mp_percent == 1.0
    assert player.is_alive is True
    assert player.is_in_combat is False


def test_game_state_defaults():
    state = GameState()
    assert state.mode == BotMode.IDLE
    assert state.kills_count == 0
    assert state.nearby_monsters == []
    assert state.nearby_items == []
    assert state.target is None


def test_needs_healing():
    state = GameState()
    state.player.hp_percent = 0.4
    assert state.needs_healing is True

    state.player.hp_percent = 0.6
    assert state.needs_healing is False


def test_needs_mp():
    state = GameState()
    state.player.mp_percent = 0.2
    assert state.needs_mp is True

    state.player.mp_percent = 0.5
    assert state.needs_mp is False


def test_is_emergency():
    state = GameState()
    state.player.hp_percent = 0.15
    assert state.is_emergency is True

    state.player.hp_percent = 0.3
    assert state.is_emergency is False


def test_has_target():
    state = GameState()
    assert state.has_target is False

    state.target = Detection("mob", 100, 100, 50, 50, 0.9)
    assert state.has_target is True


def test_has_monsters_nearby():
    state = GameState()
    assert state.has_monsters_nearby is False

    state.nearby_monsters = [Detection("mob", 100, 100, 50, 50, 0.9)]
    assert state.has_monsters_nearby is True


def test_get_closest_monster():
    state = GameState()
    state.nearby_monsters = [
        Detection("far", 500, 500, 50, 50, 0.8),
        Detection("close", 110, 110, 50, 50, 0.9),
    ]
    closest = state.get_closest_monster(100, 100)
    assert closest is not None
    assert closest.label == "close"


def test_get_closest_monster_empty():
    state = GameState()
    assert state.get_closest_monster(100, 100) is None


def test_idle_duration():
    state = GameState()
    state.idle_since = time.time() - 5.0
    assert state.idle_duration >= 4.9


def test_get_stats_summary():
    state = GameState()
    state.stats.kills_count = 10
    state.stats.items_looted = 5
    summary = state.get_stats_summary()
    assert "Kills: 10" in summary
    assert "Loot: 5" in summary


def test_session_stats_kills_per_hour():
    stats = SessionStats()
    now = time.time()
    stats._kills_history = [now - 60, now - 30, now - 10]
    stats.kills_count = 3
    kph = stats.kills_per_hour()
    assert kph > 0


def test_session_stats_record_kill():
    stats = SessionStats()
    stats.record_kill()
    stats.record_kill()
    assert stats.kills_count == 2
    assert len(stats._kills_history) == 2


def test_is_out_of_potions():
    state = GameState()
    assert state.is_out_of_potions is False
    state.potions_remaining = 0
    assert state.is_out_of_potions is True


def test_deaths_setter():
    state = GameState()
    state.deaths = 5
    assert state.stats.deaths == 5
    assert state.deaths == 5


def test_potion_time_tracking():
    state = GameState()
    assert state.time_since_hp_potion == float("inf")
    state.last_hp_potion_time = time.time() - 3.0
    assert state.time_since_hp_potion >= 2.9


def test_get_weakest_monster():
    state = GameState()
    state.nearby_monsters = [
        Detection("strong", 100, 100, 50, 50, 0.95),
        Detection("weak", 200, 200, 50, 50, 0.3),
    ]
    weakest = state.get_weakest_monster()
    assert weakest is not None
    assert weakest.label == "weak"
