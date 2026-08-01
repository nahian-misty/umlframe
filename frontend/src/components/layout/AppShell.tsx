import type { ReactNode } from 'react';

import { Header } from './Header';
import styles from '../../App.module.css';

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className={styles.appShell}>
      <Header />
      <div className={styles.appBody}>{children}</div>
    </div>
  );
}
