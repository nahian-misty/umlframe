import { useState } from 'react';

import { computeEdgeAnchor, type Rect } from '../../utils/geometry';
import type { RelationshipState } from '../../types/diagram';
import { RELATIONSHIP_STYLES } from './relationshipStyles';
import styles from './RelationshipEdge.module.css';

type EditField = 'label' | 'source' | 'destination' | null;

interface RelationshipEdgeProps {
  relationship: RelationshipState;
  sourceBox: Rect;
  destinationBox: Rect;
  isSelected: boolean;
  onSelect: () => void;
  onUpdateLabel: (label: string) => void;
  onUpdateMultiplicity: (which: 'source' | 'destination', value: string) => void;
}

const EDIT_BOX_SIZE = { width: 44, height: 16 };

export function RelationshipEdge({
  relationship,
  sourceBox,
  destinationBox,
  isSelected,
  onSelect,
  onUpdateLabel,
  onUpdateMultiplicity,
}: RelationshipEdgeProps) {
  const [editingField, setEditingField] = useState<EditField>(null);
  const [editValue, setEditValue] = useState('');

  const sourceAnchor = computeEdgeAnchor(sourceBox, destinationBox);
  const destAnchor = computeEdgeAnchor(destinationBox, sourceBox);
  const style = RELATIONSHIP_STYLES[relationship.type];
  const midpoint = {
    x: (sourceAnchor.x + destAnchor.x) / 2,
    y: (sourceAnchor.y + destAnchor.y) / 2,
  };

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
      <line
        className={styles.hitArea}
        x1={sourceAnchor.x}
        y1={sourceAnchor.y}
        x2={destAnchor.x}
        y2={destAnchor.y}
        onClick={(e) => {
          e.stopPropagation();
          onSelect();
        }}
      />
      <line
        className={styles.line}
        x1={sourceAnchor.x}
        y1={sourceAnchor.y}
        x2={destAnchor.x}
        y2={destAnchor.y}
        stroke={isSelected ? 'var(--color-selection)' : 'var(--color-text-muted)'}
        strokeWidth={isSelected ? 2 : 1.5}
        strokeDasharray={style.dashed ? '6,4' : undefined}
        markerStart={style.markerStart ? `url(#${style.markerStart})` : undefined}
        markerEnd={style.markerEnd ? `url(#${style.markerEnd})` : undefined}
      />

      {editingField === 'source' ? (
        renderEditBox(sourceAnchor.x, sourceAnchor.y - 12)
      ) : (
        <text
          className={styles.multiplicity}
          x={sourceAnchor.x}
          y={sourceAnchor.y - 8}
          textAnchor="middle"
          onClick={(e) => {
            e.stopPropagation();
            startEdit('source', relationship.multiplicity.source);
          }}
        >
          {relationship.multiplicity.source}
        </text>
      )}

      {editingField === 'destination' ? (
        renderEditBox(destAnchor.x, destAnchor.y - 12)
      ) : (
        <text
          className={styles.multiplicity}
          x={destAnchor.x}
          y={destAnchor.y - 8}
          textAnchor="middle"
          onClick={(e) => {
            e.stopPropagation();
            startEdit('destination', relationship.multiplicity.destination);
          }}
        >
          {relationship.multiplicity.destination}
        </text>
      )}

      {editingField === 'label' ? (
        renderEditBox(midpoint.x, midpoint.y)
      ) : (
        <text
          className={styles.label}
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
