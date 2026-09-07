from __future__ import annotations

import cv2
import numpy as np


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
