import { GRID_SIZE } from './constants';

export interface Point {
  x: number;
  y: number;
}

export interface Rect {
  x: number;
  y: number;
  width: number;
  height: number;
}

export function snap(value: number, enabled: boolean): number {
  return enabled ? Math.round(value / GRID_SIZE) * GRID_SIZE : value;
}

export function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

export function rectCenter(rect: Rect): Point {
  return { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2 };
}

export function rectsIntersect(a: Rect, b: Rect): boolean {
  return a.x < b.x + b.width && a.x + a.width > b.x && a.y < b.y + b.height && a.y + a.height > b.y;
}

export function normalizeRect(a: Point, b: Point): Rect {
  return {
    x: Math.min(a.x, b.x),
    y: Math.min(a.y, b.y),
    width: Math.abs(a.x - b.x),
    height: Math.abs(a.y - b.y),
  };
}

/**
 * Point where the line from `fromBox`'s center toward `toBox`'s center
 * crosses `fromBox`'s edge. Used to anchor relationship endpoints to the
 * boundary of a class box rather than its center.
 */
export function computeEdgeAnchor(fromBox: Rect, toBox: Rect): Point {
  const from = rectCenter(fromBox);
  const to = rectCenter(toBox);
  const dx = to.x - from.x;
  const dy = to.y - from.y;

  if (dx === 0 && dy === 0) {
    return from;
  }

  const halfW = fromBox.width / 2;
  const halfH = fromBox.height / 2;
  const scaleX = dx !== 0 ? halfW / Math.abs(dx) : Infinity;
  const scaleY = dy !== 0 ? halfH / Math.abs(dy) : Infinity;
  const scale = Math.min(scaleX, scaleY);

  return { x: from.x + dx * scale, y: from.y + dy * scale };
}

export function boundsOfRects(rects: Rect[]): Rect | null {
  if (rects.length === 0) return null;
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const r of rects) {
    minX = Math.min(minX, r.x);
    minY = Math.min(minY, r.y);
    maxX = Math.max(maxX, r.x + r.width);
    maxY = Math.max(maxY, r.y + r.height);
  }
  return { x: minX, y: minY, width: maxX - minX, height: maxY - minY };
}

/** Zoom and pan that centre `bounds` inside a viewport of the given size (transform origin 0 0). */
export function fitViewToBounds(
  bounds: Rect,
  viewport: { width: number; height: number },
  padding: number,
  minZoom: number,
  maxZoom: number,
): { zoom: number; pan: Point } {
  const availableWidth = Math.max(viewport.width - padding * 2, 1);
  const availableHeight = Math.max(viewport.height - padding * 2, 1);
  const zoom = clamp(
    Math.min(
      availableWidth / Math.max(bounds.width, 1),
      availableHeight / Math.max(bounds.height, 1),
    ),
    minZoom,
    maxZoom,
  );
  return {
    zoom,
    pan: {
      x: (viewport.width - bounds.width * zoom) / 2 - bounds.x * zoom,
      y: (viewport.height - bounds.height * zoom) / 2 - bounds.y * zoom,
    },
  };
}
