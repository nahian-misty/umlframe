import { computeEdgeAnchor, rectCenter, type Point, type Rect } from './geometry';

type Side = 'left' | 'right' | 'top' | 'bottom';

export interface RouteRequest {
  id: string;
  source: string;
  destination: string;
}

const CELL = 10;
const OBSTACLE_PADDING = 16;
const STUB_LENGTH = 20;
const SEARCH_MARGIN = 120;
const TURN_PENALTY = 6;
const SHARED_CELL_PENALTY = 4;
const MAX_EXPANSIONS = 80000;
const SELF_LOOP_EXTENT = 40;

const DIRECTIONS: Point[] = [
  { x: 1, y: 0 },
  { x: -1, y: 0 },
  { x: 0, y: 1 },
  { x: 0, y: -1 },
];

const OUTWARD: Record<Side, Point> = {
  left: { x: -1, y: 0 },
  right: { x: 1, y: 0 },
  top: { x: 0, y: -1 },
  bottom: { x: 0, y: 1 },
};

interface Port {
  side: Side;
  point: Point;
  stub: Point;
}

const snapToCell = (value: number): number => Math.round(value / CELL) * CELL;

function gaps(a: Rect, b: Rect): { x: number; y: number } {
  return {
    x: Math.max(b.x - (a.x + a.width), a.x - (b.x + b.width)),
    y: Math.max(b.y - (a.y + a.height), a.y - (b.y + b.height)),
  };
}

/** Which side of `from` faces `to`: horizontal when the boxes sit side by side, vertical when stacked. */
function facingSide(from: Rect, to: Rect): Side {
  const gap = gaps(from, to);
  const a = rectCenter(from);
  const b = rectCenter(to);
  const horizontal =
    gap.x > 0 && gap.x >= gap.y
      ? true
      : gap.y > 0
        ? false
        : Math.abs(b.x - a.x) >= Math.abs(b.y - a.y);
  if (horizontal) return b.x >= a.x ? 'right' : 'left';
  return b.y >= a.y ? 'bottom' : 'top';
}

function sidePoint(rect: Rect, side: Side, fraction: number): Point {
  const alongX = rect.x + rect.width * fraction;
  const alongY = rect.y + rect.height * fraction;
  if (side === 'left') return { x: rect.x, y: snapToCell(alongY) };
  if (side === 'right') return { x: rect.x + rect.width, y: snapToCell(alongY) };
  if (side === 'top') return { x: snapToCell(alongX), y: rect.y };
  return { x: snapToCell(alongX), y: rect.y + rect.height };
}

function stubFor(point: Point, side: Side): Point {
  const out = OUTWARD[side];
  const reach = (value: number, direction: number) =>
    direction > 0 ? Math.ceil(value / CELL) * CELL : Math.floor(value / CELL) * CELL;
  return {
    x: out.x === 0 ? point.x : reach(point.x + out.x * STUB_LENGTH, out.x),
    y: out.y === 0 ? point.y : reach(point.y + out.y * STUB_LENGTH, out.y),
  };
}

class MinHeap {
  private items: { key: number; value: number }[] = [];

  get size(): number {
    return this.items.length;
  }

  push(key: number, value: number): void {
    const items = this.items;
    items.push({ key, value });
    let i = items.length - 1;
    while (i > 0) {
      const parent = (i - 1) >> 1;
      if (items[parent].key <= items[i].key) break;
      [items[parent], items[i]] = [items[i], items[parent]];
      i = parent;
    }
  }

  pop(): number {
    const items = this.items;
    const top = items[0];
    const last = items.pop() as { key: number; value: number };
    if (items.length > 0) {
      items[0] = last;
      let i = 0;
      for (;;) {
        const left = 2 * i + 1;
        const right = left + 1;
        let smallest = i;
        if (left < items.length && items[left].key < items[smallest].key) smallest = left;
        if (right < items.length && items[right].key < items[smallest].key) smallest = right;
        if (smallest === i) break;
        [items[smallest], items[i]] = [items[i], items[smallest]];
        i = smallest;
      }
    }
    return top.value;
  }
}

function simplify(points: Point[]): Point[] {
  const result: Point[] = [];
  for (const point of points) {
    const prev = result[result.length - 1];
    if (prev && prev.x === point.x && prev.y === point.y) continue;
    result.push(point);
  }
  return result.filter((point, i) => {
    if (i === 0 || i === result.length - 1) return true;
    const prev = result[i - 1];
    const next = result[i + 1];
    return !(
      (prev.x === point.x && point.x === next.x) ||
      (prev.y === point.y && point.y === next.y)
    );
  });
}

interface Grid {
  minX: number;
  minY: number;
  cols: number;
  rows: number;
  blocked: Uint8Array;
  used: Uint8Array;
}

function buildGrid(boxes: Rect[], extra: Point[]): Grid {
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const box of boxes) {
    minX = Math.min(minX, box.x);
    minY = Math.min(minY, box.y);
    maxX = Math.max(maxX, box.x + box.width);
    maxY = Math.max(maxY, box.y + box.height);
  }
  for (const point of extra) {
    minX = Math.min(minX, point.x);
    minY = Math.min(minY, point.y);
    maxX = Math.max(maxX, point.x);
    maxY = Math.max(maxY, point.y);
  }
  const originX = Math.floor((minX - SEARCH_MARGIN) / CELL) * CELL;
  const originY = Math.floor((minY - SEARCH_MARGIN) / CELL) * CELL;
  const cols = Math.ceil((maxX + SEARCH_MARGIN - originX) / CELL) + 1;
  const rows = Math.ceil((maxY + SEARCH_MARGIN - originY) / CELL) + 1;
  const blocked = new Uint8Array(cols * rows);
  for (const box of boxes) {
    const c0 = Math.floor((box.x - OBSTACLE_PADDING - originX) / CELL);
    const c1 = Math.ceil((box.x + box.width + OBSTACLE_PADDING - originX) / CELL);
    const r0 = Math.floor((box.y - OBSTACLE_PADDING - originY) / CELL);
    const r1 = Math.ceil((box.y + box.height + OBSTACLE_PADDING - originY) / CELL);
    for (let r = Math.max(0, r0 + 1); r < Math.min(rows, r1); r++) {
      for (let c = Math.max(0, c0 + 1); c < Math.min(cols, c1); c++) blocked[r * cols + c] = 1;
    }
  }
  return { minX: originX, minY: originY, cols, rows, blocked, used: new Uint8Array(cols * rows) };
}

/** Orthogonal A* between two stub points, preferring few turns and avoiding cells other edges already use. */
function findPath(grid: Grid, from: Point, to: Point): Point[] | null {
  const toCell = (p: Point) => ({
    c: Math.round((p.x - grid.minX) / CELL),
    r: Math.round((p.y - grid.minY) / CELL),
  });
  const start = toCell(from);
  const goal = toCell(to);
  const inside = (c: number, r: number) => c >= 0 && r >= 0 && c < grid.cols && r < grid.rows;
  if (!inside(start.c, start.r) || !inside(goal.c, goal.r)) return null;

  const stateCount = grid.cols * grid.rows * 4;
  const cost = new Float64Array(stateCount).fill(Infinity);
  const cameFrom = new Int32Array(stateCount).fill(-1);
  const heap = new MinHeap();
  const stateOf = (c: number, r: number, d: number) => (r * grid.cols + c) * 4 + d;
  const heuristic = (c: number, r: number) => Math.abs(c - goal.c) + Math.abs(r - goal.r);

  for (let d = 0; d < 4; d++) {
    const s = stateOf(start.c, start.r, d);
    cost[s] = 0;
    heap.push(heuristic(start.c, start.r), s);
  }

  let expansions = 0;
  while (heap.size > 0 && expansions++ < MAX_EXPANSIONS) {
    const state = heap.pop();
    const d = state % 4;
    const cell = (state - d) / 4;
    const c = cell % grid.cols;
    const r = (cell - c) / grid.cols;
    if (c === goal.c && r === goal.r) {
      const cells: Point[] = [];
      for (let s = state; s !== -1; s = cameFrom[s]) {
        const sd = s % 4;
        const sc = (s - sd) / 4;
        const col = sc % grid.cols;
        cells.push({ x: grid.minX + col * CELL, y: grid.minY + ((sc - col) / grid.cols) * CELL });
      }
      return cells.reverse();
    }
    for (let nd = 0; nd < 4; nd++) {
      const nc = c + DIRECTIONS[nd].x;
      const nr = r + DIRECTIONS[nd].y;
      if (!inside(nc, nr)) continue;
      const isGoal = nc === goal.c && nr === goal.r;
      if (grid.blocked[nr * grid.cols + nc] && !isGoal) continue;
      const step =
        1 +
        (nd === d ? 0 : TURN_PENALTY) +
        (grid.used[nr * grid.cols + nc] ? SHARED_CELL_PENALTY : 0);
      const next = stateOf(nc, nr, nd);
      const total = cost[state] + step;
      if (total < cost[next]) {
        cost[next] = total;
        cameFrom[next] = state;
        heap.push(total + heuristic(nc, nr), next);
      }
    }
  }
  return null;
}

function markUsed(grid: Grid, path: Point[]): void {
  for (let i = 1; i < path.length; i++) {
    const a = path[i - 1];
    const b = path[i];
    const steps = Math.max(Math.abs(b.x - a.x), Math.abs(b.y - a.y)) / CELL;
    for (let s = 0; s <= steps; s++) {
      const x = a.x + ((b.x - a.x) / (steps || 1)) * s;
      const y = a.y + ((b.y - a.y) / (steps || 1)) * s;
      const c = Math.round((x - grid.minX) / CELL);
      const r = Math.round((y - grid.minY) / CELL);
      if (c >= 0 && r >= 0 && c < grid.cols && r < grid.rows) grid.used[r * grid.cols + c] = 1;
    }
  }
}

function selfLoop(rect: Rect): Point[] {
  const right = rect.x + rect.width;
  const top = snapToCell(rect.y + rect.height * 0.25);
  const bottom = snapToCell(rect.y + rect.height * 0.75);
  return [
    { x: right, y: top },
    { x: right + SELF_LOOP_EXTENT, y: top },
    { x: right + SELF_LOOP_EXTENT, y: bottom },
    { x: right, y: bottom },
  ];
}

/**
 * Routes every relationship as an orthogonal polyline that goes around the
 * class boxes instead of through them. Edges that meet the same box side are
 * spread along it so they do not stack, and later routes avoid the cells
 * earlier routes already use. Falls back to a straight clipped line only when
 * no clear route exists.
 */
export function routeEdges(
  boxes: Map<string, Rect>,
  requests: RouteRequest[],
): Map<string, Point[]> {
  const result = new Map<string, Point[]>();
  const routable = requests.filter(
    (r) => r.source !== r.destination && boxes.has(r.source) && boxes.has(r.destination),
  );

  for (const request of requests) {
    const rect = boxes.get(request.source);
    if (request.source === request.destination && rect) result.set(request.id, selfLoop(rect));
  }

  const endpoints = new Map<string, { id: string; end: 'source' | 'destination'; other: Rect }[]>();
  const sides = new Map<string, { source: Side; destination: Side }>();
  for (const request of routable) {
    const a = boxes.get(request.source) as Rect;
    const b = boxes.get(request.destination) as Rect;
    const sourceSide = facingSide(a, b);
    const destinationSide = facingSide(b, a);
    sides.set(request.id, { source: sourceSide, destination: destinationSide });
    for (const [boxId, side, end, other] of [
      [request.source, sourceSide, 'source', b],
      [request.destination, destinationSide, 'destination', a],
    ] as const) {
      const key = `${boxId}:${side}`;
      endpoints.set(key, [...(endpoints.get(key) ?? []), { id: request.id, end, other }]);
    }
  }

  const ports = new Map<string, Port>();
  for (const [key, list] of endpoints) {
    const [boxId, side] = key.split(':') as [string, Side];
    const rect = boxes.get(boxId) as Rect;
    const vertical = side === 'left' || side === 'right';
    const sorted = [...list].sort((p, q) => {
      const pc = rectCenter(p.other);
      const qc = rectCenter(q.other);
      return vertical ? pc.y - qc.y : pc.x - qc.x;
    });
    sorted.forEach((entry, index) => {
      const point = sidePoint(rect, side, (index + 1) / (sorted.length + 1));
      ports.set(`${entry.id}:${entry.end}`, { side, point, stub: stubFor(point, side) });
    });
  }

  if (routable.length === 0) return result;

  const allBoxes = [...boxes.values()];
  const grid = buildGrid(
    allBoxes,
    [...ports.values()].flatMap((p) => [p.point, p.stub]),
  );

  for (const request of routable) {
    const a = boxes.get(request.source) as Rect;
    const b = boxes.get(request.destination) as Rect;
    const from = ports.get(`${request.id}:source`) as Port;
    const to = ports.get(`${request.id}:destination`) as Port;
    const middle = findPath(grid, from.stub, to.stub);
    if (middle) {
      const path = simplify([from.point, ...middle, to.point]);
      markUsed(grid, path);
      result.set(request.id, path);
    } else {
      result.set(request.id, [computeEdgeAnchor(a, b), computeEdgeAnchor(b, a)]);
    }
  }
  return result;
}
