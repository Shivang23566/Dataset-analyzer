export interface ApiError {
  detail?: string | { msg: string }[];
  message?: string;
  error?: string;
}

export const extractErrorMessage = (error: unknown): string => {
  if (!error) return 'An unknown error occurred';
  if (typeof error === 'string') return error;
  if (error instanceof Error) return error.message;

  if (typeof error === 'object') {
    const err = error as ApiError;

    if (Array.isArray(err.detail)) {
      return err.detail.map((d) => d.msg).join(', ');
    }
    if (typeof err.detail === 'string') return err.detail;
    if (err.message) return err.message;
    if (err.error) return err.error;
  }

  return 'An unexpected error occurred. Please try again.';
};

export const getUpgradeMessage = (
  errorType: string
): { title: string; message: string; cta: string } => {
  const messages: Record<string, { title: string; message: string; cta: string }> = {
    dataset_limit: {
      title: 'Dataset Limit Reached',
      message:
        'Free plan allows 3 datasets. Upgrade to Pro for unlimited datasets, preprocessing, and ML features.',
      cta: 'Upgrade to Pro — ₹219/month',
    },
    preprocessing_locked: {
      title: 'Preprocessing is a Pro Feature',
      message:
        'Unlock automated data cleaning, missing value imputation, outlier detection, and feature engineering.',
      cta: 'Unlock Preprocessing',
    },
    ml_locked: {
      title: 'ML Builder is a Pro Feature',
      message:
        'Access 12 machine learning models, hyperparameter tuning, model export, and inference code generation.',
      cta: 'Unlock ML Builder',
    },
    download_locked: {
      title: 'Downloads Require Pro',
      message:
        'Export processed datasets, trained models, and generate production-ready code.',
      cta: 'Start Exporting',
    },
  };

  return (
    messages[errorType] ?? {
      title: 'Pro Feature',
      message: 'This feature requires a Pro subscription.',
      cta: 'Upgrade to Pro',
    }
  );
};

/** Returns true when the error message looks like a plan-limit error */
export const isLimitError = (message: string): boolean =>
  /limit|3 datasets|upgrade|pro (plan|feature|required)|subscription/i.test(message);

/** Returns true when the error message looks like a feature-locked error */
export const isFeatureLockedError = (message: string): boolean =>
  /pro (feature|required|only)|not available on free|locked/i.test(message);

/** Returns true when the error is specifically a pro_required gate */
export const isProRequiredError = (message: string): boolean =>
  /pro_required|requires a Pro subscription|Pro Feature/i.test(message);
