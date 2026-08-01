import { useState } from 'react';
import { X } from 'lucide-react';

import type { MethodState, ParameterState } from '../../types/diagram';
import type { Visibility } from '../../types/uml';
import { ModifierChip } from './ModifierChip';
import styles from './MethodRow.module.css';

interface MethodRowProps {
  method: MethodState;
  onChange: (patch: Partial<Omit<MethodState, 'id'>>) => void;
  onDelete: () => void;
}

// NOTE: this naively splits params on "," and ":" — it will misparse a
// datatype that itself contains a comma (e.g. "Map<String, Integer>").
// Known limitation, not addressed by this layout pass.
function paramsToText(parameters: ParameterState[]): string {
  return parameters.map((p) => (p.datatype ? `${p.name}: ${p.datatype}` : p.name)).join(', ');
}

function textToParams(text: string): ParameterState[] {
  return text
    .split(',')
    .map((part) => part.trim())
    .filter((part) => part.length > 0)
    .map((part) => {
      const [name, datatype] = part.split(':').map((s) => s.trim());
      return { name: name ?? '', datatype: datatype ?? '' };
    });
}

export function MethodRow({ method, onChange, onDelete }: MethodRowProps) {
  const [paramsText, setParamsText] = useState(() => paramsToText(method.parameters));

  return (
    <div className={styles.entry}>
      <div className={styles.fieldRow}>
        <label className={styles.field} style={{ flex: '0 0 100px' }}>
          <span className={styles.fieldLabel}>Visibility</span>
          <select
            className={styles.visibility}
            value={method.visibility}
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
            value={method.name}
            placeholder="methodName"
            onChange={(e) => onChange({ name: e.target.value })}
          />
        </label>
      </div>

      <div className={styles.fieldRow}>
        <label className={styles.field} style={{ flex: '1 1 auto' }}>
          <span className={styles.fieldLabel}>Parameters</span>
          <input
            className={styles.input}
            value={paramsText}
            placeholder="a: Type, b: Type"
            onChange={(e) => setParamsText(e.target.value)}
            onBlur={() => onChange({ parameters: textToParams(paramsText) })}
          />
        </label>
        <label className={styles.field} style={{ flex: '0 0 88px' }}>
          <span className={styles.fieldLabel}>Return type</span>
          <input
            className={styles.input}
            value={method.returnType}
            placeholder="void"
            onChange={(e) => onChange({ returnType: e.target.value })}
          />
        </label>
      </div>

      <div className={styles.modifierRow}>
        <ModifierChip
          label="static"
          active={method.static}
          onToggle={() => onChange({ static: !method.static })}
        />
        <ModifierChip
          label="abstract"
          active={method.abstract}
          onToggle={() => onChange({ abstract: !method.abstract })}
        />
        <button
          className={styles.deleteButton}
          onClick={onDelete}
          title="Delete method"
          type="button"
        >
          <X size={12} />
          Remove
        </button>
      </div>
    </div>
  );
}
