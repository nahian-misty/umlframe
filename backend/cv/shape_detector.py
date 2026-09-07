from __future__ import annotations

import math
from dataclasses import dataclass, field

import cv2
import numpy as np

# Minimum size of a single compartment (the black rectangle inside a UML box)
MIN_COMPARTMENT_WIDTH = 50
MIN_COMPARTMENT_HEIGHT = 12

# Compartments of the same class box must share nearly the same left/right edges
X_ALIGN_TOLERANCE = 10

# Compartments of the same class box must be vertically adjacent (touching or
# separated only by a thin divider line) — bounds how large a gap can be before
# two x-aligned compartments are treated as belonging to different boxes.
Y_GAP_TOLERANCE = 20

DEDUPE_THRESHOLD = 10

# Margin (px) added around each class box when deciding whether a Hough line
# segment sits "inside" it, to absorb boundary-detection slop.
INSIDE_MARGIN = 5

# Hough accumulator vote threshold for relationship-line detection. Lower than
# a typical solid-line threshold so a short dashed stroke (few foreground px
# per dash, bridged across gaps via maxLineGap) still accumulates enough votes.
HOUGH_VOTE_THRESHOLD = 25

# Relationship line/marker classification (see relationship type table in the
# forward-pipeline CV fix plan: association/dependency use an open chevron with
# no closed marker glyph; inheritance/aggregation/composition draw a closed
# triangle or diamond glyph at one end of the line).
DASH_SAMPLE_COUNT = 40
DASH_FILL_RATIO_THRESHOLD = 0.95
MARKER_CROP_RADIUS = 48
MIN_MARKER_AREA = 20
MARKER_APPROX_EPSILON = 0.08

# A filled diamond (composition) has no hollow interior to detect via contour
# holes, and — unlike a hollow marker's isolated hole — its own outer contour
# is structurally connected to the rest of the (endless) relationship line, so
# it can never be a self-contained, non-edge-touching contour either. Instead,
# walk outward from the box edge along the line and measure the foreground's
# cross-sectional width perpendicular to it: a solid marker bulges noticeably
# wider than the line's own stroke before narrowing back down.
FILLED_BULGE_MIN_WIDTH = 10
FILLED_BULGE_SAMPLE_STEP = 2
FILLED_BULGE_MAX_HALF_WIDTH = 30


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
    dashed: bool = False
    # Closed marker glyph found at each endpoint: "triangle-hollow",
    # "diamond-hollow", "diamond-filled", or None (open chevron / no marker).
    marker_p1: str | None = None
    marker_p2: str | None = None


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


def _vertical_gap(
    comp: tuple[int, int, int, int], group: list[tuple[int, int, int, int]]
) -> int:
    """Smallest vertical gap between `comp` and any compartment already in `group`."""
    gaps = []
    for m in group:
        if comp[1] >= m[1] + m[3]:
            gaps.append(comp[1] - (m[1] + m[3]))
        elif m[1] >= comp[1] + comp[3]:
            gaps.append(m[1] - (comp[1] + comp[3]))
        else:
            gaps.append(0)  # overlapping y-range — treat as adjacent
    return min(gaps)


def _group_into_boxes(
    compartments: list[tuple[int, int, int, int]],
) -> list[list[tuple[int, int, int, int]]]:
    """Group compartments that share the same left/right edges and are vertically
    adjacent into one class box. A lone, undivided compartment is its own box."""
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
                and _vertical_gap(comp, group) <= Y_GAP_TOLERANCE
            ):
                group.append(comp)
                placed = True
                break
        if not placed:
            groups.append([comp])

    return groups


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
        threshold=HOUGH_VOTE_THRESHOLD,
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

    lines = _deduplicate(lines)
    for line in lines:
        line.dashed = _is_dashed(binary, line)
        line.marker_p1 = _classify_marker_near(binary, line.x1, line.y1, line.x2, line.y2, boxes)
        line.marker_p2 = _classify_marker_near(binary, line.x2, line.y2, line.x1, line.y1, boxes)
    return lines


def _inside(px: int, py: int, box: ClassBox) -> bool:
    # A small margin absorbs a few px of box-boundary detection slop (e.g. from
    # adaptive thresholding) so a box's own border/divider lines are never
    # mistaken for a relationship line touching the box from outside.
    return (
        box.x - INSIDE_MARGIN <= px <= box.x + box.w + INSIDE_MARGIN
        and box.y - INSIDE_MARGIN <= py <= box.y + box.h + INSIDE_MARGIN
    )


def _nearest_box_anchor(
    px: int, py: int, boxes: list[ClassBox]
) -> tuple[ClassBox, int, int] | None:
    """Nearest box to (px, py), plus the point on its boundary closest to it.

    A relationship marker is always drawn touching the box it's anchored to,
    so that boundary point — not Hough's own (possibly marker-skewed) line
    endpoint — is the reliable place to search for the marker glyph.
    """
    if not boxes:
        return None

    def edge_dist(box: ClassBox) -> float:
        cx = max(box.x, min(px, box.x + box.w))
        cy = max(box.y, min(py, box.y + box.h))
        return math.hypot(px - cx, py - cy)

    box = min(boxes, key=edge_dist)
    anchor_x = max(box.x, min(px, box.x + box.w))
    anchor_y = max(box.y, min(py, box.y + box.h))
    return box, anchor_x, anchor_y


def _classify_marker_near(
    binary: np.ndarray,
    px: int,
    py: int,
    other_x: int,
    other_y: int,
    boxes: list[ClassBox],
) -> str | None:
    found = _nearest_box_anchor(px, py, boxes)
    if found is None:
        return None
    box, anchor_x, anchor_y = found

    dx, dy = other_x - anchor_x, other_y - anchor_y
    dist = math.hypot(dx, dy)
    dir_x, dir_y = (dx / dist, dy / dist) if dist else (0.0, 0.0)

    return _classify_marker(binary, anchor_x, anchor_y, box, dir_x, dir_y)


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


# ---------------------------------------------------------------------------
# Relationship line style + endpoint marker classification
#
# The frontend draws a dashed stroke for dependency (vs. solid for the other
# four types) and a closed marker glyph — hollow triangle (inheritance) or
# hollow/filled diamond (aggregation/composition) — at one end of the line;
# association/dependency use an open two-stroke chevron that never closes into
# a fillable contour. We reuse the same hole-based contour signal already used
# for compartment detection: a "hollow" glyph rasterizes as a closed outline
# with a genuine interior hole, a filled glyph does not.
# ---------------------------------------------------------------------------


def _is_dashed(binary: np.ndarray, line: RelationshipLine) -> bool:
    """A dashed stroke has gaps along its length; sample the line's path and
    compare the fraction of foreground pixels against a solid-line baseline."""
    h, w = binary.shape
    filled = 0
    total = 0
    for t in np.linspace(0.0, 1.0, DASH_SAMPLE_COUNT):
        x = int(round(line.x1 + t * (line.x2 - line.x1)))
        y = int(round(line.y1 + t * (line.y2 - line.y1)))
        if not (0 <= x < w and 0 <= y < h):
            continue
        total += 1
        y0, y1 = max(0, y - 1), min(h, y + 2)
        x0, x1 = max(0, x - 1), min(w, x + 2)
        if np.any(binary[y0:y1, x0:x1]):
            filled += 1

    if total == 0:
        return False
    return (filled / total) < DASH_FILL_RATIO_THRESHOLD


def _contour_shape(contour) -> int | None:
    """Vertex count of a contour's polygon approximation, or None if degenerate."""
    peri = cv2.arcLength(contour, True)
    if peri == 0:
        return None
    approx = cv2.approxPolyDP(contour, MARKER_APPROX_EPSILON * peri, True)
    return len(approx)


def _touches_edge(contour, crop_w: int, crop_h: int) -> bool:
    bx, by, bw, bh = cv2.boundingRect(contour)
    return bx <= 0 or by <= 0 or bx + bw >= crop_w or by + bh >= crop_h


def _classify_marker(
    binary: np.ndarray, x: int, y: int, box: ClassBox | None, dir_x: float, dir_y: float
) -> str | None:
    """Inspect the region around a line endpoint for a closed marker glyph.

    (dir_x, dir_y) is the unit vector pointing outward from the box along the
    line, used to search for a filled marker's width bulge if no hollow glyph
    is found via contour holes.
    """
    h, w = binary.shape
    x0, x1 = max(0, x - MARKER_CROP_RADIUS), min(w, x + MARKER_CROP_RADIUS)
    y0, y1 = max(0, y - MARKER_CROP_RADIUS), min(h, y + MARKER_CROP_RADIUS)
    crop = binary[y0:y1, x0:x1].copy()
    if crop.size == 0:
        return None

    contours, hierarchy = cv2.findContours(crop, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    if hierarchy is not None:
        crop_h, crop_w = crop.shape

        def contained(i: int, contour) -> tuple[float, int] | None:
            area = cv2.contourArea(contour)
            if area < MIN_MARKER_AREA or _touches_edge(contour, crop_w, crop_h):
                return None
            vertices = _contour_shape(contour)
            if vertices is None:
                return None
            return area, vertices

        # A hollow glyph's own outline is always a top-level contour (parent=-1)
        # once the box border is far enough away, with its hollow interior as a
        # same-shaped child hole of near-identical area — so a hole match always
        # indicates a hollow glyph.
        holes = [(i, c) for i, c in enumerate(contours) if hierarchy[0][i][3] >= 0]
        best: str | None = None
        best_hole_area = 0.0
        for i, contour in holes:
            result = contained(i, contour)
            if result is None or result[0] <= best_hole_area:
                continue
            area, vertices = result
            if vertices == 3:
                best, best_hole_area = "triangle-hollow", area
            elif vertices == 4:
                best, best_hole_area = "diamond-hollow", area
        if best_hole_area:
            return best

    if _has_filled_bulge(binary, x, y, dir_x, dir_y):
        return "diamond-filled"
    return None


def _has_filled_bulge(binary: np.ndarray, x: int, y: int, dir_x: float, dir_y: float) -> bool:
    """A filled marker merges into the continuing relationship line, so it
    can't be isolated as a self-contained contour; instead, walk outward from
    the box edge and look for a point where the foreground's cross-sectional
    width (perpendicular to the line) bulges well past a plain stroke."""
    if dir_x == 0 and dir_y == 0:
        return False
    perp_x, perp_y = -dir_y, dir_x
    h, w = binary.shape

    def in_bounds(px: int, py: int) -> bool:
        return 0 <= px < w and 0 <= py < h

    def half_width(cx: float, cy: float, sign: int) -> int:
        dist = 0
        for step in range(1, FILLED_BULGE_MAX_HALF_WIDTH + 1):
            px = int(round(cx + sign * step * perp_x))
            py = int(round(cy + sign * step * perp_y))
            if not in_bounds(px, py) or not binary[py, px]:
                break
            dist = step
        return dist

    for step in range(2, MARKER_CROP_RADIUS, FILLED_BULGE_SAMPLE_STEP):
        cx, cy = x + step * dir_x, y + step * dir_y
        px, py = int(round(cx)), int(round(cy))
        if not in_bounds(px, py) or not binary[py, px]:
            continue  # a hollow marker's interior, or past the line's end
        width = half_width(cx, cy, 1) + half_width(cx, cy, -1) + 1
        if width >= FILLED_BULGE_MIN_WIDTH:
            return True
    return False
