"""Testes para o módulo de detecção visual."""

import numpy as np

from wyd_bot.vision.detector import Detection, GameDetector


def test_detection_center():
    d = Detection("test", 100, 200, 50, 30, 0.9)
    assert d.center == (125, 215)


def test_detection_area():
    d = Detection("test", 0, 0, 100, 50, 0.5)
    assert d.area == 5000


def test_detector_init():
    detector = GameDetector(threshold=0.8)
    assert detector.threshold == 0.8


def test_detect_hp_percentage_full():
    detector = GameDetector()
    # Criar barra vermelha (HP cheio)
    frame = np.zeros((100, 200, 3), dtype=np.uint8)
    # Vermelho em BGR
    frame[10:22, 10:160] = [0, 0, 200]
    pct = detector.detect_hp_percentage(frame, (10, 10, 150, 12))
    assert pct > 0.0


def test_detect_hp_percentage_empty():
    detector = GameDetector()
    # Frame preto (sem HP)
    frame = np.zeros((100, 200, 3), dtype=np.uint8)
    pct = detector.detect_hp_percentage(frame, (10, 10, 150, 12))
    assert pct == 0.0


def test_detect_hp_percentage_empty_roi():
    detector = GameDetector()
    frame = np.zeros((100, 200, 3), dtype=np.uint8)
    pct = detector.detect_hp_percentage(frame, (10, 10, 0, 0))
    assert pct == 0.0


def test_find_by_color():
    detector = GameDetector()
    # Criar frame com região colorida
    frame = np.zeros((200, 200, 3), dtype=np.uint8)
    # Criar quadrado verde em BGR -> HSV verde fica aprox (60, 255, 255)
    frame[50:80, 50:80] = [0, 255, 0]

    detections = detector.find_by_color(
        frame,
        color_lower=(35, 100, 100),
        color_upper=(85, 255, 255),
        min_area=50,
        label="green_obj",
    )
    assert len(detections) > 0
    assert detections[0].label == "green_obj"


def test_find_monsters_no_templates():
    detector = GameDetector()
    frame = np.zeros((200, 200, 3), dtype=np.uint8)
    monsters = detector.find_monsters(frame)
    assert monsters == []


def test_non_max_suppression():
    detector = GameDetector()
    detections = [
        Detection("a", 100, 100, 50, 50, 0.9),
        Detection("b", 105, 105, 50, 50, 0.7),  # Sobreposto com a
        Detection("c", 300, 300, 50, 50, 0.8),   # Separado
    ]
    result = detector._non_max_suppression(detections, overlap_thresh=0.3)
    assert len(result) == 2


def test_compute_iou_no_overlap():
    a = Detection("a", 0, 0, 50, 50, 0.5)
    b = Detection("b", 100, 100, 50, 50, 0.5)
    iou = GameDetector._compute_iou(a, b)
    assert iou == 0.0


def test_compute_iou_full_overlap():
    a = Detection("a", 0, 0, 50, 50, 0.5)
    b = Detection("b", 0, 0, 50, 50, 0.5)
    iou = GameDetector._compute_iou(a, b)
    assert iou == 1.0
