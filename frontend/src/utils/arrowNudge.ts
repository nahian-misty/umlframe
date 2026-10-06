export const ARROW_STEP = 10;
export const ARROW_STEP_LARGE = 50;

const ARROW_DIRECTIONS: Record<string, { dx: number; dy: number }> = {
  ArrowLeft: { dx: -1, dy: 0 },
  ArrowRight: { dx: 1, dy: 0 },
  ArrowUp: { dx: 0, dy: -1 },
  ArrowDown: { dx: 0, dy: 1 },
};

/** Canvas offset an arrow key asks for (Shift = larger step), or null for any other key. */
export function arrowKeyDelta(
  event: Pick<KeyboardEvent, 'key' | 'shiftKey' | 'ctrlKey' | 'metaKey' | 'altKey' | 'target'>,
): { dx: number; dy: number } | null {
  const direction = ARROW_DIRECTIONS[event.key];
  if (!direction || event.ctrlKey || event.metaKey || event.altKey) return null;
  if (event.target instanceof HTMLSelectElement) return null;
  const step = event.shiftKey ? ARROW_STEP_LARGE : ARROW_STEP;
  return { dx: direction.dx * step, dy: direction.dy * step };
}
