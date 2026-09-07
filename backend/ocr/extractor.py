from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
import pytesseract

from backend.cv.shape_detector import ClassBox

_TESS_CONFIG = "--oem 3 --psm 6 --dpi 300"
_UPSCALE = 4
_PAD = 12  # white border added around each crop before OCR
# Shrink each compartment strip inward before cropping so a sliver of the box
# border/divider line — a couple of px of detection noise, e.g. from adaptive
# thresholding rounding differently per compartment — never bleeds into the
# crop and skews its per-region Otsu threshold.
_BORDER_INSET = 3


@dataclass
class ClassTextRegions:
    class_name: str
    attribute_lines: list[str]
    method_lines: list[str]


def extract_class_text(gray: np.ndarray, box: ClassBox) -> ClassTextRegions:
    """Split a class box into its three compartments and OCR each one."""
    dividers = sorted(box.dividers_y)
    y0, y1 = box.y, box.y + box.h

    if len(dividers) >= 2:
        name_strip = (box.x, y0, box.w, dividers[0] - y0)
        attr_strip = (box.x, dividers[0], box.w, dividers[1] - dividers[0])
        meth_strip = (box.x, dividers[1], box.w, y1 - dividers[1])
    elif len(dividers) == 1:
        name_strip = (box.x, y0, box.w, dividers[0] - y0)
        attr_strip = (box.x, dividers[0], box.w, y1 - dividers[0])
        meth_strip = None
    else:
        name_strip = (box.x, y0, box.w, y1 - y0)
        attr_strip = None
        meth_strip = None

    class_name = _ocr_region(gray, _inset(name_strip)).strip()
    attr_text = _ocr_region(gray, _inset(attr_strip)) if attr_strip else ""
    meth_text = _ocr_region(gray, _inset(meth_strip)) if meth_strip else ""

    return ClassTextRegions(
        class_name=class_name,
        attribute_lines=_split_lines(attr_text),
        method_lines=_split_lines(meth_text),
    )


def _inset(region: tuple[int, int, int, int] | None) -> tuple[int, int, int, int] | None:
    if region is None:
        return None
    x, y, w, h = region
    return (
        x + _BORDER_INSET,
        y + _BORDER_INSET,
        max(0, w - 2 * _BORDER_INSET),
        max(0, h - 2 * _BORDER_INSET),
    )


def _ocr_region(gray: np.ndarray, region: tuple[int, int, int, int] | None) -> str:
    if region is None:
        return ""
    x, y, w, h = region
    if h < 4 or w < 4:
        return ""

    crop = gray[y : y + h, x : x + w]

    # Add white padding so Tesseract doesn't clip edge characters
    padded = cv2.copyMakeBorder(crop, _PAD, _PAD, _PAD, _PAD, cv2.BORDER_CONSTANT, value=255)

    # Upscale with cubic interpolation for sharper edges at small font sizes
    ph, pw = padded.shape[:2]
    scaled = cv2.resize(padded, (pw * _UPSCALE, ph * _UPSCALE), interpolation=cv2.INTER_CUBIC)

    # Otsu thresholding on the upscaled crop gives Tesseract clean binary text
    _, binary = cv2.threshold(scaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    return pytesseract.image_to_string(binary, config=_TESS_CONFIG)


def _split_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]
