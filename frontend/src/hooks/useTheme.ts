import { useCallback, useEffect, useState } from 'react';

const STORAGE_KEY = 'umlframe-theme';

type StoredTheme = 'light' | 'dark' | null;

function readStoredTheme(): StoredTheme {
  const value = localStorage.getItem(STORAGE_KEY);
  return value === 'light' || value === 'dark' ? value : null;
}

function systemPrefersDark(): boolean {
  return window.matchMedia('(prefers-color-scheme: dark)').matches;
}

function applyTheme(theme: StoredTheme) {
  if (theme) {
    document.documentElement.dataset.theme = theme;
  } else {
    delete document.documentElement.dataset.theme;
  }
}

export function useTheme() {
  const [explicitTheme, setExplicitTheme] = useState<StoredTheme>(() => readStoredTheme());
  const [systemDark, setSystemDark] = useState<boolean>(() => systemPrefersDark());

  useEffect(() => {
    applyTheme(explicitTheme);
  }, [explicitTheme]);

  useEffect(() => {
    const media = window.matchMedia('(prefers-color-scheme: dark)');
    const onChange = () => setSystemDark(media.matches);
    media.addEventListener('change', onChange);
    return () => media.removeEventListener('change', onChange);
  }, []);

  const resolvedTheme: 'light' | 'dark' = explicitTheme ?? (systemDark ? 'dark' : 'light');

  const toggle = useCallback(() => {
    const next: StoredTheme = resolvedTheme === 'dark' ? 'light' : 'dark';
    localStorage.setItem(STORAGE_KEY, next);
    setExplicitTheme(next);
  }, [resolvedTheme]);

  return { resolvedTheme, toggle };
}
