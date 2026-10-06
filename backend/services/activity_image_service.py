"""Milestone 9 forward pipeline: activity-diagram image -> validated
ActivityDocument. Sequences cv/ -> ocr/ -> parser/ -> schemas/activity.py,
mirroring backend/services/image_service.py.

Edge direction is NOT read from arrowheads (consistent with the class pipeline
never reading line direction from CV). It is resolved by a depth-first search
from the unique START node over the undirected CV-detected adjacency: the first
time the DFS reaches a node fixes the direction of the edge it arrived on, a
back edge into a node still on the DFS stack is a loop, and a node the DFS
never reaches is a hard error rather than a silently wrong graph.
"""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass

import cv2
import numpy as np

from backend.cv.activity_shape_detector import (
    ActivityConnector,
    ActivityShape,
    detect_activity_connectors,
    detect_activity_shapes,
)
from backend.cv.preprocessor import preprocess_activity_ink
from backend.ocr.activity_extractor import (
    GrayImage,
    extract_activity_labels,
    extract_edge_guard_candidates,
)
from backend.parser.activity_text_parser import classify_guard, normalize_label
from backend.schemas.activity import ActivityDocument, ActivityEdge, ActivityNode, ActivityNodeType
from backend.schemas.uml import Position, Size

# A connector endpoint farther than this from every shape (label gaps are already
# bridged by the CV stage, so only a stroke's own slack remains) is treated as
# dangling (not a real connection) rather than snapped to a distant shape.
_MAX_ENDPOINT_GAP = 20.0


# Vertical slack allowed before a back edge pointing downward is considered a
# violation of the top-to-bottom drawing convention.
_BACK_EDGE_Y_TOLERANCE = 20.0

# Only a tiny screenshot (longer side below this) is enlarged, to about TARGET_SIDE: its nodes
# would otherwise fall under the detector's pixel limits. Larger images already clear them, and
# enlarging those thickens lines until they read as fork/join bars.
MIN_WORKING_SIDE = 350
TARGET_SIDE = 700

# How much less of its length must be inked for a connector to be a caption's twin of a line.
_MIN_SOLIDITY_GAP = 0.25

_KIND_TO_TYPE: dict[str, ActivityNodeType] = {
    "start": ActivityNodeType.START,
    "end": ActivityNodeType.END,
    "action": ActivityNodeType.ACTION,
    "decision": ActivityNodeType.DECISION,
}


@dataclass(frozen=True)
class _UndirectedEdge:
    a: int  # shape index
    b: int  # shape index
    connector: int  # index into the connectors list


def activity_image_to_document(image_bytes: bytes) -> ActivityDocument:
    """Full forward pipeline: activity-diagram image bytes -> ActivityDocument."""
    _, gray, binary = preprocess_activity_ink(_upscale_if_small(image_bytes))

    shapes = detect_activity_shapes(binary)
    if not shapes:
        raise ValueError("No activity-diagram shapes detected in the image.")

    connectors = detect_activity_connectors(binary, shapes)
    adjacency = _build_adjacency(connectors, shapes)
    shapes, adjacency = _without_notes(shapes, adjacency)
    if not shapes:
        raise ValueError("No activity-diagram shapes detected in the image.")

    labels = extract_activity_labels(gray, shapes)
    directed = _orient_edges(shapes, adjacency, connectors)
    node_types = _resolve_node_types(shapes, directed)

    nodes = [
        ActivityNode(
            id=_node_id(i),
            type=node_types[i],
            label=normalize_label(labels[i]),
            position=Position(x=float(shape.x), y=float(shape.y)),
            size=Size(width=float(shape.w), height=float(shape.h)),
        )
        for i, shape in enumerate(shapes)
    ]

    edges = _build_edges(directed, shapes, node_types, connectors, gray)
    return ActivityDocument(nodes=nodes, edges=edges)


def _upscale_if_small(image_bytes: bytes) -> bytes:
    """The shape detector's size limits are in pixels; a small screenshot is enlarged so its
    nodes clear them. Larger images are returned untouched."""
    image = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_UNCHANGED)
    if image is None or max(image.shape[:2]) >= MIN_WORKING_SIDE:
        return image_bytes
    factor = math.ceil(TARGET_SIDE / max(image.shape[:2]))
    enlarged = cv2.resize(image, None, fx=factor, fy=factor, interpolation=cv2.INTER_CUBIC)
    ok, encoded = cv2.imencode(".png", enlarged)
    return encoded.tobytes() if ok else image_bytes


def _without_notes(
    shapes: list[ActivityShape], adjacency: list[_UndirectedEdge]
) -> tuple[list[ActivityShape], list[_UndirectedEdge]]:
    """UML notes (folded-corner boxes) annotate a diagram; they are not nodes, and neither
    is the line that attaches one."""
    kept = [i for i, shape in enumerate(shapes) if shape.kind != "note"]
    new_index = {old: new for new, old in enumerate(kept)}
    remapped = [
        _UndirectedEdge(a=new_index[e.a], b=new_index[e.b], connector=e.connector)
        for e in adjacency
        if e.a in new_index and e.b in new_index
    ]
    return [shapes[i] for i in kept], remapped


# ---------------------------------------------------------------------------
# Undirected adjacency from connector line segments
# ---------------------------------------------------------------------------


def _build_adjacency(
    connectors: list[ActivityConnector], shapes: list[ActivityShape]
) -> list[_UndirectedEdge]:
    """One undirected edge per connector whose two ends land on two distinct
    shapes. Parallel connectors between the same pair are kept (an activity
    loop is a legitimate two-edge cycle between a decision and its body)."""
    edges: list[_UndirectedEdge] = []
    for idx, connector in enumerate(connectors):
        a = _nearest_shape(connector.x1, connector.y1, shapes)
        b = _nearest_shape(connector.x2, connector.y2, shapes)
        if a is None or b is None or a == b:
            continue
        edges.append(_UndirectedEdge(a=a, b=b, connector=idx))
    return _drop_duplicate_connectors(edges, connectors)


def _drop_duplicate_connectors(
    edges: list[_UndirectedEdge], connectors: list[ActivityConnector]
) -> list[_UndirectedEdge]:
    """A caption beside a line ("Yes") can be bridged into a second connector between the
    same two shapes, with its ends beside the real line's. Of two such connectors, the one
    clearly less solid than the other is the caption. A loop's back edge is kept: it either
    starts and ends far from the forward edge, or is just as solid."""
    return [
        edge
        for edge in edges
        if not any(_is_weaker_twin(edge, other, connectors) for other in edges if other is not edge)
    ]


def _is_weaker_twin(
    edge: _UndirectedEdge, other: _UndirectedEdge, connectors: list[ActivityConnector]
) -> bool:
    if {edge.a, edge.b} != {other.a, other.b}:
        return False
    mine, theirs = connectors[edge.connector], connectors[other.connector]
    if theirs.solidity - mine.solidity < _MIN_SOLIDITY_GAP:
        return False
    reach = min(_connector_length(mine), _connector_length(theirs))
    ends_mine = ((mine.x1, mine.y1), (mine.x2, mine.y2))
    ends_theirs = ((theirs.x1, theirs.y1), (theirs.x2, theirs.y2))
    return any(
        all(math.dist(p, q) <= reach for p, q in zip(ends_mine, ordered, strict=True))
        for ordered in (ends_theirs, ends_theirs[::-1])
    )


def _nearest_shape(px: int, py: int, shapes: list[ActivityShape]) -> int | None:
    best_idx: int | None = None
    best_dist = _MAX_ENDPOINT_GAP
    for idx, shape in enumerate(shapes):
        dist = _point_to_box_edge_dist(px, py, shape)
        if dist < best_dist:
            best_dist = dist
            best_idx = idx
    return best_idx


def _point_to_box_edge_dist(px: int, py: int, shape: ActivityShape) -> float:
    cx = max(shape.x, min(px, shape.x + shape.w))
    cy = max(shape.y, min(py, shape.y + shape.h))
    return math.hypot(px - cx, py - cy)


# ---------------------------------------------------------------------------
# Edge orientation (DFS from START, disambiguated by hop-distance from START)
# ---------------------------------------------------------------------------


def _orient_edges(
    shapes: list[ActivityShape],
    adjacency: list[_UndirectedEdge],
    connectors: list[ActivityConnector],
) -> list[tuple[int, int, int]]:
    """Directed edges as (source shape, target shape, connector index). The connector
    index is kept so an edge's guard label is read from its own line even when a
    decision and its loop body are joined by two (forward and back) connectors."""
    starts = [i for i, s in enumerate(shapes) if s.kind == "start"]
    if len(starts) != 1:
        raise ValueError(
            f"Activity diagram must have exactly one start node, found {len(starts)}. "
            "The start marker is a filled circle; if the diagram has one, the image may be too "
            "small or its lines too faint for it to be recognised."
        )
    start = starts[0]

    # neighbour lists carry the connector index so parallel edges stay distinct
    # (a loop is a legitimate two-connector cycle between a decision and body).
    neighbours: dict[int, list[tuple[int, int]]] = {i: [] for i in range(len(shapes))}
    for edge in adjacency:
        neighbours[edge.a].append((edge.b, edge.connector))
        neighbours[edge.b].append((edge.a, edge.connector))

    hops = _distances_from_start(start, neighbours, connectors, len(shapes))

    directed: list[tuple[int, int, int]] = []
    visited: set[int] = set()
    on_stack: set[int] = set()
    processed: set[int] = set()

    def dfs(u: int) -> None:
        visited.add(u)
        on_stack.add(u)
        # Neighbours in shape order; among parallel connectors to the same shape
        # (a decision and its loop body: forward edge plus the back edge) the shorter
        # one is taken first, so the straight forward edge is never mistaken for the
        # long curved back edge.
        for v, connector in sorted(
            neighbours[u], key=lambda n: (n[0], _connector_length(connectors[n[1]]), n[1])
        ):
            if connector in processed:
                continue
            if v not in visited:
                # Flow runs away from START. If v is nearer START than u, this
                # connector is being crossed backwards -- orient it v -> u and
                # let v be reached later on its own shorter path.
                if hops[v] > hops[u]:
                    processed.add(connector)
                    directed.append((u, v, connector))
                    dfs(v)
                else:
                    processed.add(connector)
                    directed.append((v, u, connector))
            elif v in on_stack:
                processed.add(connector)
                if shapes[v].y > shapes[u].y + _BACK_EDGE_Y_TOLERANCE:
                    raise ValueError(
                        "Detected a back edge pointing downward, which violates the "
                        "top-to-bottom activity-diagram convention."
                    )
                directed.append((u, v, connector))  # loop back edge
            else:
                processed.add(connector)
                directed.append((u, v, connector))  # forward / cross edge (e.g. an if/else merge)
        on_stack.discard(u)

    dfs(start)

    if len(visited) != len(shapes):
        unreachable = sorted(set(range(len(shapes))) - visited)
        raise ValueError(
            f"Nodes {unreachable} are not reachable from the start node. A line joining them "
            "to the rest of the diagram was not recognised (a gap in it, or a node cut by the "
            "image edge)."
        )

    return directed


def _connector_length(connector: ActivityConnector) -> float:
    return math.hypot(connector.x2 - connector.x1, connector.y2 - connector.y1)


def _distances_from_start(
    start: int,
    neighbours: dict[int, list[tuple[int, int]]],
    connectors: list[ActivityConnector],
    node_count: int,
) -> list[float]:
    """Shortest drawn-line distance from START over the undirected adjacency
    (Dijkstra, weighted by connector length). Counting hops instead would let a
    long loop-back connector shortcut to a node deep in the flow and make the
    flow into it look backwards. Unreachable nodes stay at infinity so the DFS's
    reachability check is what actually reports them."""
    dist = [math.inf] * node_count
    dist[start] = 0.0
    heap = [(0.0, start)]
    while heap:
        d, u = heapq.heappop(heap)
        if d > dist[u]:
            continue
        for v, connector in neighbours[u]:
            candidate = d + _connector_length(connectors[connector])
            if candidate < dist[v]:
                dist[v] = candidate
                heapq.heappush(heap, (candidate, v))
    return dist


def _resolve_node_types(
    shapes: list[ActivityShape], directed: list[tuple[int, int, int]]
) -> list[ActivityNodeType]:
    out_degree = [0] * len(shapes)
    in_degree = [0] * len(shapes)
    for src, dst, _ in directed:
        out_degree[src] += 1
        in_degree[dst] += 1

    types: list[ActivityNodeType] = []
    for i, shape in enumerate(shapes):
        if shape.kind in _KIND_TO_TYPE:
            types.append(_KIND_TO_TYPE[shape.kind])
        else:  # "bar" -- fork splits control, join merges it
            types.append(
                ActivityNodeType.JOIN if in_degree[i] > out_degree[i] else ActivityNodeType.FORK
            )
    return types


# ---------------------------------------------------------------------------
# Edge assembly + guard labels
# ---------------------------------------------------------------------------


def _build_edges(
    directed: list[tuple[int, int, int]],
    shapes: list[ActivityShape],
    node_types: list[ActivityNodeType],
    connectors: list[ActivityConnector],
    gray: GrayImage,
) -> list[ActivityEdge]:
    edges: list[ActivityEdge] = []
    for n, (src, dst, connector_index) in enumerate(directed, start=1):
        label = ""
        if node_types[src] == ActivityNodeType.DECISION:
            candidates = extract_edge_guard_candidates(
                gray, shapes, connectors[connector_index], shapes[dst]
            )
            label = next((guard for guard in map(classify_guard, candidates) if guard), "")
        edges.append(
            ActivityEdge(id=f"e{n}", source=_node_id(src), target=_node_id(dst), label=label)
        )
    return edges


def _node_id(index: int) -> str:
    return f"n{index + 1}"
