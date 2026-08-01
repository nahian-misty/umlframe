import type { PointerEvent as ReactPointerEvent } from 'react';

import type { GenericShape } from '../../types/diagram';
import styles from './ShapeRenderer.module.css';

interface ShapeRendererProps {
  shape: GenericShape;
  isSelected: boolean;
  onPointerDown: (event: ReactPointerEvent<HTMLDivElement>) => void;
}

export function ShapeRenderer({ shape, isSelected, onPointerDown }: ShapeRendererProps) {
  const { kind, position, size } = shape;

  return (
    <div
      className={`${styles.shape} ${isSelected ? styles.selected : ''}`}
      style={{ left: position.x, top: position.y, width: size.width, height: size.height }}
      onPointerDown={onPointerDown}
      data-shape-id={shape.id}
    >
      {kind === 'rectangle' && <div className={styles.rectangle} />}
      {kind === 'circle' && <div className={styles.circle} />}
      {kind === 'diamond' && <div className={styles.diamond} />}
      {(kind === 'line' || kind === 'arrow') && (
        <svg
          className={styles.lineSvg}
          width={size.width}
          height={size.height}
          viewBox={`0 0 ${size.width} ${size.height}`}
          preserveAspectRatio="none"
        >
          {kind === 'arrow' && (
            <defs>
              <marker
                id={`arrowhead-${shape.id}`}
                markerWidth="10"
                markerHeight="10"
                refX="8"
                refY="5"
                orient="auto"
              >
                <path d="M0,0 L10,5 L0,10" fill="none" stroke="var(--color-border-strong)" />
              </marker>
            </defs>
          )}
          <line
            x1={0}
            y1={0}
            x2={size.width}
            y2={size.height}
            markerEnd={kind === 'arrow' ? `url(#arrowhead-${shape.id})` : undefined}
          />
        </svg>
      )}
    </div>
  );
}
