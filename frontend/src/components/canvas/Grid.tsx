import { CANVAS_WIDTH, CANVAS_HEIGHT, GRID_SIZE } from '../../utils/constants';
import styles from './Grid.module.css';

/** The bounded canvas "page" — sized in plain canvas-space pixels so the
 * parent content layer's pan/zoom transform scales it along with everything
 * else, exactly like class boxes and shapes. */
export function Grid() {
  return (
    <div
      className={styles.grid}
      style={{
        width: CANVAS_WIDTH,
        height: CANVAS_HEIGHT,
        backgroundSize: `${GRID_SIZE}px ${GRID_SIZE}px`,
      }}
    />
  );
}
