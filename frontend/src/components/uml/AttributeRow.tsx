import { useEffect, useRef, useState, type FocusEvent } from 'react';
import { X } from 'lucide-react';

import type { AttributeState } from '../../types/diagram';
import type { Visibility } from '../../types/uml';
import { ModifierChip } from './ModifierChip';
import { visibilitySymbol } from './visibilitySymbol';
import styles from './AttributeRow.module.css';

interface AttributeRowProps {
  attribute: AttributeState;
  startExpanded: boolean;
  onChange: (patch: Partial<Omit<AttributeState, 'id'>>) => void;
  onDelete: () => void;
}

function summarize(attribute: AttributeState): string {
  const modifiers = [attribute.static && 'static', attribute.final && 'final']
    .filter(Boolean)
    .join(' ');
  const base = `${visibilitySymbol(attribute.visibility)}${attribute.name}: ${attribute.datatype}`;
  return modifiers ? `${base} {${modifiers}}` : base;
}

export function AttributeRow({ attribute, startExpanded, onChange, onDelete }: AttributeRowProps) {
  const [isExpanded, setIsExpanded] = useState(startExpanded);
  const entryRef = useRef<HTMLDivElement>(null);
  const nameInputRef = useRef<HTMLInputElement>(null);

  // Expanding never happens mid-edit (only via the collapsed summary, which
  // has no focusable field of its own), so nothing is focused yet — without
  // this, clicking away wouldn't produce a blur to collapse back on.
  useEffect(() => {
    if (isExpanded) nameInputRef.current?.focus();
  }, [isExpanded]);

  const handleBlur = (e: FocusEvent<HTMLDivElement>) => {
    if (!entryRef.current?.contains(e.relatedTarget as Node | null)) {
      setIsExpanded(false);
    }
  };

  if (!isExpanded) {
    return (
      <div
        className={styles.summary}
        onClick={() => setIsExpanded(true)}
        title="Click to edit"
      >
        {summarize(attribute)}
      </div>
    );
  }

  return (
    <div className={styles.entry} ref={entryRef} onBlur={handleBlur}>
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
            ref={nameInputRef}
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
