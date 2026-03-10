import { Toast } from './Toast';
import { useToast } from '../hooks/useToast';

export function ToastContainer() {
  const { toasts, dismissToast } = useToast();

  if (toasts.length === 0) return null;

  return (
    <div className="toast-container">
      {toasts.map((t) => (
        <Toast
          key={t.id}
          type={t.type}
          title={t.title}
          message={t.message}
          ctaText={t.ctaText}
          onCtaClick={t.onCtaClick}
          onClose={() => dismissToast(t.id)}
          duration={t.duration}
        />
      ))}
    </div>
  );
}
