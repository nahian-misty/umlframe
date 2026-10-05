import { useEffect, useRef, useState, type KeyboardEvent } from 'react';
import { ChevronDown, LogOut, Moon, Settings, Sun } from 'lucide-react';

import styles from './UserMenu.module.css';

interface UserMenuProps {
  email: string;
  resolvedTheme: 'light' | 'dark';
  onToggleTheme: () => void;
  onOpenAccount: () => void;
  onLogout: () => void;
}

export function UserMenu({ email, resolvedTheme, onToggleTheme, onOpenAccount, onLogout }: UserMenuProps) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!isOpen) return;
    const onPointerDown = (event: PointerEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) setIsOpen(false);
    };
    document.addEventListener('pointerdown', onPointerDown);
    return () => document.removeEventListener('pointerdown', onPointerDown);
  }, [isOpen]);

  useEffect(() => {
    if (isOpen) containerRef.current?.querySelector<HTMLElement>('[role="menuitem"]')?.focus();
  }, [isOpen]);

  const close = () => {
    setIsOpen(false);
    triggerRef.current?.focus();
  };

  const handleMenuKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'Escape') {
      event.preventDefault();
      close();
      return;
    }
    if (event.key !== 'ArrowDown' && event.key !== 'ArrowUp') return;
    event.preventDefault();
    const items = Array.from(
      containerRef.current?.querySelectorAll<HTMLElement>('[role="menuitem"]') ?? [],
    );
    const current = items.indexOf(document.activeElement as HTMLElement);
    const step = event.key === 'ArrowDown' ? 1 : -1;
    items[(current + step + items.length) % items.length]?.focus();
  };

  const isDark = resolvedTheme === 'dark';
  const initial = email.trim().charAt(0).toUpperCase() || '?';

  return (
    <div ref={containerRef} className={styles.container}>
      <button
        ref={triggerRef}
        type="button"
        className={styles.trigger}
        aria-haspopup="menu"
        aria-expanded={isOpen}
        aria-label={`Account menu for ${email}`}
        onClick={() => setIsOpen((open) => !open)}
      >
        <span className={styles.avatar} aria-hidden="true">
          {initial}
        </span>
        <ChevronDown size={14} aria-hidden="true" />
      </button>

      {isOpen && (
        <div role="menu" className={styles.menu} onKeyDown={handleMenuKeyDown}>
          <div className={styles.identity}>
            <span className={styles.identityLabel}>Signed in as</span>
            <span className={styles.identityEmail}>{email}</span>
          </div>
          <button
            type="button"
            role="menuitem"
            className={styles.item}
            onClick={() => {
              setIsOpen(false);
              onOpenAccount();
            }}
          >
            <Settings size={14} />
            Account settings
          </button>
          <button
            type="button"
            role="menuitem"
            className={styles.item}
            onClick={() => {
              onToggleTheme();
              close();
            }}
          >
            {isDark ? <Sun size={14} /> : <Moon size={14} />}
            {isDark ? 'Switch to light mode' : 'Switch to dark mode'}
          </button>
          <button
            type="button"
            role="menuitem"
            className={styles.item}
            onClick={() => {
              setIsOpen(false);
              onLogout();
            }}
          >
            <LogOut size={14} />
            Log out
          </button>
        </div>
      )}
    </div>
  );
}
