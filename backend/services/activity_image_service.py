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

import math
from collections import deque
from dataclasses import dataclass

from backend.cv.activity_shape_detector import (
    ActivityConnector,
    ActivityShape,
    detect_activity_connectors,
    detect_activity_shapes,
)
from backend.cv.preprocessor import preprocess
from backend.ocr.activity_extractor import GrayImage, extract_activity_labels, extract_guard_label
from backend.parser.activity_text_parser import classify_guard, normalize_label
from backend.schemas.activity import ActivityDocument, ActivityEdge, ActivityNode, ActivityNodeType
from backend.schemas.uml import Position, Size

# A connector endpoint farther than this from every shape is treated as
# dangling (not a real connection) rather than snapped to a distant shape.
_MAX_ENDPOINT_GAP = 45.0

# Vertical slack allowed before a back edge pointing downward is considered a
# violation of the top-to-bottom drawing convention.
_BACK_EDGE_Y_TOLERANCE = 20.0

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
    _, gray, binary = preprocess(image_bytes)

    shapes = detect_activity_shapes(binary)
    if not shapes:
        raise ValueError("No activity-diagram shapes detected in the image.")

    connectors = detect_activity_connectors(binary, shapes)
    adjacency = _build_adjacency(connectors, shapes)

    labels = extract_activity_labels(gray, shapes)
    directed = _orient_edges(shapes, adjacency)
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
    return edges


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
    shapes: list[ActivityShape], adjacency: list[_UndirectedEdge]
) -> list[tuple[int, int]]:
    starts = [i for i, s in enumerate(shapes) if s.kind == "start"]
    if len(starts) != 1:
        raise ValueError(
            f"Activity diagram must have exactly one start node, found {len(starts)}."
        )
    start = starts[0]

    # neighbour lists carry the connector index so parallel edges stay distinct
    # (a loop is a legitimate two-connector cycle between a decision and body).
    neighbours: dict[int, list[tuple[int, int]]] = {i: [] for i in range(len(shapes))}
    for edge in adjacency:
        neighbours[edge.a].append((edge.b, edge.connector))
        neighbours[edge.b].append((edge.a, edge.connector))

    hops = _hop_distances(start, neighbours, len(shapes))

    directed: list[tuple[int, int]] = []
    visited: set[int] = set()
    on_stack: set[int] = set()
    processed: set[int] = set()

    def dfs(u: int) -> None:
        visited.add(u)
        on_stack.add(u)
        for v, connector in sorted(neighbours[u]):
            if connector in processed:
                continue
            if v not in visited:
                # Flow runs away from START. If v is nearer START than u, this
                # connector is being crossed backwards -- orient it v -> u and
                # let v be reached later on its own shorter path.
                if hops[v] > hops[u]:
                    processed.add(connector)
                    directed.append((u, v))
                    dfs(v)
                else:
                    processed.add(connector)
                    directed.append((v, u))
            elif v in on_stack:
                processed.add(connector)
                if shapes[v].y > shapes[u].y + _BACK_EDGE_Y_TOLERANCE:
                    raise ValueError(
                        "Detected a back edge pointing downward, which violates the "
                        "top-to-bottom activity-diagram convention."
                    )
                directed.append((u, v))  # loop back edge
            else:
                processed.add(connector)
                directed.append((u, v))  # forward / cross edge (e.g. an if/else merge)
        on_stack.discard(u)

    dfs(start)

    if len(visited) != len(shapes):
        unreachable = sorted(set(range(len(shapes))) - visited)
        raise ValueError(f"Nodes {unreachable} are not reachable from the start node.")

    return directed


def _hop_distances(
    start: int, neighbours: dict[int, list[tuple[int, int]]], node_count: int
) -> list[int]:
    """Undirected BFS hop count from START; unreachable nodes stay at a large
    sentinel so the DFS's reachability check is what actually reports them."""
    dist = [node_count + 1] * node_count
    dist[start] = 0
    queue = deque([start])
    while queue:
        u = queue.popleft()
        for v, _ in neighbours[u]:
            if dist[v] == node_count + 1:
                dist[v] = dist[u] + 1
                queue.append(v)
    return dist


def _resolve_node_types(
    shapes: list[ActivityShape], directed: list[tuple[int, int]]
) -> list[ActivityNodeType]:
    out_degree = [0] * len(shapes)
    in_degree = [0] * len(shapes)
    for src, dst in directed:
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
    directed: list[tuple[int, int]],
    shapes: list[ActivityShape],
    node_types: list[ActivityNodeType],
    connectors: list[ActivityConnector],
    gray: GrayImage,
) -> list[ActivityEdge]:
    edges: list[ActivityEdge] = []
    for n, (src, dst) in enumerate(directed, start=1):
        label = ""
        if node_types[src] == ActivityNodeType.DECISION:
            connector = _connector_for_pair(src, dst, shapes, connectors)
            if connector is not None:
                label = classify_guard(
                    extract_guard_label(
                        gray, connector.x1, connector.y1, connector.x2, connector.y2
                    )
                )
        edges.append(
            ActivityEdge(id=f"e{n}", source=_node_id(src), target=_node_id(dst), label=label)
        )
    return edges


def _connector_for_pair(
    a: int, b: int, shapes: list[ActivityShape], connectors: list[ActivityConnector]
) -> ActivityConnector | None:
    best: ActivityConnector | None = None
    best_score = _MAX_ENDPOINT_GAP * 2
    for connector in connectors:
        d1 = _point_to_box_edge_dist(
            connector.x1, connector.y1, shapes[a]
        ) + _point_to_box_edge_dist(connector.x2, connector.y2, shapes[b])
        d2 = _point_to_box_edge_dist(
            connector.x1, connector.y1, shapes[b]
        ) + _point_to_box_edge_dist(connector.x2, connector.y2, shapes[a])
        score = min(d1, d2)
        if score < best_score:
            best_score = score
            best = connector
    return best


def _node_id(index: int) -> str:
    return f"n{index + 1}"
