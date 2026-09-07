import type { ReactNode } from 'react';
import { X } from 'lucide-react';

import { IconButton } from './IconButton';
import styles from './Modal.module.css';

interface ModalProps {
  title: string;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
  wide?: boolean;
}

export function Modal({ title, onClose, children, footer, wide = false }: ModalProps) {
  return (
    <div className={styles.backdrop} onClick={onClose}>
      <div
        className={wide ? `${styles.modal} ${styles.wide}` : styles.modal}
        onClick={(e) => e.stopPropagation()}
      >
        <div className={styles.header}>
          <strong className={styles.title}>{title}</strong>
          <IconButton icon={X} aria-label="Close" size="sm" onClick={onClose} />
        </div>

        <div className={styles.body}>{children}</div>

        {footer && <div className={styles.footer}>{footer}</div>}
      </div>
    </div>
  );
}
