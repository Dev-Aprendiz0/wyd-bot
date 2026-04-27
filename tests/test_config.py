"""Testes para o módulo de configuração."""

import os
import tempfile

from wyd_bot.utils.config import BotConfig, Config, ScreenRegion


def test_screen_region_defaults():
    region = ScreenRegion()
    assert region.as_tuple() == (0, 0, 0, 0)


def test_screen_region_custom():
    region = ScreenRegion(x=10, y=20, width=100, height=50)
    assert region.as_tuple() == (10, 20, 100, 50)


def test_bot_config_defaults():
    cfg = BotConfig()
    assert cfg.capture_fps == 10
    assert cfg.hotkey_toggle == "f9"
    assert cfg.combat.attack_key == "space"


def test_config_load_nonexistent():
    config = Config("/nonexistent/path.yaml")
    assert config.bot.capture_fps == 10


def test_config_save_and_load():
    config = Config()
    config.bot.capture_fps = 30
    config.bot.combat.attack_key = "a"

    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
        tmp_path = f.name

    try:
        config.save(tmp_path)
        loaded = Config(tmp_path)
        assert loaded.bot.capture_fps == 30
        assert loaded.bot.combat.attack_key == "a"
    finally:
        os.unlink(tmp_path)


def test_config_partial_load():
    import yaml

    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
        yaml.dump({"capture_fps": 60}, f)
        tmp_path = f.name

    try:
        config = Config(tmp_path)
        assert config.bot.capture_fps == 60
        assert config.bot.combat.attack_key == "space"  # default mantido
    finally:
        os.unlink(tmp_path)
