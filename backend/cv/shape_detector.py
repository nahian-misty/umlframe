from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np

# Minimum size of a single compartment (the black rectangle inside a UML box)
MIN_COMPARTMENT_WIDTH = 50
MIN_COMPARTMENT_HEIGHT = 12

# Compartments of the same class box must share nearly the same left/right edges
X_ALIGN_TOLERANCE = 10

DEDUPE_THRESHOLD = 10


@dataclass
class ClassBox:
    x: int
    y: int
    w: int
    h: int
    dividers_y: list[int] = field(default_factory=list)


@dataclass
class RelationshipLine:
    x1: int
    y1: int
    x2: int
    y2: int


@dataclass
class DetectedShapes:
    class_boxes: list[ClassBox]
    lines: list[RelationshipLine]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def detect_shapes(binary: np.ndarray) -> DetectedShapes:
    boxes = _detect_class_boxes(binary)
    lines = _detect_relationship_lines(binary, boxes)
    return DetectedShapes(class_boxes=boxes, lines=lines)


# ---------------------------------------------------------------------------
# Class box detection — hole-based approach
#
# A UML class box is a rectangle with horizontal dividers. The dividers create
# black rectangular "holes" (compartments) enclosed by white border lines.
# We find these holes, group them by shared horizontal extent, and reconstruct
# the outer class box from each group.
#
# This approach is robust to relationship lines connecting boxes: even when two
# white box borders merge into one connected white structure, the compartment
# holes remain independent and are detected correctly.
# ---------------------------------------------------------------------------


def _detect_class_boxes(binary: np.ndarray) -> list[ClassBox]:
    compartments = _find_compartment_holes(binary)
    groups = _group_into_boxes(compartments)
    boxes = [b for g in groups if (b := _build_class_box(g)) is not None]
    return sorted(boxes, key=lambda b: (b.y, b.x))


def _find_compartment_holes(
    binary: np.ndarray,
) -> list[tuple[int, int, int, int]]:
    """Return bounding rects of rectangular black holes inside white line structures."""
    contours, hierarchy = cv2.findContours(binary, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    if hierarchy is None:
        return []

    holes: list[tuple[int, int, int, int]] = []
    for i, contour in enumerate(contours):
        if hierarchy[0][i][3] < 0:
            continue  # outer contour — skip; we only want holes

        peri = cv2.arcLength(contour, True)
        if peri == 0:
            continue
        approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
        if len(approx) == 4:
            x, y, w, h = cv2.boundingRect(contour)
            if w >= MIN_COMPARTMENT_WIDTH and h >= MIN_COMPARTMENT_HEIGHT:
                holes.append((x, y, w, h))

    return holes


def _group_into_boxes(
    compartments: list[tuple[int, int, int, int]],
) -> list[list[tuple[int, int, int, int]]]:
    """Group compartments that share the same left/right edges into one class box."""
    if not compartments:
        return []

    groups: list[list[tuple[int, int, int, int]]] = []
    for comp in sorted(compartments, key=lambda c: (c[0], c[1])):
        placed = False
        for group in groups:
            ref = group[0]
            if (
                abs(comp[0] - ref[0]) <= X_ALIGN_TOLERANCE
                and abs((comp[0] + comp[2]) - (ref[0] + ref[2])) <= X_ALIGN_TOLERANCE
            ):
                group.append(comp)
                placed = True
                break
        if not placed:
            groups.append([comp])

    return [g for g in groups if len(g) >= 2]


def _build_class_box(group: list[tuple[int, int, int, int]]) -> ClassBox | None:
    if not group:
        return None

    ordered = sorted(group, key=lambda c: c[1])

    min_x = min(c[0] for c in ordered)
    min_y = min(c[1] for c in ordered)
    max_x = max(c[0] + c[2] for c in ordered)
    max_y = max(c[1] + c[3] for c in ordered)

    # Dividers sit between compartments: midpoint between bottom-of-[i] and top-of-[i+1]
    dividers = [
        (ordered[i][1] + ordered[i][3] + ordered[i + 1][1]) // 2
        for i in range(len(ordered) - 1)
    ]

    return ClassBox(
        x=min_x,
        y=min_y,
        w=max_x - min_x,
        h=max_y - min_y,
        dividers_y=dividers,
    )


# ---------------------------------------------------------------------------
# Relationship line detection
# ---------------------------------------------------------------------------


def _detect_relationship_lines(
    binary: np.ndarray,
    boxes: list[ClassBox],
) -> list[RelationshipLine]:
    raw = cv2.HoughLinesP(
        binary,
        rho=1,
        theta=np.pi / 180,
        threshold=40,
        minLineLength=30,
        maxLineGap=15,
    )
    if raw is None:
        return []

    lines = []
    for segment in raw:
        x1, y1, x2, y2 = segment[0]
        mx, my = (x1 + x2) // 2, (y1 + y2) // 2
        if not any(_inside(mx, my, b) for b in boxes):
            lines.append(RelationshipLine(x1=x1, y1=y1, x2=x2, y2=y2))

    return _deduplicate(lines)


def _inside(px: int, py: int, box: ClassBox) -> bool:
    return box.x <= px <= box.x + box.w and box.y <= py <= box.y + box.h


def _deduplicate(lines: list[RelationshipLine]) -> list[RelationshipLine]:
    unique: list[RelationshipLine] = []
    for line in lines:
        if not any(
            abs(line.x1 - k.x1) < DEDUPE_THRESHOLD
            and abs(line.y1 - k.y1) < DEDUPE_THRESHOLD
            and abs(line.x2 - k.x2) < DEDUPE_THRESHOLD
            and abs(line.y2 - k.y2) < DEDUPE_THRESHOLD
            for k in unique
        ):
            unique.append(line)
    return unique
