from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
import pytesseract

from backend.cv.shape_detector import ClassBox

_TESS_CONFIG = "--oem 3 --psm 6 --dpi 300"
_UPSCALE = 3
_PAD = 12  # white border added around each crop before OCR
# Shrink each compartment strip inward before cropping so a sliver of the box
# border/divider line — a couple of px of detection noise, e.g. from adaptive
# thresholding rounding differently per compartment — never bleeds into the
# crop and skews its per-region Otsu threshold.
_BORDER_INSET = 3
# A multiplicity label is a short run of digits, dots and "*" on one line.
_LABEL_TESS_CONFIG = "--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789.*n"
_LABEL_UPSCALE = 6
_LABEL_MARGIN = 2
# Italic detection: how far upright text is sheared to probe for a lean, how much
# better the leaning probe must line up than the upright one, and the smallest line
# worth testing (px).
_ITALIC_PROBE_SLANT = 10.0
_ITALIC_MIN_RATIO = 0.98
_ITALIC_MIN_HEIGHT = 8
_INK_MAX_MEAN = 127
# A tilde's ink centre moves at least this many (upscaled) px along its length.
_TILDE_WOBBLE = 1.0


@dataclass
class ClassTextRegions:
    class_name: str
    attribute_lines: list[str]
    method_lines: list[str]
    # The class name itself is set in italics (UML's way of marking an abstract class).
    italic_name: bool = False


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
        italic_name=_is_italic(gray, _inset(name_strip)),
    )


def _is_italic(gray: np.ndarray, region: tuple[int, int, int, int] | None) -> bool:
    """Whether the last line of text in a compartment (the class name, below any
    stereotype) leans right. Upright text lines up best in vertical columns;
    italic text lines up best once sheared back by its slant."""
    line = _last_text_line(gray, region)
    if line is None:
        return False
    height, width = line.shape
    if height < _ITALIC_MIN_HEIGHT:
        return False
    upright = _column_sharpness(line, 0.0)
    leaning = _column_sharpness(line, _ITALIC_PROBE_SLANT)
    return upright > 0 and leaning / upright >= _ITALIC_MIN_RATIO


def _last_text_line(
    gray: np.ndarray, region: tuple[int, int, int, int] | None
) -> np.ndarray | None:
    if region is None:
        return None
    x, y, w, h = region
    crop = gray[y : y + h, x : x + w]
    if crop.size == 0:
        return None
    _, ink = cv2.threshold(crop, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    if ink.mean() > _INK_MAX_MEAN:
        ink = 255 - ink
    rows = np.nonzero(ink.any(axis=1))[0]
    if len(rows) == 0:
        return None
    # last run of consecutive inked rows
    breaks = np.nonzero(np.diff(rows) > 1)[0]
    start = rows[breaks[-1] + 1] if len(breaks) else rows[0]
    line = ink[start : rows[-1] + 1]
    cols = np.nonzero(line.any(axis=0))[0]
    return line[:, cols[0] : cols[-1] + 1] if len(cols) else None


def _column_sharpness(line: np.ndarray, slant_degrees: float) -> float:
    """Variance of the column ink totals after shearing each row sideways (lower rows
    further right), which is how far an italic stroke has to be pushed to stand
    upright in this image's orientation."""
    height, width = line.shape
    tangent = float(np.tan(np.radians(slant_degrees)))
    sheared = np.zeros((height, width + int(abs(tangent) * height) + 2), dtype=np.float32)
    for row in range(height):
        shift = int(round(row * tangent))
        sheared[row, shift : shift + width] = line[row]
    return float(np.var(sheared.sum(axis=0)))


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

    # Pad with the compartment's own background so Tesseract doesn't clip edge
    # characters and a tinted header does not meet a white frame.
    background = int(np.median(crop))
    padded = cv2.copyMakeBorder(crop, _PAD, _PAD, _PAD, _PAD, cv2.BORDER_CONSTANT, value=background)

    # Upscale with cubic interpolation for sharper edges at small font sizes. The
    # grey levels are kept: Tesseract binarises better than a global threshold does
    # for anti-aliased text, which fills in thin glyph strokes at this size.
    ph, pw = padded.shape[:2]
    scaled = cv2.resize(padded, (pw * _UPSCALE, ph * _UPSCALE), interpolation=cv2.INTER_CUBIC)

    text = pytesseract.image_to_string(scaled, config=_TESS_CONFIG)
    return _restore_hyphens(text, scaled) if "~" in text else text


def _restore_hyphens(text: str, scaled: np.ndarray) -> str:
    """Tesseract often reads a small "-" visibility mark as "~" (package). A real
    tilde wobbles up and down; a hyphen is level, so only wobbling ones stay."""
    height = scaled.shape[0]
    flat: list[bool] = []
    for row in pytesseract.image_to_boxes(scaled, config=_TESS_CONFIG).splitlines():
        char, left, bottom, right, top = row.split()[:5]
        if char == "~":
            patch = scaled[
                height - int(top) - 1 : height - int(bottom) + 1, int(left) - 1 : int(right) + 2
            ]
            flat.append(_is_level(patch))
    if len(flat) != text.count("~"):
        return text
    levels = iter(flat)
    return "".join("-" if char == "~" and next(levels) else char for char in text)


def _is_level(patch: np.ndarray) -> bool:
    """Whether the dark ink in a glyph patch stays at one height across its width."""
    if patch.size == 0:
        return False
    ink = patch < (int(patch.max()) + int(patch.min())) // 2
    centres = [
        float(np.nonzero(ink[:, col])[0].mean()) for col in range(ink.shape[1]) if ink[:, col].any()
    ]
    return bool(centres) and max(centres) - min(centres) < _TILDE_WOBBLE


def _split_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def extract_multiplicity(gray: np.ndarray, rect: tuple[int, int, int, int]) -> str:
    """Raw OCR of a short multiplicity label ("1", "0..*") inside `rect`."""
    x, y, w, h = rect
    crop = gray[max(0, y - _LABEL_MARGIN) : y + h + _LABEL_MARGIN, max(0, x - _LABEL_MARGIN) : x + w + _LABEL_MARGIN]
    if crop.size == 0:
        return ""
    background = int(np.median(crop))
    padded = cv2.copyMakeBorder(
        crop, _PAD, _PAD, _PAD, _PAD, cv2.BORDER_CONSTANT, value=background
    )
    scaled = cv2.resize(
        padded, None, fx=_LABEL_UPSCALE, fy=_LABEL_UPSCALE, interpolation=cv2.INTER_CUBIC
    )
    return pytesseract.image_to_string(scaled, config=_LABEL_TESS_CONFIG).strip()
