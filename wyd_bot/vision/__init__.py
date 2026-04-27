"""Módulo de visão computacional para captura e análise de tela."""

from wyd_bot.vision.detector import GameDetector
from wyd_bot.vision.ocr import TextReader
from wyd_bot.vision.screen_capture import ScreenCapture

__all__ = ["ScreenCapture", "GameDetector", "TextReader"]
