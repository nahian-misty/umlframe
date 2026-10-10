import { useState, type PointerEvent as ReactPointerEvent } from 'react';

import type { AttributeState, MethodState, UmlClassState } from '../../types/diagram';
import type { ClassKind } from '../../types/uml';
import { AttributeRow } from './AttributeRow';
import { MethodRow } from './MethodRow';
import styles from './UmlClassBox.module.css';

interface UmlClassBoxProps {
  cls: UmlClassState;
  isSelected: boolean;
  isPendingRelationshipSource: boolean;
  onPointerDownBox: (event: ReactPointerEvent<HTMLDivElement>) => void;
  onUpdate: (patch: Partial<Omit<UmlClassState, 'id'>>) => void;
}

const KIND_LABELS: Record<ClassKind, string> = {
  class: '«class»',
  abstract: '«abstract»',
  interface: '«interface»',
};
const KIND_ORDER: ClassKind[] = ['class', 'abstract', 'interface'];

function newAttribute(classId: string): AttributeState {
  return {
    id: crypto.randomUUID(),
    name: `${classId}Field`,
    datatype: 'String',
    visibility: 'private',
    defaultValue: null,
    static: false,
    final: false,
  };
}

function newMethod(): MethodState {
  return {
    id: crypto.randomUUID(),
    name: 'method',
    visibility: 'public',
    parameters: [],
    returnType: 'void',
    static: false,
    abstract: false,
  };
}

export function UmlClassBox({
  cls,
  isSelected,
  isPendingRelationshipSource,
  onPointerDownBox,
  onUpdate,
}: UmlClassBoxProps) {
  // Rows created via "+ attribute"/"+ method" start expanded for editing;
  // rows already present when the box mounted (loaded from a document) start
  // collapsed. Tracked by id since AttributeState/MethodState are pure data
  // shared with the wire format — this is UI-only and never persisted.
  const [autoExpandIds, setAutoExpandIds] = useState<Set<string>>(new Set());

  const updateAttribute = (id: string, patch: Partial<Omit<AttributeState, 'id'>>) => {
    onUpdate({ attributes: cls.attributes.map((a) => (a.id === id ? { ...a, ...patch } : a)) });
  };
  const deleteAttribute = (id: string) => {
    onUpdate({ attributes: cls.attributes.filter((a) => a.id !== id) });
  };
  const addAttribute = () => {
    const attribute = newAttribute(cls.name || 'new');
    setAutoExpandIds((prev) => new Set(prev).add(attribute.id));
    onUpdate({ attributes: [...cls.attributes, attribute] });
  };

  const updateMethod = (id: string, patch: Partial<Omit<MethodState, 'id'>>) => {
    onUpdate({ methods: cls.methods.map((m) => (m.id === id ? { ...m, ...patch } : m)) });
  };
  const deleteMethod = (id: string) => {
    onUpdate({ methods: cls.methods.filter((m) => m.id !== id) });
  };
  const addMethod = () => {
    const method = newMethod();
    setAutoExpandIds((prev) => new Set(prev).add(method.id));
    onUpdate({ methods: [...cls.methods, method] });
  };

  const boxClassName = [
    styles.box,
    isSelected ? styles.selected : '',
    isPendingRelationshipSource ? styles.pendingSource : '',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <div
      className={boxClassName}
      style={{
        left: cls.position.x,
        top: cls.position.y,
        width: cls.size.width,
        minHeight: cls.size.height,
      }}
      onPointerDown={onPointerDownBox}
      data-class-id={cls.id}
    >
      <div className={styles.nameCompartment}>
        <div className={styles.kindRow}>
          <label
            className={styles.kindLabel}
            title="Change between class, abstract class and interface"
          >
            <span className={styles.kindText}>{KIND_LABELS[cls.kind]}</span>
            <select
              className={styles.kindSelect}
              value={cls.kind}
              aria-label="Class kind"
              onChange={(e) => onUpdate({ kind: e.target.value as ClassKind })}
            >
              {KIND_ORDER.map((kind) => (
                <option key={kind} value={kind}>
                  {KIND_LABELS[kind]}
                </option>
              ))}
            </select>
          </label>
        </div>
        <input
          className={`${styles.nameInput} ${cls.kind === 'abstract' ? styles.abstractName : ''}`}
          value={cls.name}
          onChange={(e) => onUpdate({ name: e.target.value })}
        />
      </div>

      <div className={styles.compartment}>
        {cls.attributes.map((attribute) => (
          <AttributeRow
            key={attribute.id}
            attribute={attribute}
            startExpanded={autoExpandIds.has(attribute.id)}
            onChange={(patch) => updateAttribute(attribute.id, patch)}
            onDelete={() => deleteAttribute(attribute.id)}
          />
        ))}
        <button className={styles.addRow} data-export-hide onClick={addAttribute} type="button">
          + attribute
        </button>
      </div>

      <div className={styles.compartment}>
        {cls.methods.map((method) => (
          <MethodRow
            key={method.id}
            method={method}
            startExpanded={autoExpandIds.has(method.id)}
            onChange={(patch) => updateMethod(method.id, patch)}
            onDelete={() => deleteMethod(method.id)}
          />
        ))}
        <button className={styles.addRow} data-export-hide onClick={addMethod} type="button">
          + method
        </button>
      </div>
    </div>
  );
}
