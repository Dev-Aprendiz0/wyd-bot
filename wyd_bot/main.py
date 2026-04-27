"""Bot principal do WYD - integra todos os módulos."""

from __future__ import annotations

import signal
import time
from pathlib import Path
from threading import Event

from pynput import keyboard as kb

from wyd_bot.automation.actions import GameActions
from wyd_bot.automation.keyboard import KeyboardController
from wyd_bot.automation.mouse import MouseController
from wyd_bot.decision.rule_engine import RuleEngine
from wyd_bot.decision.state import GameState
from wyd_bot.utils.config import Config
from wyd_bot.utils.logger import setup_logger
from wyd_bot.vision.detector import GameDetector
from wyd_bot.vision.screen_capture import ScreenCapture

logger = setup_logger("wyd_bot.main")


class WYDBot:
    """Bot principal para WYD - Legends of Midgard.

    Integra captura de tela, visão computacional, automação e decisão
    em um loop principal contínuo.
    """

    def __init__(self, config_path: str | None = None) -> None:
        self.config = Config(config_path)
        cfg = self.config.bot

        self.capture = ScreenCapture(target_fps=cfg.capture_fps)

        self.detector = GameDetector(
            monster_template_dir=cfg.detection.monster_template_dir,
            item_template_dir=cfg.detection.item_template_dir,
            threshold=cfg.detection.detection_threshold,
        )

        kb_ctrl = KeyboardController()
        mouse_ctrl = MouseController()

        self.actions = GameActions(
            keyboard=kb_ctrl,
            mouse=mouse_ctrl,
            combat_config=cfg.combat,
            farm_config=cfg.farm,
        )

        self.rule_engine = RuleEngine()
        self.rule_engine.register_defaults(
            hp_threshold=cfg.combat.hp_heal_threshold,
            mp_threshold=cfg.combat.mp_heal_threshold,
            emergency_threshold=cfg.combat.hp_emergency_threshold,
        )

        self.state = GameState()
        self._running = False
        self._paused = False
        self._stop_event = Event()
        self._hotkey_listener: kb.GlobalHotKeys | None = None

        if cfg.log_file:
            setup_logger("wyd_bot", log_file=cfg.log_file)

    def start(self) -> None:
        """Inicia o bot."""
        logger.info("=" * 60)
        logger.info("WYD Bot - Legends of Midgard")
        logger.info("=" * 60)
        logger.info("Pressione %s para pausar/continuar", self.config.bot.hotkey_toggle)
        logger.info("Pressione %s para parar", self.config.bot.hotkey_stop)
        logger.info("=" * 60)

        self._running = True
        self._setup_hotkeys()
        self._setup_signal_handlers()

        try:
            self.capture.start()
            self._main_loop()
        except KeyboardInterrupt:
            logger.info("Interrompido pelo usuário")
        finally:
            self.stop()

    def stop(self) -> None:
        """Para o bot."""
        self._running = False
        self._stop_event.set()
        self.capture.stop()

        if self._hotkey_listener:
            self._hotkey_listener.stop()

        logger.info("Bot parado")
        logger.info(self.state.get_stats_summary())

    def _main_loop(self) -> None:
        """Loop principal do bot."""
        interval = self.config.bot.decision_interval

        while self._running and not self._stop_event.is_set():
            if self._paused:
                time.sleep(0.5)
                continue

            try:
                loop_start = time.time()

                frame = self.capture.capture_frame()

                self._update_state(frame)

                strategy_name = self.rule_engine.tick(self.state, self.actions)

                if self.rule_engine.tick_count % 100 == 0:
                    logger.info(
                        "[Tick %d] Modo: %s | Estratégia: %s | %s",
                        self.rule_engine.tick_count,
                        self.state.mode.name,
                        strategy_name or "None",
                        self.state.get_stats_summary(),
                    )

                elapsed = time.time() - loop_start
                sleep_time = max(0, interval - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)

            except Exception:
                logger.exception("Erro no loop principal")
                if self.config.bot.screenshot_on_error:
                    self._save_error_screenshot()
                time.sleep(1.0)

    def _update_state(self, frame: object) -> None:
        """Atualiza o estado do jogo baseado no frame capturado."""
        import numpy as np
        from numpy.typing import NDArray

        np_frame: NDArray[np.uint8] = frame  # type: ignore[assignment]
        cfg = self.config.bot

        hp_region = cfg.hp_mp.hp_region.as_tuple()
        mp_region = cfg.hp_mp.mp_region.as_tuple()

        if hp_region != (0, 0, 0, 0):
            self.state.player.hp_percent = self.detector.detect_hp_percentage(
                np_frame,
                hp_region,
                cfg.hp_mp.hp_color_lower,
                cfg.hp_mp.hp_color_upper,
            )

        if mp_region != (0, 0, 0, 0):
            self.state.player.mp_percent = self.detector.detect_mp_percentage(
                np_frame,
                mp_region,
                cfg.hp_mp.mp_color_lower,
                cfg.hp_mp.mp_color_upper,
            )

        self.state.player.is_alive = self.state.player.hp_percent > 0

        self.state.nearby_monsters = self.detector.find_monsters(np_frame)
        self.state.nearby_items = self.detector.find_items(np_frame)

        hp_bars = self.detector.find_hp_bars_above_entities(np_frame)
        self.state.nearby_hp_bars = hp_bars

        if self.state.nearby_monsters:
            self.state.player.is_in_combat = True
            self.state.idle_since = time.time()
        elif self.state.player.is_in_combat and self.state.time_since_combat > 3.0:
            self.state.player.is_in_combat = False

        if not self.state.has_target and not self.state.has_monsters_nearby:
            pass
        elif self.state.has_target and not self.state.has_monsters_nearby:
            self.state.target = None
            self.state.stats.record_kill()

    def _save_error_screenshot(self) -> None:
        """Salva screenshot quando ocorre erro."""
        try:
            import cv2

            frame = self.capture.capture_frame()
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            path = f"screenshots/error_{timestamp}.png"
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(path, frame)
            logger.info("Screenshot de erro salva: %s", path)
        except Exception:
            logger.exception("Falha ao salvar screenshot de erro")

    def _setup_hotkeys(self) -> None:
        """Configura hotkeys globais."""
        toggle_key = f"<{self.config.bot.hotkey_toggle}>"
        stop_key = f"<{self.config.bot.hotkey_stop}>"

        self._hotkey_listener = kb.GlobalHotKeys(
            {
                toggle_key: self._toggle_pause,
                stop_key: self._request_stop,
            }
        )
        self._hotkey_listener.start()

    def _toggle_pause(self) -> None:
        """Pausa ou continua o bot."""
        self._paused = not self._paused
        status = "PAUSADO" if self._paused else "RODANDO"
        logger.info("Bot %s", status)

    def _request_stop(self) -> None:
        """Solicita parada do bot."""
        logger.info("Parada solicitada via hotkey")
        self._running = False
        self._stop_event.set()

    def _setup_signal_handlers(self) -> None:
        """Configura handlers para sinais do sistema."""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum: int, frame: object) -> None:
        """Handler para SIGINT/SIGTERM."""
        logger.info("Sinal recebido: %d", signum)
        self._running = False
        self._stop_event.set()


def main() -> None:
    """Entry point do bot."""
    import argparse

    parser = argparse.ArgumentParser(description="WYD Bot - Legends of Midgard")
    parser.add_argument(
        "-c",
        "--config",
        default="config/default.yaml",
        help="Caminho para o arquivo de configuração (default: config/default.yaml)",
    )
    parser.add_argument(
        "--calibrate",
        action="store_true",
        help="Modo de calibração - captura screenshots para configurar regiões",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Ativa logging detalhado (DEBUG)",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Abre a interface gráfica (GUI) ao invés do terminal",
    )
    args = parser.parse_args()

    if args.verbose:
        import logging

        setup_logger("wyd_bot", level=logging.DEBUG)

    if args.gui:
        from wyd_bot.gui import run_gui

        run_gui()
        return

    if args.calibrate:
        _run_calibration()
        return

    config_path = args.config if Path(args.config).exists() else None
    bot = WYDBot(config_path)
    bot.start()


def _run_calibration() -> None:
    """Modo de calibração - ajuda a configurar as regiões da tela."""
    import cv2

    logger.info("=" * 60)
    logger.info("MODO DE CALIBRAÇÃO")
    logger.info("=" * 60)
    logger.info("Posicione a janela do WYD e pressione Enter...")
    input()

    capture = ScreenCapture()
    capture.start()
    frame = capture.capture_frame()
    capture.stop()

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    path = f"screenshots/calibration_{timestamp}.png"
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(path, frame)
    logger.info("Screenshot salva: %s", path)
    logger.info(
        "Use esta imagem para identificar as regiões de HP, MP, etc. "
        "e configure no arquivo config/default.yaml"
    )


if __name__ == "__main__":
    main()
