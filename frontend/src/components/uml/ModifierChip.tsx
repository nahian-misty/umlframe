import styles from './ModifierChip.module.css';

interface ModifierChipProps {
  label: string;
  active: boolean;
  onToggle: () => void;
}

export function ModifierChip({ label, active, onToggle }: ModifierChipProps) {
  return (
    <button
      type="button"
      className={`${styles.chip} ${active ? styles.active : ''}`}
      aria-pressed={active}
      onClick={onToggle}
      title={`Toggle "${label}"`}
    >
      {label}
    </button>
  );
}
