import { useEffect } from 'react';
import { X, CheckCircle, AlertCircle, Lock, TrendingUp } from 'lucide-react';

export type ToastType = 'success' | 'error' | 'warning' | 'upgrade' | 'locked';

interface ToastProps {
  type: ToastType;
  title: string;
  message: string;
  ctaText?: string;
  onCtaClick?: () => void;
  onClose: () => void;
  duration?: number;
}

const icons: Record<ToastType, React.ReactNode> = {
  success:  <CheckCircle size={20} />,
  error:    <AlertCircle size={20} />,
  warning:  <AlertCircle size={20} />,
  upgrade:  <TrendingUp size={20} />,
  locked:   <Lock size={20} />,
};

export function Toast({
  type,
  title,
  message,
  ctaText,
  onCtaClick,
  onClose,
  duration = 6000,
}: ToastProps) {
  useEffect(() => {
    if (duration > 0) {
      const timer = setTimeout(onClose, duration);
      return () => clearTimeout(timer);
    }
  }, [duration, onClose]);

  return (
    <div className={`toast toast-${type}`}>
      <div className="toast-icon">{icons[type]}</div>
      <div className="toast-content">
        <div className="toast-title">{title}</div>
        <div className="toast-message">{message}</div>
        {ctaText && (
          <button className="toast-cta" onClick={onCtaClick}>
            {ctaText}
          </button>
        )}
      </div>
      <button className="toast-close" onClick={onClose} aria-label="Dismiss">
        <X size={16} />
      </button>
    </div>
  );
}
