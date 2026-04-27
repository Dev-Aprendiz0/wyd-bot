"""Módulo de detecção visual de elementos do jogo WYD."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import cv2
import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray

from wyd_bot.utils.logger import setup_logger

logger = setup_logger("wyd_bot.vision.detector")


@dataclass
class Detection:
    """Representa um objeto detectado na tela."""

    label: str
    x: int
    y: int
    width: int
    height: int
    confidence: float

    @property
    def center(self) -> tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)

    @property
    def area(self) -> int:
        return self.width * self.height


class GameDetector:
    """Detector de elementos do jogo WYD usando OpenCV."""

    def __init__(
        self,
        monster_template_dir: str | None = None,
        item_template_dir: str | None = None,
        threshold: float = 0.7,
    ) -> None:
        self.threshold = threshold
        self._monster_templates: dict[str, NDArray[np.uint8]] = {}
        self._item_templates: dict[str, NDArray[np.uint8]] = {}

        if monster_template_dir:
            self._load_templates(monster_template_dir, self._monster_templates)
        if item_template_dir:
            self._load_templates(item_template_dir, self._item_templates)

    def _load_templates(
        self, directory: str, storage: dict[str, NDArray[np.uint8]]
    ) -> None:
        """Carrega templates de imagens de um diretório."""
        path = Path(directory)
        if not path.exists():
            logger.warning("Diretório de templates não encontrado: %s", directory)
            return

        for img_file in path.glob("*.png"):
            template = cv2.imread(str(img_file))
            if template is not None:
                storage[img_file.stem] = template
                logger.info("Template carregado: %s", img_file.stem)

    def detect_hp_percentage(
        self,
        frame: NDArray[np.uint8],
        region: tuple[int, int, int, int],
        color_lower: tuple[int, int, int] = (0, 100, 100),
        color_upper: tuple[int, int, int] = (10, 255, 255),
    ) -> float:
        """Detecta a porcentagem de HP baseado na cor da barra.

        Args:
            frame: Frame da tela (BGR).
            region: Região da barra (x, y, w, h).
            color_lower: Limite inferior HSV da cor da barra.
            color_upper: Limite superior HSV da cor da barra.

        Returns:
            Porcentagem de HP (0.0 a 1.0).
        """
        x, y, w, h = region
        bar_roi = frame[y : y + h, x : x + w]

        if bar_roi.size == 0:
            return 0.0

        hsv = cv2.cvtColor(bar_roi, cv2.COLOR_BGR2HSV)
        lower = np.array(color_lower, dtype=np.uint8)
        upper = np.array(color_upper, dtype=np.uint8)
        mask = cv2.inRange(hsv, lower, upper)

        total_pixels = w * h
        if total_pixels == 0:
            return 0.0

        filled_pixels = int(cv2.countNonZero(mask))
        return filled_pixels / total_pixels

    def detect_mp_percentage(
        self,
        frame: NDArray[np.uint8],
        region: tuple[int, int, int, int],
        color_lower: tuple[int, int, int] = (100, 100, 100),
        color_upper: tuple[int, int, int] = (130, 255, 255),
    ) -> float:
        """Detecta a porcentagem de MP baseado na cor da barra."""
        return self.detect_hp_percentage(frame, region, color_lower, color_upper)

    def find_by_template(
        self,
        frame: NDArray[np.uint8],
        templates: dict[str, NDArray[np.uint8]] | None = None,
        label_prefix: str = "",
    ) -> list[Detection]:
        """Encontra objetos na tela usando template matching.

        Args:
            frame: Frame da tela (BGR).
            templates: Dicionário de templates. Se None, usa monster_templates.
            label_prefix: Prefixo para o label das detecções.

        Returns:
            Lista de detecções encontradas.
        """
        if templates is None:
            templates = self._monster_templates

        detections: list[Detection] = []
        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        for name, template in templates.items():
            template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
            h, w = template_gray.shape[:2]

            result = cv2.matchTemplate(frame_gray, template_gray, cv2.TM_CCOEFF_NORMED)
            locations = np.where(result >= self.threshold)

            for pt_y, pt_x in zip(*locations):
                confidence = float(result[pt_y, pt_x])
                label = f"{label_prefix}{name}" if label_prefix else name
                detections.append(
                    Detection(
                        label=label,
                        x=int(pt_x),
                        y=int(pt_y),
                        width=w,
                        height=h,
                        confidence=confidence,
                    )
                )

        return self._non_max_suppression(detections)

    def find_monsters(self, frame: NDArray[np.uint8]) -> list[Detection]:
        """Encontra monstros na tela."""
        return self.find_by_template(frame, self._monster_templates, "monster_")

    def find_items(self, frame: NDArray[np.uint8]) -> list[Detection]:
        """Encontra itens no chão."""
        return self.find_by_template(frame, self._item_templates, "item_")

    def find_by_color(
        self,
        frame: NDArray[np.uint8],
        color_lower: tuple[int, int, int],
        color_upper: tuple[int, int, int],
        min_area: int = 100,
        label: str = "object",
    ) -> list[Detection]:
        """Encontra objetos por faixa de cor HSV.

        Args:
            frame: Frame da tela (BGR).
            color_lower: Limite inferior HSV.
            color_upper: Limite superior HSV.
            min_area: Área mínima do contorno.
            label: Label para as detecções.

        Returns:
            Lista de detecções.
        """
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        lower = np.array(color_lower, dtype=np.uint8)
        upper = np.array(color_upper, dtype=np.uint8)
        mask = cv2.inRange(hsv, lower, upper)

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        detections: list[Detection] = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < min_area:
                continue
            bx, by, bw, bh = cv2.boundingRect(contour)
            detections.append(
                Detection(
                    label=label,
                    x=bx,
                    y=by,
                    width=bw,
                    height=bh,
                    confidence=min(area / 1000.0, 1.0),
                )
            )

        return detections

    def find_hp_bars_above_entities(
        self,
        frame: NDArray[np.uint8],
        bar_color_lower: tuple[int, int, int] = (0, 100, 100),
        bar_color_upper: tuple[int, int, int] = (10, 255, 255),
        min_width: int = 20,
        max_height: int = 10,
    ) -> list[Detection]:
        """Encontra barras de HP acima de entidades (monstros/NPCs).

        Usa detecção de cor para encontrar barras vermelhas/verdes finas.
        """
        detections = self.find_by_color(
            frame, bar_color_lower, bar_color_upper, min_area=50, label="hp_bar"
        )
        return [
            d
            for d in detections
            if d.width >= min_width and d.height <= max_height and d.width > d.height * 2
        ]

    def _non_max_suppression(
        self, detections: list[Detection], overlap_thresh: float = 0.3
    ) -> list[Detection]:
        """Remove detecções sobrepostas mantendo as de maior confiança."""
        if not detections:
            return []

        sorted_dets = sorted(detections, key=lambda d: d.confidence, reverse=True)
        kept: list[Detection] = []

        for det in sorted_dets:
            overlap = False
            for kept_det in kept:
                iou = self._compute_iou(det, kept_det)
                if iou > overlap_thresh:
                    overlap = True
                    break
            if not overlap:
                kept.append(det)

        return kept

    @staticmethod
    def _compute_iou(a: Detection, b: Detection) -> float:
        """Calcula Intersection over Union entre duas detecções."""
        x1 = max(a.x, b.x)
        y1 = max(a.y, b.y)
        x2 = min(a.x + a.width, b.x + b.width)
        y2 = min(a.y + a.height, b.y + b.height)

        intersection = max(0, x2 - x1) * max(0, y2 - y1)
        union = a.area + b.area - intersection

        if union == 0:
            return 0.0
        return intersection / union
