from __future__ import annotations

import math

from backend.cv.preprocessor import preprocess
from backend.cv.shape_detector import ClassBox, DetectedShapes, RelationshipLine, detect_shapes
from backend.ocr.extractor import extract_class_text
from backend.parser.text_parser import parse_attribute_line, parse_class_name, parse_method_line
from backend.schemas.uml import (
    Attribute,
    Method,
    Multiplicity,
    Parameter,
    Position,
    Relationship,
    RelationshipType,
    Size,
    UmlClass,
    UmlDocument,
    Visibility,
)

_DEFAULT_MULTIPLICITY = Multiplicity(source="1", destination="1")


def image_to_document(image_bytes: bytes) -> UmlDocument:
    """Full forward pipeline: image bytes → validated UmlDocument."""
    color, gray, binary = preprocess(image_bytes)
    shapes = detect_shapes(binary)

    classes = _build_classes(gray, shapes.class_boxes)
    relationships = _build_relationships(shapes.lines, shapes.class_boxes, classes)

    return UmlDocument(classes=classes, relationships=relationships)


# ---------------------------------------------------------------------------
# Class building
# ---------------------------------------------------------------------------


def _build_classes(gray, boxes: list[ClassBox]) -> list[UmlClass]:
    classes = []
    for idx, box in enumerate(boxes, start=1):
        regions = extract_class_text(gray, box)
        cls = _class_from_regions(f"class_{idx}", regions, box)
        classes.append(cls)
    return classes


def _class_from_regions(class_id: str, regions, box: ClassBox) -> UmlClass:
    name = parse_class_name(regions.class_name) or f"Class{class_id.split('_')[1]}"

    attributes: list[Attribute] = []
    for line in regions.attribute_lines:
        parsed = parse_attribute_line(line)
        if parsed:
            attributes.append(
                Attribute(
                    name=parsed.name,
                    datatype=parsed.datatype,
                    visibility=Visibility(parsed.visibility),
                    default_value=parsed.default_value,
                )
            )

    methods: list[Method] = []
    for line in regions.method_lines:
        parsed = parse_method_line(line)
        if parsed:
            methods.append(
                Method(
                    name=parsed.name,
                    visibility=Visibility(parsed.visibility),
                    parameters=[
                        Parameter(name=p.name, datatype=p.datatype)
                        for p in parsed.parameters
                    ],
                    return_type=parsed.return_type,
                )
            )

    return UmlClass(
        id=class_id,
        name=name,
        attributes=attributes,
        methods=methods,
        position=Position(x=float(box.x), y=float(box.y)),
        size=Size(width=float(box.w), height=float(box.h)),
    )


# ---------------------------------------------------------------------------
# Relationship building
# ---------------------------------------------------------------------------


def _build_relationships(
    lines: list[RelationshipLine],
    boxes: list[ClassBox],
    classes: list[UmlClass],
) -> list[Relationship]:
    if not lines or len(classes) < 2:
        return []

    relationships: list[Relationship] = []
    seen: set[tuple[str, str]] = set()
    rel_id = 1

    for line in lines:
        src_box_idx = _nearest_box(line.x1, line.y1, boxes)
        dst_box_idx = _nearest_box(line.x2, line.y2, boxes)

        if src_box_idx is None or dst_box_idx is None:
            continue
        if src_box_idx == dst_box_idx:
            continue

        src_class = classes[src_box_idx]
        dst_class = classes[dst_box_idx]
        pair = (src_class.id, dst_class.id)

        if pair in seen:
            continue
        seen.add(pair)

        relationships.append(
            Relationship(
                id=f"rel_{rel_id}",
                source=src_class.id,
                destination=dst_class.id,
                type=RelationshipType.ASSOCIATION,
                multiplicity=_DEFAULT_MULTIPLICITY,
                label="",
            )
        )
        rel_id += 1

    return relationships


def _nearest_box(px: int, py: int, boxes: list[ClassBox]) -> int | None:
    """Return the index of the box whose edge is closest to point (px, py)."""
    best_idx: int | None = None
    best_dist = float("inf")

    for idx, box in enumerate(boxes):
        dist = _point_to_box_edge_dist(px, py, box)
        if dist < best_dist:
            best_dist = dist
            best_idx = idx

    # Reject if the nearest box is too far away (not actually connected)
    max_dist = max(b.w + b.h for b in boxes) if boxes else 200
    return best_idx if best_dist < max_dist else None


def _point_to_box_edge_dist(px: int, py: int, box: ClassBox) -> float:
    cx = max(box.x, min(px, box.x + box.w))
    cy = max(box.y, min(py, box.y + box.h))
    return math.hypot(px - cx, py - cy)
