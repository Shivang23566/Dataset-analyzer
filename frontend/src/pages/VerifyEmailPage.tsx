import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Mail, ArrowLeft, CheckCircle } from 'lucide-react';
import AnimatedOTPInput from '../components/OTPInput';
import { verifySignupOTP, resendSignupOTP } from '../lib/api';
import { saveAuth } from '../lib/authStore';
import { extractErrorMessage } from '../lib/errorUtils';

export default function VerifyEmailPage() {
  const navigate = useNavigate();
  const location = useLocation();

  const email: string = (location.state as { email?: string })?.email || '';

  const [otp, setOtp] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [resendCooldown, setResendCooldown] = useState(0);
  const [expiryTime, setExpiryTime] = useState(600); // 10 min

  // Redirect if no email in state
  useEffect(() => {
    if (!email) navigate('/signup', { replace: true });
  }, [email, navigate]);

  // Resend cooldown timer
  useEffect(() => {
    if (resendCooldown <= 0) return;
    const t = setTimeout(() => setResendCooldown((c) => c - 1), 1000);
    return () => clearTimeout(t);
  }, [resendCooldown]);

  // Expiry countdown
  useEffect(() => {
    if (expiryTime <= 0 || success) return;
    const t = setTimeout(() => setExpiryTime((c) => c - 1), 1000);
    return () => clearTimeout(t);
  }, [expiryTime, success]);

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  const handleVerify = async (code?: string) => {
    const finalOtp = code || otp;
    if (finalOtp.length !== 6) {
      setError('Please enter the complete 6-digit code');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const data = await verifySignupOTP(email, finalOtp);
      saveAuth(data.access_token, email);
      setSuccess(true);
      setTimeout(() => navigate('/dashboard', { replace: true }), 1500);
    } catch (err: unknown) {
      setError(extractErrorMessage(err));
      setOtp('');
    } finally {
      setIsLoading(false);
    }
  };

  const handleResend = async () => {
    if (resendCooldown > 0) return;
    setError(null);
    try {
      await resendSignupOTP(email);
      setResendCooldown(60);
      setExpiryTime(600);
      setOtp('');
    } catch (err: unknown) {
      setError(extractErrorMessage(err));
    }
  };

  const handleOTPComplete = (value: string) => {
    handleVerify(value);
  };

  if (!email) return null;

  return (
    <div className="verify-page">
      <motion.div
        className="verify-card"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        {/* Icon */}
        <motion.div
          className="verify-icon"
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
        >
          {success ? <CheckCircle size={40} /> : <Mail size={40} />}
        </motion.div>

        {/* Title */}
        <h1 className="verify-title">
          {success ? 'Email Verified!' : 'Verify your email'}
        </h1>

        {success ? (
          <motion.p
            className="verify-subtitle"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            Redirecting to dashboard...
          </motion.p>
        ) : (
          <>
            <p className="verify-subtitle">We sent a verification code to</p>
            <p className="verify-email">{email}</p>

            {/* OTP Input */}
            <div className="verify-otp-section">
              <p className="verify-label">Enter 6-digit code</p>
              <AnimatedOTPInput
                value={otp}
                onChange={setOtp}
                onComplete={handleOTPComplete}
                error={!!error}
                disabled={isLoading || success}
              />

              {expiryTime > 0 && (
                <p className="verify-timer">
                  Code expires in <span>{formatTime(expiryTime)}</span>
                </p>
              )}

              {expiryTime === 0 && (
                <p className="verify-error">
                  Code expired. Please request a new one.
                </p>
              )}
            </div>

            {/* Error */}
            {error && (
              <motion.div
                className="verify-error"
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
              >
                {error}
              </motion.div>
            )}

            {/* Verify Button */}
            <button
              className="verify-button"
              onClick={() => handleVerify()}
              disabled={otp.length !== 6 || isLoading || success}
            >
              {isLoading ? 'Verifying...' : 'Verify Email'}
            </button>

            {/* Resend */}
            <div className="verify-resend">
              Didn't receive the code?{' '}
              <button onClick={handleResend} disabled={resendCooldown > 0}>
                {resendCooldown > 0
                  ? `Resend in ${resendCooldown}s`
                  : 'Resend Code'}
              </button>
            </div>
          </>
        )}

        {/* Back to signup */}
        {!success && (
          <div className="verify-back">
            <button onClick={() => navigate('/signup')}>
              <ArrowLeft size={14} style={{ marginRight: 6, verticalAlign: 'middle' }} />
              Back to signup
            </button>
          </div>
        )}
      </motion.div>
    </div>
  );
}
