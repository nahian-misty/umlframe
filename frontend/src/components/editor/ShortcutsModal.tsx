import { Modal } from '../common/Modal';
import styles from './ShortcutsModal.module.css';

const SHORTCUTS: { keys: string; action: string }[] = [
  { keys: 'Ctrl/Cmd + S', action: 'Save the project' },
  { keys: 'Ctrl/Cmd + Z', action: 'Undo' },
  { keys: 'Ctrl/Cmd + Shift + Z  or  Ctrl + Y', action: 'Redo' },
  { keys: 'Delete / Backspace', action: 'Delete the selection' },
  { keys: 'Ctrl/Cmd + D', action: 'Duplicate the selection' },
  { keys: 'Shift/Ctrl/Cmd + click', action: 'Add to the selection' },
  { keys: 'Esc', action: 'Clear the selection and return to the Select tool' },
  { keys: 'Ctrl/Cmd + scroll', action: 'Zoom at the cursor' },
  { keys: 'Middle-drag, or the Pan tool', action: 'Pan the canvas' },
  { keys: '?', action: 'Show this list' },
];

export function ShortcutsModal({ onClose }: { onClose: () => void }) {
  return (
    <Modal title="Keyboard shortcuts" onClose={onClose}>
      <dl className={styles.list}>
        {SHORTCUTS.map((shortcut) => (
          <div key={shortcut.keys} className={styles.row}>
            <dt>
              <kbd className={styles.keys}>{shortcut.keys}</kbd>
            </dt>
            <dd>{shortcut.action}</dd>
          </div>
        ))}
      </dl>
    </Modal>
  );
}
