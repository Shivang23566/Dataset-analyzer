/**
 * HeroSection.tsx
 * Complete Hero Section with Exploding Dataset Visualization
 */

import { useState, useCallback } from 'react';
import ExplodingDatasetViz, { EXPLODING_VIZ_CONFIG, type Visualization } from './ExplodingDatasetViz';
import './HeroSection.css';

interface HeroSectionProps {
  onLoginClick?: () => void;
  onSignupClick?: () => void;
  onFeaturesClick?: () => void;
}

export default function HeroSection({ onSignupClick, onFeaturesClick }: HeroSectionProps) {
  const [currentViz, setCurrentViz] = useState<Visualization>(EXPLODING_VIZ_CONFIG.visualizations[0]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isLabelUpdating, setIsLabelUpdating] = useState(false);
  const [hintHidden, setHintHidden] = useState(false);

  const handleVisualizationChange = useCallback((viz: Visualization, index: number) => {
    setIsLabelUpdating(true);
    setTimeout(() => {
      setCurrentViz(viz);
      setCurrentIndex(index);
      setIsLabelUpdating(false);
    }, 150);
    setHintHidden(true);
  }, []);

  const {
    containerRef,
    handleClick,
    handleDotClick,
    visualizations,
  } = ExplodingDatasetViz({ onVisualizationChange: handleVisualizationChange });

  return (
    <section className="exploding-hero">
      <div className="exploding-hero__container">
        {/* Left Content */}
        <div className="exploding-hero__content">
          <div className="exploding-hero__badge">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
            </svg>
            <span>NEW: AI-Powered Analysis</span>
          </div>
          
          <h1 className="exploding-hero__title">
            From raw data<br/>
            to <span className="exploding-hero__highlight">insights</span><br/>
            in minutes
          </h1>
          
          <p className="exploding-hero__description">
            AI-powered data analysis platform with automated EDA, smart preprocessing, 
            and one-click ML model training. No coding required.
          </p>
          
          <div className="exploding-hero__buttons">
            <button className="exploding-hero__btn exploding-hero__btn--primary" onClick={onSignupClick}>
              Start Analyzing Free
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M5 12h14M12 5l7 7-7 7"/>
              </svg>
            </button>
            <button className="exploding-hero__btn exploding-hero__btn--outline" onClick={onFeaturesClick}>
              See Features
            </button>
          </div>
          
          <div className="exploding-hero__stats">
            <div className="exploding-hero__stat">
              <span className="exploding-hero__stat-value">50MB</span>
              <span className="exploding-hero__stat-label">Max File Size</span>
            </div>
            <div className="exploding-hero__stat">
              <span className="exploding-hero__stat-value">12</span>
              <span className="exploding-hero__stat-label">ML Models</span>
            </div>
            <div className="exploding-hero__stat">
              <span className="exploding-hero__stat-value">&lt;60s</span>
              <span className="exploding-hero__stat-label">Avg Analysis</span>
            </div>
          </div>
        </div>
        
        {/* Right Side - Three.js Canvas */}
        <div className="exploding-hero__visual">
          <div className="exploding-hero__browser">
            <div className="exploding-hero__browser-header">
              <div className="exploding-hero__browser-dots">
                <span className="exploding-hero__dot exploding-hero__dot--red"></span>
                <span className="exploding-hero__dot exploding-hero__dot--yellow"></span>
                <span className="exploding-hero__dot exploding-hero__dot--green"></span>
              </div>
              <div className="exploding-hero__browser-url">datalens.app/workspace</div>
            </div>
            <div 
              className="exploding-hero__browser-content"
              ref={containerRef}
              onClick={handleClick}
            >
              {/* Visualization Label */}
              <div className={`exploding-hero__viz-label ${isLabelUpdating ? 'updating' : ''}`}>
                <span className="exploding-hero__viz-icon">{currentViz.icon}</span>
                <span className="exploding-hero__viz-name">{currentViz.name}</span>
              </div>
              
              {/* Progress Indicator */}
              <div className="exploding-hero__viz-progress">
                {visualizations.map((_, i) => (
                  <div
                    key={i}
                    className={`exploding-hero__progress-dot ${i === currentIndex ? 'active' : ''}`}
                    onClick={(e) => handleDotClick(i, e)}
                  />
                ))}
              </div>
              
              {/* Click Hint */}
              <div className={`exploding-hero__click-hint ${hintHidden ? 'hidden' : ''}`}>
                <span>Click anywhere to transform</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
