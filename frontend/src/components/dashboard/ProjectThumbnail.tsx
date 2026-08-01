import { LayoutGrid } from 'lucide-react';

import type { ClassBoxSummary } from '../../api/projectsApi';
import styles from './ProjectThumbnail.module.css';

const VIEW_WIDTH = 240;
const VIEW_HEIGHT = 72;
const PADDING = 6;

interface ProjectThumbnailProps {
  classBoxes: ClassBoxSummary[];
}

export function ProjectThumbnail({ classBoxes }: ProjectThumbnailProps) {
  if (classBoxes.length === 0) {
    return (
      <div className={styles.placeholder}>
        <LayoutGrid size={20} />
      </div>
    );
  }

  const minX = Math.min(...classBoxes.map((box) => box.x));
  const minY = Math.min(...classBoxes.map((box) => box.y));
  const maxX = Math.max(...classBoxes.map((box) => box.x + box.width));
  const maxY = Math.max(...classBoxes.map((box) => box.y + box.height));

  const boundsWidth = Math.max(maxX - minX, 1);
  const boundsHeight = Math.max(maxY - minY, 1);
  const scale = Math.min(
    (VIEW_WIDTH - PADDING * 2) / boundsWidth,
    (VIEW_HEIGHT - PADDING * 2) / boundsHeight,
  );
  const offsetX = PADDING + (VIEW_WIDTH - PADDING * 2 - boundsWidth * scale) / 2;
  const offsetY = PADDING + (VIEW_HEIGHT - PADDING * 2 - boundsHeight * scale) / 2;

  return (
    <svg
      className={styles.svg}
      viewBox={`0 0 ${VIEW_WIDTH} ${VIEW_HEIGHT}`}
      preserveAspectRatio="xMidYMid meet"
      aria-hidden="true"
    >
      {classBoxes.map((box, i) => (
        <rect
          key={i}
          x={offsetX + (box.x - minX) * scale}
          y={offsetY + (box.y - minY) * scale}
          width={Math.max(box.width * scale, 2)}
          height={Math.max(box.height * scale, 2)}
          rx={1.5}
          className={styles.classBox}
        />
      ))}
    </svg>
  );
}
