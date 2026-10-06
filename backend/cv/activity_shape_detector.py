from __future__ import annotations

import itertools
import math
from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

import cv2
import numpy as np
import numpy.typing as npt

# Single-channel image buffer. Contour/hierarchy arrays from cv2 carry a union
# dtype its stubs don't pin down, so they stay `Any` at the helper boundary.
BinaryImage = npt.NDArray[np.uint8]
Contour = Any
Hierarchy = Any

# An enclosed interior (hole) smaller than this is a letter counter, not a node.
MIN_HOLE_AREA = 300

# Interiors/solid blobs narrower than this are text or noise, not a node.
MIN_SHAPE_SIDE = 18

# A node's interior is a convex region; a hole formed by lines and nodes
# enclosing blank space (a loop) is not.
MIN_HOLE_SOLIDITY = 0.9

# A diamond is recognisable by its four midpoint vertices even when tiny; only a diamond may
# be this small, because letter counters (the hole in an "o") are not diamonds.
MIN_SMALL_DIAMOND_AREA = 100
MIN_SMALL_DIAMOND_SIDE = 12
# Rounded diamond corners add vertices; every one must still sit nearer an edge midpoint.
MAX_DIAMOND_VERTICES = 8

# An ellipse fills pi/4 of its box, below a rounded rectangle's ACTION_MIN_EXTENT, and matches
# the ellipse fitted to its outline almost exactly. (Circularity cannot be used: it falls
# steadily as an ellipse gets wider.)
ELLIPSE_EXTENT_RANGE = (0.7, 0.82)
ELLIPSE_FIT_RATIO = (0.93, 1.07)
MIN_CONTOUR_POINTS_FOR_FIT = 5

# A UML note is a rectangle with one corner folded: three corners sit on the bounding box's
# corners and the fourth is cut away. A rounded box has none of its four on the corner.
NOTE_SHARP_CORNER = 0.04  # of the shorter side: this close to the box corner is "sharp"
NOTE_CUT_CORNER = 0.10  # of the shorter side: this far from the box corner is "cut"
NOTE_SHARP_CORNERS = 3

# Blank pixels added around the image so a node touching its edge still has a closed outline.
EDGE_PAD = 8

# Two nodes never overlap. Where two found shapes do, the larger is the blank space
# that lines and nodes enclose (a loop), not a node.
MAX_SHAPE_OVERLAP = 0.15

# A start marker with a ring around it (at these multiples of its radius) is an end node.
RING_RADIUS_RANGE = (1.15, 2.0)
RING_ANGLE_STEPS = 72
RING_MIN_COVERAGE = 0.75

# 4*pi*area/perimeter^2 is 1.0 for a perfect circle.
CIRCLE_CIRCULARITY_THRESHOLD = 0.8
HOLE_CIRCLE_ASPECT = (0.8, 1.25)

# A circle fills pi/4 (~0.785) of its bounding box. A diamond's staircase contour
# is measured with a shortened perimeter and can pass the circularity test alone,
# but it fills only about half of its box.
CIRCLE_MIN_EXTENT = 0.7

# A rounded rectangle's interior fills nearly all of its bounding box; a
# diamond's fills about half.
ACTION_MIN_EXTENT = 0.82
DIAMOND_EXTENT_RANGE = (0.4, 0.6)

# A start marker is a filled disk. Connector lines (and an END ring) are a few
# px thick, so opening with a disk this wide removes them -- crucially even
# where a line touches the marker and the two fuse into one contour.
SOLID_KERNEL = 11
# Arrowheads grow with the image, so a bare solid disc must also be this share of its shorter
# side (start markers are 4-8%, arrowheads 1-2%).
MIN_SOLID_DIAMETER = 18
MIN_SOLID_SHARE = 0.03
# An end node's dot can be smaller than a start marker; only its ring tells it from an arrowhead.
MIN_RINGED_DIAMETER = 12
SOLID_MIN_EXTENT = 0.65

# A fork/join bar is a deliberately solid glyph, many times wider than tall (or
# the reverse). It survives a thin opening that erases outlines and lines.
BAR_KERNEL = 7
BAR_ASPECT_RATIO_MIN = 4.0
MIN_BAR_THICKNESS = 6
MIN_BAR_LENGTH = 40

# Vertex-approximation tolerance, as a fraction of contour perimeter.
APPROX_EPSILON_RATIO = 0.02

# How far outward to look for a node outline's thickness, and the fallback.
MAX_OUTLINE_THICKNESS = 12
DEFAULT_OUTLINE_THICKNESS = 3


@dataclass
class ActivityShape:
    x: int
    y: int
    w: int
    h: int
    # "start", "end", "action", "decision", or "bar" (fork/join -- CV can only
    # detect the bar shape; which one it is depends on edge direction/degree,
    # resolved later once edges are known, not from geometry alone).
    kind: str
    # The enclosed interior (outlined nodes only), kept so later stages can mask a
    # node's outline precisely instead of by its bounding box, which for a
    # diamond also covers the empty corners where edge labels sit.
    interior: Contour = field(default=None, compare=False, repr=False)


def detect_activity_shapes(binary: BinaryImage) -> list[ActivityShape]:
    """Find nodes without depending on them being separate from their lines.

    Outlined nodes (action, decision, end) are found by the blank interior their
    outline encloses; a connector touching the outline cannot change that hole.
    Solid nodes (start, fork/join bars) are found by morphological opening,
    which erases lines and outlines but keeps thick filled regions."""
    # A node touching the image edge has no closed outline; a blank margin closes it.
    padded = np.asarray(
        cv2.copyMakeBorder(binary, EDGE_PAD, EDGE_PAD, EDGE_PAD, EDGE_PAD, cv2.BORDER_CONSTANT, value=0),
        dtype=np.uint8,
    )
    shapes = _hole_shapes(padded)
    shapes += _solid_shapes(padded, shapes)
    shapes = _drop_enclosures(_shifted(shapes, -EDGE_PAD))
    return sorted(shapes, key=lambda s: (s.y, s.x))


def _shifted(shapes: list[ActivityShape], offset: int) -> list[ActivityShape]:
    for shape in shapes:
        shape.x += offset
        shape.y += offset
        if shape.interior is not None:
            shape.interior = shape.interior + offset
    return shapes


def _drop_enclosures(shapes: list[ActivityShape]) -> list[ActivityShape]:
    """Remove each shape that overlaps a smaller one: blank space enclosed by a loop."""
    dropped: set[int] = set()
    for i, first in enumerate(shapes):
        for j, second in enumerate(shapes):
            if i >= j:
                continue
            inter_w = min(first.x + first.w, second.x + second.w) - max(first.x, second.x)
            inter_h = min(first.y + first.h, second.y + second.h) - max(first.y, second.y)
            if inter_w <= 0 or inter_h <= 0:
                continue
            smaller = min(first.w * first.h, second.w * second.h)
            if inter_w * inter_h > MAX_SHAPE_OVERLAP * smaller:
                dropped.add(i if first.w * first.h > second.w * second.h else j)
    return [shape for index, shape in enumerate(shapes) if index not in dropped]


def _hole_shapes(binary: BinaryImage) -> list[ActivityShape]:
    contours, hierarchy = cv2.findContours(binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    if hierarchy is None:
        return []

    shapes: list[ActivityShape] = []
    for i, contour in enumerate(contours):
        parent = hierarchy[0][i][3]
        if parent < 0 or hierarchy[0][parent][3] >= 0:
            continue  # only the first nesting level: an outline's own interior

        area = cv2.contourArea(contour)
        x, y, w, h = cv2.boundingRect(contour)
        small = area < MIN_HOLE_AREA or min(w, h) < MIN_SHAPE_SIDE
        if small and (area < MIN_SMALL_DIAMOND_AREA or min(w, h) < MIN_SMALL_DIAMOND_SIDE):
            continue
        hull_area = cv2.contourArea(cv2.convexHull(contour))
        if hull_area == 0 or area / hull_area < MIN_HOLE_SOLIDITY:
            continue

        kind = _classify_hole(contour, area, x, y, w, h)
        if kind is None or (small and kind != "decision"):
            continue
        t = _outline_thickness(binary, x, y, w, h)
        shapes.append(
            ActivityShape(x=x - t, y=y - t, w=w + 2 * t, h=h + 2 * t, kind=kind, interior=contour)
        )
    return shapes


def _classify_hole(contour: Contour, area: float, x: int, y: int, w: int, h: int) -> str | None:
    peri = cv2.arcLength(contour, True)
    if peri == 0:
        return None
    circularity = 4 * math.pi * area / (peri * peri)
    aspect = w / h
    extent = area / (w * h)

    if (
        circularity > CIRCLE_CIRCULARITY_THRESHOLD
        and HOLE_CIRCLE_ASPECT[0] <= aspect <= HOLE_CIRCLE_ASPECT[1]
        and extent >= CIRCLE_MIN_EXTENT
    ):
        return "end"
    if _is_note(contour, x, y, w, h):
        return "note"
    if extent >= ACTION_MIN_EXTENT:
        return "action"
    if ELLIPSE_EXTENT_RANGE[0] <= extent < ELLIPSE_EXTENT_RANGE[1] and _is_ellipse(contour, area):
        return "action"
    if DIAMOND_EXTENT_RANGE[0] <= extent <= DIAMOND_EXTENT_RANGE[1]:
        approx = cv2.approxPolyDP(contour, APPROX_EPSILON_RATIO * peri, True)
        if 4 <= len(approx) <= MAX_DIAMOND_VERTICES and _is_diamond(approx, x, y, w, h):
            return "decision"
    return None


def _is_ellipse(contour: Contour, area: float) -> bool:
    if len(contour) < MIN_CONTOUR_POINTS_FOR_FIT:
        return False
    _, (width, height), _ = cv2.fitEllipse(contour)
    fitted = math.pi * width * height / 4
    return fitted > 0 and ELLIPSE_FIT_RATIO[0] <= area / fitted <= ELLIPSE_FIT_RATIO[1]


def _is_note(contour: Contour, x: int, y: int, w: int, h: int) -> bool:
    points = contour.reshape(-1, 2).astype(np.float64)
    scale = min(w, h)
    corners = [(x, y), (x + w - 1, y), (x, y + h - 1), (x + w - 1, y + h - 1)]
    gaps = [float(np.hypot(points[:, 0] - cx, points[:, 1] - cy).min()) for cx, cy in corners]
    sharp = sum(gap <= NOTE_SHARP_CORNER * scale for gap in gaps)
    cut = sum(gap >= NOTE_CUT_CORNER * scale for gap in gaps)
    return sharp == NOTE_SHARP_CORNERS and cut == 1


def _outline_thickness(binary: BinaryImage, x: int, y: int, w: int, h: int) -> int:
    """Outline thickness, read outward from the middle of each side of the
    interior. The smallest run wins: a connector attached at one side makes that
    run longer, never shorter."""
    height, width = binary.shape[:2]
    cx, cy = x + w // 2, y + h // 2
    runs: list[int] = []
    for start, step in (
        ((cx, y - 1), (0, -1)),
        ((cx, y + h), (0, 1)),
        ((x - 1, cy), (-1, 0)),
        ((x + w, cy), (1, 0)),
    ):
        px, py = start
        run = 0
        while (
            0 <= px < width
            and 0 <= py < height
            and binary[py, px] > 0
            and run < MAX_OUTLINE_THICKNESS
        ):
            run += 1
            px += step[0]
            py += step[1]
        if run > 0:
            runs.append(run)
    return min(runs) if runs else DEFAULT_OUTLINE_THICKNESS


def _solid_shapes(binary: BinaryImage, taken: list[ActivityShape]) -> list[ActivityShape]:
    shapes: list[ActivityShape] = []
    min_bare_diameter = max(MIN_SOLID_DIAMETER, MIN_SOLID_SHARE * min(binary.shape[:2]))

    disk = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (SOLID_KERNEL, SOLID_KERNEL))
    opened = cv2.morphologyEx(binary, cv2.MORPH_OPEN, disk)
    for contour in cv2.findContours(opened, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]:
        x, y, w, h = cv2.boundingRect(contour)
        if min(w, h) < MIN_RINGED_DIAMETER or _inside_any(x, y, w, h, taken):
            continue
        area = cv2.contourArea(contour)
        peri = cv2.arcLength(contour, True)
        if peri == 0:
            continue
        if _is_solid_diamond(contour, area, peri, x, y, w, h):
            shapes.append(ActivityShape(x=x, y=y, w=w, h=h, kind="decision"))
            continue
        if area / (w * h) < SOLID_MIN_EXTENT:
            continue
        if 4 * math.pi * area / (peri * peri) > CIRCLE_CIRCULARITY_THRESHOLD:
            ring = _ring_radius(binary, x + w / 2, y + h / 2, (w + h) / 4)
            if ring is None and min(w, h) < min_bare_diameter:
                continue  # arrowhead-sized and bare: not a node
            if ring is None:
                shapes.append(ActivityShape(x=x, y=y, w=w, h=h, kind="start"))
            else:
                cx, cy = x + w // 2, y + h // 2
                span = int(ring)
                shapes.append(
                    ActivityShape(
                        x=cx - span, y=cy - span, w=2 * span, h=2 * span, kind="end"
                    )
                )

    thin = cv2.getStructuringElement(cv2.MORPH_RECT, (BAR_KERNEL, BAR_KERNEL))
    bars = cv2.morphologyEx(binary, cv2.MORPH_OPEN, thin)
    for contour in cv2.findContours(bars, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]:
        x, y, w, h = cv2.boundingRect(contour)
        aspect = w / h
        if aspect < BAR_ASPECT_RATIO_MIN and aspect > 1 / BAR_ASPECT_RATIO_MIN:
            continue
        if min(w, h) < MIN_BAR_THICKNESS or max(w, h) < MIN_BAR_LENGTH:
            continue
        if _inside_any(x, y, w, h, taken + shapes):
            continue
        shapes.append(ActivityShape(x=x, y=y, w=w, h=h, kind="bar"))
    return shapes


def _is_solid_diamond(
    contour: Contour, area: float, perimeter: float, x: int, y: int, w: int, h: int
) -> bool:
    """A decision whose fill is dark enough to be solid ink: a filled blob that fills about
    half its box with its vertices at the box's edge midpoints."""
    extent = area / (w * h)
    if not DIAMOND_EXTENT_RANGE[0] <= extent <= DIAMOND_EXTENT_RANGE[1]:
        return False
    approx = cv2.approxPolyDP(contour, APPROX_EPSILON_RATIO * perimeter, True)
    return 4 <= len(approx) <= MAX_DIAMOND_VERTICES and _is_diamond(approx, x, y, w, h)


def _ring_radius(binary: BinaryImage, cx: float, cy: float, radius: float) -> float | None:
    """Radius of the outline ring drawn around a filled disk (an end node), or None."""
    height, width = binary.shape[:2]
    best: float | None = None
    for step in range(int(radius * RING_RADIUS_RANGE[0]), int(radius * RING_RADIUS_RANGE[1]) + 1):
        hits = 0
        for k in range(RING_ANGLE_STEPS):
            angle = 2 * math.pi * k / RING_ANGLE_STEPS
            px, py = round(cx + step * math.cos(angle)), round(cy + step * math.sin(angle))
            if 0 <= px < width and 0 <= py < height and binary[py, px] > 0:
                hits += 1
        if hits / RING_ANGLE_STEPS >= RING_MIN_COVERAGE:
            best = float(step)
    return best


def _inside_any(x: int, y: int, w: int, h: int, shapes: Sequence[ActivityShape]) -> bool:
    """Whether the centre of this box falls inside any already-found shape."""
    cx, cy = x + w / 2, y + h / 2
    return any(s.x <= cx <= s.x + s.w and s.y <= cy <= s.y + s.h for s in shapes)


def _is_diamond(approx: Contour, x: int, y: int, w: int, h: int) -> bool:
    """A decision diamond's four vertices sit near the bounding box's edge
    midpoints; an action box's (even rounded) sit near its corners."""
    cx, cy = x + w / 2, y + h / 2
    midpoints = [(cx, y), (cx, y + h), (x, cy), (x + w, cy)]
    corners = [(x, y), (x + w, y), (x, y + h), (x + w, y + h)]

    for point in approx:
        px, py = point[0]
        dist_mid = min(math.hypot(px - mx, py - my) for mx, my in midpoints)
        dist_corner = min(math.hypot(px - cx2, py - cy2) for cx2, cy2 in corners)
        if dist_mid > dist_corner:
            return False
    return True


# ---------------------------------------------------------------------------
# Connector detection -- the undirected line segments joining shapes. Whichever
# shapes a segment's two ends land on become graph-adjacent; direction is
# resolved later (DFS from START), not from arrowheads, matching the class
# pipeline's own precedent of not reading line direction from CV.
# ---------------------------------------------------------------------------

# Erase each shape's footprint plus this margin before looking for connectors,
# so a shape outline never registers as a line.
_SHAPE_ERASE_MARGIN = 6

# Ignore leftover blobs shorter than this: edge-guard text ("yes"/"no") and
# speckle left beside a line, not a connector.
MIN_CONNECTOR_LENGTH = 30
MIN_SHAPES_FOR_SHORT_CONNECTOR = 2
# Pixels either side of the straight segment still counted as on the line.
SOLIDITY_REACH = 2

# A label drawn over a line leaves a gap in it. Two free stroke ends facing each
# other across a gap between these lengths, each pointing straight at the other
# (within the angle), are drawn back together as one stroke.
MIN_LABEL_GAP = 12
MAX_LABEL_GAP = 60
MAX_BRIDGE_ANGLE_DEG = 20
# Drawn lines are straight, so the two ends must also line up to within this many px.
MAX_BRIDGE_OFFSET = 8
# A side branch of a line (a T-junction where one line splits into several) must stand
# this far off the path between the stroke's two farthest ends; an arrowhead's wings do not.
MIN_BRANCH_LENGTH = 20
MAX_BRANCH_TIPS = 6
MIN_TREE_TIPS = 3
# A line's lone end at the top (a fork) or bottom (a join) must clear the others by this.
MIN_HUB_SEPARATION = 10
# A line end this close to a shape's edge lands on that shape.
TIP_SHAPE_REACH = _SHAPE_ERASE_MARGIN + 12
# Steps back along a stroke used to read which way its end points.
TANGENT_REACH = 8
# An end this close to a shape is attached to it, not a free end.
FREE_END_MIN_SHAPE_DIST = _SHAPE_ERASE_MARGIN + 4
MIN_STROKE_AREA = 3
# A stroke within this many px of a shape's erased footprint is attached to it.
ATTACH_SLACK = 3


@dataclass
class ActivityConnector:
    x1: int
    y1: int
    x2: int
    y2: int
    # Fraction of the straight segment between the ends that is inked. A drawn line is
    # solid; letters bridged into a fake connector leave gaps.
    solidity: float = 1.0


def _solidity(binary: BinaryImage, start: tuple[int, int], end: tuple[int, int]) -> float:
    steps = max(abs(end[0] - start[0]), abs(end[1] - start[1]), 1)
    height, width = binary.shape[:2]
    inked = 0
    for step in range(steps + 1):
        px = round(start[0] + (end[0] - start[0]) * step / steps)
        py = round(start[1] + (end[1] - start[1]) * step / steps)
        window = binary[
            max(0, py - SOLIDITY_REACH) : min(height, py + SOLIDITY_REACH + 1),
            max(0, px - SOLIDITY_REACH) : min(width, px + SOLIDITY_REACH + 1),
        ]
        inked += int(window.any())
    return inked / (steps + 1)


def detect_activity_connectors(
    binary: BinaryImage, shapes: list[ActivityShape]
) -> list[ActivityConnector]:
    """Straight line segments left over once every shape footprint is erased, with
    the pieces of a line that a label interrupted joined back into one."""
    strokes = _find_strokes(_erase_shapes(binary, shapes), shapes)
    chain = list(range(len(strokes)))

    def root(i: int) -> int:
        while chain[i] != i:
            chain[i] = chain[chain[i]]
            i = chain[i]
        return i

    joined = _join_facing_ends(strokes)
    for (i, _), (j, _) in joined:
        chain[root(i)] = root(j)
    closed = {end for pair in joined for end in pair}
    _extend_loose_ends(strokes, shapes, closed)

    loose: dict[int, list[tuple[int, int]]] = {}
    touched: dict[int, set[int]] = {}
    for i, stroke in enumerate(strokes):
        touched.setdefault(root(i), set()).update(stroke.touched)
        loose.setdefault(root(i), []).extend(stroke.branch_tips)
        for k, end in enumerate(stroke.ends):
            if (i, k) not in closed:
                loose.setdefault(root(i), []).append(end)

    connectors: list[ActivityConnector] = []
    for group, ends in loose.items():
        if len(ends) < 2:
            continue
        landed = [end for end in ends if _lands_on_shape(end, shapes)]
        if len(landed) >= MIN_TREE_TIPS:
            connectors.extend(_branch_connectors(landed))
            continue
        (ax, ay), (bx, by) = max(
            itertools.combinations(ends, 2),
            key=lambda pair: math.hypot(pair[0][0] - pair[1][0], pair[0][1] - pair[1][1]),
        )
        # A short stub touching two shapes is the visible part of a long line between
        # close shapes, not text speckle.
        long_enough = math.hypot(bx - ax, by - ay) >= MIN_CONNECTOR_LENGTH
        if long_enough or len(touched[group]) >= MIN_SHAPES_FOR_SHORT_CONNECTOR:
            connectors.append(
                ActivityConnector(
                    x1=ax, y1=ay, x2=bx, y2=by, solidity=_solidity(binary, (ax, ay), (bx, by))
                )
            )
    return connectors


def _lands_on_shape(end: tuple[int, int], shapes: list[ActivityShape]) -> bool:
    return any(_box_gap(end[0], end[1], shape) <= TIP_SHAPE_REACH for shape in shapes)


def _box_gap(px: int, py: int, shape: ActivityShape) -> float:
    cx = max(shape.x, min(px, shape.x + shape.w))
    cy = max(shape.y, min(py, shape.y + shape.h))
    return math.hypot(px - cx, py - cy)


def _branch_connectors(tips: list[tuple[int, int]]) -> list[ActivityConnector]:
    """One line that splits (or merges) is one edge per branch from its lone end -- the hub,
    alone at the top for a fork or at the bottom for a join. Without a lone end the shape is
    ambiguous and nothing is guessed."""
    ordered = sorted(tips, key=lambda tip: tip[1])
    if ordered[1][1] - ordered[0][1] >= MIN_HUB_SEPARATION:
        hub = ordered[0]
    elif ordered[-1][1] - ordered[-2][1] >= MIN_HUB_SEPARATION:
        hub = ordered[-1]
    else:
        return []
    return [
        ActivityConnector(x1=hub[0], y1=hub[1], x2=tip[0], y2=tip[1])
        for tip in ordered
        if tip != hub
    ]


def _branch_tips(
    pixels: set[tuple[int, int]], first: tuple[int, int], second: tuple[int, int]
) -> list[tuple[int, int]]:
    """Far tips of the side branches of a stroke, beyond its two farthest ends."""
    covered = _path_between(pixels, first, second)
    tips: list[tuple[int, int]] = []
    for _ in range(MAX_BRANCH_TIPS):
        tip, length, route = _farthest_from(pixels, covered)
        if length < MIN_BRANCH_LENGTH:
            break
        tips.append(tip)
        covered |= route
    return tips


def _neighbours(point: tuple[int, int], pixels: set[tuple[int, int]]) -> list[tuple[int, int]]:
    px, py = point
    return [
        (px + dx, py + dy)
        for dx in (-1, 0, 1)
        for dy in (-1, 0, 1)
        if (dx or dy) and (px + dx, py + dy) in pixels
    ]


def _path_between(
    pixels: set[tuple[int, int]], start: tuple[int, int], goal: tuple[int, int]
) -> set[tuple[int, int]]:
    parent: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
    queue = deque([start])
    while queue and goal not in parent:
        current = queue.popleft()
        for neighbour in _neighbours(current, pixels):
            if neighbour not in parent:
                parent[neighbour] = current
                queue.append(neighbour)
    route: set[tuple[int, int]] = set()
    node: tuple[int, int] | None = goal if goal in parent else None
    while node is not None:
        route.add(node)
        node = parent[node]
    return route


def _farthest_from(
    pixels: set[tuple[int, int]], covered: set[tuple[int, int]]
) -> tuple[tuple[int, int], int, set[tuple[int, int]]]:
    """The pixel farthest (by walking the stroke) from `covered`, how far, and the walk."""
    parent: dict[tuple[int, int], tuple[int, int] | None] = {p: None for p in covered}
    depth = {p: 0 for p in covered}
    queue = deque(covered)
    last = next(iter(covered))
    while queue:
        current = queue.popleft()
        last = current
        for neighbour in _neighbours(current, pixels):
            if neighbour not in parent:
                parent[neighbour] = current
                depth[neighbour] = depth[current] + 1
                queue.append(neighbour)
    route: set[tuple[int, int]] = set()
    node: tuple[int, int] | None = last
    while node is not None and node not in covered:
        route.add(node)
        node = parent[node]
    return last, depth[last], route


@dataclass
class _Stroke:
    ends: list[tuple[int, int]]  # the two ends, farthest apart along the stroke
    # Unit vector pointing out of the stroke at each end; None for an end that is
    # attached to a shape (or whose direction cannot be read).
    outward: list[tuple[float, float] | None]
    attached: bool  # some part of the stroke touches a shape
    touched: frozenset[int] = frozenset()  # indices of the shapes it touches
    # Ends of side branches beyond the two farthest ends, e.g. where one line splits in two.
    branch_tips: list[tuple[int, int]] = field(default_factory=list)


def _find_strokes(canvas: BinaryImage, shapes: list[ActivityShape]) -> list[_Stroke]:
    count, labels = cv2.connectedComponents(canvas, connectivity=8)
    strokes: list[_Stroke] = []
    for label in range(1, count):
        ys, xs = np.where(labels == label)
        if len(xs) < MIN_STROKE_AREA:
            continue
        pixels = set(zip(xs.tolist(), ys.tolist(), strict=True))
        first = _farthest_pixel(next(iter(pixels)), pixels)
        second = _farthest_pixel(first, pixels)
        ends = [first, second]
        outward = [
            _end_direction(end, pixels) if _is_free_end(end, shapes) else None for end in ends
        ]
        touched = frozenset(
            index
            for index, shape in enumerate(shapes)
            if any(_inside_erase_box(px, py, shape, ATTACH_SLACK) for px, py in pixels)
        )
        strokes.append(
            _Stroke(
                ends=ends,
                outward=outward,
                attached=bool(touched),
                touched=touched,
                branch_tips=_branch_tips(pixels, first, second),
            )
        )
    return strokes


def _join_facing_ends(strokes: list[_Stroke]) -> list[tuple[tuple[int, int], tuple[int, int]]]:
    """Pairs of (stroke, end) whose free ends face each other across a label gap,
    closest first, each end used once."""
    candidates = [
        (_distance(sa.ends[ka], sb.ends[kb]), (ia, ka), (ib, kb))
        for ia, sa in enumerate(strokes)
        for ib, sb in enumerate(strokes)
        if ia < ib
        for ka in range(2)
        for kb in range(2)
        if _faces(sa.ends[ka], sa.outward[ka], sb.ends[kb], sb.outward[kb])
    ]
    joined: list[tuple[tuple[int, int], tuple[int, int]]] = []
    used: set[tuple[int, int]] = set()
    for _, a, b in sorted(candidates):
        if a not in used and b not in used:
            used.update((a, b))
            joined.append((a, b))
    return joined


def _extend_loose_ends(
    strokes: list[_Stroke], shapes: list[ActivityShape], closed: set[tuple[int, int]]
) -> None:
    """Carry a free stroke end straight on to the shape it points at. A label hid
    the rest of the line, and a shape's erase margin can swallow a short stub. Only
    a stroke already touching a shape is extended: a word's letters touch none and
    must not grow into a connector."""
    for i, stroke in enumerate(strokes):
        for k, direction in enumerate(stroke.outward):
            if direction is None or (i, k) in closed or not stroke.attached:
                continue
            ex, ey = stroke.ends[k]
            for step in range(1, MAX_LABEL_GAP + 1):
                px = round(ex + direction[0] * step)
                py = round(ey + direction[1] * step)
                if any(_inside_erase_box(px, py, shape) for shape in shapes):
                    stroke.ends[k] = (px, py)
                    break


def _distance(a: tuple[int, int], b: tuple[int, int]) -> float:
    return math.hypot(b[0] - a[0], b[1] - a[1])


def _inside_erase_box(px: int, py: int, shape: ActivityShape, slack: int = 0) -> bool:
    reach = _SHAPE_ERASE_MARGIN + slack
    return (
        shape.x - reach <= px <= shape.x + shape.w + reach
        and shape.y - reach <= py <= shape.y + shape.h + reach
    )


def _touches_shape(px: int, py: int, shapes: list[ActivityShape]) -> bool:
    return any(_inside_erase_box(px, py, shape, ATTACH_SLACK) for shape in shapes)


def _is_free_end(end: tuple[int, int], shapes: list[ActivityShape]) -> bool:
    px, py = end
    for shape in shapes:
        cx = max(shape.x, min(px, shape.x + shape.w))
        cy = max(shape.y, min(py, shape.y + shape.h))
        if math.hypot(px - cx, py - cy) <= FREE_END_MIN_SHAPE_DIST:
            return False
    return True


def _end_direction(
    end: tuple[int, int], pixels: set[tuple[int, int]]
) -> tuple[float, float] | None:
    """Unit vector from the stroke's body (a few steps in) out to its end."""
    seen = {end: 0}
    queue = deque([end])
    ring: list[tuple[int, int]] = []
    while queue:
        px, py = queue.popleft()
        if seen[(px, py)] == TANGENT_REACH:
            ring.append((px, py))
            continue
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                neighbour = (px + dx, py + dy)
                if neighbour in pixels and neighbour not in seen:
                    seen[neighbour] = seen[(px, py)] + 1
                    queue.append(neighbour)
    if not ring:
        return None
    mx = sum(p[0] for p in ring) / len(ring)
    my = sum(p[1] for p in ring) / len(ring)
    length = math.hypot(end[0] - mx, end[1] - my)
    if length == 0:
        return None
    return (end[0] - mx) / length, (end[1] - my) / length


def _faces(
    a: tuple[int, int],
    dir_a: tuple[float, float] | None,
    b: tuple[int, int],
    dir_b: tuple[float, float] | None,
) -> bool:
    if dir_a is None or dir_b is None:
        return False
    gap = _distance(a, b)
    if not MIN_LABEL_GAP <= gap <= MAX_LABEL_GAP:
        return False
    ux, uy = (b[0] - a[0]) / gap, (b[1] - a[1]) / gap
    cos_limit = math.cos(math.radians(MAX_BRIDGE_ANGLE_DEG))
    if dir_a[0] * ux + dir_a[1] * uy < cos_limit or -(dir_b[0] * ux + dir_b[1] * uy) < cos_limit:
        return False
    offset_a = abs((b[0] - a[0]) * dir_a[1] - (b[1] - a[1]) * dir_a[0])
    offset_b = abs((a[0] - b[0]) * dir_b[1] - (a[1] - b[1]) * dir_b[0])
    return max(offset_a, offset_b) <= MAX_BRIDGE_OFFSET


def _erase_shapes(binary: BinaryImage, shapes: list[ActivityShape]) -> BinaryImage:
    canvas = binary.copy()
    h_img, w_img = canvas.shape[:2]
    for shape in shapes:
        x0 = max(0, shape.x - _SHAPE_ERASE_MARGIN)
        y0 = max(0, shape.y - _SHAPE_ERASE_MARGIN)
        x1 = min(w_img, shape.x + shape.w + _SHAPE_ERASE_MARGIN)
        y1 = min(h_img, shape.y + shape.h + _SHAPE_ERASE_MARGIN)
        canvas[y0:y1, x0:x1] = 0
    return canvas


def _farthest_pixel(origin: tuple[int, int], pixels: set[tuple[int, int]]) -> tuple[int, int]:
    seen = {origin}
    queue = deque([origin])
    last = origin
    while queue:
        last = queue.popleft()
        px, py = last
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                neighbour = (px + dx, py + dy)
                if neighbour in pixels and neighbour not in seen:
                    seen.add(neighbour)
                    queue.append(neighbour)
    return last
