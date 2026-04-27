"""Janela de calibração visual integrada à GUI."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import cv2
import numpy as np
import yaml
from PIL import Image, ImageTk

from wyd_bot.utils.logger import setup_logger
from wyd_bot.vision.screen_capture import ScreenCapture

logger = setup_logger("wyd_bot.calibration")

BG_DARK = "#1a1a2e"
BG_PANEL = "#16213e"
FG_TEXT = "#e0e0e0"
FG_ACCENT = "#00d4ff"
FG_HP = "#ff4444"
FG_MP = "#4488ff"
FG_GREEN = "#44ff44"


class CalibrationWindow:
    """Janela de calibração com seleção visual de regiões."""

    REGION_COLORS: dict[str, str] = {
        "hp": FG_HP,
        "mp": FG_MP,
        "minimap": FG_GREEN,
    }

    def __init__(self, parent: tk.Tk, config_path: str) -> None:
        self._parent = parent
        self._config_path = config_path
        self._screenshot: np.ndarray | None = None
        self._photo: ImageTk.PhotoImage | None = None
        self._scale: float = 1.0
        self._selecting = False
        self._sel_start: tuple[int, int] = (0, 0)
        self._sel_rect: int | None = None
        self._current_mode: str | None = None
        self._regions: dict[str, tuple[int, int, int, int]] = {}
        self._monster_templates: list[np.ndarray] = []
        self._rect_ids: dict[str, int] = {}
        self._label_ids: dict[str, int] = {}

        self._win = tk.Toplevel(parent)
        self._win.title("Calibração - WYD Bot")
        self._win.configure(bg=BG_DARK)
        self._win.geometry("1100x750")
        self._win.minsize(900, 600)
        self._win.grab_set()

        self._build_ui()

    def _build_ui(self) -> None:
        toolbar = tk.Frame(self._win, bg=BG_PANEL)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        tk.Button(
            toolbar,
            text="Capturar Tela",
            command=self._capture_screen,
            bg="#0f3460",
            fg=FG_TEXT,
            font=("Segoe UI", 10, "bold"),
            padx=10,
        ).pack(side=tk.LEFT, padx=3)

        tk.Button(
            toolbar,
            text="Carregar Imagem",
            command=self._load_image,
            bg="#0f3460",
            fg=FG_TEXT,
            font=("Segoe UI", 10),
            padx=10,
        ).pack(side=tk.LEFT, padx=3)

        sep = tk.Frame(toolbar, bg=FG_ACCENT, width=2, height=30)
        sep.pack(side=tk.LEFT, padx=8, pady=2)

        self._mode_buttons: dict[str, tk.Button] = {}
        modes = [
            ("Barra HP", "hp", FG_HP),
            ("Barra MP", "mp", FG_MP),
            ("Minimap", "minimap", FG_GREEN),
            ("Monstro", "monster", FG_ACCENT),
        ]
        for text, mode, color in modes:
            btn = tk.Button(
                toolbar,
                text=text,
                command=lambda m=mode: self._set_mode(m),
                bg=BG_DARK,
                fg=color,
                font=("Segoe UI", 9, "bold"),
                relief=tk.RAISED,
                padx=8,
            )
            btn.pack(side=tk.LEFT, padx=2)
            self._mode_buttons[mode] = btn

        sep2 = tk.Frame(toolbar, bg=FG_ACCENT, width=2, height=30)
        sep2.pack(side=tk.LEFT, padx=8, pady=2)

        tk.Button(
            toolbar,
            text="Salvar Config",
            command=self._save_config,
            bg="#1a6b3c",
            fg=FG_TEXT,
            font=("Segoe UI", 10, "bold"),
            padx=10,
        ).pack(side=tk.LEFT, padx=3)

        tk.Button(
            toolbar,
            text="Fechar",
            command=self._win.destroy,
            bg="#6b1a1a",
            fg=FG_TEXT,
            font=("Segoe UI", 10),
            padx=10,
        ).pack(side=tk.RIGHT, padx=3)

        info_frame = tk.Frame(self._win, bg=BG_PANEL)
        info_frame.pack(fill=tk.X, padx=5, pady=(0, 5))

        self._info_var = tk.StringVar(
            value="Clique em 'Capturar Tela' para iniciar a calibração"
        )
        tk.Label(
            info_frame,
            textvariable=self._info_var,
            bg=BG_PANEL,
            fg=FG_ACCENT,
            font=("Segoe UI", 10),
        ).pack(padx=10, pady=4, anchor=tk.W)

        self._status_var = tk.StringVar(value="")
        tk.Label(
            info_frame,
            textvariable=self._status_var,
            bg=BG_PANEL,
            fg=FG_TEXT,
            font=("Consolas", 9),
        ).pack(padx=10, pady=(0, 4), anchor=tk.W)

        canvas_frame = tk.Frame(self._win, bg=BG_DARK)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self._canvas = tk.Canvas(
            canvas_frame, bg="#0a0a1a", highlightthickness=0
        )
        self._canvas.pack(fill=tk.BOTH, expand=True)

        self._canvas.bind("<ButtonPress-1>", self._on_press)
        self._canvas.bind("<B1-Motion>", self._on_drag)
        self._canvas.bind("<ButtonRelease-1>", self._on_release)

    def _capture_screen(self) -> None:
        self._win.withdraw()
        self._parent.update_idletasks()

        import time
        time.sleep(0.5)

        try:
            with ScreenCapture() as capture:
                frame = capture.capture_frame()
            self._screenshot = frame
            self._display_image(frame)
            self._info_var.set(
                "Screenshot capturada! Selecione um modo e arraste para marcar regiões."
            )
            logger.info("Screenshot capturada para calibração")
        except Exception:
            logger.exception("Erro ao capturar tela")
            messagebox.showerror(
                "Erro", "Não foi possível capturar a tela.", parent=self._win
            )
        finally:
            self._win.deiconify()

    def _load_image(self) -> None:
        path = filedialog.askopenfilename(
            title="Selecionar imagem",
            filetypes=[
                ("Imagens", "*.png *.jpg *.jpeg *.bmp"),
                ("Todos", "*.*"),
            ],
            parent=self._win,
        )
        if not path:
            return
        frame = cv2.imread(path)
        if frame is None:
            messagebox.showerror(
                "Erro", "Não foi possível carregar a imagem.", parent=self._win
            )
            return
        self._screenshot = frame
        self._display_image(frame)
        self._info_var.set(
            "Imagem carregada! Selecione um modo e arraste para marcar regiões."
        )

    def _display_image(self, frame: np.ndarray) -> None:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)

        cw = self._canvas.winfo_width() or 1000
        ch = self._canvas.winfo_height() or 600
        iw, ih = img.size

        self._scale = min(cw / iw, ch / ih, 1.0)
        new_w = int(iw * self._scale)
        new_h = int(ih * self._scale)
        img = img.resize((new_w, new_h), Image.LANCZOS)

        self._photo = ImageTk.PhotoImage(img)
        self._canvas.delete("all")
        self._rect_ids.clear()
        self._label_ids.clear()
        self._canvas.create_image(0, 0, anchor=tk.NW, image=self._photo)

        for mode, region in self._regions.items():
            self._draw_region_rect(mode, region)

        self._update_status()

    def _set_mode(self, mode: str) -> None:
        self._current_mode = mode
        for m, btn in self._mode_buttons.items():
            if m == mode:
                btn.configure(relief=tk.SUNKEN, bg="#0f3460")
            else:
                btn.configure(relief=tk.RAISED, bg=BG_DARK)

        if mode == "monster":
            self._info_var.set(
                "Modo MONSTRO: arraste para selecionar um monstro na tela e salvar como template."
            )
        else:
            label = {"hp": "HP", "mp": "MP", "minimap": "Minimap"}[mode]
            self._info_var.set(
                f"Modo {label}: arraste para selecionar a região da barra de {label}."
            )

    def _on_press(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        if self._screenshot is None or self._current_mode is None:
            return
        self._selecting = True
        self._sel_start = (event.x, event.y)
        if self._sel_rect is not None:
            self._canvas.delete(self._sel_rect)
        color = self.REGION_COLORS.get(self._current_mode, FG_ACCENT)
        self._sel_rect = self._canvas.create_rectangle(
            event.x, event.y, event.x, event.y,
            outline=color, width=2, dash=(4, 4),
        )

    def _on_drag(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        if not self._selecting or self._sel_rect is None:
            return
        self._canvas.coords(
            self._sel_rect,
            self._sel_start[0], self._sel_start[1], event.x, event.y,
        )

    def _on_release(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        if not self._selecting or self._screenshot is None:
            return
        self._selecting = False

        x1 = min(self._sel_start[0], event.x)
        y1 = min(self._sel_start[1], event.y)
        x2 = max(self._sel_start[0], event.x)
        y2 = max(self._sel_start[1], event.y)

        if self._sel_rect is not None:
            self._canvas.delete(self._sel_rect)
            self._sel_rect = None

        if x2 - x1 < 5 or y2 - y1 < 5:
            return

        real_x1 = int(x1 / self._scale)
        real_y1 = int(y1 / self._scale)
        real_x2 = int(x2 / self._scale)
        real_y2 = int(y2 / self._scale)
        real_w = real_x2 - real_x1
        real_h = real_y2 - real_y1

        mode = self._current_mode
        if mode == "monster":
            self._save_monster_template(real_x1, real_y1, real_w, real_h)
        elif mode is not None:
            self._regions[mode] = (real_x1, real_y1, real_w, real_h)
            self._draw_region_rect(mode, (real_x1, real_y1, real_w, real_h))
            label = {"hp": "HP", "mp": "MP", "minimap": "Minimap"}[mode]
            self._info_var.set(
                f"Região {label} definida: x={real_x1} y={real_y1} "
                f"w={real_w} h={real_h}"
            )

        self._update_status()

    def _draw_region_rect(
        self, mode: str, region: tuple[int, int, int, int]
    ) -> None:
        if mode in self._rect_ids:
            self._canvas.delete(self._rect_ids[mode])
        if mode in self._label_ids:
            self._canvas.delete(self._label_ids[mode])

        x, y, w, h = region
        sx = int(x * self._scale)
        sy = int(y * self._scale)
        sw = int((x + w) * self._scale)
        sh = int((y + h) * self._scale)

        color = self.REGION_COLORS.get(mode, FG_ACCENT)
        self._rect_ids[mode] = self._canvas.create_rectangle(
            sx, sy, sw, sh, outline=color, width=2,
        )
        label = {"hp": "HP", "mp": "MP", "minimap": "Minimap"}.get(mode, mode)
        self._label_ids[mode] = self._canvas.create_text(
            sx + 4, sy + 2, text=label, anchor=tk.NW,
            fill=color, font=("Segoe UI", 9, "bold"),
        )

    def _save_monster_template(
        self, x: int, y: int, w: int, h: int
    ) -> None:
        if self._screenshot is None:
            return

        crop = self._screenshot[y:y + h, x:x + w]
        if crop.size == 0:
            return

        self._monster_templates.append(crop)

        template_dir = Path("templates/monsters")
        template_dir.mkdir(parents=True, exist_ok=True)

        idx = len(list(template_dir.glob("monster_*.png"))) + 1
        path = template_dir / f"monster_{idx:03d}.png"
        cv2.imwrite(str(path), crop)

        self._info_var.set(f"Template de monstro salvo: {path}")
        logger.info("Template de monstro salvo: %s (%dx%d)", path, w, h)

        color = FG_ACCENT
        sx = int(x * self._scale)
        sy = int(y * self._scale)
        sw = int((x + w) * self._scale)
        sh = int((y + h) * self._scale)
        self._canvas.create_rectangle(
            sx, sy, sw, sh, outline=color, width=2,
        )
        self._canvas.create_text(
            sx + 4, sy + 2, text=f"Monstro {idx}", anchor=tk.NW,
            fill=color, font=("Segoe UI", 9, "bold"),
        )

    def _update_status(self) -> None:
        parts: list[str] = []
        for mode, region in self._regions.items():
            label = {"hp": "HP", "mp": "MP", "minimap": "Minimap"}.get(
                mode, mode
            )
            x, y, w, h = region
            parts.append(f"{label}: ({x},{y},{w},{h})")
        n_monsters = len(self._monster_templates)
        if n_monsters:
            parts.append(f"Monstros: {n_monsters} template(s)")
        self._status_var.set("  |  ".join(parts) if parts else "")

    def _save_config(self) -> None:
        if not self._regions and not self._monster_templates:
            messagebox.showwarning(
                "Nada para salvar",
                "Marque pelo menos uma região antes de salvar.",
                parent=self._win,
            )
            return

        config_file = Path(self._config_path)

        if config_file.exists():
            with open(config_file, encoding="utf-8") as f:
                raw = f.read()
        else:
            config_file.parent.mkdir(parents=True, exist_ok=True)
            raw = ""

        data: dict = yaml.safe_load(raw) or {} if raw else {}

        if "hp" in self._regions:
            x, y, w, h = self._regions["hp"]
            hp_mp = data.setdefault("hp_mp", {})
            hp_mp["hp_region"] = {"x": x, "y": y, "width": w, "height": h}

        if "mp" in self._regions:
            x, y, w, h = self._regions["mp"]
            hp_mp = data.setdefault("hp_mp", {})
            hp_mp["mp_region"] = {"x": x, "y": y, "width": w, "height": h}

        if "minimap" in self._regions:
            x, y, w, h = self._regions["minimap"]
            detection = data.setdefault("detection", {})
            detection["minimap_region"] = {
                "x": x, "y": y, "width": w, "height": h,
            }

        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

        saved: list[str] = []
        if "hp" in self._regions:
            saved.append("HP")
        if "mp" in self._regions:
            saved.append("MP")
        if "minimap" in self._regions:
            saved.append("Minimap")
        if self._monster_templates:
            saved.append(f"{len(self._monster_templates)} monstro(s)")

        msg = f"Calibração salva em {config_file}: {', '.join(saved)}"
        self._info_var.set(msg)
        logger.info(msg)
        messagebox.showinfo("Salvo", msg, parent=self._win)
