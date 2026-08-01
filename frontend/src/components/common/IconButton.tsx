import type { ButtonHTMLAttributes } from 'react';
import type { LucideIcon } from 'lucide-react';

import styles from './IconButton.module.css';

type IconButtonVariant = 'ghost' | 'solid';
type IconButtonSize = 'sm' | 'md';

interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  icon: LucideIcon;
  'aria-label': string;
  variant?: IconButtonVariant;
  size?: IconButtonSize;
}

export function IconButton({
  icon: Icon,
  variant = 'ghost',
  size = 'md',
  className,
  type = 'button',
  ...rest
}: IconButtonProps) {
  const classes = [styles.iconButton, styles[variant], styles[size], className ?? '']
    .filter(Boolean)
    .join(' ');

  return (
    <button type={type} className={classes} {...rest}>
      <Icon size={size === 'sm' ? 14 : 18} />
    </button>
  );
}
