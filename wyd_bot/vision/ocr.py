"""Módulo de leitura de texto na tela (OCR simples com OpenCV)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import cv2
import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray

from wyd_bot.utils.logger import setup_logger

logger = setup_logger("wyd_bot.vision.ocr")


class TextReader:
    """Leitor de texto simples usando processamento de imagem.

    Para OCR completo, considere usar pytesseract ou easyocr.
    Esta classe fornece detecção básica de regiões de texto.
    """

    def __init__(self, scale_factor: float = 2.0) -> None:
        """Inicializa o leitor de texto.

        Args:
            scale_factor: Fator de escala para melhorar a leitura.
        """
        self.scale_factor = scale_factor

    def preprocess_for_ocr(self, frame: NDArray[np.uint8]) -> NDArray[np.uint8]:
        """Pré-processa a imagem para melhor leitura de texto.

        Args:
            frame: Frame BGR.

        Returns:
            Imagem binária pré-processada.
        """
        h, w = frame.shape[:2]
        new_w, new_h = int(w * self.scale_factor), int(h * self.scale_factor)
        scaled = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_CUBIC)

        gray = cv2.cvtColor(scaled, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        return binary

    def find_text_regions(
        self,
        frame: NDArray[np.uint8],
        min_area: int = 50,
    ) -> list[tuple[int, int, int, int]]:
        """Encontra regiões que provavelmente contêm texto.

        Args:
            frame: Frame BGR.
            min_area: Área mínima de uma região de texto.

        Returns:
            Lista de regiões (x, y, w, h).
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        mser = cv2.MSER_create()
        regions, _ = mser.detectRegions(gray)

        hulls = [cv2.convexHull(p.reshape(-1, 1, 2)) for p in regions]

        text_regions: list[tuple[int, int, int, int]] = []
        for hull in hulls:
            bx, by, bw, bh = cv2.boundingRect(hull)
            area = bw * bh
            if area >= min_area and bh < bw * 3:
                text_regions.append((bx, by, bw, bh))

        return self._merge_overlapping(text_regions)

    def extract_number_from_bar(
        self,
        frame: NDArray[np.uint8],
        region: tuple[int, int, int, int],
    ) -> str | None:
        """Tenta extrair números de uma região (ex: "1234/5000").

        Usa contornos para detectar dígitos. Para melhor precisão, use pytesseract.

        Args:
            frame: Frame BGR.
            region: Região (x, y, w, h).

        Returns:
            Texto extraído ou None.
        """
        x, y, w, h = region
        roi = frame[y : y + h, x : x + w]
        if roi.size == 0:
            return None

        processed = self.preprocess_for_ocr(roi)
        contours, _ = cv2.findContours(processed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if len(contours) > 2:
            return f"~{len(contours)} chars detected"
        return None

    @staticmethod
    def _merge_overlapping(
        regions: list[tuple[int, int, int, int]],
        overlap_thresh: float = 0.5,
    ) -> list[tuple[int, int, int, int]]:
        """Merge de regiões sobrepostas."""
        if not regions:
            return []

        sorted_regions = sorted(regions, key=lambda r: r[0])
        merged: list[tuple[int, int, int, int]] = [sorted_regions[0]]

        for region in sorted_regions[1:]:
            last = merged[-1]
            lx1, ly1, lw, lh = last
            rx1, ry1, rw, rh = region

            lx2 = lx1 + lw
            ly2 = ly1 + lh
            rx2 = rx1 + rw
            ry2 = ry1 + rh

            overlap_x = max(0, min(lx2, rx2) - max(lx1, rx1))
            overlap_y = max(0, min(ly2, ry2) - max(ly1, ry1))
            overlap_area = overlap_x * overlap_y

            min_area = min(lw * lh, rw * rh)
            if min_area > 0 and overlap_area / min_area > overlap_thresh:
                nx = min(lx1, rx1)
                ny = min(ly1, ry1)
                nw = max(lx2, rx2) - nx
                nh = max(ly2, ry2) - ny
                merged[-1] = (nx, ny, nw, nh)
            else:
                merged.append(region)

        return merged
