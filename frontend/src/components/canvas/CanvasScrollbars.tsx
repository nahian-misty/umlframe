import { useEffect, useState, type PointerEvent as ReactPointerEvent, type RefObject } from 'react';

import { MIN_SCROLLBAR_THUMB } from '../../utils/constants';
import type { Rect } from '../../utils/geometry';
import styles from './CanvasScrollbars.module.css';

interface CanvasScrollbarsProps {
  viewportRef: RefObject<HTMLDivElement | null>;
  pan: { x: number; y: number };
  zoom: number;
  /** Bounds of everything drawn, in canvas coordinates; null when the canvas is empty. */
  contentBounds: Rect | null;
  onPan: (pan: { x: number; y: number }) => void;
}

type Axis = 'x' | 'y';

interface Metrics {
  /** Canvas-space start of the scrollable extent and its length, plus the visible window. */
  extentStart: number;
  extentLength: number;
  viewStart: number;
  viewLength: number;
  thumb: number;
  travel: number;
  track: number;
}

/**
 * The canvas has no edges, so the scrollbar covers the content plus one
 * viewport of slack on every side, growing whenever the view goes past it.
 */
function metricsFor(
  trackPx: number,
  zoom: number,
  pan: number,
  content: { start: number; length: number } | null,
): Metrics | null {
  if (trackPx <= 0) return null;
  const viewLength = trackPx / zoom;
  const viewStart = -pan / zoom;
  const base = content
    ? { start: content.start - viewLength, end: content.start + content.length + viewLength }
    : { start: viewStart - viewLength, end: viewStart + 2 * viewLength };
  const extentStart = Math.min(base.start, viewStart);
  const extentEnd = Math.max(base.end, viewStart + viewLength);
  const extentLength = extentEnd - extentStart;
  const thumb = Math.max(MIN_SCROLLBAR_THUMB, (viewLength / extentLength) * trackPx);
  return {
    extentStart,
    extentLength,
    viewStart,
    viewLength,
    thumb,
    travel: trackPx - thumb,
    track: trackPx,
  };
}

const thumbOffset = (m: Metrics): number =>
  ((m.viewStart - m.extentStart) / (m.extentLength - m.viewLength)) * m.travel;

/** Draggable scrollbars over an unbounded canvas, driven by the same pan/zoom the wheel uses. */
export function CanvasScrollbars({
  viewportRef,
  pan,
  zoom,
  contentBounds,
  onPan,
}: CanvasScrollbarsProps) {
  const [size, setSize] = useState({ width: 0, height: 0 });

  useEffect(() => {
    const el = viewportRef.current;
    if (!el) return;
    const measure = () => setSize({ width: el.clientWidth, height: el.clientHeight });
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(el);
    return () => observer.disconnect();
  }, [viewportRef]);

  const horizontal = metricsFor(
    size.width,
    zoom,
    pan.x,
    contentBounds && { start: contentBounds.x, length: contentBounds.width },
  );
  const vertical = metricsFor(
    size.height,
    zoom,
    pan.y,
    contentBounds && { start: contentBounds.y, length: contentBounds.height },
  );

  const panTo = (axis: Axis, metrics: Metrics, viewStart: number) => {
    const next = -viewStart * zoom;
    onPan(axis === 'x' ? { x: next, y: pan.y } : { x: pan.x, y: next });
    void metrics;
  };

  const viewStartForThumb = (metrics: Metrics, thumbPos: number) => {
    const fraction = Math.min(1, Math.max(0, thumbPos / metrics.travel));
    return metrics.extentStart + fraction * (metrics.extentLength - metrics.viewLength);
  };

  const startDrag = (axis: Axis, metrics: Metrics, e: ReactPointerEvent<HTMLDivElement>) => {
    e.stopPropagation();
    const startClient = axis === 'x' ? e.clientX : e.clientY;
    const startThumb = thumbOffset(metrics);
    const onMove = (ev: PointerEvent) => {
      const delta = (axis === 'x' ? ev.clientX : ev.clientY) - startClient;
      panTo(axis, metrics, viewStartForThumb(metrics, startThumb + delta));
    };
    const onUp = () => {
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
    };
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
  };

  const jumpTo = (axis: Axis, metrics: Metrics, e: ReactPointerEvent<HTMLDivElement>) => {
    e.stopPropagation();
    const rect = e.currentTarget.getBoundingClientRect();
    const click = axis === 'x' ? e.clientX - rect.left : e.clientY - rect.top;
    panTo(axis, metrics, viewStartForThumb(metrics, click - metrics.thumb / 2));
  };

  return (
    <>
      {horizontal && (
        <div
          className={`${styles.track} ${styles.horizontal}`}
          onPointerDown={(e) => jumpTo('x', horizontal, e)}
        >
          <div
            className={styles.thumb}
            style={{ width: horizontal.thumb, left: thumbOffset(horizontal) }}
            onPointerDown={(e) => startDrag('x', horizontal, e)}
          />
        </div>
      )}
      {vertical && (
        <div
          className={`${styles.track} ${styles.vertical}`}
          onPointerDown={(e) => jumpTo('y', vertical, e)}
        >
          <div
            className={styles.thumb}
            style={{ height: vertical.thumb, top: thumbOffset(vertical) }}
            onPointerDown={(e) => startDrag('y', vertical, e)}
          />
        </div>
      )}
    </>
  );
}
