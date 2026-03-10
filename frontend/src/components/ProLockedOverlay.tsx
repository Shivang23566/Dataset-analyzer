import { Lock, Sparkles } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface ProLockedOverlayProps {
  feature: 'preprocessing' | 'ml';
}

const featureDetails = {
  preprocessing: {
    title: 'Preprocessing is a Pro Feature',
    description:
      'Unlock automated data cleaning, missing value imputation, outlier detection, and advanced feature engineering with a Pro subscription.',
    benefits: [
      'Handle missing values intelligently',
      'Detect and remove outliers',
      'Encode categorical variables',
      'Scale and normalize features',
      'Feature engineering tools',
    ],
  },
  ml: {
    title: 'ML Model Builder is a Pro Feature',
    description:
      'Access 12 machine learning algorithms, hyperparameter tuning, model comparison, and export production-ready code.',
    benefits: [
      '12 ML algorithms (XGBoost, Random Forest, etc.)',
      'Auto hyperparameter tuning',
      'Cross-validation support',
      'Model performance comparison',
      'Export trained models & inference code',
    ],
  },
};

export function ProLockedOverlay({ feature }: ProLockedOverlayProps) {
  const navigate = useNavigate();
  const details = featureDetails[feature];

  return (
    <div className="pro-locked-overlay">
      <div className="pro-locked-card">
        <div className="pro-locked-icon">
          <Lock size={48} strokeWidth={1.5} />
        </div>

        <h2 className="pro-locked-title">{details.title}</h2>

        <p className="pro-locked-description">{details.description}</p>

        <ul className="pro-locked-benefits">
          {details.benefits.map((benefit, index) => (
            <li key={index}>
              <Sparkles size={14} />
              <span>{benefit}</span>
            </li>
          ))}
        </ul>

        <button
          className="pro-locked-cta"
          onClick={() => navigate('/dashboard?tab=billing')}
        >
          <Lock size={16} />
          Upgrade to Pro — ₹219/month
        </button>

        <p className="pro-locked-helper">
          Already Pro?{' '}
          <button onClick={() => window.location.reload()}>Refresh page</button>
        </p>
      </div>
    </div>
  );
}
