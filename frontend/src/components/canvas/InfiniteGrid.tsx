import { GRID_COARSE_FACTOR, GRID_SIZE, MIN_GRID_SCREEN_SPACING } from '../../utils/constants';
import styles from './InfiniteGrid.module.css';

interface InfiniteGridProps {
  pan: { x: number; y: number };
  zoom: number;
}

/** Grid drawn on the viewport itself, offset by pan and scaled by zoom, so it never runs out. */
export function InfiniteGrid({ pan, zoom }: InfiniteGridProps) {
  let spacing = GRID_SIZE * zoom;
  // Zoomed far out, fine lines blur into a solid tint; draw every Nth line instead.
  while (spacing < MIN_GRID_SCREEN_SPACING) spacing *= GRID_COARSE_FACTOR;
  return (
    <div
      className={styles.grid}
      style={{
        backgroundSize: `${spacing}px ${spacing}px`,
        backgroundPosition: `${pan.x}px ${pan.y}px`,
      }}
    />
  );
}
