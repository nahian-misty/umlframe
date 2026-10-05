import type { ActivityDocument } from '../types/activity';

/** Rules the backend schema enforces (ActivityDocument validator). */
export function schemaProblems(doc: ActivityDocument): string[] {
  const problems: string[] = [];
  const ids = new Set(doc.nodes.map((n) => n.id));
  const starts = doc.nodes.filter((n) => n.type === 'start').length;
  if (starts !== 1) problems.push(`Needs exactly one Start node (found ${starts}).`);
  if (!doc.nodes.some((n) => n.type === 'end')) problems.push('Needs at least one End node.');
  for (const edge of doc.edges) {
    if (!ids.has(edge.source) || !ids.has(edge.target)) {
      problems.push(`Edge ${edge.id} points at a missing node.`);
    }
  }
  return problems;
}

function nodeName(node: ActivityDocument['nodes'][number]): string {
  return node.label ? `"${node.label}"` : `${node.type} node`;
}

/**
 * Mirrors the shapes backend/services/activity_structuring.py can turn into
 * code. The backend stays the authority — this only lets the UI explain the
 * problem before a round trip.
 */
export function codegenProblems(doc: ActivityDocument): string[] {
  const problems = schemaProblems(doc);
  const outCount = new Map<string, number>();
  for (const edge of doc.edges) outCount.set(edge.source, (outCount.get(edge.source) ?? 0) + 1);

  for (const node of doc.nodes) {
    const outs = outCount.get(node.id) ?? 0;
    if (node.type === 'fork' || node.type === 'join') {
      problems.push(`Fork/join (${nodeName(node)}) is not supported for code generation.`);
    } else if ((node.type === 'start' || node.type === 'action') && outs !== 1) {
      problems.push(`${nodeName(node)} needs exactly one outgoing edge (has ${outs}).`);
    } else if (node.type === 'decision' && outs !== 2) {
      problems.push(`Decision ${nodeName(node)} needs exactly two outgoing edges (has ${outs}).`);
    }
  }

  const start = doc.nodes.find((n) => n.type === 'start');
  if (start) {
    const reached = new Set<string>([start.id]);
    const queue = [start.id];
    while (queue.length) {
      const current = queue.shift() as string;
      for (const edge of doc.edges) {
        if (edge.source === current && !reached.has(edge.target)) {
          reached.add(edge.target);
          queue.push(edge.target);
        }
      }
    }
    for (const node of doc.nodes) {
      if (!reached.has(node.id)) problems.push(`${nodeName(node)} is not connected to Start.`);
    }
  }
  return problems;
}
