from __future__ import annotations

import math

from backend.cv.preprocessor import preprocess_class_ink
from backend.cv.shape_detector import ClassBox, RelationshipLine, detect_shapes
from backend.ocr.extractor import extract_class_text, extract_multiplicity
from backend.parser.text_parser import (
    is_method_line,
    parse_attribute_line,
    parse_class_header,
    parse_method_line,
    parse_multiplicity,
)
from backend.schemas.uml import (
    Attribute,
    ClassKind,
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
    color, gray, binary = preprocess_class_ink(image_bytes)
    shapes = detect_shapes(binary, gray)

    classes = _build_classes(gray, shapes.class_boxes)
    relationships = _build_relationships(shapes.lines, shapes.class_boxes, classes, gray)

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
    return _reconcile_member_names(classes)


_KIND_BY_STEREOTYPE = {"interface": ClassKind.INTERFACE, "abstract": ClassKind.ABSTRACT}


def _class_from_regions(class_id: str, regions, box: ClassBox) -> UmlClass:
    name, stereotype = parse_class_header(regions.class_name)
    name = name or f"Class{class_id.split('_')[1]}"
    kind = _KIND_BY_STEREOTYPE.get(stereotype or "")
    if kind is None:
        # An italic name is UML's other way of marking an abstract class.
        kind = ClassKind.ABSTRACT if regions.italic_name else ClassKind.CLASS

    attributes: list[Attribute] = []
    methods: list[Method] = []
    # A box with only two compartments has no way to say which one holds the
    # methods, so every line is routed by its own shape: a call signature is a
    # method, anything else an attribute (and a plain line in the method
    # compartment is only noise).
    for line in regions.attribute_lines:
        if is_method_line(line):
            _append_method(methods, line)
        else:
            _append_attribute(attributes, line)
    for line in regions.method_lines:
        if is_method_line(line):
            _append_method(methods, line)

    return UmlClass(
        id=class_id,
        name=name,
        kind=kind,
        attributes=attributes,
        methods=methods,
        position=Position(x=float(box.x), y=float(box.y)),
        size=Size(width=float(box.w), height=float(box.h)),
    )


def _append_attribute(attributes: list[Attribute], line: str) -> None:
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


def _append_method(methods: list[Method], line: str) -> None:
    parsed = parse_method_line(line)
    if parsed:
        methods.append(
            Method(
                name=parsed.name,
                visibility=Visibility(parsed.visibility),
                parameters=[Parameter(name=p.name, datatype=p.datatype) for p in parsed.parameters],
                return_type=parsed.return_type,
            )
        )


def _reconcile_member_names(classes: list[UmlClass]) -> list[UmlClass]:
    """OCR often capitalises one letter of a name it has read correctly elsewhere
    ("pLayGame" beside "playGame"). Names that differ only in letter case are the
    same name: the spelling with the fewest capitals wins, since a stray capital is
    the usual misreading."""
    spellings: dict[str, str] = {}
    for cls in classes:
        for member in [*cls.attributes, *cls.methods]:
            key = member.name.lower()
            best = spellings.get(key)
            if best is None or _capitals(member.name) < _capitals(best):
                spellings[key] = member.name
    for cls in classes:
        for member in [*cls.attributes, *cls.methods]:
            member.name = spellings[member.name.lower()]
    return classes


def _capitals(name: str) -> int:
    return sum(1 for char in name if char.isupper())


# ---------------------------------------------------------------------------
# Relationship building
# ---------------------------------------------------------------------------


_DIAMOND_TYPES = {
    "diamond-hollow": RelationshipType.AGGREGATION,
    "diamond-filled": RelationshipType.COMPOSITION,
}
_TRIANGLE_MARKERS = frozenset({"triangle-hollow", "triangle-filled"})
_ARROW_MARKER = "arrow-open"


def _classify_relationship(
    line: RelationshipLine, p1_box_idx: int, p2_box_idx: int
) -> tuple[RelationshipType, int, int]:
    """Derive (type, source_box_idx, destination_box_idx) from the line's detected
    dash style and endpoint markers. Diamond markers sit at the "whole" side
    (source); a triangle sits at the parent side (destination, whether the line is
    solid -- inheritance -- or dashed -- realisation, a distinct type); an open arrowhead points at
    the destination of an association (solid) or dependency (dashed) — see
    frontend/src/components/uml/relationshipStyles.ts for the marker convention
    this mirrors."""
    if line.marker_p1 in _DIAMOND_TYPES:
        return _DIAMOND_TYPES[line.marker_p1], p1_box_idx, p2_box_idx
    if line.marker_p2 in _DIAMOND_TYPES:
        return _DIAMOND_TYPES[line.marker_p2], p2_box_idx, p1_box_idx

    triangle_type = RelationshipType.REALIZATION if line.dashed else RelationshipType.INHERITANCE
    if line.marker_p1 in _TRIANGLE_MARKERS:
        return triangle_type, p2_box_idx, p1_box_idx
    if line.marker_p2 in _TRIANGLE_MARKERS:
        return triangle_type, p1_box_idx, p2_box_idx

    rel_type = RelationshipType.DEPENDENCY if line.dashed else RelationshipType.ASSOCIATION
    if line.marker_p1 == _ARROW_MARKER and line.marker_p2 != _ARROW_MARKER:
        return rel_type, p2_box_idx, p1_box_idx
    return rel_type, p1_box_idx, p2_box_idx


# Only these carry quantities; a generalisation or dependency is not counted.
_COUNTED_TYPES = frozenset(
    {RelationshipType.ASSOCIATION, RelationshipType.AGGREGATION, RelationshipType.COMPOSITION}
)


def _read_multiplicity(gray, rect: tuple[int, int, int, int] | None) -> str:
    if rect is None:
        return _DEFAULT_MULTIPLICITY.source
    return parse_multiplicity(extract_multiplicity(gray, rect)) or _DEFAULT_MULTIPLICITY.source


def _multiplicity_for(
    line: RelationshipLine, gray, rel_type: RelationshipType, src_idx: int
) -> Multiplicity:
    """The label beside each end of the line, assigned to the relationship's source
    and destination ends."""
    if rel_type not in _COUNTED_TYPES:
        return _DEFAULT_MULTIPLICITY
    p1 = _read_multiplicity(gray, line.label_p1)
    p2 = _read_multiplicity(gray, line.label_p2)
    source_is_p1 = line.box_p1 == src_idx
    return Multiplicity(
        source=p1 if source_is_p1 else p2, destination=p2 if source_is_p1 else p1
    )


def _build_relationships(
    lines: list[RelationshipLine],
    boxes: list[ClassBox],
    classes: list[UmlClass],
    gray=None,
) -> list[Relationship]:
    if not lines or len(classes) < 2:
        return []

    relationships: list[Relationship] = []
    seen: set[tuple[str, str]] = set()
    rel_id = 1

    for line in lines:
        p1_box_idx = line.box_p1 if line.box_p1 is not None else _nearest_box(line.x1, line.y1, boxes)
        p2_box_idx = line.box_p2 if line.box_p2 is not None else _nearest_box(line.x2, line.y2, boxes)

        if p1_box_idx is None or p2_box_idx is None:
            continue
        if p1_box_idx == p2_box_idx:
            continue

        rel_type, src_idx, dst_idx = _classify_relationship(line, p1_box_idx, p2_box_idx)

        src_class = classes[src_idx]
        dst_class = classes[dst_idx]
        pair = (src_class.id, dst_class.id)

        if pair in seen:
            continue
        seen.add(pair)

        if rel_type == RelationshipType.REALIZATION:
            dst_class.kind = ClassKind.INTERFACE  # a dashed triangle is a realisation
        relationships.append(
            Relationship(
                id=f"rel_{rel_id}",
                source=src_class.id,
                destination=dst_class.id,
                type=rel_type,
                multiplicity=(
                    _multiplicity_for(line, gray, rel_type, src_idx)
                    if gray is not None
                    else _DEFAULT_MULTIPLICITY
                ),
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
