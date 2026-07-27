"""
Run this script once to generate the PNG fixture images used by the test suite.

    python3 tests/fixtures/make_fixtures.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).parent

# Try to load a decent monospace font; fall back to PIL default if unavailable
FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
]


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in FONT_PATHS:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _text_height(font, text: str, draw: ImageDraw.ImageDraw) -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[3] - bbox[1]


def make_simple_class() -> None:
    """One UML class box: User with one attribute and one method."""
    font_title = _font(18)
    font_body = _font(14)

    pad = 8
    line_h = 20
    box_w = 200

    name_h = line_h + pad * 2
    attr_h = line_h + pad * 2
    meth_h = line_h + pad * 2
    box_h = name_h + attr_h + meth_h

    margin = 30
    img_w = box_w + margin * 2
    img_h = box_h + margin * 2

    img = Image.new("RGB", (img_w, img_h), "white")
    draw = ImageDraw.Draw(img)

    bx, by = margin, margin

    # Outer rectangle
    draw.rectangle([bx, by, bx + box_w, by + box_h], outline="black", width=2)

    # Dividers
    d1 = by + name_h
    d2 = d1 + attr_h
    draw.line([bx, d1, bx + box_w, d1], fill="black", width=2)
    draw.line([bx, d2, bx + box_w, d2], fill="black", width=2)

    # Text — class name
    draw.text((bx + pad, by + pad), "User", fill="black", font=font_title)
    # Attribute
    draw.text((bx + pad, d1 + pad), "- email : String", fill="black", font=font_body)
    # Method
    draw.text((bx + pad, d2 + pad), "+ login() : void", fill="black", font=font_body)

    img.save(OUT / "simple_class.png")
    print("Written simple_class.png")


def make_two_classes() -> None:
    """Two UML class boxes side by side (no relationship lines)."""
    font_title = _font(16)
    font_body = _font(13)

    pad = 8
    line_h = 18
    box_w = 190

    name_h = line_h + pad * 2
    attr_h = (line_h + 4) * 2 + pad
    meth_h = line_h + pad * 2
    box_h = name_h + attr_h + meth_h

    gap = 60
    margin = 30
    img_w = box_w * 2 + gap + margin * 2
    img_h = box_h + margin * 2

    img = Image.new("RGB", (img_w, img_h), "white")
    draw = ImageDraw.Draw(img)

    def draw_box(bx: int, by: int, title: str, attrs: list[str], methods: list[str]) -> None:
        bh = name_h + (line_h + 4) * len(attrs) + pad + (line_h + 4) * len(methods) + pad
        draw.rectangle([bx, by, bx + box_w, by + bh], outline="black", width=2)
        d1 = by + name_h
        d2 = d1 + (line_h + 4) * len(attrs) + pad
        draw.line([bx, d1, bx + box_w, d1], fill="black", width=2)
        draw.line([bx, d2, bx + box_w, d2], fill="black", width=2)

        draw.text((bx + pad, by + pad), title, fill="black", font=font_title)
        for i, a in enumerate(attrs):
            draw.text((bx + pad, d1 + pad + i * (line_h + 4)), a, fill="black", font=font_body)
        for i, m in enumerate(methods):
            draw.text((bx + pad, d2 + pad + i * (line_h + 4)), m, fill="black", font=font_body)

    draw_box(
        margin,
        margin,
        "Order",
        ["- total : float", "- status : String"],
        ["+ submit() : void"],
    )
    draw_box(
        margin + box_w + gap,
        margin,
        "Product",
        ["- name : String"],
        ["+ getPrice() : float"],
    )

    img.save(OUT / "two_classes.png")
    print("Written two_classes.png")


if __name__ == "__main__":
    make_simple_class()
    make_two_classes()
