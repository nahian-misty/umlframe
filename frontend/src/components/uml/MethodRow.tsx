import { useEffect, useRef, useState, type FocusEvent } from 'react';
import { X } from 'lucide-react';

import type { MethodState, ParameterState } from '../../types/diagram';
import type { Visibility } from '../../types/uml';
import { ModifierChip } from './ModifierChip';
import { visibilitySymbol } from './visibilitySymbol';
import styles from './MethodRow.module.css';

interface MethodRowProps {
  method: MethodState;
  startExpanded: boolean;
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

function summarize(method: MethodState): string {
  const modifiers = [method.static && 'static', method.abstract && 'abstract']
    .filter(Boolean)
    .join(' ');
  const base = `${visibilitySymbol(method.visibility)}${method.name}(${paramsToText(method.parameters)}): ${method.returnType}`;
  return modifiers ? `${base} {${modifiers}}` : base;
}

export function MethodRow({ method, startExpanded, onChange, onDelete }: MethodRowProps) {
  const [paramsText, setParamsText] = useState(() => paramsToText(method.parameters));
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
      onChange({ parameters: textToParams(paramsText) });
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
        {summarize(method)}
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
            ref={nameInputRef}
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
