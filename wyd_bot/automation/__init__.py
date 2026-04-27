"""Módulo de automação de inputs (teclado e mouse)."""

from wyd_bot.automation.actions import GameActions
from wyd_bot.automation.keyboard import KeyboardController
from wyd_bot.automation.mouse import MouseController

__all__ = ["KeyboardController", "MouseController", "GameActions"]
