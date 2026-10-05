import type { RefObject } from 'react';
import { Maximize } from 'lucide-react';

import { FIT_VIEW_PADDING, MAX_ZOOM, MIN_ZOOM } from '../../utils/constants';
import { fitViewToBounds, type Point, type Rect } from '../../utils/geometry';
import { Button } from '../common/Button';

interface FittableCanvas {
  contentRef: RefObject<HTMLDivElement | null>;
  getContentBounds: () => Rect | null;
  setZoom: (zoom: number) => void;
  setPan: (pan: Point) => void;
}

/** Zooms and pans so the whole diagram is visible; works for either canvas. */
export function FitToContentButton({ canvas }: { canvas: FittableCanvas }) {
  const handleFit = () => {
    const bounds = canvas.getContentBounds();
    // The content layer is the viewport's only transformed child, so its parent is the viewport.
    const viewport = canvas.contentRef.current?.parentElement?.getBoundingClientRect();
    if (!bounds || !viewport) return;
    const fit = fitViewToBounds(bounds, viewport, FIT_VIEW_PADDING, MIN_ZOOM, MAX_ZOOM);
    canvas.setZoom(fit.zoom);
    canvas.setPan(fit.pan);
  };

  return (
    <Button
      size="sm"
      icon={Maximize}
      disabled={canvas.getContentBounds() === null}
      onClick={handleFit}
      title="Zoom to fit the whole diagram"
    >
      Fit
    </Button>
  );
}
