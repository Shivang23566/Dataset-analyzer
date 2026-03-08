import { Link } from 'react-router-dom';
import { motion, useScroll, useTransform } from 'framer-motion';
import { 
  ArrowRight, 
  Database, 
  LineChart, 
  LockKeyhole, 
  Sparkles,
  BarChart3,
  Brain,
  Zap,
  Shield,
  Cpu,
  TrendingUp,
  FileText,
  Boxes,
  GitBranch,
  Workflow
} from 'lucide-react';
import { useRef } from 'react';
import BallpitBackground from '../components/BallpitBackground';
import Navbar from '../components/Navbar';

const featureCards = [
  {
    title: 'Intelligent Upload Pipeline',
    desc: 'Drag & drop CSV/JSON files up to 500MB. Automatic validation, encoding detection, and instant preview.',
    icon: Database,
    gradient: 'from-indigo-500 to-purple-500',
    delay: 0
  },
  {
    title: 'Zero-Code EDA Engine',
    desc: 'Statistical summaries, distribution analysis, correlation matrices, and missing value detection in milliseconds.',
    icon: Sparkles,
    gradient: 'from-sky-500 to-indigo-500',
    delay: 0.1
  },
  {
    title: 'Premium Visualization Studio',
    desc: 'Generate publication-ready charts with smart axis detection. 7 chart types, Dark Cosmos theme, 300 DPI export.',
    icon: LineChart,
    gradient: 'from-violet-500 to-pink-500',
    delay: 0.2
  },
  {
    title: 'Enterprise-Grade Security',
    desc: 'JWT authentication, bcrypt password hashing, SQLAlchemy ORM, and role-based access control.',
    icon: LockKeyhole,
    gradient: 'from-emerald-500 to-teal-500',
    delay: 0.3
  },
  {
    title: 'ML Model Builder',
    desc: 'Train classification and regression models with hyperparameter tuning. One-click prediction deployment.',
    icon: Brain,
    gradient: 'from-orange-500 to-red-500',
    delay: 0.4
  },
  {
    title: 'Data Preprocessing Suite',
    desc: 'Handle missing values, encode categoricals, scale features, and engineer new columns with visual feedback.',
    icon: Cpu,
    gradient: 'from-blue-500 to-cyan-500',
    delay: 0.5
  },
];

const capabilities = [
  {
    icon: BarChart3,
    title: 'Advanced Chart Types',
    items: ['Bar Charts', 'Line Graphs', 'Scatter Plots', 'Histograms', 'Pie Charts', 'Box Plots', 'Heatmaps']
  },
  {
    icon: FileText,
    title: 'Statistical Analysis',
    items: ['Descriptive Stats', 'Correlation Matrix', 'Distribution Tests', 'Outlier Detection', 'Group Aggregations']
  },
  {
    icon: Boxes,
    title: 'Data Transforms',
    items: ['Missing Value Imputation', 'One-Hot Encoding', 'Label Encoding', 'Feature Scaling', 'Column Engineering']
  },
  {
    icon: GitBranch,
    title: 'ML Algorithms',
    items: ['Linear Regression', 'Logistic Regression', 'Decision Trees', 'Random Forest', 'Cross-Validation']
  },
];

const workflow = [
  {
    number: '01',
    title: 'Authenticate',
    desc: 'Create your account with email verification. Secure JWT-based session management ensures your data stays private.',
    icon: Shield,
    color: 'indigo'
  },
  {
    number: '02',
    title: 'Upload Dataset',
    desc: 'Drag & drop your CSV/JSON file. The system automatically profiles columns, detects data types, and generates a preview.',
    icon: Database,
    color: 'sky'
  },
  {
    number: '03',
    title: 'Explore & Analyze',
    desc: 'Navigate between EDA, Preprocessing, Visualization, and ML Builder tabs. Real-time insights update as you interact.',
    icon: Zap,
    color: 'violet'
  },
  {
    number: '04',
    title: 'Export Results',
    desc: 'Download high-resolution charts (PNG), statistical reports (JSON), or trained ML models for production deployment.',
    icon: TrendingUp,
    color: 'emerald'
  },
];

export default function LandingPage() {
  const containerRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start start", "end start"]
  });

  const heroY = useTransform(scrollYProgress, [0, 1], ["0%", "50%"]);
  const heroOpacity = useTransform(scrollYProgress, [0, 0.5], [1, 0]);

  return (
    <div className="page-shell" ref={containerRef}>
      <div className="noise-layer" />
      <Navbar />

      {/* HERO SECTION with 3D Background */}
      <motion.section 
        className="hero"
        style={{ y: heroY, opacity: heroOpacity }}
      >
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
          initial={{ opacity: 0, y: 30, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
        >
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
          >
            <p className="eyebrow">
              <Workflow className="inline" size={14} />
              <span>Data Intelligence Platform • Engineered for Speed</span>
            </p>
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
          >
            From raw datasets to
            <br />
            <span className="gradient-text">explainable insights</span>
            <br />
            in one focused workflow
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.4 }}
          >
            Enterprise-grade data analysis platform with zero-code EDA, automated visualization, 
            ML model building, and secure team collaboration. Built for data scientists, analysts, 
            and business intelligence teams.
          </motion.p>

          <motion.div
            className="hero-actions"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.5 }}
          >
            <Link to="/signup" className="btn btn-primary group">
              Launch Workspace 
              <ArrowRight size={16} className="transition-transform group-hover:translate-x-1" />
            </Link>
            <a href="#features" className="btn btn-ghost group">
              Explore Features
              <motion.span
                className="inline-block ml-2"
                animate={{ y: [0, 4, 0] }}
                transition={{ duration: 1.5, repeat: Infinity }}
              >
                ↓
              </motion.span>
            </a>
          </motion.div>

          {/* Trust Indicators */}
          <motion.div
            className="hero-stats"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.7 }}
          >
            <div>
              <span className="stat-number">500MB</span>
              <span className="stat-label">Max File Size</span>
            </div>
            <div className="divider" />
            <div>
              <span className="stat-number">7</span>
              <span className="stat-label">Chart Types</span>
            </div>
            <div className="divider" />
            <div>
              <span className="stat-number">300 DPI</span>
              <span className="stat-label">Export Quality</span>
            </div>
          </motion.div>
        </motion.div>
      </motion.section>

      {/* FEATURES SECTION with 3D Cards */}
      <section id="features" className="section-block features-section">
        <motion.div 
          className="section-head"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          viewport={{ once: true, margin: "-100px" }}
        >
          <h2>
            Built for <span className="gradient-text">Analyst Velocity</span>
          </h2>
          <p>
            Everything is organized around your real analysis journey, not generic dashboards. 
            From upload to deployment in minutes.
          </p>
        </motion.div>

        <div className="feature-grid-enhanced">
          {featureCards.map((card, index) => {
            const Icon = card.icon;
            return (
              <motion.article
                className="feature-card-3d"
                key={card.title}
                initial={{ opacity: 0, y: 40, rotateX: -15 }}
                whileInView={{ opacity: 1, y: 0, rotateX: 0 }}
                whileHover={{ 
                  y: -8, 
                  rotateX: 5,
                  transition: { duration: 0.2, ease: "easeOut" }
                }}
                transition={{ 
                  duration: 0.6, 
                  delay: card.delay,
                  ease: [0.22, 1, 0.36, 1]
                }}
                viewport={{ once: true, margin: "-50px" }}
                style={{ transformStyle: 'preserve-3d' }}
              >
                <div className={`icon-wrapper bg-gradient-to-br ${card.gradient}`}>
                  <Icon size={24} strokeWidth={2} />
                </div>
                <h3>{card.title}</h3>
                <p>{card.desc}</p>
                <div className="card-glow" />
              </motion.article>
            );
          })}
        </div>
      </section>

      {/* CAPABILITIES SECTION */}
      <section className="section-block capabilities-section">
        <motion.div 
          className="section-head"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          viewport={{ once: true, margin: "-100px" }}
        >
          <h2>
            Complete <span className="gradient-text">Analysis Toolkit</span>
          </h2>
          <p>
            Production-ready features for the entire data analysis lifecycle
          </p>
        </motion.div>

        <div className="capabilities-grid">
          {capabilities.map((capability, index) => {
            const Icon = capability.icon;
            return (
              <motion.div
                key={capability.title}
                className="capability-card"
                initial={{ opacity: 0, scale: 0.9 }}
                whileInView={{ opacity: 1, scale: 1 }}
                whileHover={{ scale: 1.02 }}
                transition={{ duration: 0.4, delay: index * 0.1 }}
                viewport={{ once: true, margin: "-50px" }}
              >
                <div className="capability-header">
                  <Icon size={20} className="capability-icon" />
                  <h3>{capability.title}</h3>
                </div>
                <ul className="capability-list">
                  {capability.items.map((item, i) => (
                    <motion.li
                      key={item}
                      initial={{ opacity: 0, x: -10 }}
                      whileInView={{ opacity: 1, x: 0 }}
                      transition={{ duration: 0.3, delay: index * 0.1 + i * 0.05 }}
                      viewport={{ once: true }}
                    >
                      <span className="bullet">→</span>
                      {item}
                    </motion.li>
                  ))}
                </ul>
              </motion.div>
            );
          })}
        </div>
      </section>

      {/* WORKFLOW SECTION */}
      <section id="workflow" className="section-block workflow-section">
        <motion.div 
          className="section-head"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          viewport={{ once: true, margin: "-100px" }}
        >
          <h2>
            Streamlined <span className="gradient-text">Analysis Workflow</span>
          </h2>
          <p>
            Four steps from raw data to actionable insights. No tool-switching required.
          </p>
        </motion.div>

        <div className="workflow-timeline">
          {workflow.map((step, index) => {
            const Icon = step.icon;
            return (
              <motion.div
                key={step.number}
                className="workflow-step"
                initial={{ opacity: 0, x: index % 2 === 0 ? -40 : 40 }}
                whileInView={{ opacity: 1, x: 0 }}
                whileHover={{ scale: 1.05 }}
                transition={{ duration: 0.5, delay: index * 0.15 }}
                viewport={{ once: true, margin: "-100px" }}
              >
                <div className={`step-indicator ${step.color}`}>
                  <span className="step-number">{step.number}</span>
                  <div className="step-icon-wrapper">
                    <Icon size={20} />
                  </div>
                </div>
                <div className="step-content">
                  <h3>{step.title}</h3>
                  <p>{step.desc}</p>
                </div>
                {index < workflow.length - 1 && (
                  <motion.div
                    className="step-connector"
                    initial={{ scaleX: 0 }}
                    whileInView={{ scaleX: 1 }}
                    transition={{ duration: 0.6, delay: index * 0.15 + 0.3 }}
                    viewport={{ once: true }}
                  />
                )}
              </motion.div>
            );
          })}
        </div>
      </section>

      {/* CTA SECTION */}
      <section className="section-block cta-section">
        <motion.div
          className="cta-container"
          initial={{ opacity: 0, scale: 0.95 }}
          whileInView={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.6 }}
          viewport={{ once: true }}
        >
          <motion.div
            animate={{ 
              rotate: [0, 360],
              scale: [1, 1.1, 1]
            }}
            transition={{ 
              duration: 20, 
              repeat: Infinity,
              ease: "linear"
            }}
            className="cta-background-orb"
          />
          
          <h2>Ready to accelerate your data analysis?</h2>
          <p>
            Join data teams who've reduced their analysis time from hours to minutes. 
            Start analyzing datasets today—completely free.
          </p>
          <Link to="/signup" className="btn btn-primary btn-large group">
            Get Started Free
            <ArrowRight size={20} className="transition-transform group-hover:translate-x-1" />
          </Link>
        </motion.div>
      </section>
    </div>
  );
}
