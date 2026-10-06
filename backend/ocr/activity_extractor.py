from __future__ import annotations

import cv2
import numpy as np
import numpy.typing as npt
import pytesseract

from backend.cv.activity_shape_detector import ActivityConnector, ActivityShape

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

# Thickness used to blank out the connector itself before reading its label, so
# the line crossing the window is not read as stray characters.
_CONNECTOR_BLANK_THICKNESS = 5
# A guard is one short word ("yes"/"no"): single-word page segmentation.
_GUARD_TESS_CONFIG = "--oem 3 --psm 7 --dpi 300"

# Grey levels below which a pixel counts as text ink.
_GUARD_DARK_INK_LEVEL = 80
_GUARD_ANY_INK_LEVEL = 140
_GUARD_MAX_GLYPH_SIDE = 40
_GUARD_MAX_DISTANCE = 70
_GUARD_MIN_GLYPH_AREA = 6
_GUARD_PAD = 8
_GLYPH_HALO = 4
_GUARD_LINE_THICKNESS = 3
_GUARD_LINE_MIN_LENGTH = 8
_WHITE = 255
# A crop whose darkest and lightest pixels differ by less than this holds no text.
_MIN_TEXT_CONTRAST = 50
# The background is most of a label's crop; below this share of white, the polarity is flipped.
_MIN_BACKGROUND_SHARE = 0.5
_MASK_EXTRA_PX = 6
# Arrowheads sit just outside the node an edge points at; clear this much around it.
_ARROWHEAD_CLEARANCE = 28
# The detected connector stops where node bounding boxes were erased; the real line
# continues this far on, up to the node's actual outline.
_CONNECTOR_EXTENSION = 80

# Fraction of a diamond's bounding box read for its label. A rectangle with half-
# extents (a*fx, b*fy) sits inside the diamond while fx + fy <= 1.
_DIAMOND_LABEL_WIDTH = 0.64
_DIAMOND_LABEL_HEIGHT = 0.30
# Fraction of an outlined box's own interior read for its label: the centre, clear of the
# rounded corners and of any outline thickness the interior contour sits against.
_BOX_LABEL_WIDTH = 0.88
_BOX_LABEL_HEIGHT = 0.72
# An ellipse's interior narrows toward its ends, so less of it is safe to read.
_ELLIPSE_LABEL_WIDTH = 0.70
_ELLIPSE_LABEL_HEIGHT = 0.60
_ELLIPSE_MAX_EXTENT = 0.85


def extract_activity_labels(gray: GrayImage, shapes: list[ActivityShape]) -> list[str]:
    """One raw OCR string per shape, indexed parallel to `shapes`. Start/end
    and fork/join bars carry no text, so they come back as ""."""
    labels: list[str] = []
    for shape in shapes:
        if shape.kind not in _LABELLED_KINDS:
            labels.append("")
            continue
        region = _label_region(shape)
        labels.append(_ocr_region(gray, region).strip())
    return labels


def _label_region(shape: ActivityShape) -> tuple[int, int, int, int]:
    """The safe-to-OCR interior of a shape, avoiding its own outline strokes.
    A rounded-rect's outline hugs its bounding box's perimeter, so a flat
    border inset suffices (`_inset`). A diamond's outline instead cuts
    diagonally through the *middle* of its bounding box -- no fixed border
    avoids it -- so a decision shape instead uses the largest axis-aligned
    rectangle inscribed in the diamond: half the bounding box's width and
    height, centered, which for a diamond |x|/a + |y|/b <= 1 stays strictly
    inside the |x|<=a, |y|<=b bound at every corner."""
    if shape.kind == "decision":
        cx, cy = shape.x + shape.w / 2, shape.y + shape.h / 2
        iw, ih = shape.w * _DIAMOND_LABEL_WIDTH, shape.h * _DIAMOND_LABEL_HEIGHT
        return (int(cx - iw / 2), int(cy - ih / 2), int(iw), int(ih))
    if shape.interior is not None:
        ix, iy, iw, ih = cv2.boundingRect(shape.interior)
        extent = cv2.contourArea(shape.interior) / (iw * ih) if iw * ih else 1.0
        narrow = extent < _ELLIPSE_MAX_EXTENT
        lw = iw * (_ELLIPSE_LABEL_WIDTH if narrow else _BOX_LABEL_WIDTH)
        lh = ih * (_ELLIPSE_LABEL_HEIGHT if narrow else _BOX_LABEL_HEIGHT)
        return (int(ix + (iw - lw) / 2), int(iy + (ih - lh) / 2), int(lw), int(lh))
    return _inset((shape.x, shape.y, shape.w, shape.h))


def extract_edge_guard_candidates(
    gray: GrayImage,
    shapes: list[ActivityShape],
    connector: ActivityConnector,
    target: ActivityShape,
) -> list[str]:
    """Raw OCR strings for the guard text ("yes"/"no") written beside one edge.

    Nodes are blanked by their real outline (not bounding box -- a diamond's box
    also covers the empty corners where labels sit), the edge's own line and the
    arrowhead beside its target are blanked too, and the ink still lying close to
    the connector is the label. Text is normally drawn darker and bolder than the
    lines around it, so the darkest ink is tried first (which also strips any
    sliver of line left over); if that finds nothing, all ink is used. Returns one
    candidate per ink level -- the caller decides which, if any, is a real guard."""
    cleaned = gray.copy()
    for shape in shapes:
        _mask_shape(cleaned, shape)
    cleaned[
        max(0, target.y - _ARROWHEAD_CLEARANCE) : target.y + target.h + _ARROWHEAD_CLEARANCE,
        max(0, target.x - _ARROWHEAD_CLEARANCE) : target.x + target.w + _ARROWHEAD_CLEARANCE,
    ] = _WHITE
    # Darkest ink first, on the picture with the line left in: text is darker than
    # the line, so the line drops out on its own and no letter beside it gets
    # clipped. Then all ink, with the line blanked, for text as dark as its line.
    candidates: list[str] = []
    text = _read_ink_near(cleaned, _GUARD_DARK_INK_LEVEL, connector)
    if text:
        candidates.append(text)
    # A label drawn into a gap in the line is read as it stands: blanking the line
    # would also wipe the letters sitting on it.
    text = _read_ink_near(cleaned, _GUARD_ANY_INK_LEVEL, connector)
    if text:
        candidates.append(text)
    start, end = _extended_ends(connector)
    cv2.line(cleaned, start, end, _WHITE, _CONNECTOR_BLANK_THICKNESS)
    text = _read_ink_near(cleaned, _GUARD_ANY_INK_LEVEL, connector)
    if text:
        candidates.append(text)
    return candidates


def _read_ink_near(cleaned: GrayImage, ink_level: int, connector: ActivityConnector) -> str:
    ink = (cleaned < ink_level).astype(np.uint8) * 255
    count, labels, stats, _ = cv2.connectedComponentsWithStats(ink, connectivity=8)
    kept = np.zeros_like(ink)
    for index in range(1, count):
        x, y, w, h, area = (int(v) for v in stats[index])
        if area < _GUARD_MIN_GLYPH_AREA or max(w, h) > _GUARD_MAX_GLYPH_SIDE:
            continue
        if _is_line_piece(w, h, connector):
            continue
        if _distance_to_segment(x + w / 2, y + h / 2, connector) > _GUARD_MAX_DISTANCE:
            continue
        kept[labels == index] = 255
    if not kept.any():
        return ""

    ys, xs = np.where(kept)
    region = (
        int(xs.min()) - _GUARD_PAD,
        int(ys.min()) - _GUARD_PAD,
        int(np.ptp(xs)) + 2 * _GUARD_PAD,
        int(np.ptp(ys)) + 2 * _GUARD_PAD,
    )
    halo = cv2.dilate(kept, np.ones((2 * _GLYPH_HALO + 1, 2 * _GLYPH_HALO + 1), np.uint8))
    isolated = np.where(halo > 0, cleaned, _WHITE).astype(np.uint8)
    # Tesseract reads a two- or three-letter word better from the grey levels than
    # from a global threshold, which breaks thin letters apart at this size.
    return _ocr_region(isolated, region, _GUARD_TESS_CONFIG, binarize=False).strip()


def _is_line_piece(w: int, h: int, connector: ActivityConnector) -> bool:
    """A thin sliver lying along the connector: a stub of the line left beside the
    label, not a letter."""
    horizontal = abs(connector.x2 - connector.x1) >= abs(connector.y2 - connector.y1)
    length, thickness = (w, h) if horizontal else (h, w)
    return thickness <= _GUARD_LINE_THICKNESS and length >= _GUARD_LINE_MIN_LENGTH


def _distance_to_segment(px: float, py: float, c: ActivityConnector) -> float:
    dx, dy = c.x2 - c.x1, c.y2 - c.y1
    length_sq = dx * dx + dy * dy
    if length_sq == 0:
        return float(np.hypot(px - c.x1, py - c.y1))
    t = max(0.0, min(1.0, ((px - c.x1) * dx + (py - c.y1) * dy) / length_sq))
    return float(np.hypot(px - (c.x1 + t * dx), py - (c.y1 + t * dy)))


def _mask_shape(work: GrayImage, shape: ActivityShape) -> None:
    """Blank a node (outline, interior, text) in a grayscale copy."""
    if shape.interior is None:
        work[max(0, shape.y) : shape.y + shape.h, max(0, shape.x) : shape.x + shape.w] = _WHITE
        return
    mask = np.zeros_like(work)
    cv2.drawContours(mask, [shape.interior], -1, 255, thickness=cv2.FILLED)
    width = int(cv2.boundingRect(shape.interior)[2])
    thickness = max(1, (shape.w - width) // 2) + _MASK_EXTRA_PX
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * thickness + 1, 2 * thickness + 1))
    work[cv2.dilate(mask, kernel) > 0] = _WHITE


def _extended_ends(c: ActivityConnector) -> tuple[tuple[int, int], tuple[int, int]]:
    dx, dy = c.x2 - c.x1, c.y2 - c.y1
    length = float(np.hypot(dx, dy)) or 1.0
    ux, uy = dx / length, dy / length
    return (
        (int(c.x1 - ux * _CONNECTOR_EXTENSION), int(c.y1 - uy * _CONNECTOR_EXTENSION)),
        (int(c.x2 + ux * _CONNECTOR_EXTENSION), int(c.y2 + uy * _CONNECTOR_EXTENSION)),
    )


def _inset(region: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    x, y, w, h = region
    return (
        x + _BORDER_INSET,
        y + _BORDER_INSET,
        max(0, w - 2 * _BORDER_INSET),
        max(0, h - 2 * _BORDER_INSET),
    )


def _ocr_region(
    gray: GrayImage,
    region: tuple[int, int, int, int],
    config: str = _TESS_CONFIG,
    binarize: bool = True,
) -> str:
    x, y, w, h = region
    x = max(0, x)
    y = max(0, y)
    w = min(w, gray.shape[1] - x)
    h = min(h, gray.shape[0] - y)
    if h < 4 or w < 4:
        return ""

    crop = gray[y : y + h, x : x + w]
    # Pad with the crop's own background (a coloured fill is not white), so the border does
    # not become a third grey level for the threshold to split.
    background = int(np.median(crop))
    padded = cv2.copyMakeBorder(
        crop, _PAD, _PAD, _PAD, _PAD, cv2.BORDER_CONSTANT, value=background
    )

    ph, pw = padded.shape[:2]
    scaled = cv2.resize(padded, (pw * _UPSCALE, ph * _UPSCALE), interpolation=cv2.INTER_CUBIC)

    if binarize:
        _, scaled = cv2.threshold(scaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        if (scaled == _WHITE).mean() < _MIN_BACKGROUND_SHARE:
            scaled = cv2.bitwise_not(scaled)  # light text on a dark fill: make it dark on light

    return str(pytesseract.image_to_string(scaled, config=config))
