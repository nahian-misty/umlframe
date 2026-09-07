"""
End-to-end forward activity pipeline demo:
activity-diagram image -> CV + OCR -> ActivityDocument -> structured code.

Every stage runs for real (OCR included -- requires the `tesseract` binary).
Mirrors scripts/e2e_demo.py for the class-diagram pipeline.

Usage:
    PYTHONPATH=. python3 scripts/e2e_activity_demo.py
"""
from __future__ import annotations

import io
import shutil
import sys
import textwrap

from PIL import Image, ImageDraw, ImageFont

FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
]


def _font(size: int):
    for path in FONT_PATHS:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def make_activity_image() -> bytes:
    """A while-loop activity diagram: start -> [n > 0?] --yes--> (n -= 1) -> back,
    --no--> end."""
    img = Image.new("RGB", (640, 520), "white")
    d = ImageDraw.Draw(img)

    d.ellipse([324, 24, 356, 56], fill="black")  # start
    d.polygon([(340, 110), (435, 170), (340, 230), (245, 170)], outline="black", width=3)
    d.text((300, 160), "n > 0", fill="black", font=_font(18))
    d.rounded_rectangle([250, 330, 470, 400], radius=8, outline="black", width=3)
    d.text((286, 344), "n -= 1", fill="black", font=_font(20))
    d.ellipse([540, 150, 580, 190], outline="black", width=3)  # end

    d.line([340, 60, 340, 106], fill="black", width=2)     # start -> decision
    d.line([340, 236, 340, 326], fill="black", width=2)    # decision -> body (yes)
    d.line([233, 340, 236, 185], fill="black", width=2)    # body -> decision (back edge)
    d.line([443, 170, 534, 170], fill="black", width=2)    # decision -> end (no)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def separator(title: str) -> None:
    print(f"\n{'─' * 70}\n  {title}\n{'─' * 70}")


def main() -> None:
    if shutil.which("tesseract") is None:
        sys.exit("tesseract-ocr binary not found -- install it to run this demo.")

    from backend.services.activity_codegen_service import generate_activity_code
    from backend.services.activity_image_service import activity_image_to_document

    separator("STAGE 0 — Drawing activity-diagram image")
    image_bytes = make_activity_image()
    print(f"  Image size: {len(image_bytes):,} bytes")

    separator("STAGE 1-4 — CV + OCR + edge orientation -> ActivityDocument")
    document = activity_image_to_document(image_bytes)
    for node in document.nodes:
        print(f"  {node.id}: {node.type.value:9} {node.label!r}")
    for edge in document.edges:
        guard = f"  [{edge.label}]" if edge.label else ""
        print(f"  {edge.source} -> {edge.target}{guard}")

    separator("STAGE 5 — Structured control-flow code generation")
    for language in ("python", "java", "javascript"):
        files = generate_activity_code(document, language, "generated")
        for fname, content in files.items():
            print(f"\n  ── {fname} ──")
            print(textwrap.indent(content, "  "))

    separator("RESULT")
    print("  Input:  1 PNG activity diagram")
    print("  Output: a standalone function per language, with real while/if")
    print("          structure and placeholder bodies (never fabricated logic).\n")


if __name__ == "__main__":
    main()
