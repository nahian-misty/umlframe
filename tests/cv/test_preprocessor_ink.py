"""Preprocessing for diagrams exported from the editor (transparent, light-grey outlines)."""
from __future__ import annotations

import io

import cv2
import numpy as np
from PIL import Image, ImageDraw

from backend.cv.preprocessor import (
    flatten_alpha,
    ink_binary,
    load_image,
    preprocess_ink,
    to_grayscale,
)


def _png(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_transparent_pixels_become_white_not_black():
    img = Image.new("RGBA", (40, 40), (0, 0, 0, 0))
    ImageDraw.Draw(img).rectangle([10, 10, 30, 30], fill=(29, 29, 35, 255))

    flat = load_image(flatten_alpha(_png(img)))

    assert tuple(flat[2, 2]) == (255, 255, 255)
    assert tuple(flat[20, 20]) == (35, 29, 29)  # opaque ink kept (BGR)


def test_opaque_images_pass_through_unchanged():
    data = _png(Image.new("RGB", (10, 10), "white"))

    assert flatten_alpha(data) == data


def test_light_grey_outline_counts_as_ink():
    img = Image.new("RGB", (80, 80), "white")
    ImageDraw.Draw(img).rectangle([10, 10, 70, 70], outline=(168, 168, 179), width=2)

    binary = ink_binary(to_grayscale(load_image(_png(img))))

    assert binary[10, 40] == 255
    assert binary[40, 40] == 0


def test_faint_grid_lines_stay_background():
    img = Image.new("RGB", (80, 80), "white")
    ImageDraw.Draw(img).line([(0, 40), (80, 40)], fill=(226, 226, 232), width=1)
    ImageDraw.Draw(img).rectangle([20, 20, 60, 60], outline="black", width=2)

    binary = ink_binary(to_grayscale(load_image(_png(img))))

    assert binary[40, 5] == 0  # the grid line outside the shape is not ink
    assert binary[20, 40] == 255


def test_preprocess_ink_returns_matching_shapes():
    color, gray, binary = preprocess_ink(_png(Image.new("RGB", (30, 20), "white")))

    assert color.shape == (20, 30, 3)
    assert gray.shape == binary.shape == (20, 30)
    assert isinstance(binary, np.ndarray) and binary.dtype == np.uint8
    assert cv2.countNonZero(binary) == 0
