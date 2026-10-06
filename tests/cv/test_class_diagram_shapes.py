"""Class-diagram CV on shapes the plain black-box fixtures do not cover: filled and
rounded boxes, a shared inheritance bus, open arrowheads, multiplicity text and
dashed lines whose gaps binarising closes."""

from __future__ import annotations

import io
import math

import pytest
from PIL import Image, ImageDraw

from backend.cv.preprocessor import preprocess_class_ink
from backend.cv.shape_detector import DetectedShapes, detect_shapes

OUTLINE = (40, 40, 40)
LINE_WIDTH = 2


def _png(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _detect(img: Image.Image) -> DetectedShapes:
    _, gray, binary = preprocess_class_ink(_png(img))
    return detect_shapes(binary, gray)


def _box(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, dividers=(), fill=None, radius=0):
    if radius:
        draw.rounded_rectangle([x, y, x + w, y + h], radius=radius, outline=OUTLINE, width=LINE_WIDTH, fill=fill)
    else:
        draw.rectangle([x, y, x + w, y + h], outline=OUTLINE, width=LINE_WIDTH, fill=fill)
    for d in dividers:
        draw.line([x, d, x + w, d], fill=OUTLINE, width=LINE_WIDTH)


def _canvas(w: int = 560, h: int = 420) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (w, h), "white")
    return img, ImageDraw.Draw(img)


def test_rounded_box_with_a_tinted_header_is_one_box_with_two_dividers():
    img, draw = _canvas()
    _box(draw, 60, 50, 170, 150, dividers=(95, 150), radius=10)
    draw.rectangle([62, 52, 228, 94], fill=(255, 224, 120))  # tinted header, lighter than the outline
    shapes = _detect(img)

    assert len(shapes.class_boxes) == 1
    box = shapes.class_boxes[0]
    assert len(box.dividers_y) == 2
    assert abs(box.x - 60) <= 4 and abs(box.w - 170) <= 8


def test_text_on_a_box_edge_is_not_mistaken_for_a_box_or_a_divider():
    img, draw = _canvas()
    _box(draw, 60, 50, 170, 100, dividers=(90,))
    draw.text((70, 62), "A very long attribute name that runs under the rules", fill=OUTLINE)
    shapes = _detect(img)

    assert len(shapes.class_boxes) == 1
    assert len(shapes.class_boxes[0].dividers_y) == 1


def _bus_diagram() -> Image.Image:
    img, draw = _canvas(620, 360)
    _box(draw, 220, 30, 180, 80, dividers=(60,))
    for x in (30, 230, 430):
        _box(draw, x, 250, 160, 80, dividers=(280,))
    # parent edge down to the triangle, bus, and one drop per child
    draw.line([310, 110, 310, 158], fill=OUTLINE, width=LINE_WIDTH)
    draw.polygon([(310, 158), (298, 182), (322, 182)], outline=OUTLINE, fill="white")
    draw.line([110, 182, 510, 182], fill=OUTLINE, width=LINE_WIDTH)
    for x in (110, 310, 510):
        draw.line([x, 182, x, 250], fill=OUTLINE, width=LINE_WIDTH)
    return img


def test_shared_bus_gives_one_line_per_child_with_the_triangle_on_the_parent():
    shapes = _detect(_bus_diagram())
    parent = next(i for i, b in enumerate(shapes.class_boxes) if b.y < 100)

    assert len(shapes.lines) == 3
    for line in shapes.lines:
        assert line.box_p1 == parent
        assert line.marker_p1 == "triangle-hollow"
        assert line.marker_p2 is None


def test_open_arrowhead_is_found_at_the_end_it_points_to():
    img, draw = _canvas()
    _box(draw, 40, 60, 140, 70)
    _box(draw, 340, 60, 140, 70)
    draw.line([180, 95, 340, 95], fill=OUTLINE, width=LINE_WIDTH)
    draw.line([340, 95, 322, 85], fill=OUTLINE, width=LINE_WIDTH)
    draw.line([340, 95, 322, 105], fill=OUTLINE, width=LINE_WIDTH)
    shapes = _detect(img)

    assert len(shapes.lines) == 1
    line = shapes.lines[0]
    markers = {line.box_p1: line.marker_p1, line.box_p2: line.marker_p2}
    right = max(range(2), key=lambda i: shapes.class_boxes[i].x)
    assert markers[right] == "arrow-open"
    assert markers[1 - right] is None


def test_multiplicity_text_beside_each_end_is_located():
    img, draw = _canvas()
    _box(draw, 40, 60, 140, 70)
    _box(draw, 380, 60, 140, 70)
    draw.line([180, 95, 380, 95], fill=OUTLINE, width=LINE_WIDTH)
    draw.text((190, 76), "1", fill=OUTLINE)
    draw.text((345, 76), "0..*", fill=OUTLINE)
    line = _detect(img).lines[0]

    near_left = line.label_p1 if line.x1 < line.x2 else line.label_p2
    near_right = line.label_p2 if line.x1 < line.x2 else line.label_p1
    assert near_left is not None and 180 <= near_left[0] <= 215
    assert near_right is not None and 335 <= near_right[0] <= 380


def test_dashed_line_is_recognised_even_when_binarising_closes_the_gaps():
    img, draw = _canvas()
    _box(draw, 40, 60, 140, 70)
    _box(draw, 380, 60, 140, 70)
    x = 180
    while x < 380:
        draw.line([x, 95, min(x + 9, 380), 95], fill=OUTLINE, width=LINE_WIDTH)
        x += 12  # a 3px gap: closed by the preprocessing, still there in grey levels
    line = _detect(img).lines[0]

    assert line.dashed is True


def test_solid_line_is_not_dashed():
    img, draw = _canvas()
    _box(draw, 40, 60, 140, 70)
    _box(draw, 380, 60, 140, 70)
    draw.line([180, 95, 380, 95], fill=OUTLINE, width=LINE_WIDTH)

    assert _detect(img).lines[0].dashed is False


def _arrow_between_boxes(dashed: bool, width: int, diagonal: bool) -> Image.Image:
    img, draw = _canvas(600, 420)
    second_y = 260 if diagonal else 40
    _box(draw, 40, 40, 160, 110, dividers=(70,))
    _box(draw, 380, second_y, 160, 110, dividers=(second_y + 30,))
    start, end = ((120, 150), (380, 300)) if diagonal else ((200, 95), (380, 95))
    length = math.hypot(end[0] - start[0], end[1] - start[1])
    ux, uy = (end[0] - start[0]) / length, (end[1] - start[1]) / length
    t = 0.0
    while t < length:
        stop = min(t + 8, length) if dashed else length
        draw.line(
            [start[0] + ux * t, start[1] + uy * t, start[0] + ux * stop, start[1] + uy * stop],
            fill=OUTLINE,
            width=width,
        )
        t += 13 if dashed else length
    for side in (1, -1):
        draw.line(
            [end[0] - ux * 16 - side * uy * 8, end[1] - uy * 16 + side * ux * 8, end[0], end[1]],
            fill=OUTLINE,
            width=width,
        )
    return img


@pytest.mark.parametrize("diagonal", [False, True])
@pytest.mark.parametrize("dashed", [False, True])
@pytest.mark.parametrize("width", [2, 3, 4])
def test_open_arrowhead_stays_an_arrow_however_heavy_the_stroke(width, dashed, diagonal):
    """A heavy arrowhead's arms run together into a solid-looking blob; it must not be
    mistaken for an inheritance triangle or a composition diamond."""
    line = _detect(_arrow_between_boxes(dashed, width, diagonal)).lines[0]

    assert {line.marker_p1, line.marker_p2} == {None, "arrow-open"}
    assert line.dashed is dashed
