import { ACTIVITY_LAYOUT, ACTIVITY_NODE_SIZES } from './constants';
import type { ActivityDocument } from '../types/activity';

/**
 * Top-down layered layout. Back edges (an edge whose target is still on the
 * DFS stack, i.e. a loop) are ignored when assigning layers, so loop bodies
 * sit below their header. Siblings are ordered by edge order, which puts a
 * decision's first branch on the left.
 */
export function autoLayout(doc: ActivityDocument): ActivityDocument {
  const outgoing = new Map<string, string[]>();
  for (const node of doc.nodes) outgoing.set(node.id, []);
  for (const edge of doc.edges) outgoing.get(edge.source)?.push(edge.target);

  const visitOrder: string[] = [];
  const state = new Map<string, 'active' | 'done'>();
  const forwardEdges: [string, string][] = [];

  const visit = (id: string) => {
    state.set(id, 'active');
    visitOrder.push(id);
    for (const target of outgoing.get(id) ?? []) {
      const targetState = state.get(target);
      if (targetState === 'active') continue;
      forwardEdges.push([id, target]);
      if (targetState === undefined) visit(target);
    }
    state.set(id, 'done');
  };

  const start = doc.nodes.find((n) => n.type === 'start');
  if (start) visit(start.id);
  for (const node of doc.nodes) if (!state.has(node.id)) visit(node.id);

  const layerOf = new Map<string, number>(doc.nodes.map((n) => [n.id, 0]));
  for (let pass = 0; pass < doc.nodes.length; pass++) {
    let changed = false;
    for (const [from, to] of forwardEdges) {
      const wanted = (layerOf.get(from) ?? 0) + 1;
      if (wanted > (layerOf.get(to) ?? 0)) {
        layerOf.set(to, wanted);
        changed = true;
      }
    }
    if (!changed) break;
  }

  const layers = new Map<number, string[]>();
  for (const id of visitOrder) {
    const layer = layerOf.get(id) ?? 0;
    layers.set(layer, [...(layers.get(layer) ?? []), id]);
  }

  const positions = new Map<string, { x: number; y: number }>();
  for (const [layer, ids] of layers) {
    ids.forEach((id, index) => {
      positions.set(id, {
        x: ACTIVITY_LAYOUT.originX + (index - (ids.length - 1) / 2) * ACTIVITY_LAYOUT.columnGap,
        y: ACTIVITY_LAYOUT.originY + layer * ACTIVITY_LAYOUT.rowGap,
      });
    });
  }

  return {
    ...doc,
    nodes: doc.nodes.map((node) => {
      const size = ACTIVITY_NODE_SIZES[node.type];
      const center = positions.get(node.id) ?? { x: ACTIVITY_LAYOUT.originX, y: 0 };
      return {
        ...node,
        size: { ...size },
        position: { x: center.x - size.width / 2, y: center.y },
      };
    }),
  };
}

/**
 * Whether any two nodes overlap. Documents that arrive without real positions
 * (extracted from source, or saved before layout existed) stack their nodes on
 * top of each other and need autoLayout before they can be read.
 */
export function hasOverlappingNodes(doc: ActivityDocument): boolean {
  const { nodes } = doc;
  for (let i = 0; i < nodes.length; i++) {
    for (let j = i + 1; j < nodes.length; j++) {
      const a = nodes[i];
      const b = nodes[j];
      const overlaps =
        a.position.x < b.position.x + b.size.width &&
        a.position.x + a.size.width > b.position.x &&
        a.position.y < b.position.y + b.size.height &&
        a.position.y + a.size.height > b.position.y;
      if (overlaps) return true;
    }
  }
  return false;
}
