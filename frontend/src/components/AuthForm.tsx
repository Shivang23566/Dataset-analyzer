import { useState } from 'react';
import { extractErrorMessage } from '../lib/errorUtils';

type AuthFormProps = {
  title: string;
  subtitle: string;
  submitText: string;
  loadingText: string;
  onSubmit: (email: string, password: string) => Promise<void>;
};

export default function AuthForm({
  title,
  subtitle,
  submitText,
  loadingText,
  onSubmit,
}: AuthFormProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError('');
    setLoading(true);
    try {
      await onSubmit(email, password);
    } catch (err: unknown) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-card">
      <h1>{title}</h1>
      <p>{subtitle}</p>
      <form onSubmit={handleSubmit} className="auth-form">
        <label>
          Email
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@company.com"
            required
          />
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="********"
            minLength={6}
            required
          />
        </label>
        {error ? <div className="error-banner">{error}</div> : null}
        <button type="submit" className="btn btn-primary" disabled={loading}>
          {loading ? loadingText : submitText}
        </button>
      </form>
    </div>
  );
}
