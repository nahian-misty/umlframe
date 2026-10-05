from __future__ import annotations

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

# 4*pi*area/perimeter^2 is 1.0 for a perfect circle.
CIRCLE_CIRCULARITY_THRESHOLD = 0.8
HOLE_CIRCLE_ASPECT = (0.8, 1.25)

# A rounded rectangle's interior fills nearly all of its bounding box; a
# diamond's fills about half.
ACTION_MIN_EXTENT = 0.82
DIAMOND_EXTENT_RANGE = (0.4, 0.6)

# A start marker is a filled disk. Connector lines (and an END ring) are a few
# px thick, so opening with a disk this wide removes them -- crucially even
# where a line touches the marker and the two fuse into one contour.
SOLID_KERNEL = 15
MIN_SOLID_DIAMETER = 24
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
    shapes = _hole_shapes(binary)
    shapes += _solid_shapes(binary, shapes)
    return sorted(shapes, key=lambda s: (s.y, s.x))


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
        if area < MIN_HOLE_AREA or min(w, h) < MIN_SHAPE_SIDE:
            continue
        hull_area = cv2.contourArea(cv2.convexHull(contour))
        if hull_area == 0 or area / hull_area < MIN_HOLE_SOLIDITY:
            continue

        kind = _classify_hole(contour, area, x, y, w, h)
        if kind is None:
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
    ):
        return "end"
    if extent >= ACTION_MIN_EXTENT:
        return "action"
    if DIAMOND_EXTENT_RANGE[0] <= extent <= DIAMOND_EXTENT_RANGE[1]:
        approx = cv2.approxPolyDP(contour, APPROX_EPSILON_RATIO * peri, True)
        if len(approx) == 4 and _is_diamond(approx, x, y, w, h):
            return "decision"
    return None


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

    disk = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (SOLID_KERNEL, SOLID_KERNEL))
    opened = cv2.morphologyEx(binary, cv2.MORPH_OPEN, disk)
    for contour in cv2.findContours(opened, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]:
        x, y, w, h = cv2.boundingRect(contour)
        if min(w, h) < MIN_SOLID_DIAMETER or _inside_any(x, y, w, h, taken):
            continue
        area = cv2.contourArea(contour)
        peri = cv2.arcLength(contour, True)
        if peri == 0 or area / (w * h) < SOLID_MIN_EXTENT:
            continue
        if 4 * math.pi * area / (peri * peri) > CIRCLE_CIRCULARITY_THRESHOLD:
            shapes.append(ActivityShape(x=x, y=y, w=w, h=h, kind="start"))

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


@dataclass
class ActivityConnector:
    x1: int
    y1: int
    x2: int
    y2: int


def detect_activity_connectors(
    binary: BinaryImage, shapes: list[ActivityShape]
) -> list[ActivityConnector]:
    """Straight line segments left over once every shape footprint is erased."""
    canvas = binary.copy()
    h_img, w_img = canvas.shape[:2]
    for shape in shapes:
        x0 = max(0, shape.x - _SHAPE_ERASE_MARGIN)
        y0 = max(0, shape.y - _SHAPE_ERASE_MARGIN)
        x1 = min(w_img, shape.x + shape.w + _SHAPE_ERASE_MARGIN)
        y1 = min(h_img, shape.y + shape.h + _SHAPE_ERASE_MARGIN)
        canvas[y0:y1, x0:x1] = 0

    count, labels, stats, _ = cv2.connectedComponentsWithStats(canvas, connectivity=8)

    connectors: list[ActivityConnector] = []
    for label in range(1, count):
        if stats[label, cv2.CC_STAT_AREA] < 3:
            continue
        ys, xs = np.where(labels == label)
        (ax, ay), (bx, by) = _segment_endpoints(xs, ys)
        if math.hypot(bx - ax, by - ay) < MIN_CONNECTOR_LENGTH:
            continue
        connectors.append(ActivityConnector(x1=int(ax), y1=int(ay), x2=int(bx), y2=int(by)))
    return connectors


def _segment_endpoints(
    xs: npt.NDArray[np.intp], ys: npt.NDArray[np.intp]
) -> tuple[tuple[int, int], tuple[int, int]]:
    """The two ends of a line or curve, as the pair of pixels farthest apart *along
    the line* (a double breadth-first sweep over the blob's pixels). Straight
    lines would also do with axis-extreme pixels, but those pick the far bulge
    of a curved back edge instead of its actual ends."""
    pixels = set(zip(xs.tolist(), ys.tolist(), strict=True))
    first = _farthest_pixel(next(iter(pixels)), pixels)
    second = _farthest_pixel(first, pixels)
    return first, second


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
