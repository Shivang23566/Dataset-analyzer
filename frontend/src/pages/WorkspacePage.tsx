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
import { logout } from '../lib/api';

type Tab = 'upload' | 'eda' | 'visualization' | 'preprocess' | 'ml';

const TABS = [
  { id: 'upload' as Tab, label: 'Upload', icon: Upload },
  { id: 'eda' as Tab, label: 'EDA', icon: BarChart3 },
  { id: 'visualization' as Tab, label: 'Visualize', icon: Sparkles },
  { id: 'preprocess' as Tab, label: 'Preprocess', icon: Settings },
  { id: 'ml' as Tab, label: 'ML Builder', icon: Brain },
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

  const userEmail = getLoggedInEmail() || '';

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
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

        .ws-container {
          min-height: 100vh;
          background: #0e0f0d;
          color: #cdc9c0;
          font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
          display: flex;
          flex-direction: column;
        }

        /* ─── Top Navigation ─── */
        .ws-nav {
          height: 60px;
          border-bottom: 1px solid rgba(201,168,76,0.09);
          background: rgba(14,15,13,0.97);
          backdrop-filter: blur(16px);
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 0 24px;
          position: sticky;
          top: 0;
          z-index: 100;
        }

        .ws-nav-left {
          display: flex;
          align-items: center;
          gap: 20px;
        }

        .ws-logo {
          display: flex;
          align-items: center;
          gap: 10px;
          cursor: pointer;
          padding: 6px 12px 6px 8px;
          border-radius: 8px;
          transition: background 0.2s;
        }
        .ws-logo:hover {
          background: rgba(46,184,160,0.08);
        }

        .ws-logo-icon {
          width: 32px;
          height: 32px;
          background: linear-gradient(135deg, #2eb8a0 0%, #1a8a78 100%);
          border-radius: 8px;
          display: flex;
          align-items: center;
          justify-content: center;
          box-shadow: 0 2px 12px rgba(46,184,160,0.25);
        }
        .ws-logo-icon svg {
          color: #fff;
        }

        .ws-logo-text {
          font-size: 17px;
          font-weight: 600;
          color: #d4cfc8;
          letter-spacing: -0.3px;
        }

        .ws-nav-divider {
          width: 1px;
          height: 28px;
          background: rgba(201,168,76,0.15);
        }

        /* ─── Tab Navigation ─── */
        .ws-tabs {
          display: flex;
          gap: 2px;
          background: rgba(255,255,255,0.02);
          padding: 4px;
          border-radius: 10px;
          border: 1px solid rgba(201,168,76,0.08);
        }

        .ws-tab {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 8px 16px;
          border: none;
          background: transparent;
          color: #5a5648;
          font-family: 'Inter', sans-serif;
          font-size: 13px;
          font-weight: 500;
          cursor: pointer;
          border-radius: 7px;
          transition: all 0.2s ease;
          position: relative;
        }
        .ws-tab:hover:not(:disabled) {
          color: #8a8272;
          background: rgba(201,168,76,0.05);
        }
        .ws-tab:disabled {
          opacity: 0.35;
          cursor: not-allowed;
        }
        .ws-tab.active {
          background: rgba(46,184,160,0.12);
          color: #2eb8a0;
        }
        .ws-tab.active svg {
          color: #2eb8a0;
        }

        .ws-tab-icon {
          width: 18px;
          height: 18px;
        }

        /* ─── Nav Right ─── */
        .ws-nav-right {
          display: flex;
          align-items: center;
          gap: 12px;
        }

        .ws-file-badge {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 6px 14px;
          background: rgba(46,184,160,0.08);
          border: 1px solid rgba(46,184,160,0.15);
          border-radius: 20px;
          font-size: 12px;
          color: #2eb8a0;
          font-family: 'JetBrains Mono', monospace;
          max-width: 200px;
        }
        .ws-file-badge span {
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .ws-file-dot {
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background: #2eb8a0;
          flex-shrink: 0;
          animation: wsPulse 2s ease-in-out infinite;
        }
        @keyframes wsPulse {
          0%, 100% { opacity: 0.5; }
          50% { opacity: 1; }
        }

        .ws-dashboard-btn {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 8px 14px;
          background: rgba(201,168,76,0.08);
          border: 1px solid rgba(201,168,76,0.15);
          border-radius: 8px;
          color: #c9a84c;
          font-family: 'Inter', sans-serif;
          font-size: 12px;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.2s;
        }
        .ws-dashboard-btn:hover {
          background: rgba(201,168,76,0.12);
          border-color: rgba(201,168,76,0.25);
        }

        .ws-user-avatar {
          width: 34px;
          height: 34px;
          border-radius: 50%;
          background: linear-gradient(135deg, #1e2018, #2a2b1f);
          border: 1px solid rgba(201,168,76,0.18);
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 12px;
          font-weight: 600;
          color: #8a8272;
          cursor: pointer;
          transition: all 0.2s;
        }
        .ws-user-avatar:hover {
          border-color: rgba(201,168,76,0.35);
          transform: scale(1.05);
        }

        /* ─── Main Content ─── */
        .ws-main {
          flex: 1;
          display: flex;
          flex-direction: column;
        }

        /* ─── Progress Bar ─── */
        .ws-progress-bar {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 0;
          padding: 20px 24px;
          background: rgba(0,0,0,0.2);
          border-bottom: 1px solid rgba(201,168,76,0.06);
        }

        .ws-progress-step {
          display: flex;
          align-items: center;
          gap: 10px;
        }

        .ws-progress-dot {
          width: 28px;
          height: 28px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 11px;
          font-weight: 600;
          border: 2px solid rgba(201,168,76,0.15);
          background: transparent;
          color: #4a4840;
          transition: all 0.3s ease;
        }
        .ws-progress-dot.active {
          border-color: #2eb8a0;
          background: rgba(46,184,160,0.15);
          color: #2eb8a0;
          box-shadow: 0 0 20px rgba(46,184,160,0.2);
        }
        .ws-progress-dot.completed {
          border-color: #2eb8a0;
          background: #2eb8a0;
          color: #0e0f0d;
        }

        .ws-progress-label {
          font-size: 12px;
          font-weight: 500;
          color: #4a4840;
          transition: color 0.3s;
        }
        .ws-progress-label.active {
          color: #2eb8a0;
        }
        .ws-progress-label.completed {
          color: #5a5648;
        }

        .ws-progress-line {
          width: 60px;
          height: 2px;
          background: rgba(201,168,76,0.1);
          margin: 0 12px;
          position: relative;
          overflow: hidden;
        }
        .ws-progress-line.completed {
          background: #2eb8a0;
        }
        .ws-progress-line.active::after {
          content: '';
          position: absolute;
          left: 0;
          top: 0;
          width: 50%;
          height: 100%;
          background: linear-gradient(90deg, rgba(46,184,160,0.5), #2eb8a0);
          animation: wsProgressPulse 1.5s ease-in-out infinite;
        }
        @keyframes wsProgressPulse {
          0%, 100% { transform: translateX(-100%); }
          50% { transform: translateX(100%); }
        }

        /* ─── Content Area ─── */
        .ws-content {
          flex: 1;
          padding: 24px;
          overflow-y: auto;
        }

        .ws-content-inner {
          max-width: 1400px;
          margin: 0 auto;
        }

        /* ─── Animations ─── */
        @keyframes wsFadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .ws-fade-in {
          animation: wsFadeIn 0.4s ease forwards;
        }
      `}</style>

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
