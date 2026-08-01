import { useContext } from 'react';
import { CheckCircle2, Info, XCircle, X } from 'lucide-react';

import { ToastContext } from './ToastProvider';
import { IconButton } from './IconButton';
import styles from './Toast.module.css';

const ICONS = {
  success: CheckCircle2,
  error: XCircle,
  info: Info,
} as const;

export function ToastStack() {
  const context = useContext(ToastContext);
  if (!context || context.toasts.length === 0) return null;

  return (
    <div className={styles.stack}>
      {context.toasts.map((toast) => {
        const Icon = ICONS[toast.tone];
        return (
          <div key={toast.id} className={`${styles.toast} ${styles[toast.tone]}`} role="status">
            <Icon size={16} />
            <span className={styles.message}>{toast.message}</span>
            <IconButton
              icon={X}
              aria-label="Dismiss notification"
              size="sm"
              onClick={() => context.dismissToast(toast.id)}
            />
          </div>
        );
      })}
    </div>
  );
}
