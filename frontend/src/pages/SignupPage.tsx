import { Link, useNavigate } from 'react-router-dom';
import AuthForm from '../components/AuthForm';
import { initiateSignup } from '../lib/api';

export default function SignupPage() {
  const navigate = useNavigate();

  const onSubmit = async (email: string, password: string) => {
    await initiateSignup({ email, password });
    navigate('/verify-email', { state: { email } });
  };

  return (
    <main className="auth-layout">
      <AuthForm
        title="Create Account"
        subtitle="Start your secure dataset analysis workflow in minutes."
        submitText="Sign Up"
        loadingText="Sending code..."
        onSubmit={onSubmit}
      />
      <p className="auth-switch">
        Already registered? <Link to="/login">Login</Link>
      </p>
    </main>
  );
}
