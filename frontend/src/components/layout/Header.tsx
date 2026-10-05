import { Boxes } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';

import { useAuthContext } from '../../context/AuthContext';
import { useGuardedAction, useGuardedNavigate } from '../../context/UnsavedChangesContext';
import { useTheme } from '../../hooks/useTheme';
import { UserMenu } from './UserMenu';
import styles from './Header.module.css';

export function Header() {
  const { user, logout } = useAuthContext();
  const { resolvedTheme, toggle } = useTheme();
  const navigate = useNavigate();
  const guardedNavigate = useGuardedNavigate();
  const guardedAction = useGuardedAction();

  const handleLogout = () => {
    // Navigate off the protected route first so ProtectedRoute never
    // re-renders against the about-to-be-cleared auth state and redirects
    // to /login out from under this navigation.
    guardedAction(() => {
      navigate('/');
      void logout();
    });
  };

  return (
    <header className={styles.header}>
      <div className={styles.left}>
        <Link
          to="/"
          className={styles.brand}
          aria-label="UMLFrame home"
          onClick={(event) => {
            event.preventDefault();
            guardedNavigate('/');
          }}
        >
          <Boxes size={18} />
          <span>UMLFrame</span>
        </Link>
      </div>

      <div className={styles.right}>
        {user && (
          <UserMenu
            email={user.email}
            resolvedTheme={resolvedTheme}
            onToggleTheme={toggle}
            onLogout={handleLogout}
          />
        )}
      </div>
    </header>
  );
}
