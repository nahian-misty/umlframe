import { Canvas } from '../canvas/Canvas';
import { Toolbar } from '../toolbar/Toolbar';
import styles from './Tabs.module.css';

export function UmlToCodeTab() {
  return (
    <div className={styles.workspace}>
      <div className={styles.canvasArea}>
        <Canvas />
      </div>
      <Toolbar />
    </div>
  );
}
