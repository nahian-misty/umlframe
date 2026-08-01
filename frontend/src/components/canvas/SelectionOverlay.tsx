import type { PointerEvent as ReactPointerEvent } from 'react';

import type { Rect } from '../../utils/geometry';
import styles from './SelectionOverlay.module.css';

export type ResizeHandle = 'nw' | 'ne' | 'sw' | 'se';

const HANDLES: ResizeHandle[] = ['nw', 'ne', 'sw', 'se'];

interface SelectionOverlayProps {
  rect: Rect;
  onResizeStart: (handle: ResizeHandle, event: ReactPointerEvent<HTMLDivElement>) => void;
}

/** Bounding-box outline + corner resize handles for the single selected item. */
export function SelectionOverlay({ rect, onResizeStart }: SelectionOverlayProps) {
  return (
    <div
      className={styles.overlay}
      style={{ left: rect.x, top: rect.y, width: rect.width, height: rect.height }}
    >
      {HANDLES.map((handle) => (
        <div
          key={handle}
          className={`${styles.handle} ${styles[handle]}`}
          onPointerDown={(event) => {
            event.stopPropagation();
            onResizeStart(handle, event);
          }}
        />
      ))}
    </div>
  );
}
