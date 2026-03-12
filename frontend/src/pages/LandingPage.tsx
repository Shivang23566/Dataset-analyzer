import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  BarChart3, 
  Sparkles, 
  Brain, 
  Zap,
  ArrowRight,
  Check,
  X,
  Star,
  Download,
  LineChart,
  Settings,
  Github,
  Twitter,
  Linkedin,
  Mail
} from 'lucide-react';
import BallpitBackground from '../components/BallpitBackground';
import { HeroSection } from '../components/ExplodingHero';

export default function LandingPage() {
  const navigate = useNavigate();
  const [isScrolled, setIsScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const features = [
    {
      icon: <BarChart3 size={24} />,
      title: 'Automated EDA',
      description: 'Get instant statistical analysis, data profiling, and quality metrics in seconds.'
    },
    {
      icon: <LineChart size={24} />,
      title: 'Smart Visualizations',
      description: 'Auto-generated charts and graphs. Export publication-ready visuals instantly.'
    },
    {
      icon: <Settings size={24} />,
      title: 'Data Preprocessing',
      description: '9-step automated pipeline for cleaning, encoding, scaling, and feature engineering.'
    },
    {
      icon: <Brain size={24} />,
      title: 'ML Model Builder',
      description: '12 algorithms with auto hyperparameter tuning. Train and export models easily.'
    },
    {
      icon: <Download size={24} />,
      title: 'One-Click Export',
      description: 'Download processed data, trained models, and production-ready inference code.'
    },
    {
      icon: <Zap size={24} />,
      title: 'Lightning Fast',
      description: 'Analyze datasets up to 50MB in under 60 seconds. No coding required.'
    }
  ];

  const steps = [
    {
      number: '01',
      title: 'Upload Dataset',
      description: 'Drag & drop your CSV or JSON file. We support datasets up to 50MB.',
      color: '#b7c6c2'
    },
    {
      number: '02', 
      title: 'Analyze & Clean',
      description: 'Run automated EDA and preprocessing. Fix issues with one click.',
      color: '#ffe17c'
    },
    {
      number: '03',
      title: 'Train & Export',
      description: 'Build ML models and export everything you need for production.',
      color: '#ffffff'
    }
  ];

  const testimonials = [
    {
      name: 'Sarah Chen',
      role: 'Data Scientist at TechCorp',
      content: 'DataLens cut my preprocessing time by 80%. The automated EDA is incredibly thorough.',
      rating: 5
    },
    {
      name: 'Marcus Johnson',
      role: 'ML Engineer',
      content: 'Finally, a tool that actually understands what data scientists need. The model export feature is a game-changer.',
      rating: 5
    },
    {
      name: 'Priya Sharma',
      role: 'Analytics Lead',
      content: 'We onboarded our entire team in a day. The interface is intuitive and powerful.',
      rating: 5
    }
  ];

  const problems = [
    'Hours spent on repetitive data cleaning',
    'Writing boilerplate code for every project',
    'Inconsistent preprocessing across team',
    'Manual hyperparameter tuning',
    'Difficult to reproduce analysis'
  ];

  const solutions = [
    'Automated 9-step preprocessing pipeline',
    'Zero-code analysis with full customization',
    'Standardized workflows for teams',
    'Auto hyperparameter optimization',
    'Complete session history & exports'
  ];

  return (
    <div className="neo-landing">
      {/* Navigation */}
      <nav className={`neo-nav ${isScrolled ? 'neo-nav-scrolled' : ''}`}>
        <div className="neo-nav-container">
          <div className="neo-nav-logo" onClick={() => navigate('/')}>
            <div className="neo-logo-icon">
              <Zap size={20} />
            </div>
            <span>DataLens</span>
          </div>
          
          <div className="neo-nav-links">
            <a href="#features">Features</a>
            <a href="#how-it-works">How It Works</a>
            <a href="#pricing">Pricing</a>
          </div>
          
          <div className="neo-nav-actions">
            <button 
              className="neo-btn-outline"
              onClick={() => navigate('/login')}
            >
              Login
            </button>
            <button 
              className="neo-btn-primary"
              onClick={() => navigate('/signup')}
            >
              Start Free
              <ArrowRight size={16} />
            </button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <HeroSection 
        onLoginClick={() => navigate('/login')}
        onSignupClick={() => navigate('/signup')}
        onFeaturesClick={() => {
          document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' });
        }}
      />

      {/* Social Proof Marquee */}
      <section className="neo-marquee">
        <div className="neo-marquee-track">
          <div className="neo-marquee-content">
            <span>TRUSTED BY 500+ DATA TEAMS</span>
            <span className="neo-marquee-dot">&#9670;</span>
            <span>10,000+ DATASETS ANALYZED</span>
            <span className="neo-marquee-dot">&#9670;</span>
            <span>99.9% UPTIME</span>
            <span className="neo-marquee-dot">&#9670;</span>
            <span>TRUSTED BY 500+ DATA TEAMS</span>
            <span className="neo-marquee-dot">&#9670;</span>
            <span>10,000+ DATASETS ANALYZED</span>
            <span className="neo-marquee-dot">&#9670;</span>
            <span>99.9% UPTIME</span>
            <span className="neo-marquee-dot">&#9670;</span>
          </div>
        </div>
      </section>

      {/* Problem vs Solution */}
      <section className="neo-comparison">
        <div className="neo-comparison-container">
          <motion.h2
            className="neo-section-title"
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            The Old Way vs The DataLens Way
          </motion.h2>
          
          <div className="neo-comparison-grid">
            <motion.div
              className="neo-card-problem"
              initial={{ opacity: 0, x: -30 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
            >
              <h3>&#128547; Without DataLens</h3>
              <ul>
                {problems.map((problem, index) => (
                  <li key={index}>
                    <X size={18} className="icon-x" />
                    {problem}
                  </li>
                ))}
              </ul>
            </motion.div>
            
            <motion.div
              className="neo-card-solution"
              initial={{ opacity: 0, x: 30 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
            >
              <h3>&#128640; With DataLens</h3>
              <ul>
                {solutions.map((solution, index) => (
                  <li key={index}>
                    <Check size={18} className="icon-check" />
                    {solution}
                  </li>
                ))}
              </ul>
            </motion.div>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="neo-features" id="features">
        <div className="neo-features-container">
          <motion.div
            className="neo-section-header"
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <h2 className="neo-section-title-dark">Powerful Features</h2>
            <p className="neo-section-subtitle-dark">
              Everything you need to analyze data, build models, and ship faster.
            </p>
          </motion.div>
          
          <div className="neo-features-grid">
            {features.map((feature, index) => (
              <motion.div
                key={index}
                className="neo-feature-card"
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
              >
                <div className="neo-feature-icon">
                  {feature.icon}
                </div>
                <h3>{feature.title}</h3>
                <p>{feature.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="neo-how-it-works" id="how-it-works">
        <div className="neo-how-container">
          <motion.div
            className="neo-section-header"
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <h2 className="neo-section-title-light">How It Works</h2>
            <p className="neo-section-subtitle-light">
              Three simple steps to transform your data workflow.
            </p>
          </motion.div>
          
          <div className="neo-steps">
            {steps.map((step, index) => (
              <motion.div
                key={index}
                className="neo-step"
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.2 }}
              >
                <div 
                  className="neo-step-number"
                  style={{ borderColor: step.color }}
                >
                  {step.number}
                </div>
                <h3>{step.title}</h3>
                <p>{step.description}</p>
              </motion.div>
            ))}
            <div className="neo-steps-line"></div>
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section className="neo-pricing" id="pricing">
        <div className="neo-pricing-container">
          <motion.div
            className="neo-section-header"
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <h2 className="neo-section-title">Simple Pricing</h2>
            <p className="neo-section-subtitle">
              Start free, upgrade when you need more power.
            </p>
          </motion.div>
          
          <div className="neo-pricing-grid">
            <motion.div
              className="neo-pricing-card"
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
            >
              <div className="neo-pricing-header">
                <h3>Free</h3>
                <div className="neo-pricing-price">
                  <span className="neo-price-amount">&#8377;0</span>
                  <span className="neo-price-period">/month</span>
                </div>
              </div>
              <ul className="neo-pricing-features">
                <li><Check size={16} /> Up to 3 datasets</li>
                <li><Check size={16} /> Full EDA analysis</li>
                <li><Check size={16} /> Visualization tools</li>
                <li className="disabled"><X size={16} /> Preprocessing pipeline</li>
                <li className="disabled"><X size={16} /> ML Model Builder</li>
                <li className="disabled"><X size={16} /> Export & downloads</li>
              </ul>
              <button 
                className="neo-btn-outline-dark"
                onClick={() => navigate('/signup')}
              >
                Get Started
              </button>
            </motion.div>
            
            <motion.div
              className="neo-pricing-card neo-pricing-featured"
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.1 }}
            >
              <div className="neo-pricing-badge">MOST POPULAR</div>
              <div className="neo-pricing-header">
                <h3>Pro</h3>
                <div className="neo-pricing-price">
                  <span className="neo-price-amount">&#8377;219</span>
                  <span className="neo-price-period">/month</span>
                </div>
              </div>
              <ul className="neo-pricing-features">
                <li><Check size={16} /> Unlimited datasets</li>
                <li><Check size={16} /> Full EDA analysis</li>
                <li><Check size={16} /> Visualization tools</li>
                <li><Check size={16} /> 9-step preprocessing</li>
                <li><Check size={16} /> 12 ML algorithms</li>
                <li><Check size={16} /> Model & code export</li>
              </ul>
              <button 
                className="neo-btn-primary-large"
                onClick={() => navigate('/signup')}
              >
                Start Pro Trial
                <ArrowRight size={16} />
              </button>
            </motion.div>
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section className="neo-testimonials">
        <div className="neo-testimonials-container">
          <motion.div
            className="neo-section-header"
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <h2 className="neo-section-title-dark">What Users Say</h2>
          </motion.div>
          
          <div className="neo-testimonials-grid">
            {testimonials.map((testimonial, index) => (
              <motion.div
                key={index}
                className="neo-testimonial-card"
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
              >
                <div className="neo-testimonial-stars">
                  {[...Array(testimonial.rating)].map((_, i) => (
                    <Star key={i} size={16} fill="#ffbc2e" color="#ffbc2e" />
                  ))}
                </div>
                <p className="neo-testimonial-content">&ldquo;{testimonial.content}&rdquo;</p>
                <div className="neo-testimonial-author">
                  <div className="neo-testimonial-avatar">
                    {testimonial.name[0]}
                  </div>
                  <div>
                    <div className="neo-testimonial-name">{testimonial.name}</div>
                    <div className="neo-testimonial-role">{testimonial.role}</div>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="neo-final-cta">
        <div className="neo-final-cta-container">
          <motion.h2
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            Ready to transform your data workflow?
          </motion.h2>
          <motion.p
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.1 }}
          >
            Join 500+ data teams already using DataLens.
          </motion.p>
          <motion.button
            className="neo-btn-cta"
            onClick={() => navigate('/signup')}
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.2 }}
          >
            Start Free Today
            <ArrowRight size={20} />
          </motion.button>
        </div>
      </section>

      {/* Footer */}
      <footer className="neo-footer">
        <div className="neo-footer-container">
          <div className="neo-footer-grid">
            <div className="neo-footer-brand">
              <div className="neo-footer-logo">
                <div className="neo-logo-icon">
                  <Zap size={20} />
                </div>
                <span>DataLens</span>
              </div>
              <p>AI-powered data analysis platform for modern teams.</p>
              <div className="neo-footer-social">
                <a href="#" className="neo-social-icon" aria-label="Twitter"><Twitter size={18} /></a>
                <a href="#" className="neo-social-icon" aria-label="GitHub"><Github size={18} /></a>
                <a href="#" className="neo-social-icon" aria-label="LinkedIn"><Linkedin size={18} /></a>
                <a href="#" className="neo-social-icon" aria-label="Email"><Mail size={18} /></a>
              </div>
            </div>
            
            <div className="neo-footer-links">
              <h4>Product</h4>
              <a href="#features">Features</a>
              <a href="#pricing">Pricing</a>
              <a href="#how-it-works">How It Works</a>
            </div>
            
            <div className="neo-footer-links">
              <h4>Company</h4>
              <a href="#">About</a>
              <a href="#">Blog</a>
              <a href="#">Careers</a>
            </div>
            
            <div className="neo-footer-links">
              <h4>Legal</h4>
              <a href="#">Privacy Policy</a>
              <a href="#">Terms of Service</a>
              <a href="#">Cookie Policy</a>
            </div>
          </div>
          
          <div className="neo-footer-bottom">
            <p>&copy; 2025 DataLens. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
