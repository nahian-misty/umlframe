import { rectCenter, type Point, type Rect } from './geometry';
import type { ActivityNodeType } from '../types/activity';

/**
 * Point on a node's outline in the direction of `toward`: diamond for
 * decisions, ellipse for start/end, rectangle otherwise.
 */
export function nodeAnchor(type: ActivityNodeType, rect: Rect, toward: Point): Point {
  const center = rectCenter(rect);
  const dx = toward.x - center.x;
  const dy = toward.y - center.y;
  if (dx === 0 && dy === 0) return center;

  const halfW = rect.width / 2;
  const halfH = rect.height / 2;
  let scale: number;
  if (type === 'decision') {
    scale = 1 / (Math.abs(dx) / halfW + Math.abs(dy) / halfH);
  } else if (type === 'start' || type === 'end') {
    scale = 1 / Math.sqrt((dx / halfW) ** 2 + (dy / halfH) ** 2);
  } else {
    scale = Math.min(
      dx !== 0 ? halfW / Math.abs(dx) : Infinity,
      dy !== 0 ? halfH / Math.abs(dy) : Infinity,
    );
  }
  return { x: center.x + dx * scale, y: center.y + dy * scale };
}
