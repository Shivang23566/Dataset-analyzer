import { Link, useNavigate } from 'react-router-dom';
import AuthForm from '../components/AuthForm';
import { backendLogin, backendSignup } from '../lib/api';

export default function SignupPage() {
  const navigate = useNavigate();

  const onSubmit = async (email: string, password: string) => {
    await backendSignup({ email, password });
    await backendLogin({ email, password });
    navigate('/workspace');
  };

  return (
    <main className="auth-layout">
      <AuthForm
        title="Create Account"
        subtitle="Start your secure dataset analysis workflow in minutes."
        submitText="Sign Up"
        loadingText="Creating..."
        onSubmit={onSubmit}
      />
      <p className="auth-switch">
        Already registered? <Link to="/login">Login</Link>
      </p>
    </main>
  );
}
