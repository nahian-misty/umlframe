import { useCallback, useEffect, type RefObject } from 'react';

import { MAX_ZOOM, MIN_ZOOM, WHEEL_ZOOM_SENSITIVITY } from '../utils/constants';
import { clamp, type Point } from '../utils/geometry';

interface Navigable {
  pan: Point;
  zoom: number;
  setPan: (pan: Point) => void;
  setZoom: (zoom: number) => void;
}

/** Unbounded pan/zoom for an infinite canvas: wheel, ctrl+wheel (zoom at cursor) and drag-to-pan. */
export function useViewportNavigation(
  viewportRef: RefObject<HTMLDivElement | null>,
  nav: Navigable,
) {
  // Native (non-passive) wheel listener so ctrl/cmd+wheel zoom can preventDefault
  // the browser's page-zoom gesture; React's onWheel is passive by default.
  useEffect(() => {
    const el = viewportRef.current;
    if (!el) return;

    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      if (e.ctrlKey || e.metaKey) {
        const rect = el.getBoundingClientRect();
        const cursor = { x: e.clientX - rect.left, y: e.clientY - rect.top };
        const nextZoom = clamp(nav.zoom - e.deltaY * WHEEL_ZOOM_SENSITIVITY, MIN_ZOOM, MAX_ZOOM);
        const ratio = nextZoom / nav.zoom;
        nav.setPan({
          x: cursor.x - (cursor.x - nav.pan.x) * ratio,
          y: cursor.y - (cursor.y - nav.pan.y) * ratio,
        });
        nav.setZoom(nextZoom);
        return;
      }
      const swapAxes = e.shiftKey && e.deltaX === 0;
      nav.setPan({
        x: nav.pan.x - (swapAxes ? e.deltaY : e.deltaX),
        y: nav.pan.y - (swapAxes ? 0 : e.deltaY),
      });
    };

    el.addEventListener('wheel', onWheel, { passive: false });
    return () => el.removeEventListener('wheel', onWheel);
  }, [viewportRef, nav]);

  const toCanvasPoint = useCallback(
    (clientX: number, clientY: number): Point => {
      const rect = viewportRef.current?.getBoundingClientRect();
      if (!rect) return { x: 0, y: 0 };
      return {
        x: (clientX - rect.left - nav.pan.x) / nav.zoom,
        y: (clientY - rect.top - nav.pan.y) / nav.zoom,
      };
    },
    [viewportRef, nav.pan, nav.zoom],
  );

  const startPanDrag = useCallback(
    (start: { clientX: number; clientY: number }) => {
      const startPan = nav.pan;
      const onMove = (ev: PointerEvent) =>
        nav.setPan({
          x: startPan.x + ev.clientX - start.clientX,
          y: startPan.y + ev.clientY - start.clientY,
        });
      const onUp = () => {
        window.removeEventListener('pointermove', onMove);
        window.removeEventListener('pointerup', onUp);
      };
      window.addEventListener('pointermove', onMove);
      window.addEventListener('pointerup', onUp);
    },
    [nav],
  );

  return { toCanvasPoint, startPanDrag };
}
