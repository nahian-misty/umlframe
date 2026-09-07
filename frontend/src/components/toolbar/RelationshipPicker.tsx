import { useDiagramContext } from '../../context/DiagramContext';
import { RELATIONSHIP_LABELS } from '../uml/relationshipStyles';
import type { RelationshipType } from '../../types/uml';
import { Button } from '../common/Button';
import shared from './toolbarButtons.module.css';
import styles from './RelationshipPicker.module.css';

const TYPES = Object.keys(RELATIONSHIP_LABELS) as RelationshipType[];

// Inheritance is drawn source (child) -> destination (parent), with the
// hollow triangle marker at the parent end — clarify that explicitly since
// "source"/"destination" alone reads ambiguously for which end is which.
const SOURCE_HINTS: Partial<Record<RelationshipType, string>> = {
  inheritance: 'Click the subclass (child)…',
};
const DESTINATION_HINTS: Partial<Record<RelationshipType, string>> = {
  inheritance: 'Click the superclass (parent)…',
};

export function RelationshipPicker() {
  const diagram = useDiagramContext();

  const isActive = (type: RelationshipType) =>
    diagram.activeTool === 'relationship' && diagram.activeRelationshipType === type;

  const selectType = (type: RelationshipType) => {
    diagram.setActiveRelationshipType(type);
    diagram.setActiveTool('relationship');
  };

  return (
    <div className={shared.group}>
      {TYPES.map((type) => (
        <Button
          key={type}
          size="sm"
          active={isActive(type)}
          onClick={() => selectType(type)}
          title={RELATIONSHIP_LABELS[type]}
        >
          {RELATIONSHIP_LABELS[type]}
        </Button>
      ))}
      {diagram.activeTool === 'relationship' && (
        <span className={styles.hint}>
          {diagram.pendingRelationshipSource
            ? (diagram.activeRelationshipType &&
                DESTINATION_HINTS[diagram.activeRelationshipType]) ??
              'Click the destination class…'
            : (diagram.activeRelationshipType && SOURCE_HINTS[diagram.activeRelationshipType]) ??
              'Click the source class…'}
        </span>
      )}
    </div>
  );
}
