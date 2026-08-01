import { useState } from 'react';
import { Boxes, GitBranch, Home, LogOut, Workflow } from 'lucide-react';
import { Link, useLocation, useNavigate } from 'react-router-dom';

import { Button } from '../common/Button';
import { ThemeToggle } from '../common/ThemeToggle';
import { ComingSoonModal } from '../dashboard/ComingSoonModal';
import { COMING_SOON, type ComingSoonKey } from '../../data/comingSoonCopy';
import { useAuthContext } from '../../context/AuthContext';
import { useTheme } from '../../hooks/useTheme';
import styles from './Header.module.css';

export type PipelineId = 'uml-code' | 'activity-code' | 'code-uml' | 'code-activity';

const PIPELINE_COMING_SOON: Partial<Record<PipelineId, ComingSoonKey>> = {
  'activity-code': 'activity-to-code',
  'code-uml': 'code-to-uml',
  'code-activity': 'code-to-activity',
};

export function Header() {
  const [comingSoonKey, setComingSoonKey] = useState<ComingSoonKey | null>(null);
  const { user, logout } = useAuthContext();
  const { resolvedTheme, toggle } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();

  const isEditor = location.pathname.startsWith('/editor');
  const activePipeline: PipelineId | null = isEditor ? 'uml-code' : null;

  const handlePipelineClick = (id: PipelineId) => {
    const key = PIPELINE_COMING_SOON[id];
    if (key) {
      setComingSoonKey(key);
      return;
    }
    navigate('/dashboard');
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

      {comingSoonKey && (
        <ComingSoonModal
          featureName={COMING_SOON[comingSoonKey].featureName}
          description={COMING_SOON[comingSoonKey].description}
          onClose={() => setComingSoonKey(null)}
        />
      )}
    </header>
  );
}
