import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowRight, CheckCircle2, Database, LineChart, LockKeyhole, Sparkles } from 'lucide-react';
import BallpitBackground from '../components/BallpitBackground';
import Navbar from '../components/Navbar';

const featureCards = [
  {
    title: 'Dataset Upload Pipeline',
    desc: 'Upload CSV/JSON and instantly route files into your analysis workspace.',
    icon: Database,
  },
  {
    title: 'One-Click EDA',
    desc: 'Get shape, missing values, numeric summary, and correlations without notebook scripts.',
    icon: Sparkles,
  },
  {
    title: 'Visualization Studio',
    desc: 'Generate bar, line, scatter, histogram, boxplot, and pie charts from selected columns.',
    icon: LineChart,
  },
  {
    title: 'Secure Access',
    desc: 'Database-backed authentication with JWT authorization for protected analytics routes.',
    icon: LockKeyhole,
  },
];

export default function LandingPage() {
  return (
    <div className="page-shell">
      <div className="noise-layer" />
      <Navbar />

      <section className="hero">
        <BallpitBackground
          count={150}
          colors={['#6366F1', '#0EA5E9', '#8B5CF6']}
          gravity={0.35}
          friction={0.998}
          followCursor
          className="hero-ballpit"
        />
        <div className="hero-overlay" />

        <motion.div
          className="hero-content"
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <p className="eyebrow">Data intelligence, engineered for speed</p>
          <h1>From raw dataset to explainable insights in one focused workflow.</h1>
          <p>
            Dataset Analyzer gives your team login-based access, upload automation, zero-code EDA, and visualization output in one clean web experience.
          </p>
          <div className="hero-actions">
            <Link to="/signup" className="btn btn-primary">
              Launch Workspace <ArrowRight size={16} />
            </Link>
            <a href="#workflow" className="btn btn-ghost">
              Explore Workflow
            </a>
          </div>
        </motion.div>
      </section>

      <section id="features" className="section-block">
        <div className="section-head">
          <h2>Built For Analyst Velocity</h2>
          <p>Everything is organized around your real analysis journey, not generic dashboards.</p>
        </div>
        <div className="feature-grid">
          {featureCards.map((card, index) => {
            const Icon = card.icon;
            return (
              <motion.article
                className="feature-card"
                key={card.title}
                initial={{ opacity: 0, y: 12 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.35, delay: index * 0.05 }}
                viewport={{ once: true }}
              >
                <Icon size={20} />
                <h3>{card.title}</h3>
                <p>{card.desc}</p>
              </motion.article>
            );
          })}
        </div>
      </section>

      <section id="workflow" className="section-block workflow-block">
        <div className="section-head">
          <h2>Workflow Without Tool-Switching</h2>
        </div>
        <div className="steps-grid">
          <div>
            <span>01</span>
            <h3>Sign in and authenticate</h3>
            <p>Create account or login with secure identity flow and receive backend JWT access.</p>
          </div>
          <div>
            <span>02</span>
            <h3>Upload your dataset</h3>
            <p>Push your CSV/JSON and lock that file as your active workspace source.</p>
          </div>
          <div>
            <span>03</span>
            <h3>Choose EDA or Visualization</h3>
            <p>Switch from summary statistics to chart generation directly from the side panel.</p>
          </div>
        </div>
      </section>
    </div>
  );
}
