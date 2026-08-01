import { X } from 'lucide-react';

import type { AttributeState } from '../../types/diagram';
import type { Visibility } from '../../types/uml';
import { ModifierChip } from './ModifierChip';
import styles from './AttributeRow.module.css';

interface AttributeRowProps {
  attribute: AttributeState;
  onChange: (patch: Partial<Omit<AttributeState, 'id'>>) => void;
  onDelete: () => void;
}

export function AttributeRow({ attribute, onChange, onDelete }: AttributeRowProps) {
  return (
    <div className={styles.entry}>
      <div className={styles.fieldRow}>
        <label className={styles.field} style={{ flex: '0 0 100px' }}>
          <span className={styles.fieldLabel}>Visibility</span>
          <select
            className={styles.visibility}
            value={attribute.visibility}
            onChange={(e) => onChange({ visibility: e.target.value as Visibility })}
          >
            <option value="public">+ public</option>
            <option value="private">- private</option>
            <option value="protected"># protected</option>
            <option value="package">~ package</option>
          </select>
        </label>
        <label className={styles.field} style={{ flex: '1 1 auto' }}>
          <span className={styles.fieldLabel}>Name</span>
          <input
            className={styles.input}
            value={attribute.name}
            placeholder="fieldName"
            onChange={(e) => onChange({ name: e.target.value })}
          />
        </label>
      </div>

      <div className={styles.fieldRow}>
        <label className={styles.field} style={{ flex: '1 1 auto' }}>
          <span className={styles.fieldLabel}>Type</span>
          <input
            className={styles.input}
            value={attribute.datatype}
            placeholder="String"
            onChange={(e) => onChange({ datatype: e.target.value })}
          />
        </label>
        <label className={styles.field} style={{ flex: '0 0 88px' }}>
          <span className={styles.fieldLabel}>Default value</span>
          <input
            className={styles.input}
            value={attribute.defaultValue ?? ''}
            placeholder="none"
            onChange={(e) =>
              onChange({ defaultValue: e.target.value === '' ? null : e.target.value })
            }
          />
        </label>
      </div>

      <div className={styles.modifierRow}>
        <ModifierChip
          label="static"
          active={attribute.static}
          onToggle={() => onChange({ static: !attribute.static })}
        />
        <ModifierChip
          label="final"
          active={attribute.final}
          onToggle={() => onChange({ final: !attribute.final })}
        />
        <button
          className={styles.deleteButton}
          onClick={onDelete}
          title="Delete attribute"
          type="button"
        >
          <X size={12} />
          Remove
        </button>
      </div>
    </div>
  );
}
