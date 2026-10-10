from __future__ import annotations

import math
from dataclasses import dataclass, field

import cv2
import numpy as np

from backend.cv.connector_tracer import Rect, TracedLine, split_crossing_group

# A compartment is at least this tall (px) between its two rules.
MIN_COMPARTMENT_HEIGHT = 8

# A box edge or divider is a straight stroke at least this long and at most this thick.
# Horizontals must be longer: a row of bold text can pass for a short horizontal.
MIN_RULE_LENGTH = 45
MIN_SIDE_LENGTH = 25
MAX_STROKE_THICKNESS = 7

# Rules of one box share their left/right ends to within this many px (rounded
# corners shorten the top and bottom rules relative to the dividers).
EXTENT_TOLERANCE = 14
# A box side is looked for within this many px of the rules' end, ignoring the
# corner rows, and must cover at least this fraction of the rows between rules.
SIDE_SEARCH_RADIUS = 3
CORNER_SKIP = 2
MIN_SIDE_COVERAGE = 0.85

# Relationship detection.
# Ink within this many px of a box edge is erased with the box, so a connector's
# own end is not confused with the box outline.
BOX_ERASE_MARGIN = 1
# Pieces of ink closer than this belong to one connector (the gap between dashes).
DASH_BRIDGE = 13
MIN_CONNECTOR_PIXELS = 20
MIN_FUSED_ANCHORS = 3
# A connector group touches a box when it comes this close to its border.
TOUCH_DISTANCE = 8
# Ink this close to the touching point decides which way the connector leaves the box.
ANCHOR_CLUSTER_RADIUS = 14
# A connector is straight when this fraction of its ink lies within this many px
# of its principal axis.
STRAIGHT_TOLERANCE = 6
STRAIGHT_FRACTION = 0.9
# A dashed connector has no piece longer than this fraction of the box-to-box span.
DASHED_PIECE_RATIO = 0.6
MIN_DASH_PIECES = 3
# Grey-level dash test: skip the marker ends, and call it dashed when the level
# lifts this far back towards the background in at least MIN_DASH_GAPS places.
MIN_DASH_SPAN = 30
DASH_MARGIN = 0.15
MIN_DASH_CONTRAST = 40
DASH_GAP_LEVEL = 0.5
MIN_DASH_GAPS = 3

# A bus glyph's own box faces away from the average direction of the others (cosine
# at most this).
LONE_SIDE_MAX_COSINE = -0.3

# Ink beside a solid glyph (outside SPLAY_GAP px of it, within SPLAY_RADIUS px of its
# centre) is "splayed" when its spread across its main direction exceeds this ratio.
SPLAY_GAP = 9
SPLAY_RADIUS = 30
MIN_SPLAY_PIXELS = 8
SPLAY_RATIO = 0.25
LARGE_GLYPH_AREA = 300

# Gap (px) closed in a glyph outline before it is filled in, within SEAL_REACH px
# of a box (where erasing the box opens the outline).
OUTLINE_SEAL = 5
SEAL_REACH = 8

# Text beside a line end: glyph-sized ink pieces within LABEL_RADIUS of the end,
# grouped when they lie within GLYPH_GAP of each other.
MIN_GLYPH_AREA = 4
MAX_GLYPH_SIDE = 16
LABEL_RADIUS = 36
GLYPH_GAP = 5

# End-marker analysis. The connector's width is measured every px along it, for
# MARKER_SEARCH_LENGTH px out from the box.
MARKER_SEARCH_LENGTH = 70
MARKER_HALF_WIDTH = 24
MARKER_MAX_WIDTH = 30
# Start measuring this far behind the anchor: it is the ink nearest the box, which
# for an open arrowhead is an arm tip, not the tip of the arrow on the axis.
MARKER_LEAD_IN = 8
# A triangle or diamond is a solid blob wider than any stroke (opening with this
# kernel removes lines), at least this large, within MARKER_MAX_GAP px of its box.
BLOB_KERNEL = 5
MIN_BLOB_AREA = 60
MIN_BLOB_WIDTH = 7
MARKER_MAX_GAP = 60
RADIAL_SAMPLES = 64
# A hollow glyph shows at least this many blank interior pixels once filled in.
MIN_HOLE_PIXELS = 3
# An open arrowhead spreads this much wider than the line, for at least
# MIN_ARROW_LENGTH px, within ARROW_REACH px of the box.
ARROW_REACH = 16
ARROW_SPREAD = 3
MIN_ARROW_LENGTH = 3
MAX_LINE_WIDTH = 6
DEFAULT_LINE_WIDTH = 3

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
    # Index (into DetectedShapes.class_boxes) of the box each end meets.
    box_p1: int | None = None
    box_p2: int | None = None
    # Bounding rect (x, y, w, h) of the small text written beside each end -- a
    # multiplicity such as "1" or "0..*" -- when there is any.
    label_p1: tuple[int, int, int, int] | None = None
    label_p2: tuple[int, int, int, int] | None = None


@dataclass
class DetectedShapes:
    class_boxes: list[ClassBox]
    lines: list[RelationshipLine]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def detect_shapes(binary: np.ndarray, gray: np.ndarray | None = None) -> DetectedShapes:
    """Class boxes and the relationship lines between them. `gray`, when given, lets
    dashed lines be recognised even where binarising has closed their gaps."""
    boxes = _detect_class_boxes(binary)
    lines = _detect_relationship_lines(binary, boxes, gray)
    return DetectedShapes(class_boxes=boxes, lines=lines)


# ---------------------------------------------------------------------------
# Class box detection — stacked horizontal rules
#
# A UML class box is a rectangle whose compartments are separated by horizontal
# rules: the top edge, each divider and the bottom edge are all long thin
# horizontals of (nearly) the same extent, joined by two vertical sides. Text is
# never that long and thin, and a diagonal arrow or an elbow connector does not
# line up with a box's extent, so the boxes are read straight from those rules.
# ---------------------------------------------------------------------------


@dataclass
class _Rule:
    x0: int
    x1: int
    y: int


def _detect_class_boxes(binary: np.ndarray) -> list[ClassBox]:
    rules = _horizontal_rules(binary)
    sides = _vertical_strokes(binary)
    boxes = [b for chain in _stack_rules(rules, sides) if (b := _build_class_box(chain))]
    return sorted(boxes, key=lambda b: (b.y, b.x))


def _horizontal_rules(binary: np.ndarray) -> list[_Rule]:
    opened = cv2.morphologyEx(
        binary, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (MIN_RULE_LENGTH, 1))
    )
    count, _, stats, _ = cv2.connectedComponentsWithStats(opened, connectivity=8)
    rules = []
    for i in range(1, count):
        x, y, w, h = (int(stats[i, k]) for k in range(4))
        if h <= MAX_STROKE_THICKNESS:
            rules.append(_Rule(x0=x, x1=x + w, y=y + h // 2))
    return sorted(rules, key=lambda r: (r.y, r.x0))


def _vertical_strokes(binary: np.ndarray) -> np.ndarray:
    return np.asarray(
        cv2.morphologyEx(
            binary, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, MIN_SIDE_LENGTH))
        ),
        dtype=np.uint8,
    )


def _stack_rules(rules: list[_Rule], sides: np.ndarray) -> list[list[_Rule]]:
    """Chain rules, top to bottom, that share an extent and are joined by sides."""
    chains: list[list[_Rule]] = []
    for rule in rules:
        best: list[_Rule] | None = None
        for chain in chains:
            last = chain[-1]
            if (
                _same_extent(last, rule)
                and rule.y - last.y >= MIN_COMPARTMENT_HEIGHT
                and _joined_by_sides(sides, last, rule)
                and (best is None or best[-1].y < last.y)
            ):
                best = chain
        if best is not None:
            best.append(rule)
        else:
            chains.append([rule])
    return [chain for chain in chains if len(chain) >= 2]


def _same_extent(a: _Rule, b: _Rule) -> bool:
    return abs(a.x0 - b.x0) <= EXTENT_TOLERANCE and abs(a.x1 - b.x1) <= EXTENT_TOLERANCE


def _joined_by_sides(sides: np.ndarray, upper: _Rule, lower: _Rule) -> bool:
    """Both box sides run unbroken between the two rules. A rounded corner pulls a
    top or bottom rule in from the side, so the side is looked for at the outermost
    left/right of the two rules."""
    x0, x1 = min(upper.x0, lower.x0), max(upper.x1, lower.x1)
    return all(
        _column_coverage(sides, x, upper.y, lower.y) >= MIN_SIDE_COVERAGE for x in (x0, x1 - 1)
    )


def _column_coverage(sides: np.ndarray, x: int, y0: int, y1: int) -> float:
    left, right = max(0, x - SIDE_SEARCH_RADIUS), min(sides.shape[1], x + SIDE_SEARCH_RADIUS + 1)
    rows = sides[y0 + CORNER_SKIP : y1 - CORNER_SKIP + 1, left:right]
    if rows.size == 0:
        return 1.0
    return float(np.mean(rows.any(axis=1)))


def _build_class_box(chain: list[_Rule]) -> ClassBox | None:
    x0 = min(r.x0 for r in chain)
    x1 = max(r.x1 for r in chain)
    top, bottom = chain[0].y, chain[-1].y
    return ClassBox(
        x=x0,
        y=top,
        w=x1 - x0,
        h=bottom - top,
        dividers_y=[r.y for r in chain[1:-1]],
    )


# ---------------------------------------------------------------------------
# Relationship detection
#
# With every class box erased, what ink remains is the connectors (plus their
# end markers and any multiplicity text). Pieces within a dash gap of each other
# belong to one connector, so a dashed line is a single group. A group touching
# two boxes is one relationship; one touching several (a shared "bus" fanning
# out to the children) is one relationship per spoke, the box carrying the end
# marker being the hub.
# ---------------------------------------------------------------------------


@dataclass
class _Anchor:
    box: int
    x: int  # where the connector meets the box
    y: int
    dir_x: float  # unit vector pointing from the box along the connector
    dir_y: float
    ink: tuple[int, int] = (0, 0)  # the connector's ink pixel nearest the box
    marker: str | None = None


def _detect_relationship_lines(
    binary: np.ndarray,
    boxes: list[ClassBox],
    gray: np.ndarray | None = None,
) -> list[RelationshipLine]:
    if len(boxes) < 2:
        return []

    ink = binary.copy()
    for box in boxes:
        ink[
            max(0, box.y - BOX_ERASE_MARGIN) : box.y + box.h + BOX_ERASE_MARGIN + 1,
            max(0, box.x - BOX_ERASE_MARGIN) : box.x + box.w + BOX_ERASE_MARGIN + 1,
        ] = 0

    grow = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (DASH_BRIDGE, DASH_BRIDGE))
    count, groups = cv2.connectedComponents(cv2.dilate(ink, grow), connectivity=8)

    lines: list[RelationshipLine] = []
    claimed = np.zeros_like(ink)
    near_boxes = _near_boxes(ink.shape, boxes)
    rects = [(box.x, box.y, box.w, box.h) for box in boxes]
    for group in range(1, count):
        group_mask = np.where((groups == group) & (ink > 0), 255, 0).astype(np.uint8)
        if int(np.count_nonzero(group_mask)) < MIN_CONNECTOR_PIXELS:
            continue
        for traced in _split_fused(group_mask, boxes, rects, near_boxes):
            lines.extend(_lines_in_group(traced, boxes, near_boxes, gray, claimed))
    _attach_end_labels(lines, np.where(claimed > 0, 0, ink).astype(np.uint8))
    return lines


def _split_fused(
    mask: np.ndarray, boxes: list[ClassBox], rects: list[Rect], near_boxes: np.ndarray
) -> list[TracedLine]:
    """The individual lines of a group, when it touches enough boxes to be several lines
    crossing each other; otherwise the group itself."""
    anchors = _anchors(mask, boxes)
    if len(anchors) < MIN_FUSED_ANCHORS or _is_shared_bus(mask, anchors, boxes, near_boxes):
        return [TracedLine(mask, dashed=None)]
    split = split_crossing_group(mask, _fill_closed_shapes(mask, near_boxes), rects)
    if split and all(_is_marked_line(line.mask, boxes, near_boxes) for line in split):
        return split
    return [TracedLine(mask, dashed=None)]


def _mark_anchors(
    mask: np.ndarray, anchors: list[_Anchor], boxes: list[ClassBox], near_boxes: np.ndarray
) -> None:
    """Set each anchor's end marker: a closed glyph, an open arrowhead, or none."""
    closed = _closed_markers(mask, anchors, boxes, near_boxes)
    for index, anchor in enumerate(anchors):
        anchor.marker = closed.get(index)
        if anchor.marker is None and _has_open_arrowhead(_own_piece(mask, anchor), anchor):
            anchor.marker = "arrow-open"


def _is_marked_line(mask: np.ndarray, boxes: list[ClassBox], near_boxes: np.ndarray) -> bool:
    """Whether a traced line joins two boxes and has a marker at one end. The editor draws
    every relationship with one, so an unmarked "line" is a bus bar run between two
    children, not a relationship."""
    anchors = _anchors(mask, boxes)
    if len(anchors) != 2:
        return False
    _mark_anchors(mask, anchors, boxes, near_boxes)
    return any(anchor.marker for anchor in anchors)


def _is_shared_bus(
    mask: np.ndarray, anchors: list[_Anchor], boxes: list[ClassBox], near_boxes: np.ndarray
) -> bool:
    """One box carries the group's only marker and no other end has an arrowhead: the
    children of a generalisation drawn off a single shared bar. Crossing lines, by
    contrast, each bring a marker of their own."""
    if len(_closed_markers(mask, anchors, boxes, near_boxes)) != 1:
        return False
    return not any(_has_open_arrowhead(_own_piece(mask, anchor), anchor) for anchor in anchors)


def _lines_in_group(
    traced: TracedLine,
    boxes: list[ClassBox],
    near_boxes: np.ndarray,
    gray: np.ndarray | None,
    claimed: np.ndarray,
) -> list[RelationshipLine]:
    mask = traced.mask
    anchors = _anchors(mask, boxes)
    if len(anchors) < 2:
        return []
    if len(anchors) == 2:
        _orient_straight(anchors, mask)
    _mark_anchors(mask, anchors, boxes, near_boxes)
    new_lines = _lines_for(anchors, mask, gray, traced.dashed)
    claimed |= mask if any(line.dashed for line in new_lines) else _connector_ink(mask, anchors)
    return new_lines


def _connector_ink(mask: np.ndarray, anchors: list[_Anchor]) -> np.ndarray:
    """The ink of a group that is connected to its boxes: every piece an anchor touches."""
    claimed = np.zeros_like(mask)
    for anchor in anchors:
        claimed |= _own_piece(mask, anchor)
    return claimed


def _anchors(mask: np.ndarray, boxes: list[ClassBox]) -> list[_Anchor]:
    """Where a connector group meets each box it touches (one anchor per box)."""
    ys, xs = np.nonzero(mask)
    anchors: list[_Anchor] = []
    for index, box in enumerate(boxes):
        dx = np.maximum(np.maximum(box.x - xs, xs - (box.x + box.w)), 0)
        dy = np.maximum(np.maximum(box.y - ys, ys - (box.y + box.h)), 0)
        distance = np.hypot(dx, dy)
        nearest = int(np.argmin(distance))
        if distance[nearest] > TOUCH_DISTANCE:
            continue
        px, py = int(xs[nearest]), int(ys[nearest])
        ax = max(box.x, min(px, box.x + box.w))
        ay = max(box.y, min(py, box.y + box.h))
        anchors.append(_Anchor(index, ax, ay, *_side_normal(px, py, box), ink=(px, py)))
    return anchors


def _side_normal(px: int, py: int, box: ClassBox) -> tuple[float, float]:
    """Unit vector pointing out of the box side nearest to (px, py)."""
    gaps = {
        (0.0, -1.0): abs(py - box.y),
        (0.0, 1.0): abs(py - (box.y + box.h)),
        (-1.0, 0.0): abs(px - box.x),
        (1.0, 0.0): abs(px - (box.x + box.w)),
    }
    return min(gaps, key=lambda normal: gaps[normal])


def _orient_straight(anchors: list[_Anchor], mask: np.ndarray) -> None:
    """A connector that runs straight from one box to the other (it may be diagonal)
    leaves each box along that line, not along the box side's normal."""
    ys, xs = np.nonzero(mask)
    points = np.stack([xs, ys], axis=1).astype(np.float64)
    centre = points.mean(axis=0)
    _, _, axes = np.linalg.svd(points - centre, full_matrices=False)
    axis = axes[0]
    off_line = np.abs((points - centre) @ np.array([-axis[1], axis[0]]))
    if np.mean(off_line <= STRAIGHT_TOLERANCE) < STRAIGHT_FRACTION:
        return
    for anchor in anchors:
        away = centre - np.array([anchor.x, anchor.y], dtype=np.float64)
        along = float(axis @ away)
        sign = 1.0 if along >= 0 else -1.0
        anchor.dir_x, anchor.dir_y = float(sign * axis[0]), float(sign * axis[1])
        # Measure from the point of the axis nearest the ink, not an arm tip.
        anchor.x = int(round(centre[0] - along * axis[0]))
        anchor.y = int(round(centre[1] - along * axis[1]))


def _own_piece(mask: np.ndarray, anchor: _Anchor) -> np.ndarray:
    """The connected piece of ink at the anchor: the line and its end marker, and
    not a multiplicity label sitting beside it."""
    count, labels = cv2.connectedComponents(mask, connectivity=8)
    label = labels[anchor.ink[1], anchor.ink[0]]
    return np.where(labels == label, 255, 0).astype(np.uint8) if label else mask


def _fill_closed_shapes(mask: np.ndarray, near_boxes: np.ndarray | None = None) -> np.ndarray:
    """The mask with every closed outline (a hollow triangle or diamond) filled in.

    Erasing a box takes a pixel or two off a tip that touches it, leaving a small
    gap in the outline; gaps are closed, but only beside a box, so that an open
    arrowhead further along a line is not sealed into a solid shape."""
    filled_source = mask
    if near_boxes is not None:
        seal = cv2.getStructuringElement(cv2.MORPH_RECT, (OUTLINE_SEAL, OUTLINE_SEAL))
        closed = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, seal)
        filled_source = np.where(near_boxes > 0, closed, mask).astype(np.uint8)
    contours, _ = cv2.findContours(filled_source, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    filled = np.zeros_like(mask)
    cv2.drawContours(filled, contours, -1, 255, thickness=cv2.FILLED)
    return filled


def _near_boxes(shape: tuple[int, int], boxes: list[ClassBox]) -> np.ndarray:
    """A mask of the strip around every box where outline gaps may be sealed."""
    near = np.zeros(shape, dtype=np.uint8)
    for box in boxes:
        near[
            max(0, box.y - SEAL_REACH) : box.y + box.h + SEAL_REACH + 1,
            max(0, box.x - SEAL_REACH) : box.x + box.w + SEAL_REACH + 1,
        ] = 255
    return near


def _cross_section(
    mask: np.ndarray, anchor: _Anchor, along: int
) -> tuple[int, int]:
    """(contiguous width, extent) of the ink across the connector, `along` px from
    the anchor. Contiguous width is the run through the axis; extent spans the
    outermost ink, so an open arrowhead (two thin arms) has a wide extent but a
    narrow run."""
    h, w = mask.shape
    perp_x, perp_y = -anchor.dir_y, anchor.dir_x
    cx = anchor.x + anchor.dir_x * along
    cy = anchor.y + anchor.dir_y * along

    def hit(offset: int) -> bool:
        x, y = int(round(cx + perp_x * offset)), int(round(cy + perp_y * offset))
        return 0 <= x < w and 0 <= y < h and bool(mask[y, x])

    offsets = [o for o in range(-MARKER_HALF_WIDTH, MARKER_HALF_WIDTH + 1) if hit(o)]
    if not offsets:
        return 0, 0
    extent = offsets[-1] - offsets[0] + 1
    # contiguous run closest to the axis
    run_start = min(offsets, key=abs)
    low = high = run_start
    while hit(low - 1) and low > -MARKER_HALF_WIDTH:
        low -= 1
    while hit(high + 1) and high < MARKER_HALF_WIDTH:
        high += 1
    return high - low + 1, extent


def _closed_markers(
    mask: np.ndarray, anchors: list[_Anchor], boxes: list[ClassBox], near_boxes: np.ndarray
) -> dict[int, str]:
    """Triangle and diamond glyphs in a connector group, keyed by the anchor they
    belong to. A glyph is a solid blob (once hollow outlines are filled in) wider
    than any line, found by opening the strokes away, and belongs to the nearest
    box -- its orientation is not trusted, as hand-drawn arrowheads are often
    turned away from the line."""
    filled = _fill_closed_shapes(mask, near_boxes)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (BLOB_KERNEL, BLOB_KERNEL))
    count, labels = cv2.connectedComponents(
        cv2.morphologyEx(filled, cv2.MORPH_OPEN, kernel), connectivity=8
    )
    found: dict[int, tuple[float, str]] = {}
    for label in range(1, count):
        blob = np.where(labels == label, 255, 0).astype(np.uint8)
        shape = _blob_shape(blob)
        if shape is None:
            continue
        owner, gap = _glyph_owner(blob, shape, anchors, boxes)
        if owner is None or gap > MARKER_MAX_GAP:
            continue
        ys, xs = np.nonzero(blob)
        hollow = _is_hollow(mask, filled, xs, ys)
        if not hollow and xs.size < LARGE_GLYPH_AREA and _has_splayed_arms(mask, blob):
            continue  # the core of a heavy open arrowhead, not a solid diamond
        if shape == "triangle" and not hollow:
            # No drawn triangle is solid (inheritance is hollow): a solid one is a
            # heavy open arrowhead whose arms have run together.
            continue
        marker = f"{shape}-{'hollow' if hollow else 'filled'}"
        if owner not in found or gap < found[owner][0]:
            found[owner] = (gap, marker)
    return {index: marker for index, (_, marker) in found.items()}


def _glyph_owner(
    blob: np.ndarray, shape: str, anchors: list[_Anchor], boxes: list[ClassBox]
) -> tuple[int | None, float]:
    """Index of the anchor whose box the glyph belongs to, and its distance.

    Normally the nearest box. Where several boxes share one connector (a bus), a
    triangle belongs to the one box that lies on the opposite side of it from all
    the others: the children fan out from its base, the parent sits at its tip."""
    ys, xs = np.nonzero(blob)
    distances = [_distance_to_box(xs, ys, boxes[anchor.box]) for anchor in anchors]
    candidates = list(range(len(anchors)))
    if len(anchors) > 2 and shape == "triangle":
        lone = _lone_side_anchors(xs, ys, anchors)
        candidates = lone or candidates
    owner = min(candidates, key=lambda index: distances[index], default=None)
    return (owner, distances[owner]) if owner is not None else (None, 0.0)


def _lone_side_anchors(xs: np.ndarray, ys: np.ndarray, anchors: list[_Anchor]) -> list[int]:
    """Anchors that lie away from the glyph in a direction roughly opposite to the
    average direction of all the other anchors."""
    centre = np.array([xs.mean(), ys.mean()])
    unit = []
    for anchor in anchors:
        offset = np.array(anchor.ink, dtype=np.float64) - centre
        unit.append(offset / max(float(np.hypot(*offset)), 1e-9))
    lone = []
    for index, vector in enumerate(unit):
        others = np.mean([u for i, u in enumerate(unit) if i != index], axis=0)
        if float(vector @ others) <= LONE_SIDE_MAX_COSINE:
            lone.append(index)
    return lone


def _has_splayed_arms(mask: np.ndarray, blob: np.ndarray) -> bool:
    """Whether ink around a solid-looking glyph spreads sideways beyond it. A real
    solid diamond has only the straight line leaving it; a heavy open arrowhead
    (whose arms fused into a core) has two arms diverging from the core."""
    grown = cv2.dilate(blob, np.ones((SPLAY_GAP, SPLAY_GAP), np.uint8))
    ys, xs = np.nonzero(blob)
    cx, cy = xs.mean(), ys.mean()
    outside = np.where((mask > 0) & (grown == 0), 255, 0).astype(np.uint8)
    # Only ink actually joined to the glyph counts; a nearby label or another line does not.
    touching = cv2.dilate(grown, np.ones((3, 3), np.uint8))
    count, labels = cv2.connectedComponents(outside, connectivity=8)
    joined = {int(v) for v in np.unique(labels[(touching > 0) & (outside > 0)]) if v}
    py, px = np.nonzero(np.isin(labels, list(joined)))
    near = np.hypot(px - cx, py - cy) <= SPLAY_RADIUS
    if np.count_nonzero(near) < MIN_SPLAY_PIXELS:
        return False
    points = np.stack([px[near], py[near]], axis=1).astype(np.float64)
    singular = np.linalg.svd(points - points.mean(axis=0), compute_uv=False)
    return bool(singular[0] > 0 and singular[1] / singular[0] > SPLAY_RATIO)


def _distance_to_box(xs: np.ndarray, ys: np.ndarray, box: ClassBox) -> float:
    dx = np.maximum(np.maximum(box.x - xs, xs - (box.x + box.w)), 0)
    dy = np.maximum(np.maximum(box.y - ys, ys - (box.y + box.h)), 0)
    return float(np.hypot(dx, dy).min())


def _blob_shape(blob: np.ndarray) -> str | None:
    """"triangle" or "diamond", whatever the glyph's orientation. The distance from
    the glyph's centre to its outline, taken once round, repeats three times for a
    triangle and twice (or four times) for a diamond."""
    contours, _ = cv2.findContours(blob, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    contour = max(contours, key=cv2.contourArea)
    if cv2.contourArea(contour) < MIN_BLOB_AREA:
        return None
    (_, _), (rect_w, rect_h), _ = cv2.minAreaRect(contour)
    if min(rect_w, rect_h) < MIN_BLOB_WIDTH:
        return None
    moments = cv2.moments(blob, binaryImage=True)
    offsets = contour[:, 0, :].astype(np.float64) - np.array(
        [moments["m10"] / moments["m00"], moments["m01"] / moments["m00"]]
    )
    angles = np.arctan2(offsets[:, 1], offsets[:, 0])
    order = np.argsort(angles)
    samples = np.linspace(-np.pi, np.pi, RADIAL_SAMPLES, endpoint=False)
    radius = np.interp(
        samples, angles[order], np.hypot(offsets[:, 0], offsets[:, 1])[order], period=2 * np.pi
    )
    harmonics = np.abs(np.fft.rfft(radius))
    triangle, diamond = harmonics[3], max(harmonics[2], harmonics[4])
    return "triangle" if triangle > diamond else "diamond"


def _is_hollow(piece: np.ndarray, filled: np.ndarray, xs: np.ndarray, ys: np.ndarray) -> bool:
    """Whether the glyph is an outline: filling it in added blank interior."""
    x0, x1, y0, y1 = xs.min() - 1, xs.max() + 2, ys.min() - 1, ys.max() + 2
    interior = (filled[y0:y1, x0:x1] > 0) & (piece[y0:y1, x0:x1] == 0)
    return int(np.count_nonzero(interior)) >= MIN_HOLE_PIXELS


def _has_open_arrowhead(piece: np.ndarray, anchor: _Anchor) -> bool:
    """An open "V" arrowhead: ink spreads wider than the line right at the box."""
    widths = []
    runs = []
    for along in range(-MARKER_LEAD_IN, ARROW_REACH):
        run, extent = _cross_section(piece, anchor, along)
        runs.append(run)
        widths.append(extent)
    line_width = _line_width(runs)
    spread = [w for w in widths if line_width + ARROW_SPREAD <= w <= MARKER_MAX_WIDTH]
    return len(spread) >= MIN_ARROW_LENGTH


def _line_width(filled_runs: list[int]) -> int:
    thin = [r for r in filled_runs if 0 < r <= MAX_LINE_WIDTH]
    return int(np.median(thin)) if thin else DEFAULT_LINE_WIDTH


def _lines_for(
    anchors: list[_Anchor], mask: np.ndarray, gray: np.ndarray | None, dashed: bool | None = None
) -> list[RelationshipLine]:
    """One RelationshipLine per spoke: the whole group when it joins two boxes, or
    from the hub (the end carrying a marker) out to each other box."""
    if len(anchors) == 2:
        a, b = anchors
        known = _is_dashed(mask, a, b, gray) if dashed is None else dashed
        return [_line(a, b, dashed=known)]
    hub = next((a for a in anchors if a.marker not in (None, "arrow-open")), None)
    if hub is None:
        hub = anchors[0]
    return [_line(hub, other, dashed=False) for other in anchors if other is not hub]


def _line(a: _Anchor, b: _Anchor, dashed: bool) -> RelationshipLine:
    return RelationshipLine(
        x1=a.x,
        y1=a.y,
        x2=b.x,
        y2=b.y,
        dashed=dashed,
        marker_p1=a.marker,
        marker_p2=b.marker,
        box_p1=a.box,
        box_p2=b.box,
    )


def _is_dashed(mask: np.ndarray, a: _Anchor, b: _Anchor, gray: np.ndarray | None) -> bool:
    """A dashed connector is a row of short separate strokes: no single piece spans
    most of the way between the boxes, or the line's own grey level keeps breaking
    (binarising can close gaps that the grey image still shows)."""
    span = math.hypot(b.x - a.x, b.y - a.y)
    count, _, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    longest = max(
        (
            math.hypot(stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT])
            for i in range(1, count)
        ),
        default=0.0,
    )
    if count > MIN_DASH_PIECES + 1 and longest < DASHED_PIECE_RATIO * span:
        return True
    return gray is not None and _grey_level_breaks(gray, a, b)


def _grey_level_breaks(gray: np.ndarray, a: _Anchor, b: _Anchor) -> bool:
    """Whether the grey level along the straight line from a to b repeatedly lifts
    back towards the background (the gaps between dashes)."""
    span = math.hypot(b.x - a.x, b.y - a.y)
    if span < MIN_DASH_SPAN:
        return False
    h, w = gray.shape
    perp_x, perp_y = -(b.y - a.y) / span, (b.x - a.x) / span
    levels = []
    for step in np.linspace(DASH_MARGIN, 1.0 - DASH_MARGIN, int(span)):
        x, y = a.x + step * (b.x - a.x), a.y + step * (b.y - a.y)
        # Darkest across the stroke only: a window along it would fill the gaps.
        across = [
            gray[py, px]
            for t in (-1, 0, 1)
            if 0 <= (px := int(round(x + t * perp_x))) < w
            and 0 <= (py := int(round(y + t * perp_y))) < h
        ]
        levels.append(float(min(across)) if across else 255.0)
    ink_level = float(np.percentile(levels, 10))
    background = float(np.median(gray))
    if background - ink_level < MIN_DASH_CONTRAST:
        return False
    gap = np.array(levels) > ink_level + DASH_GAP_LEVEL * (background - ink_level)
    runs = int(np.count_nonzero(gap[1:] & ~gap[:-1])) + int(gap[0])
    return runs >= MIN_DASH_GAPS


# ---------------------------------------------------------------------------
# Text beside the ends of a line (multiplicities)
# ---------------------------------------------------------------------------


def _attach_end_labels(lines: list[RelationshipLine], loose_ink: np.ndarray) -> None:
    """Find the small text written near each end of a solid line. `loose_ink` is the
    ink that belongs to no connector; its glyph-sized pieces are text, and the
    cluster of them nearest an end is that end's label."""
    count, _, stats, _ = cv2.connectedComponentsWithStats(loose_ink, connectivity=8)
    pieces = []
    for index in range(1, count):
        x, y, w, h, area = (int(v) for v in stats[index])
        if area >= MIN_GLYPH_AREA and w <= MAX_GLYPH_SIDE and h <= MAX_GLYPH_SIDE:
            pieces.append((x, y, w, h))
    for line in lines:
        if not line.dashed:
            line.label_p1 = _nearest_cluster(pieces, line.x1, line.y1)
            line.label_p2 = _nearest_cluster(pieces, line.x2, line.y2)


def _nearest_cluster(
    pieces: list[tuple[int, int, int, int]], px: int, py: int
) -> tuple[int, int, int, int] | None:
    near = [p for p in pieces if _piece_distance(p, px, py) <= LABEL_RADIUS]
    if not near:
        return None
    seed = min(near, key=lambda p: _piece_distance(p, px, py))
    cluster = [seed]
    grew = True
    while grew:
        grew = False
        for piece in near:
            if piece not in cluster and any(_pieces_touch(piece, other) for other in cluster):
                cluster.append(piece)
                grew = True
    x0 = min(p[0] for p in cluster)
    y0 = min(p[1] for p in cluster)
    x1 = max(p[0] + p[2] for p in cluster)
    y1 = max(p[1] + p[3] for p in cluster)
    return x0, y0, x1 - x0, y1 - y0


def _piece_distance(piece: tuple[int, int, int, int], px: int, py: int) -> float:
    x, y, w, h = piece
    return math.hypot(max(x - px, 0, px - (x + w)), max(y - py, 0, py - (y + h)))


def _pieces_touch(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> bool:
    gap_x = max(a[0] - (b[0] + b[2]), b[0] - (a[0] + a[2]), 0)
    gap_y = max(a[1] - (b[1] + b[3]), b[1] - (a[1] + a[3]), 0)
    return gap_x <= GLYPH_GAP and gap_y <= GLYPH_GAP
