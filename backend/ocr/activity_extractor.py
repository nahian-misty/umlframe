from __future__ import annotations

import cv2
import numpy as np
import numpy.typing as npt
import pytesseract

from backend.cv.activity_shape_detector import ActivityShape

# Grayscale / binary single-channel image buffers.
GrayImage = npt.NDArray[np.uint8]

# Same crop/pad/upscale/Otsu/pytesseract recipe as backend/ocr/extractor.py --
# duplicated rather than shared, mirroring how the two image *_service modules
# each carry their own small geometry helpers.
_TESS_CONFIG = "--oem 3 --psm 6 --dpi 300"
_UPSCALE = 4
_PAD = 12  # white border added around each crop before OCR
_BORDER_INSET = 4  # shrink the crop inward so the shape outline never bleeds in

# Only these shape kinds carry a text label worth reading.
_LABELLED_KINDS = frozenset({"action", "decision"})

# Half-size of the square OCR window centred on an edge's midpoint.
_GUARD_BOX_HALF = 26


def extract_activity_labels(gray: GrayImage, shapes: list[ActivityShape]) -> list[str]:
    """One raw OCR string per shape, indexed parallel to `shapes`. Start/end
    and fork/join bars carry no text, so they come back as ""."""
    labels: list[str] = []
    for shape in shapes:
        if shape.kind not in _LABELLED_KINDS:
            labels.append("")
            continue
        region = _inset((shape.x, shape.y, shape.w, shape.h))
        labels.append(_ocr_region(gray, region).strip())
    return labels


def extract_guard_label(gray: GrayImage, x1: int, y1: int, x2: int, y2: int) -> str:
    """Raw OCR of a small window around an edge's midpoint, for guard text
    ("yes"/"no") written beside a decision's outgoing branch."""
    mid_x, mid_y = (x1 + x2) // 2, (y1 + y2) // 2
    region = (
        mid_x - _GUARD_BOX_HALF,
        mid_y - _GUARD_BOX_HALF,
        _GUARD_BOX_HALF * 2,
        _GUARD_BOX_HALF * 2,
    )
    return _ocr_region(gray, region).strip()


def _inset(region: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    x, y, w, h = region
    return (
        x + _BORDER_INSET,
        y + _BORDER_INSET,
        max(0, w - 2 * _BORDER_INSET),
        max(0, h - 2 * _BORDER_INSET),
    )


def _ocr_region(gray: GrayImage, region: tuple[int, int, int, int]) -> str:
    x, y, w, h = region
    x = max(0, x)
    y = max(0, y)
    w = min(w, gray.shape[1] - x)
    h = min(h, gray.shape[0] - y)
    if h < 4 or w < 4:
        return ""

    crop = gray[y : y + h, x : x + w]
    padded = cv2.copyMakeBorder(crop, _PAD, _PAD, _PAD, _PAD, cv2.BORDER_CONSTANT, value=255)

    ph, pw = padded.shape[:2]
    scaled = cv2.resize(padded, (pw * _UPSCALE, ph * _UPSCALE), interpolation=cv2.INTER_CUBIC)

    _, binary = cv2.threshold(scaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    return str(pytesseract.image_to_string(binary, config=_TESS_CONFIG))
