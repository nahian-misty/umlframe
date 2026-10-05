import { useState } from 'react';

import { useCssColors } from '../../hooks/useCssColors';
import type { Point } from '../../utils/geometry';
import type { RelationshipState } from '../../types/diagram';
import { RELATIONSHIP_STYLES } from './relationshipStyles';
import styles from './RelationshipEdge.module.css';

type EditField = 'label' | 'source' | 'destination' | null;

interface RelationshipEdgeProps {
  relationship: RelationshipState;
  points: Point[];
  isSelected: boolean;
  onSelect: () => void;
  onUpdateLabel: (label: string) => void;
  onUpdateMultiplicity: (which: 'source' | 'destination', value: string) => void;
}

const EDGE_COLOR_VARS = {
  line: '--color-text-muted',
  selected: '--color-selection',
  text: '--color-text',
  muted: '--color-text-muted',
};
const EDGE_STROKE = 1.5;
const EDGE_HIT_WIDTH = 14;
const EDGE_STROKE_SELECTED = 2;
const EDGE_TEXT_FONT_SIZE = 11;
const EDIT_BOX_SIZE = { width: 44, height: 16 };
const END_LABEL_ALONG = 14;
const END_LABEL_ACROSS = 10;

/** Midpoint of the longest segment, so the label sits on a stretch of line with room for it. */
function labelAnchor(points: Point[]): Point {
  let best = { from: points[0], to: points[points.length - 1], length: -1 };
  for (let i = 1; i < points.length; i++) {
    const length =
      Math.abs(points[i].x - points[i - 1].x) + Math.abs(points[i].y - points[i - 1].y);
    if (length > best.length) best = { from: points[i - 1], to: points[i], length };
  }
  return { x: (best.from.x + best.to.x) / 2, y: (best.from.y + best.to.y) / 2 };
}

/** Multiplicity label position: just along the line from the box and to one side of it. */
function endLabelAnchor(end: Point, next: Point): Point {
  const dx = Math.sign(next.x - end.x);
  const dy = Math.sign(next.y - end.y);
  return dx !== 0
    ? { x: end.x + dx * END_LABEL_ALONG, y: end.y - END_LABEL_ACROSS + 4 }
    : { x: end.x + END_LABEL_ACROSS + 4, y: end.y + dy * END_LABEL_ALONG };
}

export function RelationshipEdge({
  relationship,
  points,
  isSelected,
  onSelect,
  onUpdateLabel,
  onUpdateMultiplicity,
}: RelationshipEdgeProps) {
  const colors = useCssColors(EDGE_COLOR_VARS);
  const [editingField, setEditingField] = useState<EditField>(null);
  const [editValue, setEditValue] = useState('');

  const destAnchor = points[points.length - 1];
  const style = RELATIONSHIP_STYLES[relationship.type];
  const path = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x},${p.y}`).join(' ');
  const midpoint = labelAnchor(points);
  const sourceLabelAt = endLabelAnchor(points[0], points[1]);
  const destLabelAt = endLabelAnchor(destAnchor, points[points.length - 2]);

  const startEdit = (field: EditField, currentValue: string) => {
    setEditingField(field);
    setEditValue(currentValue);
  };

  const commitEdit = () => {
    if (editingField === 'label') onUpdateLabel(editValue);
    if (editingField === 'source') onUpdateMultiplicity('source', editValue);
    if (editingField === 'destination') onUpdateMultiplicity('destination', editValue);
    setEditingField(null);
  };

  const renderEditBox = (x: number, y: number) => (
    <foreignObject
      x={x - EDIT_BOX_SIZE.width / 2}
      y={y - EDIT_BOX_SIZE.height / 2}
      width={EDIT_BOX_SIZE.width}
      height={EDIT_BOX_SIZE.height}
    >
      <input
        className={styles.editInput}
        autoFocus
        value={editValue}
        onChange={(e) => setEditValue(e.target.value)}
        onBlur={commitEdit}
        onKeyDown={(e) => {
          if (e.key === 'Enter') commitEdit();
          if (e.key === 'Escape') setEditingField(null);
        }}
        onClick={(e) => e.stopPropagation()}
      />
    </foreignObject>
  );

  return (
    <g>
      <path
        className={styles.hitArea}
        d={path}
        fill="none"
        stroke="transparent"
        strokeWidth={EDGE_HIT_WIDTH}
        onClick={(e) => {
          e.stopPropagation();
          onSelect();
        }}
      />
      <path
        className={styles.line}
        d={path}
        fill="none"
        stroke={isSelected ? colors.selected : colors.line}
        strokeWidth={isSelected ? EDGE_STROKE_SELECTED : EDGE_STROKE}
        strokeLinejoin="round"
        strokeDasharray={style.dashed ? '6,4' : undefined}
        markerStart={style.markerStart ? `url(#${style.markerStart})` : undefined}
        markerEnd={style.markerEnd ? `url(#${style.markerEnd})` : undefined}
      />

      {style.showMultiplicity &&
        (editingField === 'source' ? (
          renderEditBox(sourceLabelAt.x, sourceLabelAt.y - 4)
        ) : (
          <text
            className={styles.multiplicity}
            fill={colors.muted}
            fontSize={EDGE_TEXT_FONT_SIZE}
            x={sourceLabelAt.x}
            y={sourceLabelAt.y}
            textAnchor="middle"
            onClick={(e) => {
              e.stopPropagation();
              startEdit('source', relationship.multiplicity.source);
            }}
          >
            {relationship.multiplicity.source}
          </text>
        ))}

      {style.showMultiplicity &&
        (editingField === 'destination' ? (
          renderEditBox(destLabelAt.x, destLabelAt.y - 4)
        ) : (
          <text
            className={styles.multiplicity}
            fill={colors.muted}
            fontSize={EDGE_TEXT_FONT_SIZE}
            x={destLabelAt.x}
            y={destLabelAt.y}
            textAnchor="middle"
            onClick={(e) => {
              e.stopPropagation();
              startEdit('destination', relationship.multiplicity.destination);
            }}
          >
            {relationship.multiplicity.destination}
          </text>
        ))}

      {editingField === 'label' ? (
        renderEditBox(midpoint.x, midpoint.y)
      ) : (
        <text
          className={styles.label}
          fill={colors.text}
          fontSize={EDGE_TEXT_FONT_SIZE}
          x={midpoint.x}
          y={midpoint.y}
          textAnchor="middle"
          onClick={(e) => {
            e.stopPropagation();
            startEdit('label', relationship.label);
          }}
        >
          {relationship.label || ' '}
        </text>
      )}
    </g>
  );
}
