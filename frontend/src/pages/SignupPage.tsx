import { useState, type FormEvent } from 'react';
import { Boxes } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';

import { Button } from '../components/common/Button';
import { useAuthContext } from '../context/AuthContext';
import { ApiError } from '../api/client';
import styles from './AuthPage.module.css';

export function SignupPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { register } = useAuthContext();
  const navigate = useNavigate();

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!email.trim() || !password.trim() || !confirmPassword.trim()) {
      setError('Please fill in all fields.');
      return;
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }
    setError(null);
    setIsSubmitting(true);
    try {
      await register(email.trim(), password);
      navigate('/dashboard', { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Sign up failed. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className={styles.page}>
      <form className={styles.card} onSubmit={handleSubmit}>
        <Link to="/" className={styles.brand}>
          <Boxes size={22} />
          <h1 className={styles.title}>UMLFrame</h1>
        </Link>
        <p className={styles.subtitle}>Create an account to continue</p>

        <label className={styles.field}>
          <span>Email</span>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
          />
        </label>

        <label className={styles.field}>
          <span>Password</span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
          />
        </label>

        <label className={styles.field}>
          <span>Confirm Password</span>
          <input
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder="••••••••"
          />
        </label>

        {error && <div className={styles.error}>{error}</div>}

        <Button type="submit" variant="primary" className={styles.submitButton} disabled={isSubmitting}>
          {isSubmitting ? 'Signing up…' : 'Sign Up'}
        </Button>

        <p className={styles.switchLine}>
          Already have an account?{' '}
          <Link to="/login" className={styles.linkButton}>
            Log in
          </Link>
        </p>
      </form>
    </div>
  );
}
