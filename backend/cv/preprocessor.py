from __future__ import annotations

import cv2
import numpy as np
import numpy.typing as npt


def load_image(image_bytes: bytes) -> np.ndarray:
    arr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image — unsupported format or corrupted data")
    return img


def to_grayscale(img: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def to_binary(gray: np.ndarray) -> np.ndarray:
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    # Bridge small gaps from noise, thin lines, or anti-aliasing before contour detection.
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    return binary


def preprocess(image_bytes: bytes) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Decode image bytes and return (color BGR, grayscale, binary-inverted)."""
    color = load_image(image_bytes)
    gray = to_grayscale(color)
    binary = to_binary(gray)
    return color, gray, binary


# ---------------------------------------------------------------------------
# Screenshots and canvas exports (UI-drawn diagrams, as opposed to clean renders)
# ---------------------------------------------------------------------------

# Grey levels: outlines up to this brightness count as ink; never go above the ceiling
# or faint grid lines (~#e2e2e8) would become ink too.
INK_FLOOR = 200
INK_CEILING = 225
BGRA_CHANNELS = 4
ALPHA_OPAQUE = 255.0


def flatten_alpha(image_bytes: bytes) -> bytes:
    """Composite a transparent PNG onto white. OpenCV decodes transparency as black,
    which would turn a transparent-background export into one solid dark page."""
    decoded = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_UNCHANGED)
    if decoded is None or decoded.ndim != 3 or decoded.shape[2] != BGRA_CHANNELS:
        return image_bytes
    alpha = decoded[:, :, 3:4].astype(np.float32) / ALPHA_OPAQUE
    colour = decoded[:, :, :3].astype(np.float32)
    flattened = (colour * alpha + ALPHA_OPAQUE * (1.0 - alpha)).astype(np.uint8)
    ok, encoded = cv2.imencode(".png", flattened)
    return encoded.tobytes() if ok else image_bytes


def ink_binary(gray: npt.NDArray[np.uint8]) -> npt.NDArray[np.uint8]:
    """Binary-inverted image where outlines drawn in light gray still count as ink.

    Otsu alone splits dark text from the page, which can put a mid-gray outline
    (a common UI border colour) on the background side and erase the node
    entirely. Using the brighter of Otsu and a fixed floor keeps those outlines
    while still excluding near-white grid lines and shadows. Thresholded
    unblurred: blurring a 2px light-grey outline pushes it back above the cutoff."""
    otsu, _ = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    threshold = min(INK_CEILING, max(otsu, INK_FLOOR))
    _, binary = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY_INV)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    return np.asarray(cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel), dtype=np.uint8)


def preprocess_ink(
    image_bytes: bytes,
) -> tuple[npt.NDArray[np.uint8], npt.NDArray[np.uint8], npt.NDArray[np.uint8]]:
    """Like preprocess(), for diagrams exported from the editor: transparency is
    flattened onto white and light-grey outlines are kept as ink."""
    color = load_image(flatten_alpha(image_bytes))
    gray = to_grayscale(color)
    return color, gray, ink_binary(gray)


# Light fills (a coloured header, a tinted box) sit below the ink floor and would
# turn whole compartments into solid ink. When the wide binary has this much solid
# area and the plain Otsu one does not, the outlines are dark enough for Otsu.
SOLID_KERNEL = 9
SOLID_FILL_FRACTION = 0.01


def _solid_fraction(binary: npt.NDArray[np.uint8]) -> float:
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (SOLID_KERNEL, SOLID_KERNEL))
    return float((cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel) > 0).mean())


def class_ink_binary(gray: npt.NDArray[np.uint8]) -> npt.NDArray[np.uint8]:
    """Binary-inverted ink for class diagrams: ink_binary(), unless that turns
    light box fills into solid ink, in which case plain Otsu (dark strokes only)."""
    wide = ink_binary(gray)
    if _solid_fraction(wide) <= SOLID_FILL_FRACTION:
        return wide
    otsu, _ = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    _, dark = cv2.threshold(gray, otsu, 255, cv2.THRESH_BINARY_INV)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    dark = np.asarray(cv2.morphologyEx(dark, cv2.MORPH_CLOSE, kernel), dtype=np.uint8)
    return dark if _solid_fraction(dark) < _solid_fraction(wide) / 2 else wide


def preprocess_class_ink(
    image_bytes: bytes,
) -> tuple[npt.NDArray[np.uint8], npt.NDArray[np.uint8], npt.NDArray[np.uint8]]:
    """preprocess_ink() with class_ink_binary(): the class-diagram image pipeline."""
    color = load_image(flatten_alpha(image_bytes))
    gray = to_grayscale(color)
    return color, gray, class_ink_binary(gray)


# Darkest thresholds tried, in order, when a coloured node fill is dark enough to count as ink.
ACTIVITY_FILL_THRESHOLDS = (150, 120, 90, 60)


def activity_ink_binary(gray: npt.NDArray[np.uint8]) -> npt.NDArray[np.uint8]:
    """Binary-inverted ink for activity diagrams. Starts from class_ink_binary(); if a coloured
    node fill (purple, green, red...) is still dark enough to be solid ink, the threshold is
    lowered until fills fall back to background and only outlines, lines and text remain."""
    binary = class_ink_binary(gray)
    if _solid_fraction(binary) <= SOLID_FILL_FRACTION:
        return binary
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    for threshold in ACTIVITY_FILL_THRESHOLDS:
        _, darker = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY_INV)
        darker = np.asarray(cv2.morphologyEx(darker, cv2.MORPH_CLOSE, kernel), dtype=np.uint8)
        if _solid_fraction(darker) <= SOLID_FILL_FRACTION:
            return darker
    return binary


def preprocess_activity_ink(
    image_bytes: bytes,
) -> tuple[npt.NDArray[np.uint8], npt.NDArray[np.uint8], npt.NDArray[np.uint8]]:
    """preprocess_ink() with activity_ink_binary(): the activity-diagram image pipeline."""
    color = load_image(flatten_alpha(image_bytes))
    gray = to_grayscale(color)
    return color, gray, activity_ink_binary(gray)
