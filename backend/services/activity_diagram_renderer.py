"""Renders an ActivityDocument back to a PNG using the exact shape
conventions backend/cv/activity_shape_detector.py was built and tested
against (a solid-filled circle for START, a ringed/outlined circle for END,
an outlined rounded-rect for ACTION, an outlined diamond for DECISION), with
generous clearance between every connector line and every shape's bounding
box -- the CV pipeline erases a shape's full bounding box (plus a margin)
when looking for connector lines, so a line that merely clears a shape's
*outline* but not its *bounding box* still gets silently fused or erased.

This exists because the human-facing Mermaid rendering used by
Code -> Activity Diagram (Milestone 6, backend/mermaid/activity_diagram.py)
uses a visually different, CV-incompatible convention by design -- outlined
circles with text baked inside, curved arrows touching node borders directly
-- and was never meant to round-trip through the Activity-image -> Code
pipeline (Milestone 9). This module is that round-trip's missing other half:
given the same ActivityDocument, produce an image Milestone 9's own image
pipeline can actually re-ingest.

Layout reuses activity_structuring's Action/If/While recognition rather than
laying out the raw graph directly -- that IR is guaranteed to exist for any
document Milestone 6's own extraction can produce (both were designed
against the same "loop is a back edge into its decision" convention), so
there is no separate, weaker graph-layout fallback to maintain.
"""

from __future__ import annotations

import math
import textwrap
from dataclasses import dataclass, field
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

from backend.schemas.activity import ActivityDocument
from backend.services.activity_structuring import (
    IRAction,
    IRIf,
    IRNode,
    IRWhile,
    structure_activity,
)

# Shape sizing.
_CIRCLE_D = 50
_ACTION_W, _ACTION_LINE_H, _ACTION_PAD_Y = 240, 22, 16
_DECISION_HW, _DECISION_HH = 130, 90

# Spacing. _V_GAP is the vertical clearance between two stacked shapes'
# bounding boxes; _BRANCH_GAP is the horizontal offset of an if/while
# branch's own center column from its parent's center.
_V_GAP = 60
_BRANCH_GAP = 320
_LOOP_SIDE_GAP = 70  # extra clearance for a while loop's back/exit channels

_MARGIN = 60
_FONT_SIZE = 16
_LINE_W = 3

# Clearance beyond a shape's bounding box a connector line must keep -- well
# past the 6px erasure margin detect_activity_connectors uses, so rounding
# never lets a line's endpoint land back inside the erased zone.
_EDGE_GAP = 14.0

_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]


def _load_font() -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, _FONT_SIZE)
        except OSError:
            continue
    return ImageFont.load_default()


@dataclass
class _Box:
    kind: str  # "start" | "end" | "action" | "decision"
    cx: float
    cy: float
    w: float
    h: float
    label: str = ""


@dataclass
class _Line:
    x1: float
    y1: float
    x2: float
    y2: float
    label: str = ""


def _edge_point(box: _Box, towards_x: float, towards_y: float) -> tuple[float, float]:
    """Where a line from box's center toward (towards_x, towards_y) exits
    box's bounding rectangle, pushed out by _EDGE_GAP. A zero-size box (a
    routing waypoint, not a drawn shape) has no edge to clear, so it returns
    the box's own point unchanged."""
    if box.w == 0 and box.h == 0:
        return box.cx, box.cy
    dx, dy = towards_x - box.cx, towards_y - box.cy
    dist = math.hypot(dx, dy)
    if dist == 0:
        return box.cx, box.cy
    ux, uy = dx / dist, dy / dist
    hw, hh = box.w / 2, box.h / 2
    candidates = []
    if ux != 0:
        candidates.append(hw / abs(ux))
    if uy != 0:
        candidates.append(hh / abs(uy))
    t_exit = min(candidates) if candidates else 0.0
    t_final = t_exit + _EDGE_GAP
    return box.cx + ux * t_final, box.cy + uy * t_final


@dataclass
class _Canvas:
    boxes: list[_Box] = field(default_factory=list)
    lines: list[_Line] = field(default_factory=list)

    def add_box(self, box: _Box) -> _Box:
        self.boxes.append(box)
        return box

    def connect(self, a: _Box, b: _Box, label: str = "") -> None:
        """A line between two boxes' *bounding-box edges* (plus a gap), not
        their centers -- detect_activity_connectors erases a shape's full
        bounding box (plus a 6px margin) when isolating connector lines, so a
        line that runs through a shape's center would get fused into it."""
        p1 = _edge_point(a, b.cx, b.cy)
        p2 = _edge_point(b, a.cx, a.cy)
        self.lines.append(_Line(p1[0], p1[1], p2[0], p2[1], label))

    def connect_distinct(self, a: _Box, b: _Box, skew_x: float, skew_y: float, label: str = "") -> None:
        """Like connect(), but aims each side at a point offset from the
        other box's true center (by skew_x/skew_y) rather than its center.
        For a second edge between the *same* pair of shapes (a loop's back
        edge, alongside its forward entry edge) -- aiming both at the same
        centers would produce an identical line, which the CV pipeline would
        see as one connected blob rather than two distinct edges (its
        connectivity model has no notion of parallel edges beyond "two
        separate, non-touching line segments"). A deliberately different aim
        point gives each a different boundary-crossing point on both shapes,
        keeping them geometrically apart while each stays a single straight
        line directly between the two real shapes -- never through a
        waypoint, since an endpoint that isn't within range of a real shape
        is silently dropped during adjacency building, not treated as a
        routing joint."""
        p1 = _edge_point(a, b.cx + skew_x, b.cy + skew_y)
        p2 = _edge_point(b, a.cx + skew_x, a.cy + skew_y)
        self.lines.append(_Line(p1[0], p1[1], p2[0], p2[1], label))


def render_activity_diagram(document: ActivityDocument) -> bytes:
    """ActivityDocument -> PNG bytes, in the CV-compatible shape convention."""
    ir = structure_activity(document)

    canvas = _Canvas()
    start = canvas.add_box(_Box("start", 0.0, _CIRCLE_D / 2, _CIRCLE_D, _CIRCLE_D))
    bottom_y = start.cy + _CIRCLE_D / 2 + _V_GAP
    exits, bottom_y = _layout_sequence(canvas, ir, cx=0.0, top_y=bottom_y, entry=start)

    end = canvas.add_box(_Box("end", 0.0, bottom_y + _CIRCLE_D / 2, _CIRCLE_D, _CIRCLE_D))
    for exit_box in exits:
        canvas.connect(exit_box, end)

    return _rasterize(canvas)


# ---------------------------------------------------------------------------
# Layout: walks the IR top-to-bottom, returns the open exit box(es) the next
# statement (or END) should connect to, and the y coordinate layout may
# resume from.
# ---------------------------------------------------------------------------


def _layout_sequence(
    canvas: _Canvas, nodes: list[IRNode], cx: float, top_y: float, entry: _Box, entry_label: str = ""
) -> tuple[list[_Box], float]:
    exits = [entry]
    label = entry_label
    y = top_y
    for node in nodes:
        if isinstance(node, IRAction):
            box = _place_action(canvas, node.label, cx, y)
            for e in exits:
                canvas.connect(e, box, label)
            exits = [box]
            y = box.cy + box.h / 2 + _V_GAP

        elif isinstance(node, IRIf):
            decision = _place_decision(canvas, node.condition_label, cx, y)
            for e in exits:
                canvas.connect(e, decision, label)
            branch_top = decision.cy + _DECISION_HH + _V_GAP

            then_exits, then_bottom = _layout_branch(
                canvas, node.then_body, cx - _BRANCH_GAP, branch_top, decision, "yes"
            )
            else_exits, else_bottom = _layout_branch(
                canvas, node.else_body, cx + _BRANCH_GAP, branch_top, decision, "no"
            )

            exits = then_exits + else_exits
            y = max(then_bottom, else_bottom)

        elif isinstance(node, IRWhile):
            decision = _place_decision(canvas, node.condition_label, cx, y)
            for e in exits:
                canvas.connect(e, decision, label)

            body_cx = cx - _BRANCH_GAP
            body_top = decision.cy + _DECISION_HH + _V_GAP
            body_exits, body_bottom = _layout_branch(
                canvas, node.body, body_cx, body_top, decision, "yes"
            )
            # Back edge: body's own exit(s) loop back up to the decision --
            # a single straight line directly between the two real shapes
            # (never via a waypoint: an endpoint not within range of an
            # actual shape is silently dropped, not treated as a routing
            # joint). Skewed via connect_distinct so it doesn't coincide with
            # the forward entry edge above, which already runs directly
            # between this same pair of shapes.
            for e in body_exits:
                canvas.connect_distinct(e, decision, skew_x=0, skew_y=-_LOOP_SIDE_GAP)

            # Exit edge: continues straight down the parent's own center
            # column, past the body's full height, well clear of the body
            # (which sits in a dedicated, offset column).
            exit_anchor = _Box("loop-exit", cx + _LOOP_SIDE_GAP, body_bottom, 0, 0)
            canvas.connect(decision, exit_anchor, "no")
            exits = [exit_anchor]
            y = body_bottom + _V_GAP

        label = ""  # only the very first connector in this sequence carries entry_label

    return exits, y


def _layout_branch(
    canvas: _Canvas, body: list[IRNode], cx: float, top_y: float, decision: _Box, guard_label: str
) -> tuple[list[_Box], float]:
    """Lays out one branch of an if/while. An empty branch is a direct pass-
    through: the decision itself becomes the (sole) exit, at its own y, so
    the caller's merge math still works without an empty placeholder shape
    (and without a guard-labeled edge, since there is nothing to label)."""
    if not body:
        return [decision], decision.cy
    return _layout_sequence(canvas, body, cx, top_y, decision, guard_label)


def _place_action(canvas: _Canvas, label: str, cx: float, top_y: float) -> _Box:
    lines = _wrap(label, _ACTION_W - 24)
    h = max(_ACTION_LINE_H * len(lines) + _ACTION_PAD_Y * 2, 70)
    box = _Box("action", cx, top_y + h / 2, _ACTION_W, h, "\n".join(lines))
    return canvas.add_box(box)


def _place_decision(canvas: _Canvas, label: str, cx: float, top_y: float) -> _Box:
    lines = _wrap(label, _DECISION_HW * 1.3)
    box = _Box("decision", cx, top_y + _DECISION_HH, _DECISION_HW * 2, _DECISION_HH * 2, "\n".join(lines))
    return canvas.add_box(box)


def _wrap(text: str, max_width_px: float) -> list[str]:
    approx_chars = max(int(max_width_px / (_FONT_SIZE * 0.6)), 8)
    return textwrap.wrap(text, width=approx_chars) or [""]


# ---------------------------------------------------------------------------
# Rasterization
# ---------------------------------------------------------------------------


def _rasterize(canvas: _Canvas) -> bytes:
    xs = [b.cx - b.w / 2 for b in canvas.boxes] + [b.cx + b.w / 2 for b in canvas.boxes]
    ys = [b.cy - b.h / 2 for b in canvas.boxes] + [b.cy + b.h / 2 for b in canvas.boxes]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    off_x, off_y = -min_x + _MARGIN, -min_y + _MARGIN
    width = int(max_x - min_x) + _MARGIN * 2
    height = int(max_y - min_y) + _MARGIN * 2

    img = Image.new("RGB", (width, height), "white")
    d = ImageDraw.Draw(img)
    font = _load_font()

    def tx(x: float) -> float:
        return x + off_x

    def ty(y: float) -> float:
        return y + off_y

    for line in canvas.lines:
        p1 = (tx(line.x1), ty(line.y1))
        p2 = (tx(line.x2), ty(line.y2))
        d.line([p1, p2], fill="black", width=_LINE_W)
        if line.label:
            mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
            d.text((mx + 6, my - 10), line.label, fill="black", font=font)

    for box in canvas.boxes:
        x0, y0 = tx(box.cx - box.w / 2), ty(box.cy - box.h / 2)
        x1, y1 = tx(box.cx + box.w / 2), ty(box.cy + box.h / 2)
        if box.kind == "start":
            d.ellipse([x0, y0, x1, y1], fill="black")
        elif box.kind == "end":
            d.ellipse([x0, y0, x1, y1], outline="black", width=_LINE_W)
        elif box.kind == "action":
            d.rounded_rectangle([x0, y0, x1, y1], radius=10, outline="black", width=_LINE_W)
            _centered_text(d, (x0, y0, x1, y1), box.label, font)
        elif box.kind == "decision":
            cx, cy = tx(box.cx), ty(box.cy)
            hw, hh = box.w / 2, box.h / 2
            d.polygon(
                [(cx, cy - hh), (cx + hw, cy), (cx, cy + hh), (cx - hw, cy)],
                outline="black",
                width=_LINE_W,
            )
            pad = hw * 0.35
            _centered_text(d, (cx - hw + pad, cy - hh * 0.3, cx + hw - pad, cy + hh * 0.3), box.label, font)

    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _centered_text(
    d: ImageDraw.ImageDraw,
    box: tuple[float, float, float, float],
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    x0, y0, x1, y1 = box
    lines = text.split("\n")
    line_h = _FONT_SIZE + 4
    total_h = line_h * len(lines)
    cy = (y0 + y1) / 2 - total_h / 2
    for i, line in enumerate(lines):
        bbox = d.textbbox((0, 0), line, font=font)
        lw = bbox[2] - bbox[0]
        cx = (x0 + x1) / 2 - lw / 2
        d.text((cx, cy + i * line_h), line, fill="black", font=font)
