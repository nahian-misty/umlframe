import { useState, type KeyboardEvent } from 'react';

import styles from './EditableProjectName.module.css';

interface EditableProjectNameProps {
  name: string;
  /** Resolves once the new name is saved; the field stays open until then. */
  onRename: (name: string) => Promise<void>;
}

export function EditableProjectName({ name, onRename }: EditableProjectNameProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState(name);
  const [isSaving, setIsSaving] = useState(false);

  const startEditing = () => {
    setDraft(name);
    setIsEditing(true);
  };

  const commit = async () => {
    if (isSaving) return;
    const next = draft.trim();
    if (!next || next === name) {
      setIsEditing(false);
      return;
    }
    setIsSaving(true);
    try {
      await onRename(next);
    } finally {
      setIsSaving(false);
      setIsEditing(false);
    }
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter') {
      event.currentTarget.blur();
    } else if (event.key === 'Escape') {
      setDraft(name);
      setIsEditing(false);
    }
  };

  if (isEditing) {
    return (
      <input
        className={styles.input}
        value={draft}
        autoFocus
        maxLength={255}
        aria-label="Project name"
        disabled={isSaving}
        onFocus={(e) => e.currentTarget.select()}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={() => void commit()}
        onKeyDown={handleKeyDown}
      />
    );
  }

  return (
    <button type="button" className={styles.name} title="Click to rename" onClick={startEditing}>
      {name}
    </button>
  );
}
