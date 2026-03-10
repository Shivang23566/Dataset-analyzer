import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  getDashboardSummary,
  getDashboardDatasets,
  getDashboardSessions,
  getDashboardDownloads,
  getPaymentStatus,
  deleteDataset,
  logout,
} from '../lib/api';
import type {
  DashboardSummary,
  DashboardDataset,
  DashboardSession,
  DashboardDownload,
  PaymentStatus,
} from '../lib/types';
import { extractErrorMessage } from '../lib/errorUtils';

// ── Type configs (same as mockup) ──────────────
const typeConfig: Record<string, {
  color: string; bg: string; border: string; glyph: string;
}> = {
  ml:            { color: "#2eb8a0", bg: "rgba(46,184,160,0.07)",  border: "rgba(46,184,160,0.2)",  glyph: "◈" },
  preprocessing: { color: "#c9933a", bg: "rgba(201,147,58,0.07)",  border: "rgba(201,147,58,0.2)",  glyph: "◎" },
  eda:           { color: "#9b87c2", bg: "rgba(155,135,194,0.07)", border: "rgba(155,135,194,0.2)", glyph: "◉" },
  upload:        { color: "#7a7669", bg: "rgba(122,118,105,0.07)", border: "rgba(122,118,105,0.18)", glyph: "⊕" },
};

const fileGlyph: Record<string, string> = {
  model: "◈", processed_csv: "▤", chart: "◭", code: "◌",
  Model: "◈", CSV: "▤", Chart: "◭", Code: "◌",
};

// ── Helpers ────────────────────────────────────
function timeAgo(isoDate: string): string {
  const now = new Date();
  const date = new Date(isoDate);
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`;
  return date.toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short',
  });
}

function formatBytes(bytes: number | null): string {
  if (!bytes) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1048576).toFixed(1)} MB`;
}

function getGreeting(): string {
  const h = new Date().getHours();
  if (h < 12) return 'Good morning';
  if (h < 17) return 'Good afternoon';
  return 'Good evening';
}

function getFirstName(fullName: string | null | undefined, email: string | undefined): string {
  if (fullName && fullName.trim()) return fullName.split(' ')[0];
  if (email && email.includes('@')) return email.split('@')[0];
  return 'User';
}

function getInitials(fullName: string | null | undefined, email: string | undefined): string {
  if (fullName && fullName.trim()) {
    return fullName.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
  }
  if (email && email.length > 0) {
    return email[0].toUpperCase();
  }
  return 'U';
}

function parseResultSummary(raw: string | null): Record<string, unknown> {
  if (!raw) return {};
  try { return JSON.parse(raw); } catch { return {}; }
}

function getSessionDetail(session: DashboardSession): string {
  const summary = parseResultSummary(session.result_summary);
  if (session.session_type === 'ml') {
    const model = summary.model_name || 'Model';
    const acc = summary.accuracy;
    return acc ? `${model} · Accuracy ${(Number(acc) * 100).toFixed(1)}%` : String(model);
  }
  if (session.session_type === 'preprocessing') {
    const rowsBefore = summary.rows_before;
    const rowsAfter = summary.rows_after;
    if (rowsBefore && rowsAfter) {
      return `${rowsBefore} → ${rowsAfter} rows`;
    }
    return 'Pipeline completed';
  }
  if (session.session_type === 'eda') {
    const rows = summary.rows;
    const cols = summary.columns;
    if (rows && cols) return `${rows} rows · ${cols} columns`;
    return 'Analysis completed';
  }
  return 'Completed';
}

function getSessionLabel(type: string): string {
  switch (type) {
    case 'ml': return 'ML Training';
    case 'preprocessing': return 'Preprocessing';
    case 'eda': return 'EDA Analysis';
    default: return type;
  }
}

// ── Sub-components (same styling as mockup) ────

function SectionCard({
  title, action, onAction, children, style = {},
}: {
  title?: string;
  action?: string;
  onAction?: () => void;
  children: React.ReactNode;
  style?: React.CSSProperties;
}) {
  return (
    <div style={{
      background: "linear-gradient(160deg, #161712 0%, #121310 100%)",
      border: "1px solid rgba(201,168,76,0.11)",
      borderRadius: 16,
      overflow: "hidden",
      boxShadow: "0 2px 24px rgba(0,0,0,0.35), inset 0 1px 0 rgba(201,168,76,0.05)",
      ...style,
    }}>
      {(title || action) && (
        <div style={{
          padding: "16px 22px 13px",
          borderBottom: "1px solid rgba(201,168,76,0.07)",
          display: "flex", justifyContent: "space-between", alignItems: "center",
          background: "rgba(201,168,76,0.02)",
        }}>
          <span style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: 12, color: "#8a8272",
            letterSpacing: "0.12em", textTransform: "uppercase",
          }}>{title}</span>
          {action && (
            <button className="link-btn" onClick={onAction}
              style={{
                fontFamily: "'Inter', sans-serif", fontSize: 11,
                color: "#5a5648", letterSpacing: "0.04em",
                background: "none", border: "none", cursor: "pointer",
              }}>
              {action} →
            </button>
          )}
        </div>
      )}
      {children}
    </div>
  );
}

function AnalysisBadge({ done, label }: { done: boolean; label: string }) {
  return (
    <span style={{
      fontSize: 10, padding: "3px 9px", borderRadius: 20,
      fontFamily: "'Inter', sans-serif", letterSpacing: "0.04em",
      background: done ? "rgba(46,184,160,0.1)" : "rgba(255,255,255,0.03)",
      color: done ? "#2eb8a0" : "#3d3b34",
      border: `1px solid ${done ? "rgba(46,184,160,0.22)" : "rgba(255,255,255,0.05)"}`,
    }}>
      {done ? "✓" : "·"} {label}
    </span>
  );
}

// ── Main Component ─────────────────────────────

export default function DashboardPage() {
  const navigate = useNavigate();
  const [tab, setTab] = useState('overview');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Data states
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [datasets, setDatasets] = useState<DashboardDataset[]>([]);
  const [sessions, setSessions] = useState<DashboardSession[]>([]);
  const [downloads, setDownloads] = useState<DashboardDownload[]>([]);
  const [payment, setPayment] = useState<PaymentStatus | null>(null);

  // Fetch all data on mount
  useEffect(() => {
    async function fetchAll() {
      setLoading(true);
      setError('');
      try {
        const [summaryRes, datasetsRes, sessionsRes, downloadsRes, paymentRes] =
          await Promise.all([
            getDashboardSummary(),
            getDashboardDatasets(),
            getDashboardSessions(),
            getDashboardDownloads(),
            getPaymentStatus(),
          ]);
        setSummary(summaryRes);
        setDatasets(datasetsRes.datasets);
        setSessions(sessionsRes.sessions);
        setDownloads(downloadsRes.downloads);
        setPayment(paymentRes);
      } catch (e: unknown) {
        const msg = extractErrorMessage(e);
        setError(msg);
        if (msg.includes('Not authenticated')) {
          navigate('/login');
        }
      } finally {
        setLoading(false);
      }
    }
    fetchAll();
  }, [navigate]);

  // Delete dataset handler
  async function handleDeleteDataset(id: number) {
    if (!confirm('Delete this dataset? This cannot be undone.')) return;
    try {
      await deleteDataset(id);
      setDatasets(prev => prev.filter(d => d.id !== id));
      if (summary) {
        setSummary({
          ...summary,
          stats: { ...summary.stats, datasets: summary.stats.datasets - 1 },
        });
      }
    } catch {
      alert('Failed to delete dataset');
    }
  }

  // Open dataset in workspace
  function handleOpenDataset(savedFilename: string) {
    navigate('/workspace', { state: { filename: savedFilename } });
  }

  // Logout
  function handleLogout() {
    logout();
    navigate('/login');
  }

  const plan = payment?.plan || summary?.subscription?.plan || 'free';
  const isPro = plan === 'pro';
  const userName = summary?.user?.full_name || '';
  const userEmail = summary?.user?.email || '';
  const firstName = getFirstName(userName, userEmail);
  const initials = getInitials(userName, userEmail);
  const memberSince = summary?.user?.member_since
    ? new Date(summary.user.member_since).toLocaleDateString('en-IN', {
        month: 'long', year: 'numeric',
      })
    : '';

  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'datasets', label: 'Datasets' },
    { id: 'activity', label: 'Activity' },
    { id: 'downloads', label: 'Downloads' },
  ];

  // Build dataset analysis map from sessions
  function getDatasetAnalyses(datasetId: number): {
    eda: boolean; preprocessing: boolean; ml: boolean;
  } {
    const datasetSessions = sessions.filter(
      s => s.dataset_id === datasetId
    );
    return {
      eda: datasetSessions.some(s => s.session_type === 'eda'),
      preprocessing: datasetSessions.some(
        s => s.session_type === 'preprocessing'
      ),
      ml: datasetSessions.some(s => s.session_type === 'ml'),
    };
  }

  // Calculate total storage
  function getTotalStorage(): string {
    const total = datasets.reduce(
      (sum, d) => sum + (d.file_size_bytes || 0), 0
    );
    return formatBytes(total);
  }

  // Get best accuracy from ML sessions
  function getBestAccuracy(): string {
    let best = 0;
    sessions.forEach(s => {
      if (s.session_type === 'ml') {
        const summary = parseResultSummary(s.result_summary);
        const acc = Number(summary.accuracy || 0);
        if (acc > best) {
          best = acc;
        }
      }
    });
    if (best > 0) return `${(best * 100).toFixed(1)}%`;
    return '—';
  }

  function getBestAccuracySub(): string {
    let best = 0;
    let bestModel = '';
    let bestFile = '';
    sessions.forEach(s => {
      if (s.session_type === 'ml') {
        const sum = parseResultSummary(s.result_summary);
        const acc = Number(sum.accuracy || 0);
        if (acc > best) {
          best = acc;
          bestModel = String(sum.model_name || 'Model');
          bestFile = String(sum.filename || '');
        }
      }
    });
    if (bestModel && bestFile) return `${bestModel} on ${bestFile}`;
    if (bestModel) return bestModel;
    return 'no models trained yet';
  }

  if (loading) {
    return (
      <div style={{
        minHeight: '100vh', background: '#0e0f0d',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        color: '#4a4840', fontFamily: "'Inter', sans-serif", fontStyle: 'italic',
      }}>
        Loading dashboard...
      </div>
    );
  }

  if (error) {
    return (
      <div style={{
        minHeight: '100vh', background: '#0e0f0d',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        flexDirection: 'column', gap: 16,
        color: '#c9933a', fontFamily: "'Inter', sans-serif",
      }}>
        <div style={{ fontSize: 16 }}>Failed to load dashboard</div>
        <div style={{ fontSize: 13, color: '#5a5648', fontStyle: 'italic' }}>{error}</div>
        <button onClick={() => window.location.reload()} style={{
          marginTop: 8, padding: '8px 20px', borderRadius: 8,
          background: 'rgba(201,168,76,0.1)',
          border: '1px solid rgba(201,168,76,0.2)',
          color: '#c9a84c', cursor: 'pointer',
          fontFamily: "'Inter', sans-serif", fontSize: 11,
        }}>Retry</button>
      </div>
    );
  }

  return (
    <div style={{
      minHeight: "100vh", background: "#0e0f0d", color: "#cdc9c0",
      fontFamily: "'Inter', -apple-system, sans-serif",
      display: "flex", flexDirection: "column",
    }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        ::-webkit-scrollbar { width: 5px; }
        ::-webkit-scrollbar-track { background: #0e0f0d; }
        ::-webkit-scrollbar-thumb { background: #2a2920; border-radius: 4px; }
        .db-link-btn { background: none; border: none; cursor: pointer; transition: color 0.2s; }
        .db-link-btn:hover { color: #c9a84c !important; }
        .db-nav-tab { background: none; border: none; cursor: pointer; transition: all 0.2s; position: relative; }
        .db-nav-tab:hover .db-tab-label { color: #c9a84c !important; }
        .db-nav-tab.active .db-tab-label { color: #c9a84c !important; }
        .db-nav-tab.active::after {
          content: ''; position: absolute; bottom: -1px; left: 0; right: 0;
          height: 1px; background: linear-gradient(90deg, #c9a84c 60%, transparent);
        }
        .db-stat-card { transition: all 0.3s cubic-bezier(0.22,1,0.36,1); cursor: default; }
        .db-stat-card:hover {
          border-color: rgba(201,168,76,0.28) !important;
          transform: translateY(-3px);
          box-shadow: 0 12px 40px rgba(0,0,0,0.5), 0 0 0 1px rgba(201,168,76,0.08) !important;
        }
        .db-dataset-card { transition: all 0.25s ease; cursor: pointer; }
        .db-dataset-card:hover {
          border-color: rgba(46,184,160,0.32) !important;
          box-shadow: 0 6px 28px rgba(0,0,0,0.4), inset 0 1px 0 rgba(46,184,160,0.06) !important;
          transform: translateY(-2px);
        }
        .db-activity-row { transition: background 0.18s ease; }
        .db-activity-row:hover { background: rgba(201,168,76,0.03) !important; }
        .db-dl-row { transition: background 0.18s ease; }
        .db-dl-row:hover { background: rgba(201,168,76,0.03) !important; }
        .db-btn-primary { transition: all 0.2s ease; cursor: pointer; border: none; font-family: 'Inter', sans-serif; }
        .db-btn-primary:hover { filter: brightness(1.15); transform: translateY(-1px); box-shadow: 0 8px 28px rgba(46,184,160,0.28) !important; }
        .db-btn-ghost { transition: all 0.2s ease; cursor: pointer; font-family: 'Inter', sans-serif; }
        .db-btn-ghost:hover { background: rgba(201,168,76,0.07) !important; border-color: rgba(201,168,76,0.3) !important; color: #c9a84c !important; }
        .db-dl-btn { transition: all 0.15s ease; cursor: pointer; font-family: 'Inter', sans-serif; }
        .db-dl-btn:hover { background: rgba(46,184,160,0.12) !important; border-color: rgba(46,184,160,0.35) !important; color: #2eb8a0 !important; }
        @keyframes dbFadeUp {
          from { opacity: 0; transform: translateY(14px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        .db-fade-up { animation: dbFadeUp 0.5s cubic-bezier(0.22,1,0.36,1) forwards; }
        .db-d1 { animation-delay: 0.04s; opacity: 0; }
        .db-d2 { animation-delay: 0.09s; opacity: 0; }
        .db-d3 { animation-delay: 0.14s; opacity: 0; }
        .db-d4 { animation-delay: 0.19s; opacity: 0; }
        .db-d5 { animation-delay: 0.24s; opacity: 0; }
        @keyframes dbGoldShimmer {
          0%   { background-position: -200% center; }
          100% { background-position:  200% center; }
        }
        .db-gold-shimmer {
          background: linear-gradient(90deg, #a07830, #e8cc7a, #c9a84c, #e8cc7a, #a07830);
          background-size: 300% auto;
          animation: dbGoldShimmer 4s linear infinite;
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
        }
        @keyframes dbBreathe { 0%,100%{opacity:0.55;} 50%{opacity:1;} }
        .db-breathe { animation: dbBreathe 2.8s ease-in-out infinite; }
        .db-divider {
          height: 1px;
          background: linear-gradient(90deg, transparent, rgba(201,168,76,0.1), transparent);
          margin: 0;
        }
      `}</style>

      {/* ── NAV ── */}
      <nav style={{
        height: 58,
        borderBottom: "1px solid rgba(201,168,76,0.09)",
        background: "rgba(14,15,13,0.97)",
        backdropFilter: "blur(16px)",
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "0 36px",
        position: "sticky", top: 0, zIndex: 100,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{
            width: 30, height: 30,
            background: "linear-gradient(135deg, #2eb8a0 0%, #1a8a78 100%)",
            borderRadius: 8,
            display: "flex", alignItems: "center", justifyContent: "center",
            boxShadow: "0 2px 12px rgba(46,184,160,0.3)",
          }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.5" strokeLinecap="round">
              <line x1="4" y1="20" x2="4" y2="14" />
              <line x1="8" y1="20" x2="8" y2="10" />
              <line x1="12" y1="20" x2="12" y2="4" />
              <line x1="16" y1="20" x2="16" y2="8" />
              <line x1="20" y1="20" x2="20" y2="12" />
            </svg>
          </div>
          <span style={{
            fontFamily: "'Inter', -apple-system, sans-serif",
            fontSize: 17, fontWeight: 600, color: "#d4cfc8", letterSpacing: "-0.3px",
          }}>DataLens</span>
        </div>

        <div style={{ display: "flex", gap: 0 }}>
          {tabs.map(t => (
            <button key={t.id}
              className={`db-nav-tab${tab === t.id ? " active" : ""}`}
              onClick={() => setTab(t.id)}
              style={{ padding: "0 18px", height: 58 }}>
              <span className="db-tab-label" style={{
                fontFamily: "'Inter', sans-serif",
                fontSize: 13,
                color: tab === t.id ? "#c9a84c" : "#5a5648",
                letterSpacing: "0.02em",
              }}>{t.label}</span>
            </button>
          ))}
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          {isPro ? (
            <div style={{
              display: "flex", alignItems: "center", gap: 7,
              background: "rgba(201,168,76,0.07)",
              border: "1px solid rgba(201,168,76,0.18)",
              borderRadius: 24, padding: "5px 13px",
            }}>
              <span className="db-breathe" style={{
                width: 5, height: 5, borderRadius: "50%",
                background: "#c9a84c", display: "block",
              }} />
              <span className="db-gold-shimmer" style={{
                fontSize: 10, letterSpacing: "0.14em",
                fontFamily: "'Inter', sans-serif",
              }}>PRO</span>
            </div>
          ) : (
            <button
              onClick={() => navigate('/upgrade')}
              style={{
                display: "flex", alignItems: "center", gap: 7,
                background: "rgba(46,184,160,0.07)",
                border: "1px solid rgba(46,184,160,0.18)",
                borderRadius: 24, padding: "5px 13px",
                cursor: "pointer",
                fontSize: 10, letterSpacing: "0.14em",
                fontFamily: "'Inter', sans-serif",
                color: "#2eb8a0",
              }}>
              ↑ UPGRADE
            </button>
          )}
          <div
            onClick={handleLogout}
            style={{
              width: 34, height: 34, borderRadius: "50%",
              background: "linear-gradient(135deg, #1e2018, #2a2b1f)",
              border: "1px solid rgba(201,168,76,0.18)",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 12, color: "#8a8272", cursor: "pointer",
              fontFamily: "'Inter', sans-serif",
            }}
            title="Logout"
          >
            {initials}
          </div>
        </div>
      </nav>

      {/* ── CONTENT ── */}
      <main style={{
        flex: 1, padding: "36px 36px 60px",
        maxWidth: 1320, margin: "0 auto", width: "100%",
      }}>

        {/* ═══════════ OVERVIEW TAB ═══════════ */}
        {tab === 'overview' && (
          <div style={{ display: "flex", flexDirection: "column", gap: 28 }}>

            {/* Greeting */}
            <div className="db-fade-up db-d1" style={{
              display: "flex", justifyContent: "space-between",
              alignItems: "flex-end",
            }}>
              <div>
                <div style={{
                  fontSize: 11, color: "#4a4840", letterSpacing: "0.12em",
                  fontFamily: "'Inter', sans-serif", marginBottom: 8,
                }}>
                  DASHBOARD · {new Date().toLocaleDateString("en-IN", {
                    weekday: "long", day: "numeric", month: "long",
                  }).toUpperCase()}
                </div>
                <h1 style={{
                  fontFamily: "'Inter', sans-serif",
                  fontSize: 42, fontWeight: 700,
                  color: "#d4cfc8", lineHeight: 1.1, letterSpacing: "-1px",
                }}>
                  {getGreeting()},<br />
                  <span style={{ color: "#2eb8a0" }}>{firstName}.</span>
                </h1>
                <p style={{
                  fontSize: 13, color: "#4a4840", marginTop: 10,
                  fontStyle: "italic", fontFamily: "'Inter', sans-serif",
                }}>
                  {memberSince && `Member since ${memberSince} · `}{userEmail}
                </p>
              </div>
              <button className="db-btn-primary" onClick={() => navigate('/workspace')}
                style={{
                  background: "linear-gradient(135deg, #2eb8a0, #1a9a88)",
                  color: "#fff", padding: "11px 24px", borderRadius: 10,
                  fontSize: 12, letterSpacing: "0.07em",
                  fontFamily: "'Inter', sans-serif", fontWeight: 500,
                  boxShadow: "0 4px 20px rgba(46,184,160,0.2)",
                }}>+ New Analysis</button>
            </div>

            {/* Stats */}
            <div className="db-fade-up db-d2" style={{
              display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 14,
            }}>
              {[
                { label: "Datasets", value: summary?.stats.datasets ?? 0, sub: "active files", accent: "#2eb8a0" },
                { label: "Sessions", value: summary?.stats.sessions ?? 0, sub: "analyses run", accent: "#c9933a" },
                { label: "Downloads", value: summary?.stats.downloads ?? 0, sub: "files exported", accent: "#9b87c2" },
                { label: "Storage Used", value: getTotalStorage(), sub: "across all datasets", accent: "#c9a84c" },
                { label: "Best Accuracy", value: getBestAccuracy(), sub: getBestAccuracySub(), accent: "#2eb8a0" },
              ].map((s, i) => (
                <div key={i} className="db-stat-card" style={{
                  background: "linear-gradient(160deg, #141510 0%, #111210 100%)",
                  border: "1px solid rgba(201,168,76,0.1)",
                  borderRadius: 14, padding: "20px 22px",
                  boxShadow: "0 2px 16px rgba(0,0,0,0.3)",
                  position: "relative", overflow: "hidden",
                }}>
                  <div style={{
                    position: "absolute", top: 0, left: 0, right: 0, height: 2,
                    background: `linear-gradient(90deg, ${s.accent}55, transparent)`,
                    borderRadius: "14px 14px 0 0",
                  }} />
                  <div style={{
                    fontFamily: "'Inter', sans-serif",
                    fontSize: 10, color: "#5a5648",
                    letterSpacing: "0.1em", marginBottom: 10,
                  }}>{s.label.toUpperCase()}</div>
                  <div style={{
                    fontFamily: "'Inter', sans-serif",
                    fontSize: 32, fontWeight: 700, color: s.accent,
                    lineHeight: 1, marginBottom: 6,
                  }}>{s.value}</div>
                  <div style={{
                    fontSize: 11, color: "#3d3b34", fontStyle: "italic",
                  }}>{s.sub}</div>
                </div>
              ))}
            </div>

            {/* Two-col layout */}
            <div style={{
              display: "grid", gridTemplateColumns: "1fr 390px",
              gap: 20, alignItems: "start",
            }}>
              {/* Datasets panel */}
              <div className="db-fade-up db-d3">
                <SectionCard title="My Datasets" action="View all"
                  onAction={() => setTab('datasets')}>
                  {datasets.length === 0 ? (
                    <div style={{
                      padding: '40px 22px', textAlign: 'center',
                      color: '#3d3b34', fontStyle: 'italic', fontSize: 13,
                    }}>
                      No datasets uploaded yet.
                      <button className="db-btn-primary"
                        onClick={() => navigate('/workspace')}
                        style={{
                          display: 'block', margin: '16px auto 0',
                          background: "linear-gradient(135deg, #2eb8a0, #1a9a88)",
                          color: "#fff", padding: "9px 20px",
                          borderRadius: 8, fontSize: 11,
                          fontFamily: "'Inter', sans-serif",
                        }}>
                        Upload your first dataset
                      </button>
                    </div>
                  ) : (
                    datasets.slice(0, 3).map((d, i) => {
                      const analyses = getDatasetAnalyses(d.id);
                      return (
                        <div key={d.id}>
                          <div className="db-dataset-card" style={{
                            padding: "18px 22px",
                            border: "1px solid transparent",
                            borderRadius: 0, background: "transparent",
                          }}>
                            <div style={{
                              display: "flex", justifyContent: "space-between",
                              alignItems: "flex-start",
                            }}>
                              <div style={{ flex: 1 }}>
                                <div style={{
                                  display: "flex", alignItems: "center",
                                  gap: 10, marginBottom: 6,
                                }}>
                                  <span style={{ fontSize: 16, color: "#3d5a54" }}>▤</span>
                                  <span style={{
                                    fontFamily: "'Inter', sans-serif", fontSize: 14,
                                    color: "#d4cfc8", fontWeight: 500,
                                  }}>{d.original_filename}</span>
                                </div>
                                <div style={{
                                  fontSize: 12, color: "#4a4840",
                                  fontStyle: "italic", marginBottom: 10,
                                }}>
                                  {d.row_count?.toLocaleString() ?? '—'} rows
                                  &nbsp;·&nbsp;{d.col_count ?? '—'} columns
                                  &nbsp;·&nbsp;{formatBytes(d.file_size_bytes)}
                                  &nbsp;·&nbsp;uploaded {timeAgo(d.uploaded_at)}
                                </div>
                                <div style={{ display: "flex", gap: 6 }}>
                                  <AnalysisBadge done={analyses.eda} label="EDA" />
                                  <AnalysisBadge done={analyses.preprocessing} label="Prep" />
                                  <AnalysisBadge done={analyses.ml} label="ML" />
                                </div>
                              </div>
                              <div style={{
                                display: "flex", gap: 8,
                                marginLeft: 16, flexShrink: 0,
                              }}>
                                <button className="db-btn-primary"
                                  onClick={() => handleOpenDataset(d.saved_filename)}
                                  style={{
                                    background: "linear-gradient(135deg, #2eb8a0, #1a9a88)",
                                    color: "#fff", padding: "7px 14px",
                                    borderRadius: 8, fontSize: 11,
                                    letterSpacing: "0.05em",
                                    fontFamily: "'Inter', sans-serif",
                                  }}>Open</button>
                                <button className="db-btn-ghost"
                                  onClick={() => handleDeleteDataset(d.id)}
                                  style={{
                                    padding: "7px 10px", fontSize: 13, color: "#4a4840",
                                    background: "rgba(255,255,255,0.03)",
                                    border: "1px solid rgba(255,255,255,0.07)",
                                    borderRadius: 8,
                                  }}>⌫</button>
                              </div>
                            </div>
                          </div>
                          {i < Math.min(datasets.length, 3) - 1 && (
                            <div className="db-divider" />
                          )}
                        </div>
                      );
                    })
                  )}
                </SectionCard>
              </div>

              {/* Right column */}
              <div className="db-fade-up db-d4" style={{
                display: "flex", flexDirection: "column", gap: 16,
              }}>
                {/* Recent Activity */}
                <SectionCard title="Recent Activity" action="View all"
                  onAction={() => setTab('activity')}>
                  {sessions.length === 0 ? (
                    <div style={{
                      padding: '30px 22px', textAlign: 'center',
                      color: '#3d3b34', fontStyle: 'italic', fontSize: 12,
                    }}>No analysis sessions yet</div>
                  ) : (
                    sessions.slice(0, 4).map((s, i) => {
                      const c = typeConfig[s.session_type] || typeConfig.eda;
                      return (
                        <div key={s.id}>
                          <div className="db-activity-row" style={{
                            padding: "14px 22px",
                            display: "flex", gap: 12,
                            alignItems: "flex-start",
                          }}>
                            <div style={{
                              width: 32, height: 32, borderRadius: 8,
                              flexShrink: 0, background: c.bg,
                              border: `1px solid ${c.border}`,
                              display: "flex", alignItems: "center",
                              justifyContent: "center",
                              fontSize: 14, color: c.color,
                            }}>{c.glyph}</div>
                            <div style={{ flex: 1, minWidth: 0 }}>
                              <div style={{
                                display: "flex", justifyContent: "space-between",
                                marginBottom: 3,
                              }}>
                                <span style={{
                                  fontFamily: "'Inter', sans-serif",
                                  fontSize: 10, color: c.color,
                                  letterSpacing: "0.08em",
                                }}>
                                  {getSessionLabel(s.session_type).toUpperCase()}
                                </span>
                                <span style={{
                                  fontSize: 10, color: "#3d3b34",
                                  fontStyle: "italic",
                                }}>
                                  {timeAgo(s.created_at)}
                                </span>
                              </div>
                              <div style={{
                                fontSize: 12, color: "#cdc9c0",
                                whiteSpace: "nowrap", overflow: "hidden",
                                textOverflow: "ellipsis",
                              }}>
                                {parseResultSummary(s.result_summary)?.filename as string || 'Dataset'}
                              </div>
                              <div style={{
                                fontSize: 11, color: "#4a4840",
                                marginTop: 2, fontStyle: "italic",
                              }}>
                                {getSessionDetail(s)}
                              </div>
                            </div>
                          </div>
                          {i < Math.min(sessions.length, 4) - 1 && (
                            <div className="db-divider" />
                          )}
                        </div>
                      );
                    })
                  )}
                </SectionCard>

                {/* Downloads */}
                <SectionCard title="Downloads" action="View all"
                  onAction={() => setTab('downloads')}>
                  {downloads.length === 0 ? (
                    <div style={{
                      padding: '30px 22px', textAlign: 'center',
                      color: '#3d3b34', fontStyle: 'italic', fontSize: 12,
                    }}>No downloads yet</div>
                  ) : (
                    downloads.slice(0, 4).map((d, i) => (
                      <div key={d.id}>
                        <div className="db-dl-row" style={{
                          padding: "12px 22px",
                          display: "flex", alignItems: "center",
                          justifyContent: "space-between", gap: 10,
                        }}>
                          <div style={{
                            display: "flex", alignItems: "center",
                            gap: 10, minWidth: 0,
                          }}>
                            <span style={{
                              fontSize: 14, color: "#4a4840", flexShrink: 0,
                            }}>{fileGlyph[d.file_type] || "◌"}</span>
                            <div style={{ minWidth: 0 }}>
                              <div style={{
                                fontSize: 11, color: "#9a9688",
                                whiteSpace: "nowrap", overflow: "hidden",
                                textOverflow: "ellipsis", maxWidth: 195,
                              }}>{d.original_filename}</div>
                              <div style={{
                                fontSize: 10, color: "#3d3b34",
                                marginTop: 2, fontStyle: "italic",
                              }}>
                                {d.file_type} · {timeAgo(d.downloaded_at)}
                              </div>
                            </div>
                          </div>
                        </div>
                        {i < Math.min(downloads.length, 4) - 1 && (
                          <div className="db-divider" />
                        )}
                      </div>
                    ))
                  )}
                </SectionCard>
              </div>
            </div>
          </div>
        )}

        {/* ═══════════ DATASETS TAB ═══════════ */}
        {tab === 'datasets' && (
          <div style={{ display: "flex", flexDirection: "column", gap: 24 }}
            className="db-fade-up">
            <div style={{
              display: "flex", justifyContent: "space-between",
              alignItems: "flex-end",
            }}>
              <div>
                <div style={{
                  fontFamily: "'Inter', sans-serif", fontSize: 10,
                  color: "#4a4840", letterSpacing: "0.12em", marginBottom: 6,
                }}>ALL DATASETS</div>
                <h2 style={{
                  fontFamily: "'Inter', sans-serif",
                  fontSize: 34, color: "#d4cfc8", fontWeight: 700,
                }}>
                  {datasets.length} Files
                </h2>
                <p style={{
                  fontSize: 12, color: "#4a4840",
                  fontStyle: "italic", marginTop: 4,
                }}>{getTotalStorage()} total storage</p>
              </div>
              <button className="db-btn-primary"
                onClick={() => navigate('/workspace')}
                style={{
                  background: "linear-gradient(135deg, #2eb8a0, #1a9a88)",
                  color: "#fff", padding: "11px 22px", borderRadius: 10,
                  fontSize: 11, letterSpacing: "0.07em",
                  fontFamily: "'Inter', sans-serif",
                  boxShadow: "0 4px 20px rgba(46,184,160,0.2)",
                }}>+ Upload Dataset</button>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {datasets.map((d, i) => {
                const analyses = getDatasetAnalyses(d.id);
                return (
                  <div key={d.id} className="db-dataset-card db-fade-up"
                    style={{
                      background: "linear-gradient(160deg, #141510 0%, #111210 100%)",
                      border: "1px solid rgba(201,168,76,0.1)",
                      borderRadius: 14, padding: "22px 26px",
                      boxShadow: "0 2px 20px rgba(0,0,0,0.3)",
                      animationDelay: `${i * 0.06}s`, opacity: 0,
                      display: "flex", justifyContent: "space-between",
                      alignItems: "center",
                    }}>
                    <div style={{ flex: 1 }}>
                      <div style={{
                        display: "flex", alignItems: "center",
                        gap: 10, marginBottom: 7,
                      }}>
                        <span style={{ fontSize: 18, color: "#3d5a54" }}>▤</span>
                        <span style={{
                          fontFamily: "'Inter', sans-serif", fontSize: 15,
                          color: "#d4cfc8", fontWeight: 500,
                        }}>{d.original_filename}</span>
                      </div>
                      <div style={{
                        fontSize: 12, color: "#4a4840",
                        fontStyle: "italic", marginBottom: 12,
                      }}>
                        {d.row_count?.toLocaleString() ?? '—'} rows
                        &nbsp;·&nbsp;{d.col_count ?? '—'} columns
                        &nbsp;·&nbsp;{formatBytes(d.file_size_bytes)}
                        &nbsp;·&nbsp;uploaded {timeAgo(d.uploaded_at)}
                        {d.last_accessed_at &&
                          <>&nbsp;·&nbsp;last used {timeAgo(d.last_accessed_at)}</>
                        }
                      </div>
                      <div style={{ display: "flex", gap: 7 }}>
                        <AnalysisBadge done={analyses.eda} label="EDA" />
                        <AnalysisBadge done={analyses.preprocessing} label="Prep" />
                        <AnalysisBadge done={analyses.ml} label="ML" />
                      </div>
                    </div>
                    <div style={{
                      display: "flex", gap: 10, marginLeft: 24, flexShrink: 0,
                    }}>
                      <button className="db-btn-primary"
                        onClick={() => handleOpenDataset(d.saved_filename)}
                        style={{
                          background: "linear-gradient(135deg, #2eb8a0, #1a9a88)",
                          color: "#fff", padding: "9px 18px",
                          borderRadius: 9, fontSize: 11,
                          letterSpacing: "0.06em",
                          fontFamily: "'Inter', sans-serif",
                        }}>▶ Open</button>
                      <button className="db-btn-ghost"
                        onClick={() => handleDeleteDataset(d.id)}
                        style={{
                          padding: "9px 14px", fontSize: 14, color: "#4a4840",
                          background: "rgba(255,255,255,0.03)",
                          border: "1px solid rgba(255,255,255,0.07)",
                          borderRadius: 9,
                        }}>⌫</button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* ═══════════ ACTIVITY TAB ═══════════ */}
        {tab === 'activity' && (
          <div style={{ display: "flex", flexDirection: "column", gap: 24 }}
            className="db-fade-up">
            <div>
              <div style={{
                fontFamily: "'Inter', sans-serif", fontSize: 10,
                color: "#4a4840", letterSpacing: "0.12em", marginBottom: 6,
              }}>ANALYSIS HISTORY</div>
              <h2 style={{
                fontFamily: "'Inter', sans-serif",
                fontSize: 34, color: "#d4cfc8", fontWeight: 700,
              }}>
                {sessions.length} Sessions
              </h2>
            </div>
            <SectionCard>
              {sessions.length === 0 ? (
                <div style={{
                  padding: '40px 22px', textAlign: 'center',
                  color: '#3d3b34', fontStyle: 'italic', fontSize: 13,
                }}>No analysis sessions yet</div>
              ) : (
                sessions.map((s, i) => {
                  const c = typeConfig[s.session_type] || typeConfig.eda;
                  return (
                    <div key={s.id}>
                      <div className="db-activity-row" style={{
                        padding: "20px 26px",
                        display: "flex", gap: 18,
                        alignItems: "center",
                      }}>
                        <div style={{
                          width: 40, height: 40, borderRadius: 10,
                          flexShrink: 0, background: c.bg,
                          border: `1px solid ${c.border}`,
                          display: "flex", alignItems: "center",
                          justifyContent: "center",
                          fontSize: 18, color: c.color,
                        }}>{c.glyph}</div>
                        <div style={{ flex: 1 }}>
                          <div style={{
                            display: "flex", alignItems: "center",
                            gap: 10, marginBottom: 4,
                          }}>
                            <span style={{
                              fontFamily: "'Inter', sans-serif",
                              fontSize: 10, color: c.color,
                              letterSpacing: "0.1em",
                            }}>
                              {getSessionLabel(s.session_type).toUpperCase()}
                            </span>
                            <span style={{
                              fontSize: 13, color: "#d4cfc8", fontWeight: 500,
                            }}>
                              {parseResultSummary(s.result_summary)?.filename as string || 'Dataset'}
                            </span>
                          </div>
                          <div style={{
                            fontSize: 12, color: "#5a5648", fontStyle: "italic",
                          }}>
                            {getSessionDetail(s)}
                          </div>
                        </div>
                        <div style={{ textAlign: "right", flexShrink: 0 }}>
                          <div style={{
                            fontSize: 11, color: "#3d3b34",
                            fontStyle: "italic",
                          }}>
                            {timeAgo(s.created_at)}
                          </div>
                        </div>
                      </div>
                      {i < sessions.length - 1 && <div className="db-divider" />}
                    </div>
                  );
                })
              )}
            </SectionCard>
          </div>
        )}

        {/* ═══════════ DOWNLOADS TAB ═══════════ */}
        {tab === 'downloads' && (
          <div style={{ display: "flex", flexDirection: "column", gap: 24 }}
            className="db-fade-up">
            <div>
              <div style={{
                fontFamily: "'Inter', sans-serif", fontSize: 10,
                color: "#4a4840", letterSpacing: "0.12em", marginBottom: 6,
              }}>EXPORT HISTORY</div>
              <h2 style={{
                fontFamily: "'Inter', sans-serif",
                fontSize: 34, color: "#d4cfc8", fontWeight: 700,
              }}>
                {downloads.length} Downloads
              </h2>
            </div>
            <SectionCard>
              {downloads.length === 0 ? (
                <div style={{
                  padding: '40px 22px', textAlign: 'center',
                  color: '#3d3b34', fontStyle: 'italic', fontSize: 13,
                }}>No downloads yet</div>
              ) : (
                <>
                  <div style={{
                    padding: "11px 26px",
                    borderBottom: "1px solid rgba(201,168,76,0.07)",
                    display: "grid",
                    gridTemplateColumns: "1fr 120px 160px",
                    gap: 16,
                  }}>
                    {["Filename", "Type", "Downloaded"].map((h, i) => (
                      <span key={i} style={{
                        fontFamily: "'Inter', sans-serif",
                        fontSize: 9, color: "#3d3b34",
                        letterSpacing: "0.12em",
                      }}>
                        {h.toUpperCase()}
                      </span>
                    ))}
                  </div>
                  {downloads.map((d, i) => (
                    <div key={d.id}>
                      <div className="db-dl-row" style={{
                        padding: "16px 26px",
                        display: "grid",
                        gridTemplateColumns: "1fr 120px 160px",
                        gap: 16, alignItems: "center",
                      }}>
                        <div style={{
                          display: "flex", alignItems: "center", gap: 12,
                        }}>
                          <span style={{ fontSize: 16, color: "#4a4840" }}>
                            {fileGlyph[d.file_type] || "◌"}
                          </span>
                          <span style={{ fontSize: 13, color: "#cdc9c0" }}>
                            {d.original_filename}
                          </span>
                        </div>
                        <span style={{
                          fontFamily: "'Inter', sans-serif",
                          fontSize: 9, padding: "3px 10px",
                          borderRadius: 20, letterSpacing: "0.08em",
                          background: "rgba(255,255,255,0.04)",
                          color: "#5a5648",
                          border: "1px solid rgba(255,255,255,0.07)",
                          width: "fit-content",
                        }}>{d.file_type.toUpperCase()}</span>
                        <span style={{
                          fontSize: 12, color: "#4a4840", fontStyle: "italic",
                        }}>
                          {timeAgo(d.downloaded_at)}
                        </span>
                      </div>
                      {i < downloads.length - 1 && <div className="db-divider" />}
                    </div>
                  ))}
                </>
              )}
            </SectionCard>
          </div>
        )}
      </main>
    </div>
  );
}
