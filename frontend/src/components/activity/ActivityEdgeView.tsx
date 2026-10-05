import { useState, type MouseEvent as ReactMouseEvent } from 'react';

import { useCssColors } from '../../hooks/useCssColors';
import { nodeAnchor } from '../../utils/activityGeometry';
import { ACTIVITY_BACK_EDGE_OFFSET } from '../../utils/constants';
import { rectCenter, type Point, type Rect } from '../../utils/geometry';
import type { ActivityEdge, ActivityNode } from '../../types/activity';
import styles from './ActivityEdgeView.module.css';

interface ActivityEdgeViewProps {
  edge: ActivityEdge;
  source: ActivityNode;
  target: ActivityNode;
  isSelected: boolean;
  onSelect: () => void;
  onUpdateLabel: (label: string) => void;
}

const EDIT_BOX = { width: 64, height: 20 };
export const ACTIVITY_ARROW_MARKER_ID = 'activity-arrow';

const EDGE_COLOR_VARS = {
  line: '--color-text-muted',
  selected: '--color-selection',
  text: '--color-text',
  surface: '--color-surface',
};
const EDGE_STROKE = 1.75;
const EDGE_HIT_WIDTH = 14;
const EDGE_STROKE_SELECTED = 2.5;
const EDGE_LABEL_FONT_SIZE = 12;
const EDGE_LABEL_FONT_WEIGHT = 600;

function rectOf(node: ActivityNode): Rect {
  return {
    x: node.position.x,
    y: node.position.y,
    width: node.size.width,
    height: node.size.height,
  };
}

/** Shared arrowhead for every activity edge; render once inside the canvas <svg>. */
export function ActivityMarkerDefs() {
  const colors = useCssColors(EDGE_COLOR_VARS);
  return (
    <defs>
      <marker
        id={ACTIVITY_ARROW_MARKER_ID}
        viewBox="0 0 10 10"
        refX="9"
        refY="5"
        markerWidth="9"
        markerHeight="9"
        orient="auto-start-reverse"
      >
        <path d="M0,1 L10,5 L0,9 Z" fill={colors.text} />
      </marker>
    </defs>
  );
}

export function ActivityEdgeView({
  edge,
  source,
  target,
  isSelected,
  onSelect,
  onUpdateLabel,
}: ActivityEdgeViewProps) {
  const colors = useCssColors(EDGE_COLOR_VARS);
  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState('');

  const sourceRect = rectOf(source);
  const targetRect = rectOf(target);
  const sourceCenter = rectCenter(sourceRect);
  const targetCenter = rectCenter(targetRect);

  // An edge that climbs back up the diagram (a loop's back edge) bows out beside
  // the loop body, on whichever side the body sits relative to the loop header,
  // so it never has to cross the header's other outgoing edge (the loop exit).
  const isBackEdge = targetCenter.y < sourceCenter.y;
  const bowLeft = sourceCenter.x <= targetCenter.x;
  const bend: Point | null = isBackEdge
    ? {
        x: bowLeft
          ? Math.min(sourceRect.x, targetRect.x) - ACTIVITY_BACK_EDGE_OFFSET
          : Math.max(sourceRect.x + sourceRect.width, targetRect.x + targetRect.width) +
            ACTIVITY_BACK_EDGE_OFFSET,
        y: (sourceCenter.y + targetCenter.y) / 2,
      }
    : null;

  const start = nodeAnchor(source.type, sourceRect, bend ?? targetCenter);
  const end = nodeAnchor(target.type, targetRect, bend ?? sourceCenter);
  const path = bend
    ? `M${start.x},${start.y} Q${bend.x},${bend.y} ${end.x},${end.y}`
    : `M${start.x},${start.y} L${end.x},${end.y}`;
  const labelAt: Point = bend
    ? { x: (start.x + 2 * bend.x + end.x) / 4, y: (start.y + 2 * bend.y + end.y) / 4 }
    : { x: (start.x + end.x) / 2, y: (start.y + end.y) / 2 };

  const commit = () => {
    onUpdateLabel(draft);
    setIsEditing(false);
  };

  const select = (e: ReactMouseEvent) => {
    e.stopPropagation();
    onSelect();
  };

  return (
    <g>
      <path
        className={styles.hitArea}
        d={path}
        fill="none"
        stroke="transparent"
        strokeWidth={EDGE_HIT_WIDTH}
        onClick={select}
      />
      <path
        className={styles.line}
        d={path}
        fill="none"
        stroke={isSelected ? colors.selected : colors.line}
        strokeWidth={isSelected ? EDGE_STROKE_SELECTED : EDGE_STROKE}
        markerEnd={`url(#${ACTIVITY_ARROW_MARKER_ID})`}
      />
      {isEditing ? (
        <foreignObject
          x={labelAt.x - EDIT_BOX.width / 2}
          y={labelAt.y - EDIT_BOX.height / 2}
          width={EDIT_BOX.width}
          height={EDIT_BOX.height}
        >
          <input
            className={styles.editInput}
            autoFocus
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onBlur={commit}
            onKeyDown={(e) => {
              if (e.key === 'Enter') commit();
              if (e.key === 'Escape') setIsEditing(false);
            }}
            onClick={(e) => e.stopPropagation()}
          />
        </foreignObject>
      ) : (
        <text
          className={styles.label}
          fill={colors.text}
          fontSize={EDGE_LABEL_FONT_SIZE}
          fontWeight={EDGE_LABEL_FONT_WEIGHT}
          x={labelAt.x + 6}
          y={labelAt.y - 6}
          onClick={select}
          onDoubleClick={(e) => {
            e.stopPropagation();
            setDraft(edge.label);
            setIsEditing(true);
          }}
        >
          {edge.label || (isSelected ? 'double-click: guard' : '')}
        </text>
      )}
    </g>
  );
}
