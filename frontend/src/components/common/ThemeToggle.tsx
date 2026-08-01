import { Moon, Sun } from 'lucide-react';

import { IconButton } from './IconButton';

interface ThemeToggleProps {
  resolvedTheme: 'light' | 'dark';
  onToggle: () => void;
}

export function ThemeToggle({ resolvedTheme, onToggle }: ThemeToggleProps) {
  return (
    <IconButton
      icon={resolvedTheme === 'dark' ? Sun : Moon}
      aria-label={resolvedTheme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
      title={resolvedTheme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
      onClick={onToggle}
      variant="solid"
    />
  );
}
