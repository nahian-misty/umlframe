import { useState, type FormEvent } from 'react';
import { ArrowLeft } from 'lucide-react';

import { ApiError } from '../api/client';
import { Button } from '../components/common/Button';
import { useToast } from '../components/common/ToastProvider';
import { useAuthContext } from '../context/AuthContext';
import { useGuardedNavigate } from '../context/UnsavedChangesContext';
import styles from './AccountPage.module.css';

const MIN_PASSWORD_LENGTH = 8;

function validatePasswordChange(current: string, next: string, confirm: string): string | null {
  if (!current || !next || !confirm) return 'Please fill in all fields.';
  if (next.length < MIN_PASSWORD_LENGTH) {
    return `The new password must be at least ${MIN_PASSWORD_LENGTH} characters.`;
  }
  if (next !== confirm) return 'The new passwords do not match.';
  if (next === current) return 'The new password must be different from the current one.';
  return null;
}

export function AccountPage() {
  const { user, changePassword } = useAuthContext();
  const { showToast } = useToast();
  const navigate = useGuardedNavigate();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    const problem = validatePasswordChange(currentPassword, newPassword, confirmPassword);
    if (problem) {
      setError(problem);
      return;
    }
    setError(null);
    setIsSubmitting(true);
    try {
      await changePassword(currentPassword, newPassword);
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      showToast('Password changed. Other devices have been signed out.', 'success');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not change the password.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className={styles.page}>
      <div className={styles.content}>
        <Button size="sm" variant="ghost" icon={ArrowLeft} onClick={() => navigate('/dashboard')}>
          Projects
        </Button>
        <h1 className={styles.title}>Account settings</h1>

        <section className={styles.card}>
          <h2 className={styles.sectionTitle}>Profile</h2>
          <div className={styles.field}>
            <span>Username</span>
            <strong className={styles.value}>{user?.username}</strong>
          </div>
          <div className={styles.field}>
            <span>Email</span>
            <strong className={styles.value}>{user?.email}</strong>
          </div>
        </section>

        <form className={styles.card} onSubmit={handleSubmit}>
          <h2 className={styles.sectionTitle}>Change password</h2>
          <label className={styles.field}>
            <span>Current password</span>
            <input
              type="password"
              autoComplete="current-password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
            />
          </label>
          <label className={styles.field}>
            <span>New password</span>
            <input
              type="password"
              autoComplete="new-password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
            />
            <small>At least {MIN_PASSWORD_LENGTH} characters.</small>
          </label>
          <label className={styles.field}>
            <span>Confirm new password</span>
            <input
              type="password"
              autoComplete="new-password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
            />
          </label>
          {error && (
            <div className={styles.error} role="alert">
              {error}
            </div>
          )}
          <Button type="submit" variant="primary" disabled={isSubmitting}>
            {isSubmitting ? 'Changing…' : 'Change password'}
          </Button>
        </form>
      </div>
    </div>
  );
}
