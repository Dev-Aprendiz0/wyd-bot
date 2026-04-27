"""Interface gráfica (GUI) do WYD Bot usando tkinter."""

from __future__ import annotations

import logging
import queue
import threading
import tkinter as tk
from tkinter import scrolledtext, ttk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wyd_bot.main import WYDBot

from wyd_bot.utils.logger import setup_logger

logger = setup_logger("wyd_bot.gui")


class QueueHandler(logging.Handler):
    """Handler que envia logs para uma queue thread-safe."""

    def __init__(self, log_queue: queue.Queue[str]) -> None:
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        self.log_queue.put(msg)


class BotGUI:
    """Interface gráfica principal do WYD Bot."""

    BG_DARK = "#1a1a2e"
    BG_PANEL = "#16213e"
    BG_INPUT = "#0f3460"
    FG_TEXT = "#e0e0e0"
    FG_ACCENT = "#00d4ff"
    FG_HP = "#ff4444"
    FG_MP = "#4488ff"
    FG_GREEN = "#44ff44"
    FG_YELLOW = "#ffcc00"
    FG_ORANGE = "#ff8800"

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("WYD Bot - Legends of Midgard")
        self.root.geometry("780x620")
        self.root.configure(bg=self.BG_DARK)
        self.root.resizable(True, True)
        self.root.minsize(700, 550)

        self._bot: WYDBot | None = None
        self._bot_thread: threading.Thread | None = None
        self._running = False
        self._paused = False
        self._log_queue: queue.Queue[str] = queue.Queue()
        self._update_interval = 500
        self._bot_generation = 0

        self._setup_styles()
        self._build_ui()
        self._setup_log_handler()
        self._schedule_updates()

    def _setup_styles(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(
            "Dark.TFrame", background=self.BG_DARK
        )
        style.configure(
            "Panel.TFrame", background=self.BG_PANEL
        )
        style.configure(
            "Dark.TLabel",
            background=self.BG_DARK,
            foreground=self.FG_TEXT,
            font=("Segoe UI", 10),
        )
        style.configure(
            "Title.TLabel",
            background=self.BG_DARK,
            foreground=self.FG_ACCENT,
            font=("Segoe UI", 14, "bold"),
        )
        style.configure(
            "Status.TLabel",
            background=self.BG_PANEL,
            foreground=self.FG_TEXT,
            font=("Segoe UI", 10),
        )
        style.configure(
            "Value.TLabel",
            background=self.BG_PANEL,
            foreground=self.FG_ACCENT,
            font=("Consolas", 11, "bold"),
        )
        style.configure(
            "Start.TButton",
            font=("Segoe UI", 10, "bold"),
        )
        style.configure(
            "Stop.TButton",
            font=("Segoe UI", 10, "bold"),
        )

    def _build_ui(self) -> None:
        main = ttk.Frame(self.root, style="Dark.TFrame")
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        ttk.Label(
            main,
            text="WYD Bot - Legends of Midgard",
            style="Title.TLabel",
        ).pack(pady=(0, 10))

        top = ttk.Frame(main, style="Dark.TFrame")
        top.pack(fill=tk.X)

        self._build_status_panel(top)
        self._build_controls_panel(top)

        mid = ttk.Frame(main, style="Dark.TFrame")
        mid.pack(fill=tk.X, pady=(10, 0))
        self._build_config_panel(mid)

        self._build_log_panel(main)

    def _build_status_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.Frame(parent, style="Panel.TFrame")
        frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        pad = {"padx": 10, "pady": 2}

        ttk.Label(frame, text="Status", style="Title.TLabel").pack(
            **pad, anchor=tk.W
        )

        row_hp = ttk.Frame(frame, style="Panel.TFrame")
        row_hp.pack(fill=tk.X, **pad)
        ttk.Label(row_hp, text="HP:", style="Status.TLabel").pack(
            side=tk.LEFT
        )
        self._hp_bar = ttk.Progressbar(
            row_hp, length=180, mode="determinate"
        )
        self._hp_bar.pack(side=tk.LEFT, padx=(5, 5))
        self._hp_bar["value"] = 100
        self._hp_label = ttk.Label(
            row_hp, text="100%", style="Value.TLabel"
        )
        self._hp_label.pack(side=tk.LEFT)

        row_mp = ttk.Frame(frame, style="Panel.TFrame")
        row_mp.pack(fill=tk.X, **pad)
        ttk.Label(row_mp, text="MP:", style="Status.TLabel").pack(
            side=tk.LEFT
        )
        self._mp_bar = ttk.Progressbar(
            row_mp, length=180, mode="determinate"
        )
        self._mp_bar.pack(side=tk.LEFT, padx=(5, 5))
        self._mp_bar["value"] = 100
        self._mp_label = ttk.Label(
            row_mp, text="100%", style="Value.TLabel"
        )
        self._mp_label.pack(side=tk.LEFT)

        stats = ttk.Frame(frame, style="Panel.TFrame")
        stats.pack(fill=tk.X, **pad)

        self._mode_var = tk.StringVar(value="IDLE")
        self._kills_var = tk.StringVar(value="Kills: 0 (0/h)")
        self._loot_var = tk.StringVar(value="Loot: 0 (0/h)")
        self._potions_var = tk.StringVar(value="Poções: 0")
        self._deaths_var = tk.StringVar(value="Mortes: 0")
        self._session_var = tk.StringVar(value="Sessão: 0.0 min")

        ttk.Label(
            stats, textvariable=self._mode_var, style="Value.TLabel"
        ).pack(anchor=tk.W)
        ttk.Label(
            stats, textvariable=self._kills_var, style="Status.TLabel"
        ).pack(anchor=tk.W)
        ttk.Label(
            stats, textvariable=self._loot_var, style="Status.TLabel"
        ).pack(anchor=tk.W)
        ttk.Label(
            stats, textvariable=self._potions_var, style="Status.TLabel"
        ).pack(anchor=tk.W)
        ttk.Label(
            stats, textvariable=self._deaths_var, style="Status.TLabel"
        ).pack(anchor=tk.W)
        ttk.Label(
            stats, textvariable=self._session_var, style="Status.TLabel"
        ).pack(anchor=tk.W)

    def _build_controls_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.Frame(parent, style="Panel.TFrame")
        frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))

        pad = {"padx": 10, "pady": 3}

        ttk.Label(
            frame, text="Controles", style="Title.TLabel"
        ).pack(**pad)

        self._status_var = tk.StringVar(value="Parado")
        self._status_label = ttk.Label(
            frame, textvariable=self._status_var, style="Value.TLabel"
        )
        self._status_label.pack(**pad)

        self._start_btn = ttk.Button(
            frame,
            text="Iniciar Bot",
            command=self._on_start,
            style="Start.TButton",
            width=18,
        )
        self._start_btn.pack(**pad)

        self._pause_btn = ttk.Button(
            frame,
            text="Pausar",
            command=self._on_pause,
            style="Start.TButton",
            width=18,
            state=tk.DISABLED,
        )
        self._pause_btn.pack(**pad)

        self._stop_btn = ttk.Button(
            frame,
            text="Parar Bot",
            command=self._on_stop,
            style="Stop.TButton",
            width=18,
            state=tk.DISABLED,
        )
        self._stop_btn.pack(**pad)

        ttk.Separator(frame, orient=tk.HORIZONTAL).pack(
            fill=tk.X, **pad
        )

        self._calibrate_btn = ttk.Button(
            frame,
            text="Calibrar",
            command=self._on_calibrate,
            style="Start.TButton",
            width=18,
        )
        self._calibrate_btn.pack(**pad)

        ttk.Separator(frame, orient=tk.HORIZONTAL).pack(
            fill=tk.X, **pad
        )

        self._config_var = tk.StringVar(value="config/default.yaml")
        ttk.Label(
            frame, text="Config:", style="Status.TLabel"
        ).pack(anchor=tk.W, padx=10)
        ttk.Entry(
            frame,
            textvariable=self._config_var,
            width=20,
            font=("Consolas", 9),
        ).pack(padx=10, pady=2)

    def _build_config_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.Frame(parent, style="Panel.TFrame")
        frame.pack(fill=tk.X)

        ttk.Label(
            frame, text="Teclas", style="Title.TLabel"
        ).pack(padx=10, pady=(5, 2), anchor=tk.W)

        keys_frame = ttk.Frame(frame, style="Panel.TFrame")
        keys_frame.pack(fill=tk.X, padx=10, pady=2)

        self._key_vars: dict[str, tk.StringVar] = {}

        key_defs = [
            ("HP Potion", "q"),
            ("MP Potion", "w"),
            ("Ataque", "space"),
            ("Alvo", "tab"),
            ("Loot", "z"),
            ("Fuga", "escape"),
            ("Ressuscitar", "enter"),
        ]

        for i, (label, default) in enumerate(key_defs):
            col = i % 4
            row = i // 4
            var = tk.StringVar(value=default)
            self._key_vars[label] = var

            cell = ttk.Frame(keys_frame, style="Panel.TFrame")
            cell.grid(row=row, column=col, padx=5, pady=2, sticky=tk.W)

            ttk.Label(
                cell, text=f"{label}:", style="Status.TLabel"
            ).pack(side=tk.LEFT)
            ttk.Entry(
                cell,
                textvariable=var,
                width=7,
                font=("Consolas", 9),
            ).pack(side=tk.LEFT, padx=(3, 0))

    def _build_log_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.Frame(parent, style="Dark.TFrame")
        frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        ttk.Label(
            frame, text="Log", style="Title.TLabel"
        ).pack(anchor=tk.W)

        self._log_text = scrolledtext.ScrolledText(
            frame,
            height=10,
            bg="#0a0a1a",
            fg="#00ff88",
            font=("Consolas", 9),
            insertbackground="#00ff88",
            selectbackground="#0f3460",
            wrap=tk.WORD,
            state=tk.DISABLED,
        )
        self._log_text.pack(fill=tk.BOTH, expand=True)

    def _setup_log_handler(self) -> None:
        handler = QueueHandler(self._log_queue)
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%H:%M:%S")
        )
        root_logger = logging.getLogger("wyd_bot")
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.INFO)

    def _schedule_updates(self) -> None:
        self._update_log()
        self._update_status()
        self.root.after(self._update_interval, self._schedule_updates)

    def _update_log(self) -> None:
        while True:
            try:
                msg = self._log_queue.get_nowait()
            except queue.Empty:
                break
            self._log_text.configure(state=tk.NORMAL)
            self._log_text.insert(tk.END, msg + "\n")
            self._log_text.see(tk.END)
            self._log_text.configure(state=tk.DISABLED)

    def _update_status(self) -> None:
        if not self._bot or not self._running:
            return

        state = self._bot.state

        hp = state.player.hp_percent
        mp = state.player.mp_percent
        self._hp_bar["value"] = int(hp * 100)
        self._hp_label.configure(text=f"{hp:.0%}")
        self._mp_bar["value"] = int(mp * 100)
        self._mp_label.configure(text=f"{mp:.0%}")

        self._mode_var.set(f"Modo: {state.mode.name}")

        kph = state.stats.kills_per_hour()
        self._kills_var.set(
            f"Kills: {state.stats.kills_count} ({kph:.0f}/h)"
        )
        lph = state.stats.loot_per_hour()
        self._loot_var.set(
            f"Loot: {state.stats.items_looted} ({lph:.0f}/h)"
        )
        self._potions_var.set(
            f"Poções: {state.stats.potions_used} "
            f"(HP:{state.stats.hp_potions_used} MP:{state.stats.mp_potions_used})"
        )
        self._deaths_var.set(f"Mortes: {state.stats.deaths}")

        mins = state.session_duration / 60
        self._session_var.set(f"Sessão: {mins:.1f} min")

        self._paused = self._bot._paused
        if self._paused:
            self._pause_btn.configure(text="Continuar")
            self._status_var.set("Pausado")
        else:
            self._pause_btn.configure(text="Pausar")
            self._status_var.set("Rodando")

    def _on_start(self) -> None:
        from wyd_bot.main import WYDBot

        config_path = self._config_var.get().strip()

        try:
            from pathlib import Path

            path = config_path if Path(config_path).exists() else None
            self._bot = WYDBot(path)
        except Exception:
            logger.exception("Erro ao criar bot")
            return

        self._apply_key_config()
        self._sync_strategy_keys()

        self._running = True
        self._paused = False
        self._start_btn.configure(state=tk.DISABLED)
        self._pause_btn.configure(state=tk.NORMAL)
        self._stop_btn.configure(state=tk.NORMAL)
        self._status_var.set("Rodando")

        self._bot_generation += 1
        gen = self._bot_generation
        self._bot_thread = threading.Thread(
            target=self._run_bot, args=(gen,), daemon=True
        )
        self._bot_thread.start()
        logger.info("Bot iniciado via GUI")

    def _apply_key_config(self) -> None:
        """Aplica as teclas da GUI in-memory no config do bot."""
        if not self._bot:
            return

        cfg = self._bot.config.bot

        key_map: dict[str, tuple[object, str]] = {
            "HP Potion": (cfg.combat, "hp_potion_key"),
            "MP Potion": (cfg.combat, "mp_potion_key"),
            "Ataque": (cfg.combat, "attack_key"),
            "Alvo": (cfg.combat, "target_key"),
            "Loot": (cfg.farm, "loot_key"),
            "Fuga": (cfg.combat, "flee_key"),
            "Ressuscitar": (cfg.resurrect, "resurrect_key"),
        }

        for label, (obj, attr) in key_map.items():
            if label in self._key_vars:
                val = self._key_vars[label].get().strip()
                if val:
                    setattr(obj, attr, val)

    def _sync_strategy_keys(self) -> None:
        """Atualiza teclas em strategies que armazenam cópia própria."""
        if not self._bot:
            return
        from wyd_bot.decision.strategy import ResurrectStrategy

        for s in self._bot.rule_engine._strategies:
            if isinstance(s, ResurrectStrategy):
                val = self._key_vars.get("Ressuscitar")
                if val:
                    s.resurrect_key = val.get().strip() or s.resurrect_key

    def _run_bot(self, generation: int) -> None:
        try:
            if self._bot:
                self._bot.start()
        except Exception:
            logger.exception("Erro no bot")
        finally:
            if self._bot_generation == generation:
                self._running = False
                try:
                    self.root.after(0, self._on_bot_stopped)
                except Exception:
                    pass

    def _on_bot_stopped(self) -> None:
        self._start_btn.configure(state=tk.NORMAL)
        self._pause_btn.configure(state=tk.DISABLED)
        self._stop_btn.configure(state=tk.DISABLED)
        self._status_var.set("Parado")

    def _on_pause(self) -> None:
        if self._bot:
            self._bot._paused = not self._bot._paused
            self._paused = self._bot._paused
            if self._paused:
                self._pause_btn.configure(text="Continuar")
                self._status_var.set("Pausado")
                logger.info("Bot pausado via GUI")
            else:
                self._pause_btn.configure(text="Pausar")
                self._status_var.set("Rodando")
                logger.info("Bot continuado via GUI")

    def _on_calibrate(self) -> None:
        from wyd_bot.calibration import CalibrationWindow

        config_path = self._config_var.get().strip()
        CalibrationWindow(self.root, config_path)

    def _on_stop(self) -> None:
        if self._bot:
            self._bot._running = False
            self._bot._stop_event.set()
        self._paused = False
        self._pause_btn.configure(text="Pausar")
        self._status_var.set("Parando...")
        logger.info("Bot parado via GUI")

    def run(self) -> None:
        """Inicia a interface gráfica."""
        logger.info("Interface gráfica iniciada")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()

    def _on_close(self) -> None:
        if self._bot and self._running:
            self._bot._running = False
            self._bot._stop_event.set()
        self.root.destroy()


def run_gui() -> None:
    """Entry point para a GUI."""
    gui = BotGUI()
    gui.run()
