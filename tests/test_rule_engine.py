"""Testes para o motor de regras."""

from unittest.mock import MagicMock

from wyd_bot.decision.rule_engine import RuleEngine
from wyd_bot.decision.state import BotMode, GameState
from wyd_bot.decision.strategy import FarmStrategy, HealStrategy


def test_register_strategy():
    engine = RuleEngine()
    engine.register(HealStrategy())
    engine.register(FarmStrategy())
    assert len(engine._strategies) == 2


def test_register_defaults():
    engine = RuleEngine()
    engine.register_defaults()
    assert len(engine._strategies) == 7


def test_tick_heal_priority():
    engine = RuleEngine()
    engine.register_defaults()

    state = GameState()
    state.player.hp_percent = 0.3

    actions = MagicMock()
    strategy_name = engine.tick(state, actions)
    assert strategy_name == "Heal"
    assert state.mode == BotMode.HEALING


def test_tick_flee_priority():
    engine = RuleEngine()
    engine.register_defaults()

    state = GameState()
    state.player.hp_percent = 0.1
    state.player.is_in_combat = True

    actions = MagicMock()
    strategy_name = engine.tick(state, actions)
    assert strategy_name == "Flee"
    assert state.mode == BotMode.FLEEING


def test_tick_dead_player():
    engine = RuleEngine()
    engine.register_defaults()

    state = GameState()
    state.player.is_alive = False

    actions = MagicMock()
    engine.tick(state, actions)
    assert state.mode == BotMode.DEAD


def test_tick_dead_only_increments_once():
    """Verifica que a morte só é contada uma vez."""
    engine = RuleEngine()
    engine.register_defaults()

    state = GameState()
    state.player.is_alive = False

    actions = MagicMock()
    engine.tick(state, actions)
    engine.tick(state, actions)
    engine.tick(state, actions)
    assert state.stats.deaths == 1


def test_tick_count():
    engine = RuleEngine()
    engine.register_defaults()

    state = GameState()
    actions = MagicMock()

    engine.tick(state, actions)
    engine.tick(state, actions)
    assert engine.tick_count == 2
