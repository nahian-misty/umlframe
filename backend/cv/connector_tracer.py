"""Splits a group of fused connector ink into the individual lines it is made of.

Elbow connectors that cross each other come out of the binary image as one connected
blob that touches several boxes. Each line is recovered by walking it from where it
meets a box: straight on through a crossing, turning only where the ink ends in a
corner. A blob is only split when every walk pairs up with a walk from the other end
and no two lines share a stretch of ink; anything else (a shared "bus", diagonals) is
left to the caller's own handling.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np
import numpy.typing as npt

Mask = npt.NDArray[Any]
Ink = npt.NDArray[Any]
Rect = tuple[int, int, int, int]
Point = tuple[int, int]

TOUCH_DISTANCE = 8
CONTACT_CLUSTER = 14
ARRIVE_DISTANCE = 4
MAX_STEPS = 20000
MAX_GAP = 14
NUDGE_REACH = 4
TURN_PREVIEW = 30
MIN_TURN_RUN = 8
CENTRE_REACH = 16
MAX_CENTRED_RUN = 12
MIN_REAL_LINE = 60
MIN_DASH_GAPS = 3
STROKE_CLEARANCE = 3
MAX_SHARED_PIXELS = 80
BODY_RADIUS = 9
END_RADIUS = 20
END_LENGTH = 45
END_MATCH = 16
MARKER_ZONE = 45

_DIRECTIONS = ((1, 0), (-1, 0), (0, 1), (0, -1))


@dataclass
class TracedLine:
    mask: Mask
    dashed: bool


def split_crossing_group(mask: Mask, filled: Mask, rects: list[Rect]) -> list[TracedLine] | None:
    """One TracedLine per line in `mask`, or None when the group cannot be split with
    confidence.

    `filled` is `mask` with closed end markers filled solid, so a hollow diamond can be
    walked through."""
    ink = (mask > 0) | ((filled > 0) & _marker_zone(mask.shape, rects))
    contacts = _contacts(mask, rects)
    if len(contacts) < 2:
        return None

    walks = [_walk(ink, point, heading, box, rects) for point, heading, box in contacts]
    pairs = _pair_up(contacts, walks)
    if pairs is None:
        return None
    chosen = [walk for i, _ in pairs if (walk := walks[i]) is not None]
    paths = [walk[0] for walk in chosen]
    if not paths or _shared_pixels(paths, mask.shape) > MAX_SHARED_PIXELS:
        return None
    return [
        TracedLine(_line_mask(mask, paths, index), dashed=walk[2] >= MIN_DASH_GAPS)
        for index, walk in enumerate(chosen)
    ]


def _marker_zone(shape: tuple[int, ...], rects: list[Rect]) -> Mask:
    """Where an end marker can sit: close to a box. Elsewhere a closed outline is just the
    loop two crossing lines happen to form, and filling it would block the way."""
    zone = np.zeros(shape, dtype=np.uint8)
    for x, y, w, h in rects:
        zone[
            max(0, y - MARKER_ZONE) : y + h + MARKER_ZONE + 1,
            max(0, x - MARKER_ZONE) : x + w + MARKER_ZONE + 1,
        ] = 1
    return zone > 0


def _contacts(mask: Mask, rects: list[Rect]) -> list[tuple[Point, Point, int]]:
    """(ink point, outward heading, box index) for every place the ink meets a box."""
    ys, xs = np.nonzero(mask)
    contacts: list[tuple[Point, Point, int]] = []
    for index, (bx, by, bw, bh) in enumerate(rects):
        dx = np.maximum(np.maximum(bx - xs, xs - (bx + bw)), 0)
        dy = np.maximum(np.maximum(by - ys, ys - (by + bh)), 0)
        near = np.hypot(dx, dy) <= TOUCH_DISTANCE
        if not near.any():
            continue
        touching = np.zeros(mask.shape, dtype=np.uint8)
        touching[ys[near], xs[near]] = 255
        grown = cv2.dilate(touching, np.ones((CONTACT_CLUSTER, CONTACT_CLUSTER), np.uint8))
        count, labels = cv2.connectedComponents(grown, connectivity=8)
        for label in range(1, count):
            cluster_y, cluster_x = np.nonzero((labels == label) & (touching > 0))
            centre_x, centre_y = cluster_x.mean(), cluster_y.mean()
            nearest = int(np.argmin(np.hypot(cluster_x - centre_x, cluster_y - centre_y)))
            point = (int(cluster_x[nearest]), int(cluster_y[nearest]))
            contacts.append((point, _outward(point, rects[index]), index))
    return contacts


def _outward(point: Point, rect: Rect) -> Point:
    """The axis direction leading away from the side of `rect` that `point` is nearest."""
    bx, by, bw, bh = rect
    px, py = point
    gaps = {
        (-1, 0): abs(px - bx),
        (1, 0): abs(px - (bx + bw)),
        (0, -1): abs(py - by),
        (0, 1): abs(py - (by + bh)),
    }
    return min(gaps, key=lambda direction: gaps[direction])


def _walk(
    ink: Ink, start: Point, heading: Point, own_box: int, rects: list[Rect]
) -> tuple[list[Point], int, int] | None:
    """The path from `start` to the box the line ends at: (pixels, box index, how many
    gaps in the stroke it had to cross)."""
    position = start
    path = [position]
    gaps = 0
    height, width = ink.shape
    for _ in range(MAX_STEPS):
        position = _centre(ink, position, heading)
        path.append(position)
        arrived = _box_reached(position, own_box, rects)
        if arrived is not None:
            return path, arrived, gaps
        ahead = (position[0] + heading[0], position[1] + heading[1])
        if 0 <= ahead[0] < width and 0 <= ahead[1] < height and ink[ahead[1], ahead[0]]:
            position = ahead
            continue
        turn = _turn(ink, position, heading)
        if turn is not None:
            heading = turn
            continue
        jumped = _jump_gap(ink, position, heading)
        if jumped is not None:
            position = jumped
            gaps += 1
            continue
        nudged = _nudge(ink, position, heading)
        if nudged is not None:
            position = nudged
            continue
        reconnected = _reconnect(ink, position, heading)
        if reconnected is None:
            return None
        position, heading = reconnected
        gaps += 1
    return None


def _box_reached(position: Point, own_box: int, rects: list[Rect]) -> int | None:
    for index, (bx, by, bw, bh) in enumerate(rects):
        if index == own_box:
            continue
        dx = max(bx - position[0], position[0] - (bx + bw), 0)
        dy = max(by - position[1], position[1] - (by + bh), 0)
        if max(dx, dy) <= ARRIVE_DISTANCE:
            return index
    return None


def _ink_at(ink: Ink, x: int, y: int) -> bool:
    return 0 <= y < ink.shape[0] and 0 <= x < ink.shape[1] and bool(ink[y, x])


def _centre(ink: Ink, position: Point, heading: Point) -> Point:
    """`position` moved to the middle of the stroke it is on, across the heading. A run
    longer than a stroke is a line crossing this one, so the position is left alone."""
    side = (-heading[1], heading[0])
    up = down = 0
    while up < CENTRE_REACH and _ink_at(
        ink, position[0] + side[0] * (up + 1), position[1] + side[1] * (up + 1)
    ):
        up += 1
    while down < CENTRE_REACH and _ink_at(
        ink, position[0] - side[0] * (down + 1), position[1] - side[1] * (down + 1)
    ):
        down += 1
    if up + down + 1 > MAX_CENTRED_RUN:
        return position
    shift = (up - down) // 2
    centred = (position[0] + side[0] * shift, position[1] + side[1] * shift)
    if not _ink_at(ink, centred[0] + heading[0], centred[1] + heading[1]):
        return position
    return centred


def _nudge(ink: Ink, position: Point, heading: Point) -> Point | None:
    """`position` moved sideways onto the stroke when it has drifted off the edge of one
    (two lines side by side look like one thick stroke, then part again)."""
    side = (-heading[1], heading[0])
    for offset in range(1, NUDGE_REACH + 1):
        for sign in (1, -1):
            x = position[0] + side[0] * offset * sign
            y = position[1] + side[1] * offset * sign
            if _ink_at(ink, x, y) and _ink_at(ink, x + heading[0], y + heading[1]):
                return (x, y)
    return None


def _turn(ink: Ink, position: Point, heading: Point) -> Point | None:
    """The sideways direction a corner continues in, when the ink ahead has ended. Ink
    beside the position only counts as a branch when it runs on for a stretch; the
    stroke's own thickness does not."""
    sides = [d for d in _DIRECTIONS if d not in (heading, (-heading[0], -heading[1]))]
    runs = {direction: _run(ink, position, direction) for direction in sides}
    branches = [d for d in sides if runs[d] >= MIN_TURN_RUN]
    if len(branches) != 1:
        return None
    return branches[0]


def _run(ink: Ink, start: Point, direction: Point) -> int:
    """How many pixels of ink follow `start` in a straight line."""
    run = 0
    while run < TURN_PREVIEW and _ink_at(
        ink, start[0] + direction[0] * (run + 1), start[1] + direction[1] * (run + 1)
    ):
        run += 1
    return run


def _jump_gap(ink: Ink, position: Point, heading: Point) -> Point | None:
    """The next stretch of stroke straight ahead across a gap (a dash gap, possibly with a
    line crossing in it)."""
    for step in range(2, MAX_GAP * 2 + 1):
        x, y = position[0] + heading[0] * step, position[1] + heading[1] * step
        if _ink_at(ink, x, y) and _run(ink, (x, y), heading) >= MIN_TURN_RUN:
            return (x, y)
    return None


def _reconnect(ink: Ink, position: Point, heading: Point) -> tuple[Point, Point] | None:
    """Where a dashed line picks up again across a gap at a corner: the nearest ink ahead
    within a gap's reach, and the direction that stroke runs away from where we are."""
    best: Point | None = None
    best_distance = float(MAX_GAP + 1)
    for dx in range(-MAX_GAP, MAX_GAP + 1):
        for dy in range(-MAX_GAP, MAX_GAP + 1):
            if dx * heading[0] + dy * heading[1] <= 0:
                continue
            distance = float(np.hypot(dx, dy))
            if distance < best_distance and _ink_at(ink, position[0] + dx, position[1] + dy):
                best, best_distance = (position[0] + dx, position[1] + dy), distance
    if best is None:
        return None
    runs = {direction: _run(ink, best, direction) for direction in _DIRECTIONS}
    onward = max((d for d in _DIRECTIONS if d != (-heading[0], -heading[1])), key=lambda d: runs[d])
    return (best, onward) if runs[onward] >= MIN_TURN_RUN else None


def _pair_up(
    contacts: list[tuple[Point, Point, int]], walks: list[tuple[list[Point], int, int] | None]
) -> list[tuple[int, int]] | None:
    """(walk, partner contact) for each line, keeping each line once. None when a long
    walk has no partner walking back, or when a contact's walk never settles."""
    partner: dict[int, int] = {}
    for index, walk in enumerate(walks):
        if walk is None:
            continue
        path, box, _ = walk
        end = path[-1]
        candidates = [
            j
            for j, (point, _, contact_box) in enumerate(contacts)
            if contact_box == box
            and np.hypot(point[0] - end[0], point[1] - end[1]) <= END_MATCH + ARRIVE_DISTANCE
        ]
        if candidates:
            partner[index] = min(
                candidates,
                key=lambda j: np.hypot(contacts[j][0][0] - end[0], contacts[j][0][1] - end[1]),
            )
    pairs: list[tuple[int, int]] = []
    seen: set[int] = set()
    for index, walk in enumerate(walks):
        long_walk = walk is not None and len(walk[0]) >= MIN_REAL_LINE
        other = partner.get(index)
        if other is None or partner.get(other) != index:
            if long_walk:
                return None
            continue
        if index in seen:
            continue
        seen.update((index, other))
        pairs.append((index, other))
    return pairs or None


def _shared_pixels(paths: list[list[Point]], shape: tuple[int, ...]) -> int:
    """How many pixels more than one line's path runs over (a crossing shares a few)."""
    counts = np.zeros(shape, dtype=np.uint8)
    for path in paths:
        line = np.zeros(shape, dtype=np.uint8)
        for x, y in path:
            line[y, x] = 1
        counts += _grow(line, 1)
    return int(np.count_nonzero(counts > 1))


def _line_mask(mask: Mask, paths: list[list[Point]], index: int) -> Mask:
    """The ink belonging to line `index`: near its path, with room for an end marker, and
    only the pieces the path itself runs along (a label beside it is left out). Ink that
    lies on another line's path is left out too, except where the two cross."""
    path = paths[index]
    own = _drawn(mask.shape, path)
    reach = _drawn(mask.shape, path[:END_LENGTH] + path[-END_LENGTH:])
    near = (_grow(own, BODY_RADIUS) > 0) | (_grow(reach, END_RADIUS) > 0)
    others = np.zeros(mask.shape, dtype=bool)
    for other, other_path in enumerate(paths):
        if other != index:
            others |= _grow(_drawn(mask.shape, other_path), STROKE_CLEARANCE) > 0
    others &= ~(_grow(own, STROKE_CLEARANCE) > 0)
    local = np.where(near & (mask > 0) & ~others, 255, 0).astype(np.uint8)
    count, labels = cv2.connectedComponents(local, connectivity=8)
    on_path = {int(labels[y, x]) for x, y in path if labels[y, x]}
    return np.where(np.isin(labels, list(on_path)), 255, 0).astype(np.uint8)


def _drawn(shape: tuple[int, ...], points: list[Point]) -> Mask:
    image = np.zeros(shape, dtype=np.uint8)
    for x, y in points:
        image[y, x] = 255
    return image


def _grow(image: Mask, radius: int) -> Mask:
    """`image` dilated by a disc of `radius` pixels."""
    disc = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * radius + 1, 2 * radius + 1))
    return np.asarray(cv2.dilate(image, disc), dtype=np.uint8)
