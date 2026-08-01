import { toPng } from 'html-to-image';

import { PNG_EXPORT_PADDING, PNG_EXPORT_PIXEL_RATIO } from './constants';
import type { Rect } from './geometry';

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
  const width = bounds.width + PNG_EXPORT_PADDING * 2;
  const height = bounds.height + PNG_EXPORT_PADDING * 2;

  contentNode.style.transform = `translate(${-bounds.x + PNG_EXPORT_PADDING}px, ${
    -bounds.y + PNG_EXPORT_PADDING
  }px) scale(1)`;

  try {
    const dataUrl = await toPng(contentNode, {
      width,
      height,
      backgroundColor: '#ffffff',
      pixelRatio: PNG_EXPORT_PIXEL_RATIO,
    });

    const link = document.createElement('a');
    link.download = filename;
    link.href = dataUrl;
    link.click();
  } finally {
    contentNode.style.transform = originalTransform;
  }
}
