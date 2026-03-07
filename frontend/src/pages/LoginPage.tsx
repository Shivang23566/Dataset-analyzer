import { Link, useNavigate } from 'react-router-dom';
import AuthForm from '../components/AuthForm';
import { backendLogin } from '../lib/api';

export default function LoginPage() {
  const navigate = useNavigate();

  const onSubmit = async (email: string, password: string) => {
    await backendLogin({ email, password });
    navigate('/workspace');
  };

  return (
    <main className="auth-layout">
      <AuthForm
        title="Welcome Back"
        subtitle="Login with your secure account to continue analysis."
        submitText="Login"
        loadingText="Logging in..."
        onSubmit={onSubmit}
      />
      <p className="auth-switch">
        No account yet? <Link to="/signup">Create one</Link>
      </p>
    </main>
  );
}
