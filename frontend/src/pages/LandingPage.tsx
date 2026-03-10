import { Link } from 'react-router-dom';
import { motion, useScroll, useTransform } from 'framer-motion';
import {
  ArrowRight,
  BarChart3,
  Brain,
  Check,
  Database,
  LineChart,
  Sparkles,
  Upload,
  X,
  Zap,
} from 'lucide-react';
import { useRef } from 'react';
import BallpitBackground from '../components/BallpitBackground';
import Navbar from '../components/Navbar';

// ── Feature Cards ─────────────────────────────────────────────
const featureCards = [
  {
    title: 'Automated EDA',
    desc: 'Instant statistical analysis, data profiling, correlation matrices, and quality assessment. Understand your data in seconds.',
    icon: BarChart3,
    iconBg: 'linear-gradient(135deg, #2eb8a0, #1a9080)',
    glowColor: 'rgba(46,184,160,0.15)',
    pro: false,
    delay: 0,
  },
  {
    title: 'Smart Visualizations',
    desc: 'Auto-generated charts and graphs across 7 chart types. Export publication-ready visuals with one click.',
    icon: LineChart,
    iconBg: 'linear-gradient(135deg, #c9a84c, #b8973f)',
    glowColor: 'rgba(201,168,76,0.15)',
    pro: false,
    delay: 0.1,
  },
  {
    title: 'Intelligent Preprocessing',
    desc: '9-step automated pipeline: missing values, outlier detection, encoding, scaling, and feature engineering.',
    icon: Sparkles,
    iconBg: 'linear-gradient(135deg, #2eb8a0, #c9a84c)',
    glowColor: 'rgba(46,184,160,0.12)',
    pro: true,
    delay: 0.2,
  },
  {
    title: 'ML Model Builder',
    desc: '12 algorithms, auto hyperparameter tuning, model comparison, and production-ready inference code export.',
    icon: Brain,
    iconBg: 'linear-gradient(135deg, #c9a84c, #b8973f)',
    glowColor: 'rgba(201,168,76,0.15)',
    pro: true,
    delay: 0.3,
  },
];

// ── Workflow Steps ────────────────────────────────────────────
const workflowSteps = [
  {
    num: '01',
    label: 'Upload',
    icon: Upload,
    desc: 'Drop your CSV or JSON dataset. Schema profiling and column detection happen automatically.',
    color: '#2eb8a0',
  },
  {
    num: '02',
    label: 'EDA',
    icon: BarChart3,
    desc: 'Run exploratory analysis. Get statistics, correlations, and missing-value reports instantly.',
    color: '#c9a84c',
  },
  {
    num: '03',
    label: 'Visualize',
    icon: LineChart,
    desc: 'Generate charts automatically. Seven chart types with smart axis detection.',
    color: '#2eb8a0',
  },
  {
    num: '04',
    label: 'Preprocess',
    icon: Sparkles,
    desc: 'Run the 9-step pipeline. Clean, encode, scale, and engineer features with zero code.',
    color: '#c9a84c',
    pro: true,
  },
  {
    num: '05',
    label: 'Train',
    icon: Brain,
    desc: 'Select a model, configure hyperparameters, train, and export inference code for production.',
    color: '#2eb8a0',
    pro: true,
  },
];

// ── Free plan features ────────────────────────────────────────
const freeFeatures = [
  { text: '3 datasets', included: true },
  { text: 'Full EDA', included: true },
  { text: 'All chart types', included: true },
  { text: 'Preprocessing pipeline', included: false },
  { text: 'ML Model Builder', included: false },
  { text: 'Model & data export', included: false },
];

// ── Pro plan features ─────────────────────────────────────────
const proFeatures = [
  { text: 'Unlimited datasets', included: true },
  { text: 'Full EDA', included: true },
  { text: 'All chart types', included: true },
  { text: 'Preprocessing pipeline', included: true },
  { text: 'ML Model Builder', included: true },
  { text: 'Model & data export', included: true },
];

export default function LandingPage() {
  const containerRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ['start start', 'end start'],
  });

  const heroY = useTransform(scrollYProgress, [0, 1], ['0%', '45%']);
  const heroOpacity = useTransform(scrollYProgress, [0, 0.5], [1, 0]);

  return (
    <div className="page-shell" ref={containerRef}>
      <div className="noise-layer" />
      <Navbar />

      {/* ── HERO ─────────────────────────────────────────────── */}
      <motion.section
        className="hero"
        style={{ y: heroY, opacity: heroOpacity }}
      >
        <BallpitBackground
          count={140}
          colors={['#c9a84c', '#2eb8a0', '#b8973f']}
          gravity={0.32}
          friction={0.998}
          followCursor
          className="hero-ballpit"
        />
        <div className="hero-overlay" />

        <motion.div
          className="hero-content"
          initial={{ opacity: 0, y: 32, scale: 0.96 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
        >
          <motion.p
            className="eyebrow"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
          >
            <Zap size={13} style={{ display: 'inline', marginRight: 6, verticalAlign: 'middle' }} />
            AI-powered data analysis · zero code required
          </motion.p>

          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.3 }}
          >
            Transform raw data
            <br />
            into{' '}
            <span className="gradient-text">actionable insights</span>
            <br />
            with zero code
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.45 }}
          >
            AI-powered data analysis platform with automated EDA, smart
            preprocessing, and one-click ML model training. Built for
            analysts, scientists, and teams.
          </motion.p>

          <motion.div
            className="hero-actions"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.55 }}
          >
            <Link to="/signup" className="btn btn-primary">
              Start Analyzing Free
              <ArrowRight size={16} />
            </Link>
            <a href="#features" className="btn btn-ghost">
              See Features
              <motion.span
                animate={{ y: [0, 4, 0] }}
                transition={{ duration: 1.6, repeat: Infinity }}
                style={{ display: 'inline-block', marginLeft: 4 }}
              >
                ↓
              </motion.span>
            </a>
          </motion.div>

          {/* Stats strip */}
          <motion.div
            className="hero-stats"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.7 }}
          >
            <div>
              <span className="stat-number">50MB</span>
              <span className="stat-label">Max File</span>
            </div>
            <div className="divider" />
            <div>
              <span className="stat-number">12</span>
              <span className="stat-label">ML Models</span>
            </div>
            <div className="divider" />
            <div>
              <span className="stat-number">9</span>
              <span className="stat-label">Preprocess Steps</span>
            </div>
            <div className="divider" />
            <div>
              <span className="stat-number">&lt;60s</span>
              <span className="stat-label">Avg Analysis</span>
            </div>
          </motion.div>
        </motion.div>
      </motion.section>

      {/* ── FEATURES ─────────────────────────────────────────── */}
      <section id="features" className="section-block features-section">
        <motion.div
          className="section-head"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          viewport={{ once: true, margin: '-80px' }}
        >
          <h2>
            Everything you need to go from{' '}
            <span className="gradient-text">data to decisions</span>
          </h2>
          <p>
            Four powerful modules organized around your real analysis
            workflow — no tool-switching required.
          </p>
        </motion.div>

        <div className="feature-grid-enhanced">
          {featureCards.map((card) => {
            const Icon = card.icon;
            return (
              <motion.article
                key={card.title}
                className="feature-card-3d"
                initial={{ opacity: 0, y: 40, rotateX: -12 }}
                whileInView={{ opacity: 1, y: 0, rotateX: 0 }}
                whileHover={{
                  y: -8,
                  rotateX: 4,
                  transition: { duration: 0.2, ease: 'easeOut' },
                }}
                transition={{
                  duration: 0.55,
                  delay: card.delay,
                  ease: [0.22, 1, 0.36, 1],
                }}
                viewport={{ once: true, margin: '-40px' }}
                style={{ transformStyle: 'preserve-3d' }}
              >
                {/* Icon wrapper */}
                <div
                  className="icon-wrapper"
                  style={{ background: card.iconBg }}
                >
                  <Icon size={24} strokeWidth={2} />
                </div>

                {/* Title + PRO badge */}
                <h3 style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                  {card.title}
                  {card.pro && <span className="pro-badge">PRO</span>}
                </h3>

                <p>{card.desc}</p>

                {/* Glow overlay */}
                <div
                  className="card-glow"
                  style={{
                    background: `radial-gradient(circle at center, ${card.glowColor} 0%, transparent 50%)`,
                  }}
                />
              </motion.article>
            );
          })}
        </div>
      </section>

      {/* ── WORKFLOW ─────────────────────────────────────────── */}
      <section id="workflow" className="section-block workflow-section">
        <motion.div
          className="section-head"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          viewport={{ once: true, margin: '-80px' }}
        >
          <h2>
            From upload to trained model{' '}
            <span className="gradient-text">in five steps</span>
          </h2>
          <p>
            A single, linear workflow. No context-switching, no separate
            tools.
          </p>
        </motion.div>

        <div className="workflow-timeline">
          {workflowSteps.map((step, index) => {
            const Icon = step.icon;
            return (
              <motion.div
                key={step.num}
                className="workflow-step"
                initial={{ opacity: 0, x: index % 2 === 0 ? -32 : 32 }}
                whileInView={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
                viewport={{ once: true, margin: '-60px' }}
              >
                <div className="step-indicator">
                  <span
                    className="step-number"
                    style={{ borderColor: `${step.color}40`, color: step.color }}
                  >
                    {step.num}
                  </span>
                  <div
                    className="step-icon-wrapper"
                    style={{
                      background: `${step.color}14`,
                      borderColor: `${step.color}50`,
                    }}
                  >
                    <Icon size={20} style={{ color: step.color }} />
                  </div>
                </div>

                <div className="step-content">
                  <h3 style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    {step.label}
                    {step.pro && <span className="pro-badge">PRO</span>}
                  </h3>
                  <p>{step.desc}</p>
                </div>
              </motion.div>
            );
          })}
        </div>
      </section>

      {/* ── PRICING ──────────────────────────────────────────── */}
      <section id="pricing" className="section-block pricing-section">
        <motion.div
          className="section-head"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          viewport={{ once: true, margin: '-80px' }}
        >
          <h2>
            Simple,{' '}
            <span className="gradient-text">transparent pricing</span>
          </h2>
          <p>Start free. Upgrade when you need preprocessing and ML.</p>
        </motion.div>

        <div className="pricing-grid">
          {/* Free */}
          <motion.div
            className="pricing-card"
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0 }}
            viewport={{ once: true }}
          >
            <div className="pricing-label">Free</div>
            <div className="pricing-price">
              ₹0<span>/month</span>
            </div>
            <p className="pricing-desc">
              Perfect for exploring your data and getting started.
            </p>
            <ul className="pricing-features">
              {freeFeatures.map((f) => (
                <li
                  key={f.text}
                  className={f.included ? 'included' : 'excluded'}
                >
                  {f.included
                    ? <Check size={15} className="pricing-check" />
                    : <X size={15} className="pricing-x" />}
                  {f.text}
                </li>
              ))}
            </ul>
            <Link to="/signup" className="pricing-btn pricing-btn--free">
              Start Free
            </Link>
          </motion.div>

          {/* Pro */}
          <motion.div
            className="pricing-card pricing-card--pro"
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.12 }}
            viewport={{ once: true }}
          >
            <div className="pricing-label pricing-label--pro">Pro</div>
            <div className="pricing-price">
              ₹219<span>/month</span>
            </div>
            <p className="pricing-desc">
              Full access to preprocessing, ML builder, and exports.
            </p>
            <ul className="pricing-features">
              {proFeatures.map((f) => (
                <li key={f.text} className="included">
                  <Check size={15} className="pricing-check" />
                  {f.text}
                </li>
              ))}
            </ul>
            <Link to="/signup" className="pricing-btn pricing-btn--pro">
              Go Pro →
            </Link>
          </motion.div>
        </div>
      </section>

      {/* ── CTA ──────────────────────────────────────────────── */}
      <section className="section-block cta-section">
        <motion.div
          className="cta-container"
          initial={{ opacity: 0, scale: 0.95 }}
          whileInView={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.6 }}
          viewport={{ once: true }}
        >
          <motion.div
            className="cta-background-orb"
            animate={{ rotate: [0, 360], scale: [1, 1.08, 1] }}
            transition={{ duration: 22, repeat: Infinity, ease: 'linear' }}
          />
          <h2>Ready to accelerate your data analysis?</h2>
          <p>
            Join analysts and data scientists who reduced their exploration
            time from hours to minutes. Start for free — no credit card
            required.
          </p>
          <Link to="/signup" className="btn btn-primary btn-large">
            Start Analyzing Free
            <ArrowRight size={18} />
          </Link>
        </motion.div>
      </section>

      {/* ── FOOTER ───────────────────────────────────────────── */}
      <footer
        style={{
          padding: '32px 24px',
          borderTop: '1px solid rgba(255,255,255,0.06)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 16,
          color: 'var(--color-text-muted)',
          fontSize: '0.85rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 600, color: 'var(--color-text-secondary)' }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
            <line x1="4" y1="20" x2="4" y2="14" /><line x1="8" y1="20" x2="8" y2="10" />
            <line x1="12" y1="20" x2="12" y2="4" /><line x1="16" y1="20" x2="16" y2="8" />
            <line x1="20" y1="20" x2="20" y2="12" />
          </svg>
          DataLens
        </div>
        <div style={{ display: 'flex', gap: 24 }}>
          <a href="#features" style={{ color: 'inherit' }}>Features</a>
          <a href="#workflow" style={{ color: 'inherit' }}>Workflow</a>
          <a href="#pricing" style={{ color: 'inherit' }}>Pricing</a>
          <Link to="/login" style={{ color: 'inherit' }}>Login</Link>
        </div>
        <span>Built with ♥ · 2025</span>
      </footer>
    </div>
  );
}
