import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Upload,
  BarChart3,
  Sparkles,
  Settings,
  Brain,
  LogOut,
  LayoutDashboard,
  ChevronRight,
} from 'lucide-react';
import UploaderPanel from '../components/UploaderPanel';
import EDAView from '../components/EDAView';
import VisualizationView from '../components/VisualizationView';
import PreprocessingView from '../components/PreprocessingView';
import MLBuilderView from '../components/MLBuilderView';
import { ToastContainer } from '../components/ToastContainer';
import { getLoggedInEmail } from '../lib/authStore';
import { logout, getPaymentStatus } from '../lib/api';

type Tab = 'upload' | 'eda' | 'visualization' | 'preprocess' | 'ml';

const TABS = [
  { id: 'upload' as Tab, label: 'Upload', icon: Upload, proOnly: false },
  { id: 'eda' as Tab, label: 'EDA', icon: BarChart3, proOnly: false },
  { id: 'visualization' as Tab, label: 'Visualize', icon: Sparkles, proOnly: false },
  { id: 'preprocess' as Tab, label: 'Preprocess', icon: Settings, proOnly: true },
  { id: 'ml' as Tab, label: 'ML Builder', icon: Brain, proOnly: true },
];

function getInitials(email: string): string {
  if (!email) return 'U';
  return email[0].toUpperCase();
}

export default function WorkspacePage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [activeTab, setActiveTab] = useState<Tab>('upload');
  const [fileName, setFileName] = useState('');
  const [processedFileName, setProcessedFileName] = useState('');
  const [isPro, setIsPro] = useState(true); // default true to avoid flash

  const userEmail = getLoggedInEmail() || '';

  // Fetch subscription status
  useEffect(() => {
    getPaymentStatus()
      .then((res) => setIsPro(res.plan === 'pro'))
      .catch(() => setIsPro(false));
  }, []);

  // Auto-load file from dashboard "Open" button
  useEffect(() => {
    const state = location.state as { filename?: string } | null;
    if (state?.filename && state.filename !== fileName) {
      setFileName(state.filename);
      setProcessedFileName('');
      setActiveTab('eda');
      window.history.replaceState({}, document.title);
    }
  }, [location.state, fileName]);

  const onLogout = () => {
    logout();
    navigate('/login');
  };

  const goToDashboard = () => {
    navigate('/dashboard');
  };

  return (
    <div className="ws-container">

      {/* ─── Top Navigation ─── */}
      <nav className="ws-nav">
        <div className="ws-nav-left">
          {/* Logo */}
          <div className="ws-logo" onClick={goToDashboard} title="Go to Dashboard">
            <div className="ws-logo-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                <line x1="4" y1="20" x2="4" y2="14" />
                <line x1="8" y1="20" x2="8" y2="10" />
                <line x1="12" y1="20" x2="12" y2="4" />
                <line x1="16" y1="20" x2="16" y2="8" />
                <line x1="20" y1="20" x2="20" y2="12" />
              </svg>
            </div>
            <span className="ws-logo-text">DataLens</span>
          </div>

          <div className="ws-nav-divider" />

          {/* Tab Navigation */}
          <div className="ws-tabs">
            {TABS.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              const isDisabled = tab.id !== 'upload' && !fileName;

              return (
                <button
                  key={tab.id}
                  className={`ws-tab ${isActive ? 'active' : ''}`}
                  onClick={() => !isDisabled && setActiveTab(tab.id)}
                  disabled={isDisabled}
                >
                  <Icon className="ws-tab-icon" size={18} />
                  {tab.label}
                  {tab.proOnly && !isPro && <span className="ws-pro-badge">PRO</span>}
                </button>
              );
            })}
          </div>
        </div>

        <div className="ws-nav-right">
          {/* Current File Badge */}
          {fileName && (
            <motion.div
              className="ws-file-badge"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
            >
              <div className="ws-file-dot" />
              <span>{fileName}</span>
            </motion.div>
          )}

          {/* Dashboard Button */}
          <button className="ws-dashboard-btn" onClick={goToDashboard}>
            <LayoutDashboard size={14} />
            Dashboard
          </button>

          {/* User Avatar */}
          <div
            className="ws-user-avatar"
            onClick={onLogout}
            title={`${userEmail} - Click to logout`}
          >
            {getInitials(userEmail)}
          </div>
        </div>
      </nav>

      {/* ─── Main Content ─── */}
      <main className="ws-main">
        {/* Progress Bar */}
        <div className="ws-progress-bar">
          {TABS.map((tab, index) => {
            const isActive = activeTab === tab.id;
            const currentIndex = TABS.findIndex(t => t.id === activeTab);
            const isCompleted = fileName && index < currentIndex;
            const isPast = index < currentIndex;

            return (
              <div key={tab.id} className="ws-progress-step">
                <div className={`ws-progress-dot ${isActive ? 'active' : ''} ${isCompleted ? 'completed' : ''}`}>
                  {isCompleted ? '✓' : index + 1}
                </div>
                <span className={`ws-progress-label ${isActive ? 'active' : ''} ${isCompleted ? 'completed' : ''}`}>
                  {tab.label}
                </span>
                {index < TABS.length - 1 && (
                  <div className={`ws-progress-line ${isCompleted ? 'completed' : ''} ${isActive && index === currentIndex - 1 ? 'active' : ''}`} />
                )}
              </div>
            );
          })}
        </div>

        {/* Content Area */}
        <div className="ws-content">
          <div className="ws-content-inner ws-fade-in" key={activeTab}>
            {activeTab === 'upload' && (
              <UploaderPanel
                currentFile={fileName}
                onUploaded={(uploaded) => {
                  setFileName(uploaded);
                  setProcessedFileName('');
                  setActiveTab('eda');
                }}
              />
            )}

            {activeTab === 'eda' && fileName && <EDAView filename={fileName} />}

            {activeTab === 'visualization' && fileName && <VisualizationView filename={fileName} />}

            {activeTab === 'preprocess' && fileName && (
              <PreprocessingView
                filename={fileName}
                onProcessed={(pf) => setProcessedFileName(pf)}
              />
            )}

            {activeTab === 'ml' && fileName && (
              <MLBuilderView filename={processedFileName || fileName} />
            )}
          </div>
        </div>
      </main>
      <ToastContainer />
    </div>
  );
}
