"""Milestone 9: reconstructs a tree of Action/If/While IR nodes from an
ActivityDocument's graph shape. All structural decisions are resolved here,
in Python -- the codegen templates that consume this IR are presentation-only
(mirrors the class-diagram generator/template split).

Scope (per CLAUDE.md's Milestone 9 spec): if/else is reconstructed from a
decision's two branches plus their nearest common reconvergence point (a
bounded forward search from each branch); while loops are reconstructed from
a decision whose branch can loop back to itself (a DFS-style back edge into
the decision acting as loop header). Anything outside that shape -- fork/join
nodes, a decision without exactly two outgoing edges, a node without exactly
one outgoing edge outside a decision, an unrecoverable cycle, or no findable
reconvergence point -- raises ValueError rather than silently producing wrong
code.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.schemas.activity import ActivityDocument, ActivityEdge, ActivityNode, ActivityNodeType


@dataclass
class IRAction:
    label: str


@dataclass
class IRIf:
    condition_label: str
    then_body: list[IRNode]
    else_body: list[IRNode]


@dataclass
class IRWhile:
    condition_label: str
    body: list[IRNode]


IRNode = IRAction | IRIf | IRWhile


def structure_activity(document: ActivityDocument) -> list[IRNode]:
    """Public entrypoint: ActivityDocument -> a flat top-level IR sequence
    (branches/loop bodies nest as sub-sequences inside IRIf/IRWhile)."""
    if any(n.type in (ActivityNodeType.FORK, ActivityNodeType.JOIN) for n in document.nodes):
        raise ValueError("fork/join nodes are not supported by the structuring algorithm")

    builder = _Structurer(document)
    start = next(n for n in document.nodes if n.type == ActivityNodeType.START)
    entry = builder.single_successor(start.id)
    return builder.build_sequence(entry, frozenset())


class _Structurer:
    def __init__(self, document: ActivityDocument) -> None:
        self._nodes: dict[str, ActivityNode] = {n.id: n for n in document.nodes}
        self._outgoing: dict[str, list[ActivityEdge]] = {n.id: [] for n in document.nodes}
        for edge in document.edges:
            self._outgoing[edge.source].append(edge)

    def single_successor(self, node_id: str) -> str:
        edges = self._outgoing[node_id]
        if len(edges) != 1:
            raise ValueError(f"node '{node_id}' must have exactly one outgoing edge, found {len(edges)}")
        return edges[0].target

    def build_sequence(self, start_id: str, stop_ids: frozenset[str]) -> list[IRNode]:
        """Walk forward from start_id, converting each node into an IR
        statement, until reaching a node in stop_ids (excluded from the
        result) or an END node (terminal, included implicitly by stopping)."""
        ir: list[IRNode] = []
        current = start_id
        visited: set[str] = set()

        while True:
            if current in stop_ids:
                return ir
            node = self._nodes[current]
            if node.type == ActivityNodeType.END:
                return ir
            if current in visited:
                raise ValueError(f"irreducible control flow: cycle through node '{current}'")
            visited.add(current)

            if node.type == ActivityNodeType.ACTION:
                ir.append(IRAction(label=node.label))
                current = self.single_successor(current)

            elif node.type == ActivityNodeType.DECISION:
                current = self._structure_decision(node, ir, stop_ids)

            else:
                raise ValueError(f"unexpected '{node.type.value}' node '{current}' mid-sequence")

    def _structure_decision(self, node: ActivityNode, ir: list[IRNode], stop_ids: frozenset[str]) -> str:
        out_edges = self._outgoing[node.id]
        if len(out_edges) != 2:
            raise ValueError(
                f"decision '{node.id}' must have exactly 2 outgoing edges, found {len(out_edges)}"
            )
        edge_a, edge_b = out_edges
        back_a = self._reaches(edge_a.target, node.id, stop_ids)
        back_b = self._reaches(edge_b.target, node.id, stop_ids)

        if back_a and back_b:
            raise ValueError(f"decision '{node.id}' has a back edge on both branches")

        if back_a or back_b:
            body_start = edge_a.target if back_a else edge_b.target
            exit_start = edge_b.target if back_a else edge_a.target
            body = self.build_sequence(body_start, stop_ids | {node.id})
            ir.append(IRWhile(condition_label=node.label, body=body))
            return exit_start

        converge = self._find_convergence(edge_a.target, edge_b.target)
        if converge is None:
            raise ValueError(f"no reconvergence point found for decision '{node.id}'")
        then_body = self.build_sequence(edge_a.target, stop_ids | {converge})
        else_body = self.build_sequence(edge_b.target, stop_ids | {converge})
        ir.append(IRIf(condition_label=node.label, then_body=then_body, else_body=else_body))
        return converge

    def _reaches(self, from_id: str, target_id: str, boundary: frozenset[str]) -> bool:
        """Whether any forward path from from_id reaches target_id without
        first crossing a `boundary` node (an enclosing scope's own stop
        points, e.g. an outer loop's header) -- the back-edge test for loop
        detection, scoped to the decision's own local subgraph so an outer
        loop's cycle doesn't get mistaken for one of its inner decisions."""
        seen: set[str] = set()
        stack = [from_id]
        while stack:
            current = stack.pop()
            if current == target_id:
                return True
            if current in seen or current in boundary:
                continue
            seen.add(current)
            stack.extend(edge.target for edge in self._outgoing[current])
        return False

    def _find_convergence(self, a_start: str, b_start: str) -> str | None:
        """Nearest common node reachable from both branch starts, by summed
        BFS depth -- the bounded forward search for an if/else's merge point."""
        depths_a = self._bfs_depths(a_start)
        depths_b = self._bfs_depths(b_start)
        common = set(depths_a) & set(depths_b)
        if not common:
            return None
        return min(common, key=lambda node_id: depths_a[node_id] + depths_b[node_id])

    def _bfs_depths(self, start_id: str) -> dict[str, int]:
        depths = {start_id: 0}
        frontier = [start_id]
        while frontier:
            next_frontier = []
            for current in frontier:
                for edge in self._outgoing[current]:
                    if edge.target not in depths:
                        depths[edge.target] = depths[current] + 1
                        next_frontier.append(edge.target)
            frontier = next_frontier
        return depths
