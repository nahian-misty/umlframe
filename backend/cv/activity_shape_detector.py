from __future__ import annotations

import math
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np
import numpy.typing as npt

# Single-channel image buffer. Contour/hierarchy arrays from cv2 carry a union
# dtype its stubs don't pin down, so they stay `Any` at the helper boundary.
BinaryImage = npt.NDArray[np.uint8]
Contour = Any
Hierarchy = Any

# Minimum contour area to consider a real shape rather than noise.
MIN_SHAPE_AREA = 200

# 4*pi*area/perimeter^2 is 1.0 for a perfect circle; real, hand-drawn or
# rasterized circles land comfortably above this threshold.
CIRCLE_CIRCULARITY_THRESHOLD = 0.75

# A fork/join bar is drawn many times wider than tall (or the reverse for a
# vertical layout) -- far more extreme than any action/decision box.
BAR_ASPECT_RATIO_MIN = 4.0

# A fork/join bar is a deliberately solid glyph; a connector line is drawn a
# few px thick. This thickness floor separates the two -- below it, a
# high-aspect contour is a line to be ignored here (it is picked up by
# detect_activity_connectors instead), not a bar.
MIN_BAR_THICKNESS = 6

# A real shape's contour fills a good part of its bounding box (a diamond,
# the sparsest, fills ~half); a diagonal connector line's fills only a sliver.
# Contours below this extent are lines, not shapes.
MIN_SHAPE_EXTENT = 0.35

# Vertex-approximation tolerance, as a fraction of contour perimeter.
APPROX_EPSILON_RATIO = 0.02


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


def detect_activity_shapes(binary: BinaryImage) -> list[ActivityShape]:
    # RETR_TREE (not RETR_CCOMP): an END marker's inner disk sits inside the
    # outer ring's *hole* contour, two nesting levels down -- CCOMP flattens
    # that to a second top-level contour instead of a descendant, so the tree
    # variant is needed to recognize it as nested at all.
    contours, hierarchy = cv2.findContours(binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    if hierarchy is None:
        return []

    shapes: list[ActivityShape] = []
    for i, contour in enumerate(contours):
        if hierarchy[0][i][3] >= 0:
            continue  # a hole/child contour -- only classified via its parent

        area = cv2.contourArea(contour)
        if area < MIN_SHAPE_AREA:
            continue

        x, y, w, h = cv2.boundingRect(contour)
        peri = cv2.arcLength(contour, True)
        if peri == 0 or w == 0 or h == 0:
            continue

        if area / (w * h) < MIN_SHAPE_EXTENT:
            continue  # a diagonal connector line, not a shape

        circularity = 4 * math.pi * area / (peri * peri)
        aspect = w / h

        if circularity > CIRCLE_CIRCULARITY_THRESHOLD:
            kind = "end" if _has_circular_child(contours, hierarchy, i) else "start"
        elif aspect > BAR_ASPECT_RATIO_MIN or aspect < 1 / BAR_ASPECT_RATIO_MIN:
            if min(w, h) < MIN_BAR_THICKNESS:
                continue  # a straight connector line, not a fork/join bar
            kind = "bar"
        else:
            approx = cv2.approxPolyDP(contour, APPROX_EPSILON_RATIO * peri, True)
            kind = "decision" if len(approx) == 4 and _is_diamond(approx, x, y, w, h) else "action"

        shapes.append(ActivityShape(x=x, y=y, w=w, h=h, kind=kind))

    return sorted(shapes, key=lambda s: (s.y, s.x))


def _has_circular_child(
    contours: Sequence[Contour], hierarchy: Hierarchy, parent_index: int
) -> bool:
    """A ringed (double) circle -- the END marker -- has a descendant contour
    (its inner disk, nested inside the outer ring's own hole contour -- two
    levels down, not one) that is itself roughly circular."""
    for descendant_index in _descendants(hierarchy, parent_index):
        contour = contours[descendant_index]
        area = cv2.contourArea(contour)
        peri = cv2.arcLength(contour, True)
        if area < MIN_SHAPE_AREA / 4 or peri == 0:
            continue
        if 4 * math.pi * area / (peri * peri) > CIRCLE_CIRCULARITY_THRESHOLD:
            return True
    return False


def _descendants(hierarchy: Hierarchy, index: int) -> Iterator[int]:
    """All contour indices nested (at any depth) under `index`, via cv2's
    [next, previous, first_child, parent] hierarchy encoding."""
    child = hierarchy[0][index][2]
    while child != -1:
        yield child
        yield from _descendants(hierarchy, child)
        child = hierarchy[0][child][0]


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

# Ignore leftover blobs shorter than this (detection speckle, not a connector).
MIN_CONNECTOR_LENGTH = 15


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
    """The two most distant extreme points of a near-straight pixel blob: the
    pair, among its axis-extreme pixels, with the greatest separation."""
    extremes = [
        (int(xs[xs.argmin()]), int(ys[xs.argmin()])),
        (int(xs[xs.argmax()]), int(ys[xs.argmax()])),
        (int(xs[ys.argmin()]), int(ys[ys.argmin()])),
        (int(xs[ys.argmax()]), int(ys[ys.argmax()])),
    ]
    best = (extremes[0], extremes[1])
    best_dist = -1.0
    for i in range(len(extremes)):
        for j in range(i + 1, len(extremes)):
            dist = math.hypot(
                extremes[i][0] - extremes[j][0], extremes[i][1] - extremes[j][1]
            )
            if dist > best_dist:
                best_dist = dist
                best = (extremes[i], extremes[j])
    return best
