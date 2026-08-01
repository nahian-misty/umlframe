export const classId = (n: number): string => `class_${n}`;
export const relId = (n: number): string => `rel_${n}`;
export const shapeId = (n: number): string => `shape_${n}`;
export const attributeId = (n: number): string => `attr_${n}`;
export const methodId = (n: number): string => `method_${n}`;

/**
 * Given ids like ["class_3", "class_7"] and prefix "class_", returns 8 — the
 * next sequence number to use, so an id counter can resume correctly after
 * loadDocument() replaces state with ids from an external source.
 */
export function nextSeqFromIds(ids: string[], prefix: string): number {
  let max = 0;
  for (const id of ids) {
    if (!id.startsWith(prefix)) continue;
    const n = Number(id.slice(prefix.length));
    if (Number.isFinite(n)) max = Math.max(max, n);
  }
  return max + 1;
}
