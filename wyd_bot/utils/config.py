"""Sistema de configuração do bot."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ScreenRegion:
    """Define uma região retangular da tela."""

    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0

    def as_tuple(self) -> tuple[int, int, int, int]:
        return (self.x, self.y, self.width, self.height)


@dataclass
class HpMpConfig:
    """Configuração das barras de HP/MP."""

    hp_region: ScreenRegion = field(default_factory=ScreenRegion)
    mp_region: ScreenRegion = field(default_factory=ScreenRegion)
    hp_color_lower: tuple[int, int, int] = (0, 100, 100)
    hp_color_upper: tuple[int, int, int] = (10, 255, 255)
    mp_color_lower: tuple[int, int, int] = (100, 100, 100)
    mp_color_upper: tuple[int, int, int] = (130, 255, 255)


@dataclass
class CombatConfig:
    """Configuração de combate."""

    attack_key: str = "space"
    skill_keys: list[str] = field(default_factory=lambda: ["1", "2", "3", "4"])
    skill_cooldowns: list[float] = field(default_factory=lambda: [2.0, 3.0, 5.0, 8.0])
    target_key: str = "tab"
    hp_heal_threshold: float = 0.5
    mp_heal_threshold: float = 0.3
    hp_potion_key: str = "f1"
    mp_potion_key: str = "f2"
    hp_emergency_threshold: float = 0.2
    flee_key: str = "escape"


@dataclass
class FarmConfig:
    """Configuração de farm."""

    farm_radius: int = 200
    loot_enabled: bool = True
    loot_key: str = "z"
    auto_target: bool = True
    walk_pattern: str = "circular"
    walk_delay: float = 0.5
    max_idle_time: float = 10.0
    return_to_center: bool = True


@dataclass
class DetectionConfig:
    """Configuração de detecção visual."""

    monster_template_dir: str = "templates/monsters"
    item_template_dir: str = "templates/items"
    detection_threshold: float = 0.7
    npc_detection_enabled: bool = True
    minimap_region: ScreenRegion = field(default_factory=ScreenRegion)


@dataclass
class BotConfig:
    """Configuração principal do bot."""

    game_window_title: str = "With Your Destiny"
    capture_fps: int = 10
    decision_interval: float = 0.1
    hp_mp: HpMpConfig = field(default_factory=HpMpConfig)
    combat: CombatConfig = field(default_factory=CombatConfig)
    farm: FarmConfig = field(default_factory=FarmConfig)
    detection: DetectionConfig = field(default_factory=DetectionConfig)
    hotkey_toggle: str = "f9"
    hotkey_stop: str = "f10"
    log_file: str = "logs/wyd_bot.log"
    screenshot_on_error: bool = True


class Config:
    """Gerenciador de configuração que carrega de YAML."""

    def __init__(self, config_path: str | None = None) -> None:
        self.bot = BotConfig()
        if config_path:
            self.load(config_path)

    def load(self, config_path: str) -> None:
        """Carrega configuração de um arquivo YAML."""
        path = Path(config_path)
        if not path.exists():
            return

        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        self._apply_dict(self.bot, data)

    def save(self, config_path: str) -> None:
        """Salva configuração em um arquivo YAML."""
        path = Path(config_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = self._to_dict(self.bot)
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

    def _apply_dict(self, obj: Any, data: dict[str, Any]) -> None:
        """Aplica um dicionário a um dataclass recursivamente."""
        for key, value in data.items():
            if hasattr(obj, key):
                attr = getattr(obj, key)
                if hasattr(attr, "__dataclass_fields__") and isinstance(value, dict):
                    self._apply_dict(attr, value)
                elif isinstance(attr, tuple) and isinstance(value, list):
                    setattr(obj, key, tuple(value))
                else:
                    setattr(obj, key, value)

    def _to_dict(self, obj: Any) -> Any:
        """Converte um dataclass para dicionário recursivamente."""
        if hasattr(obj, "__dataclass_fields__"):
            result: dict[str, Any] = {}
            for field_name in obj.__dataclass_fields__:
                value = getattr(obj, field_name)
                result[field_name] = self._to_dict(value)
            return result
        if isinstance(obj, tuple):
            return list(self._to_dict(item) for item in obj)
        if isinstance(obj, list):
            return [self._to_dict(item) for item in obj]
        return obj
