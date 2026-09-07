import { useState } from 'react';
import { Boxes, GitBranch, Home, LogOut, Workflow } from 'lucide-react';
import { Link, useLocation, useNavigate } from 'react-router-dom';

import { Button } from '../common/Button';
import { ThemeToggle } from '../common/ThemeToggle';
import { ActivityCodeModal } from '../toolbar/ActivityCodeModal';
import { ReverseUmlModal } from '../toolbar/ReverseUmlModal';
import { ReverseActivityModal } from '../toolbar/ReverseActivityModal';
import { useAuthContext } from '../../context/AuthContext';
import { useTheme } from '../../hooks/useTheme';
import styles from './Header.module.css';

export type PipelineId = 'uml-code' | 'activity-code' | 'code-uml' | 'code-activity';

export function Header() {
  const [activeModal, setActiveModal] = useState<Exclude<PipelineId, 'uml-code'> | null>(null);
  const { user, logout } = useAuthContext();
  const { resolvedTheme, toggle } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();

  const isEditor = location.pathname.startsWith('/editor');
  const activePipeline: PipelineId | null = isEditor ? 'uml-code' : null;

  const handlePipelineClick = (id: PipelineId) => {
    if (id === 'uml-code') {
      navigate('/dashboard');
      return;
    }
    setActiveModal(id);
  };

  const handleLogout = () => {
    // Navigate off the protected route first so ProtectedRoute never
    // re-renders against the about-to-be-cleared auth state and redirects
    // to /login out from under this navigation.
    navigate('/');
    void logout();
  };

  return (
    <header className={styles.header}>
      <div className={styles.left}>
        <Link to="/dashboard" className={styles.brand}>
          <Boxes size={18} />
          <span>UMLFrame</span>
        </Link>

        <Button size="sm" variant="ghost" icon={Home} onClick={() => navigate('/')}>
          Home
        </Button>

        {isEditor && (
          <nav className={styles.nav}>
            <Button
              size="sm"
              variant="ghost"
              active={activePipeline === 'uml-code'}
              onClick={() => handlePipelineClick('uml-code')}
            >
              UML → Code
            </Button>
            <Button
              size="sm"
              variant="ghost"
              icon={Workflow}
              onClick={() => handlePipelineClick('activity-code')}
            >
              Activity → Code
            </Button>
            <Button
              size="sm"
              variant="ghost"
              icon={GitBranch}
              onClick={() => handlePipelineClick('code-uml')}
            >
              Code → UML
            </Button>
            <Button
              size="sm"
              variant="ghost"
              icon={GitBranch}
              onClick={() => handlePipelineClick('code-activity')}
            >
              Code → Activity
            </Button>
          </nav>
        )}
      </div>

      <div className={styles.right}>
        <ThemeToggle resolvedTheme={resolvedTheme} onToggle={toggle} />
        {user && <span className={styles.email}>{user.email}</span>}
        <Button size="sm" variant="ghost" icon={LogOut} onClick={handleLogout}>
          Log out
        </Button>
      </div>

      {activeModal === 'activity-code' && (
        <ActivityCodeModal onClose={() => setActiveModal(null)} />
      )}
      {activeModal === 'code-uml' && <ReverseUmlModal onClose={() => setActiveModal(null)} />}
      {activeModal === 'code-activity' && (
        <ReverseActivityModal onClose={() => setActiveModal(null)} />
      )}
    </header>
  );
}
