import { toPng } from 'html-to-image';

import { PNG_EXPORT_PADDING, PNG_EXPORT_PIXEL_RATIO } from './constants';
import { boundsOfRects, type Rect } from './geometry';

const EXPORT_BACKGROUND = '#ffffff';
const EXPORT_LIGHT_CLASS = 'export-light';
// Frames to let React re-render theme-dependent SVG colors before rasterizing.
const THEME_SETTLE_FRAMES = 3;

const nextFrame = (): Promise<void> =>
  new Promise((resolve) => requestAnimationFrame(() => resolve()));

/** Runs `task` with the light palette forced on, restoring the user's theme afterwards. */
async function withLightTheme<T>(task: () => Promise<T>): Promise<T> {
  const root = document.documentElement;
  root.classList.add(EXPORT_LIGHT_CLASS);
  try {
    for (let i = 0; i < THEME_SETTLE_FRAMES; i++) await nextFrame();
    return await task();
  } finally {
    root.classList.remove(EXPORT_LIGHT_CLASS);
  }
}

/**
 * html-to-image paints `backgroundColor` onto the exported node itself, and the
 * canvas content layer is zero-sized, so the PNG comes out with a transparent
 * background (which OCR/CV tools read as black). Paint it onto white ourselves.
 */
async function flattenOnWhite(dataUrl: string): Promise<string> {
  const image = new Image();
  image.src = dataUrl;
  await image.decode();
  const canvas = document.createElement('canvas');
  canvas.width = image.naturalWidth;
  canvas.height = image.naturalHeight;
  const context = canvas.getContext('2d');
  if (!context) return dataUrl;
  context.fillStyle = EXPORT_BACKGROUND;
  context.fillRect(0, 0, canvas.width, canvas.height);
  context.drawImage(image, 0, 0);
  return canvas.toDataURL('image/png');
}

/**
 * Extents of what is actually drawn, in canvas coordinates. Declared sizes lag the
 * rendered ones (a class box grows as attribute rows expand, edges route around
 * boxes), so an export framed by declared sizes crops the bottom and right.
 */
function measureDrawnBounds(contentNode: HTMLElement): Rect | null {
  const origin = contentNode.getBoundingClientRect();
  const scale = new DOMMatrixReadOnly(getComputedStyle(contentNode).transform).a || 1;
  const rects: Rect[] = [];
  for (const child of Array.from(contentNode.children)) {
    if (child instanceof SVGGraphicsElement) {
      const box = child.getBBox();
      if (box.width > 0 && box.height > 0) {
        rects.push({ x: box.x, y: box.y, width: box.width, height: box.height });
      }
    } else if (child instanceof HTMLElement) {
      const r = child.getBoundingClientRect();
      if (r.width > 0 && r.height > 0) {
        rects.push({
          x: (r.left - origin.left) / scale,
          y: (r.top - origin.top) / scale,
          width: r.width / scale,
          height: r.height / scale,
        });
      }
    }
  }
  return boundsOfRects(rects);
}

/** Triggers a browser download of a data: URL (or any href) under `filename`. */
export function downloadDataUrl(dataUrl: string, filename: string): void {
  const link = document.createElement('a');
  link.download = filename;
  link.href = dataUrl;
  link.click();
}

/**
 * Rasterizes an already-laid-out DOM node as-is (no pan/zoom bounds framing
 * needed) — used for one-shot content like a rendered Mermaid diagram.
 */
export async function exportNodeAsPng(
  node: HTMLElement,
  filename: string,
  backgroundColor: string,
): Promise<void> {
  const dataUrl = await toPng(node, {
    backgroundColor,
    pixelRatio: PNG_EXPORT_PIXEL_RATIO,
  });
  downloadDataUrl(dataUrl, filename);
}

/**
 * Rasterizes the full diagram content, framing it regardless of the current
 * pan/zoom so the export is never cropped to whatever's in the viewport.
 */
export async function exportCanvasAsPng(
  contentNode: HTMLElement,
  bounds: Rect,
  filename: string,
): Promise<void> {
  const originalTransform = contentNode.style.transform;
  const drawn = measureDrawnBounds(contentNode);
  const framed = drawn ? (boundsOfRects([bounds, drawn]) ?? bounds) : bounds;
  bounds = framed;
  const width = bounds.width + PNG_EXPORT_PADDING * 2;
  const height = bounds.height + PNG_EXPORT_PADDING * 2;

  contentNode.style.transform = `translate(${-bounds.x + PNG_EXPORT_PADDING}px, ${
    -bounds.y + PNG_EXPORT_PADDING
  }px) scale(1)`;

  try {
    const dataUrl = await withLightTheme(() =>
      toPng(contentNode, {
        width,
        height,
        backgroundColor: EXPORT_BACKGROUND,
        pixelRatio: PNG_EXPORT_PIXEL_RATIO,
      }),
    );
    downloadDataUrl(await flattenOnWhite(dataUrl), filename);
  } finally {
    contentNode.style.transform = originalTransform;
  }
}
