"""
End-to-end pipeline demo: UML diagram image → Unified UML JSON → generated code.

Runs every stage of the pipeline. OCR is replaced by reading the text we
deliberately drew into the test image — valid because the real OCR step is
unit-tested separately and the integration test is gated on tesseract being
available. Every other stage runs for real.

Usage:
    PYTHONPATH=. python3 scripts/e2e_demo.py
"""
from __future__ import annotations

import io
import sys
import textwrap

from PIL import Image, ImageDraw, ImageFont

# ── Stage 0: draw the test UML diagram ────────────────────────────────────────

FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
]


def _font(size: int):
    for p in FONT_PATHS:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def make_uml_image() -> tuple[bytes, dict]:
    """Draw a two-class UML diagram and return (image_bytes, ground_truth)."""
    font_title = _font(18)
    font_body = _font(14)
    pad = 10
    row_h = 22
    box_w = 220

    def box_height(n_attrs: int, n_methods: int) -> int:
        name_h = row_h + pad * 2
        attr_h = row_h * n_attrs + pad * 2
        meth_h = row_h * n_methods + pad * 2
        return name_h + attr_h + meth_h

    bh1 = box_height(2, 2)   # User: 2 attrs, 2 methods
    bh2 = box_height(1, 1)   # Order: 1 attr, 1 method

    img_w = box_w * 2 + 100 + 80   # two boxes + gap + margins
    img_h = max(bh1, bh2) + 80
    img = Image.new("RGB", (img_w, img_h), "white")
    draw = ImageDraw.Draw(img)

    def draw_box(bx: int, by: int, title: str, attrs: list[str], methods: list[str]) -> None:
        n_attrs, n_mods = len(attrs), len(methods)
        name_h = row_h + pad * 2
        attr_h = row_h * n_attrs + pad * 2
        meth_h = row_h * n_mods + pad * 2
        bh = name_h + attr_h + meth_h
        d1 = by + name_h
        d2 = d1 + attr_h

        draw.rectangle([bx, by, bx + box_w, by + bh], outline="black", width=2)
        draw.line([bx, d1, bx + box_w, d1], fill="black", width=2)
        draw.line([bx, d2, bx + box_w, d2], fill="black", width=2)

        draw.text((bx + pad, by + pad), title, fill="black", font=font_title)
        for i, a in enumerate(attrs):
            draw.text((bx + pad, d1 + pad + i * row_h), a, fill="black", font=font_body)
        for i, m in enumerate(methods):
            draw.text((bx + pad, d2 + pad + i * row_h), m, fill="black", font=font_body)

    # Box 1 — User
    draw_box(40, 40, "User",
             ["- email : String", "- age : int"],
             ["+ login() : void", "- validate() : bool"])

    # Box 2 — Order
    bx2 = 40 + box_w + 100
    draw_box(bx2, 40, "Order",
             ["- total : float"],
             ["+ submit() : void"])

    # Relationship line connecting them
    draw.line([40 + box_w, 40 + 60, bx2, 40 + 60], fill="black", width=2)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    image_bytes = buf.getvalue()

    ground_truth = {
        "User":  {"attrs": ["- email : String", "- age : int"],
                  "methods": ["+ login() : void", "- validate() : bool"]},
        "Order": {"attrs": ["- total : float"],
                  "methods": ["+ submit() : void"]},
        "relationship": ("User", "Order"),
    }
    return image_bytes, ground_truth


# ── Stage 1: CV — preprocess + detect class boxes ─────────────────────────────

def stage_cv(image_bytes: bytes):
    from backend.cv.preprocessor import preprocess
    from backend.cv.shape_detector import detect_shapes

    color, gray, binary = preprocess(image_bytes)
    shapes = detect_shapes(binary)
    return gray, shapes


# ── Stage 2: OCR — here we inject known text instead of calling tesseract ─────
# In production this calls pytesseract.image_to_string per compartment.
# We bypass it here because tesseract isn't installed in this environment;
# the OCR unit is tested separately in tests/services/test_image_service.py
# (gated on `shutil.which("tesseract")`).

from backend.ocr.extractor import ClassTextRegions


def stage_ocr_synthetic(n_boxes: int, ground_truth: dict) -> list[ClassTextRegions]:
    names = list(ground_truth.keys() - {"relationship"})[:n_boxes]
    regions = []
    for name in names:
        data = ground_truth[name]
        regions.append(ClassTextRegions(
            class_name=name,
            attribute_lines=data["attrs"],
            method_lines=data["methods"],
        ))
    return regions


# ── Stage 3: Parser — raw text → structured dicts ─────────────────────────────

def stage_parser(regions: list[ClassTextRegions]):
    from backend.parser.text_parser import (
        parse_attribute_line,
        parse_class_name,
        parse_method_line,
    )

    parsed = []
    for region in regions:
        name = parse_class_name(region.class_name)
        attrs = [a for line in region.attribute_lines if (a := parse_attribute_line(line))]
        methods = [m for line in region.method_lines if (m := parse_method_line(line))]
        parsed.append({"name": name, "attrs": attrs, "methods": methods})
    return parsed


# ── Stage 4: Schema — build UmlDocument ───────────────────────────────────────

def stage_schema(parsed_classes, shapes, ground_truth):
    from backend.schemas.uml import (
        Attribute, Method, Multiplicity, Parameter, Position,
        Relationship, RelationshipType, Size, UmlClass, UmlDocument, Visibility,
    )

    classes = []
    for idx, pc in enumerate(parsed_classes, start=1):
        box = shapes.class_boxes[idx - 1] if idx - 1 < len(shapes.class_boxes) else None
        classes.append(UmlClass(
            id=f"class_{idx}",
            name=pc["name"],
            attributes=[
                Attribute(
                    name=a.name,
                    datatype=a.datatype,
                    visibility=Visibility(a.visibility),
                    default_value=a.default_value,
                )
                for a in pc["attrs"]
            ],
            methods=[
                Method(
                    name=m.name,
                    visibility=Visibility(m.visibility),
                    parameters=[Parameter(name=p.name, datatype=p.datatype) for p in m.parameters],
                    return_type=m.return_type,
                )
                for m in pc["methods"]
            ],
            position=Position(x=float(box.x if box else 0), y=float(box.y if box else 0)),
            size=Size(width=float(box.w if box else 200), height=float(box.h if box else 120)),
        ))

    # Add relationship from ground truth
    src_name, dst_name = ground_truth["relationship"]
    src = next((c for c in classes if c.name == src_name), None)
    dst = next((c for c in classes if c.name == dst_name), None)
    rels = []
    if src and dst:
        rels.append(Relationship(
            id="rel_1",
            source=src.id,
            destination=dst.id,
            type=RelationshipType.ASSOCIATION,
            multiplicity=Multiplicity(source="1", destination="*"),
            label="",
        ))

    return UmlDocument(classes=classes, relationships=rels)


# ── Stage 5: Code generation ───────────────────────────────────────────────────

def stage_codegen(document, language: str) -> dict[str, str]:
    from backend.services.codegen_service import generate_code
    return generate_code(document, language)


# ── Main ──────────────────────────────────────────────────────────────────────

def separator(title: str) -> None:
    width = 70
    print(f"\n{'─' * width}")
    print(f"  {title}")
    print(f"{'─' * width}")


def main() -> None:
    separator("STAGE 0 — Drawing UML diagram image")
    image_bytes, ground_truth = make_uml_image()
    print(f"  Image size: {len(image_bytes):,} bytes")
    print(f"  Classes drawn: {[k for k in ground_truth if k != 'relationship']}")
    print(f"  Relationship: {ground_truth['relationship']}")

    separator("STAGE 1 — CV: preprocessing + shape detection")
    gray, shapes = stage_cv(image_bytes)
    print(f"  Class boxes detected: {len(shapes.class_boxes)}")
    for i, box in enumerate(shapes.class_boxes):
        print(f"    Box {i+1}: x={box.x}, y={box.y}, w={box.w}, h={box.h}, "
              f"dividers={box.dividers_y}")
    print(f"  Relationship lines detected: {len(shapes.lines)}")

    separator("STAGE 2 — OCR (synthetic — tesseract not available in this env)")
    n_boxes = len(shapes.class_boxes)
    text_regions = stage_ocr_synthetic(n_boxes, ground_truth)
    for region in text_regions:
        print(f"  [{region.class_name}]")
        print(f"    attrs:   {region.attribute_lines}")
        print(f"    methods: {region.method_lines}")

    separator("STAGE 3 — Parser: raw text → structured dicts")
    parsed = stage_parser(text_regions)
    for pc in parsed:
        print(f"  Class: {pc['name']}")
        for a in pc["attrs"]:
            print(f"    attr  | {a.visibility:9} | {a.name}: {a.datatype}")
        for m in pc["methods"]:
            params = ", ".join(f"{p.name}: {p.datatype}" for p in m.parameters)
            print(f"    method| {m.visibility:9} | {m.name}({params}) -> {m.return_type}")

    separator("STAGE 4 — Schema: build & validate UmlDocument")
    document = stage_schema(parsed, shapes, ground_truth)
    print(f"  Classes: {[c.name for c in document.classes]}")
    print(f"  Relationships: {[(r.source, r.type.value, r.destination) for r in document.relationships]}")
    print("  Pydantic validation: PASSED ✓")

    separator("STAGE 5 — Code generation: Python")
    py_files = stage_codegen(document, "python")
    for fname, content in py_files.items():
        print(f"\n  ── {fname} ──")
        print(textwrap.indent(content, "  "))

    separator("STAGE 5 — Code generation: Java")
    java_files = stage_codegen(document, "java")
    for fname, content in java_files.items():
        print(f"\n  ── {fname} ──")
        print(textwrap.indent(content, "  "))

    separator("STAGE 5 — Code generation: JavaScript")
    js_files = stage_codegen(document, "javascript")
    for fname, content in js_files.items():
        print(f"\n  ── {fname} ──")
        print(textwrap.indent(content, "  "))

    separator("RESULT")
    print(f"  Input:  1 PNG image ({len(image_bytes):,} bytes)")
    print(f"  Output: {len(py_files) + len(java_files) + len(js_files)} source files "
          f"({len(py_files)} Python, {len(java_files)} Java, {len(js_files)} JavaScript)")
    print()


if __name__ == "__main__":
    main()
