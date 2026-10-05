import { useState, type PointerEvent as ReactPointerEvent } from 'react';

import type { ActivityNode } from '../../types/activity';
import styles from './ActivityNodeView.module.css';

interface ActivityNodeViewProps {
  node: ActivityNode;
  isSelected: boolean;
  isPendingConnectSource: boolean;
  onPointerDown: (event: ReactPointerEvent<HTMLDivElement>) => void;
  onUpdateLabel: (label: string) => void;
}

const LABELLED_TYPES: ActivityNode['type'][] = ['action', 'decision'];

export function ActivityNodeView({
  node,
  isSelected,
  isPendingConnectSource,
  onPointerDown,
  onUpdateLabel,
}: ActivityNodeViewProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState('');
  const { type, position, size } = node;
  const canEditLabel = LABELLED_TYPES.includes(type);

  const startEditing = () => {
    if (!canEditLabel) return;
    setDraft(node.label);
    setIsEditing(true);
  };

  const commit = () => {
    onUpdateLabel(draft);
    setIsEditing(false);
  };

  const classes = [
    styles.node,
    styles[type],
    isSelected ? styles.selected : '',
    isPendingConnectSource ? styles.pending : '',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <div
      className={classes}
      style={{ left: position.x, top: position.y, width: size.width, height: size.height }}
      onPointerDown={onPointerDown}
      onDoubleClick={startEditing}
      data-node-id={node.id}
    >
      {type === 'decision' && (
        <svg
          className={styles.diamond}
          viewBox="0 0 100 100"
          preserveAspectRatio="none"
          aria-hidden="true"
        >
          <polygon points="50,1 99,50 50,99 1,50" vectorEffect="non-scaling-stroke" />
        </svg>
      )}
      {type === 'end' && <div className={styles.endDot} />}
      {canEditLabel &&
        (isEditing ? (
          <input
            className={styles.input}
            autoFocus
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onBlur={commit}
            onKeyDown={(e) => {
              if (e.key === 'Enter') commit();
              if (e.key === 'Escape') setIsEditing(false);
            }}
          />
        ) : (
          <span className={styles.label}>{node.label || 'double-click to edit'}</span>
        ))}
    </div>
  );
}
