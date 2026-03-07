import React, { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ChevronDown,
  Activity,
  TrendingUp,
  Database,
  AlertCircle,
  BarChart2,
} from 'lucide-react';
import { analyzeDataset } from '../lib/api';
import type { EdaResponse } from '../lib/types';

type EDAViewProps = { filename: string };

// ─── Count-up animation hook ──────────────────────────────
function useCountUp(target: number, duration = 1200, trigger: number) {
  const [value, setValue] = useState(0);
  const rafRef = useRef<number>(0);

  useEffect(() => {
    if (!trigger) return;
    setValue(0);
    const t0 = performance.now();
    const run = (now: number) => {
      const progress = Math.min((now - t0) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(Math.round(eased * target));
      if (progress < 1) rafRef.current = requestAnimationFrame(run);
    };
    rafRef.current = requestAnimationFrame(run);
    return () => cancelAnimationFrame(rafRef.current);
  }, [target, duration, trigger]);

  return value;
}

// ─── Helpers ─────────────────────────────────────────────
const fmt = (n: number) => n.toLocaleString('en-US');

function corrHeat(val: number | null): string {
  return String(Math.max(0.05, Math.abs(val ?? 0) * 0.75));
}

export default function EDAView({ filename }: EDAViewProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<EdaResponse | null>(null);
  const [runCount, setRunCount] = useState(0);
  const [splitOpen, setSplitOpen] = useState(false);
  const [scanKey, setScanKey] = useState(0);
  const splitRef = useRef<HTMLDivElement>(null);

  // Close split dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (splitRef.current && !splitRef.current.contains(e.target as Node)) {
        setSplitOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const runAnalysis = async () => {
    setLoading(true);
    setError('');
    setSplitOpen(false);
    try {
      const data = await analyzeDataset(filename);
      setResult(data);
      setRunCount((c) => c + 1);
      setScanKey((k) => k + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'EDA failed');
    } finally {
      setLoading(false);
    }
  };

  // ── Derived metrics ──────────────────────────────────────
  const totalCells = result ? result.shape.rows * result.shape.columns : 0;
  const dataQuality = result
    ? Math.max(0, Math.min(100, ((totalCells - result.missing_summary.total_missing) / (totalCells || 1)) * 100))
    : 0;
  const numericCount = result
    ? Object.values(result.column_info).filter((c) => /int|float/.test(c.dtype)).length
    : 0;
  const categoricalCount = result ? result.shape.columns - numericCount : 0;

  // Count-up values
  const rowsVal    = useCountUp(result?.shape.rows ?? 0, 1200, runCount);
  const colsVal    = useCountUp(result?.shape.columns ?? 0, 900, runCount);
  const missingVal = useCountUp(result?.missing_summary.total_missing ?? 0, 1000, runCount);
  const qualityVal = useCountUp(Math.round(dataQuality), 1100, runCount);

  const colEntries    = result ? Object.entries(result.column_info) : [];
  const numericEntries = result ? Object.entries(result.numeric_summary) : [];
  const corrCols      = result ? Object.keys(result.correlation_matrix) : [];

  return (
    <section className="panel eda-panel">

      {/* ── Header ───────────────────────────────────────── */}
      <div className="eda-header">
        <div>
          <h2 className="eda-title"><em>Exploratory Analysis</em></h2>
          <div className="eda-title-underline" />
          <p className="eda-subtitle">
            <Database size={13} style={{ display: 'inline', marginRight: 5 }} />
            {filename}
          </p>
        </div>

        {/* Split pill button */}
        <div className="eda-split-wrap" ref={splitRef}>
          <div className={`eda-split-btn${loading ? ' eda-split-btn--loading' : ''}`}>
            <button
              className="eda-split-left"
              onClick={runAnalysis}
              disabled={loading}
            >
              <span className="eda-dot" />
              {loading ? 'Analyzing…' : 'Run EDA'}
            </button>
            <span className="eda-split-sep" aria-hidden="true" />
            <button
              className="eda-split-right"
              onClick={() => setSplitOpen((o) => !o)}
              disabled={loading}
              aria-label="Analysis options"
            >
              <ChevronDown
                size={14}
                className={`eda-chevron${splitOpen ? ' eda-chevron--open' : ''}`}
              />
            </button>
          </div>
          <AnimatePresence>
            {splitOpen && (
              <motion.div
                className="eda-split-dropdown"
                initial={{ opacity: 0, y: -6, scale: 0.97 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -6, scale: 0.97 }}
                transition={{ duration: 0.15 }}
              >
                <button onClick={runAnalysis}>
                  <Activity size={13} /> Deep Profile
                </button>
                <button onClick={runAnalysis}>
                  <TrendingUp size={13} /> Quick Scan
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {error && (
        <motion.div
          className="error-banner"
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          style={{ display: 'flex', alignItems: 'center', gap: 8 }}
        >
          <AlertCircle size={14} /> {error}
        </motion.div>
      )}

      {/* ── Results ──────────────────────────────────────── */}
      <AnimatePresence>
        {result && (
          <motion.div
            key="eda-results"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.4 }}
          >

            {/* ── Bento Stats Grid ─────────────────────── */}
            <div className="eda-bento">
              {/* Hero: Rows */}
              <div className="eda-stat-card eda-stat-card--hero">
                <div className="eda-stat-noise" aria-hidden="true" />
                <span className="eda-stat-label">Total Rows</span>
                <span className="eda-stat-num">{fmt(rowsVal)}</span>
                <span className="eda-stat-sub">observations in dataset</span>
              </div>
              {/* Columns */}
              <div className="eda-stat-card">
                <div className="eda-stat-noise" aria-hidden="true" />
                <span className="eda-stat-label">Columns</span>
                <span className="eda-stat-num eda-stat-num--sm">{colsVal}</span>
                <span className="eda-stat-sub">
                  {numericCount} numeric · {categoricalCount} categorical
                </span>
              </div>
              {/* Missing */}
              <div className="eda-stat-card">
                <div className="eda-stat-noise" aria-hidden="true" />
                <span className="eda-stat-label">Missing Values</span>
                <span className="eda-stat-num eda-stat-num--sm">{fmt(missingVal)}</span>
                <span className="eda-stat-sub">null / NaN cells total</span>
              </div>
              {/* Data Quality score */}
              <div className="eda-stat-card eda-stat-card--full">
                <div className="eda-stat-noise" aria-hidden="true" />
                <div className="eda-quality-row">
                  <div>
                    <span className="eda-stat-label">Data Quality Score</span>
                    <span className="eda-stat-num eda-stat-num--sm">
                      {qualityVal}<span className="eda-stat-pct">%</span>
                    </span>
                  </div>
                  <BarChart2 size={28} className="eda-quality-icon" />
                </div>
                <div className="eda-quality-track">
                  <div
                    className="eda-quality-fill"
                    style={{ '--eda-q': `${dataQuality}%` } as React.CSSProperties}
                  />
                </div>
              </div>
            </div>

            {/* ── Column Profile Cards ────────────────────── */}
            <div className="eda-section-head">
              <span>Column Profile</span>
              <span className="eda-section-badge">{colEntries.length} columns</span>
            </div>

            <div className="eda-col-list-wrap" key={scanKey}>
              <div className="eda-scanline" aria-hidden="true" />
              <div className="eda-col-list">
                {colEntries.map(([col, info], i) => {
                  const isNumeric  = /int|float/.test(info.dtype);
                  const uniquePct  = Math.min(100, (info.unique / (result.shape.rows || 1)) * 100);
                  const missHealth = info.missing_pct > 50 ? 'danger' : info.missing_pct > 10 ? 'warn' : 'ok';
                  const numS       = result.numeric_summary[col];

                  return (
                    <div
                      key={col}
                      className={`eda-col-card eda-col-card--${isNumeric ? 'num' : 'cat'}`}
                      style={{ animationDelay: `${i * 60}ms` }}
                    >
                      <span className="eda-col-index" aria-hidden="true">
                        {String(i + 1).padStart(2, '0')}
                      </span>

                      <div className="eda-col-card-top">
                        <span className="eda-col-name">{col}</span>
                        <div className="eda-col-badges">
                          <span className="eda-col-badge">{info.dtype}</span>
                          {info.missing_pct > 0 && (
                            <span className={`eda-col-miss eda-col-miss--${missHealth}`}>
                              {info.missing_pct.toFixed(1)}% null
                            </span>
                          )}
                        </div>
                      </div>

                      <div className="eda-col-card-mid">
                        <div className="eda-col-stat">
                          <span className="eda-col-stat-val">{fmt(info.unique)}</span>
                          <span className="eda-col-stat-key">unique</span>
                        </div>
                        {numS && (
                          <>
                            <div className="eda-col-stat">
                              <span className="eda-col-stat-val">{numS.mean.toFixed(2)}</span>
                              <span className="eda-col-stat-key">mean</span>
                            </div>
                            <div className="eda-col-stat">
                              <span className="eda-col-stat-val">{numS.std.toFixed(2)}</span>
                              <span className="eda-col-stat-key">std</span>
                            </div>
                            <div className="eda-col-stat">
                              <span className="eda-col-stat-val">{numS.min.toFixed(2)}</span>
                              <span className="eda-col-stat-key">min</span>
                            </div>
                            <div className="eda-col-stat">
                              <span className="eda-col-stat-val">{numS.max.toFixed(2)}</span>
                              <span className="eda-col-stat-key">max</span>
                            </div>
                          </>
                        )}
                      </div>

                      {/* Uniqueness-density progress bar */}
                      <div className="eda-col-bar-wrap">
                        <div className="eda-col-bar-track">
                          <div
                            className="eda-col-bar-fill"
                            style={
                              { '--eda-pct': `${uniquePct}%` } as React.CSSProperties
                            }
                          />
                        </div>
                        <span className="eda-col-bar-label">
                          {uniquePct.toFixed(0)}% unique density
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* ── Numeric Statistical Summary ─────────────── */}
            {numericEntries.length > 0 && (
              <>
                <div className="eda-section-head" style={{ marginTop: 28 }}>
                  <span>Numeric Summary</span>
                  <span className="eda-section-badge">{numericEntries.length} columns</span>
                </div>
                <div className="eda-num-table-wrap">
                  <table className="eda-num-table">
                    <thead>
                      <tr>
                        <th>Column</th>
                        <th>Mean</th>
                        <th>Median</th>
                        <th>Std Dev</th>
                        <th>Min</th>
                        <th>Max</th>
                        <th>Range</th>
                        <th title="Coefficient of Variation">CV %</th>
                        <th>Outlier Signal</th>
                      </tr>
                    </thead>
                    <tbody>
                      {numericEntries.map(([col, s]) => {
                        const range      = s.max - s.min;
                        const cv         = s.mean !== 0 ? Math.abs((s.std / s.mean) * 100) : 0;
                        const hiOutlier  = s.max > s.mean + 3 * s.std;
                        const loOutlier  = s.min < s.mean - 3 * s.std;
                        return (
                          <tr key={col}>
                            <td className="eda-num-col-name">{col}</td>
                            <td>{s.mean.toFixed(3)}</td>
                            <td>{s.median.toFixed(3)}</td>
                            <td>{s.std.toFixed(3)}</td>
                            <td>{s.min.toFixed(3)}</td>
                            <td>{s.max.toFixed(3)}</td>
                            <td>{range.toFixed(3)}</td>
                            <td>{cv.toFixed(1)}%</td>
                            <td>
                              {hiOutlier || loOutlier ? (
                                <span className="eda-outlier-badge">
                                  {hiOutlier && loOutlier ? '± likely' : hiOutlier ? '↑ high' : '↓ low'}
                                </span>
                              ) : (
                                <span className="eda-clean-badge">clean</span>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </>
            )}

            {/* ── Correlation Matrix Heatmap ──────────────── */}
            {corrCols.length >= 2 && (
              <>
                <div className="eda-section-head" style={{ marginTop: 28 }}>
                  <span>Correlation Matrix</span>
                  <span className="eda-section-badge">
                    {corrCols.length} × {corrCols.length}
                  </span>
                </div>
                <div className="eda-corr-scroll">
                  <div
                    className="eda-corr-grid"
                    style={{
                      gridTemplateColumns: `minmax(90px,auto) repeat(${corrCols.length}, minmax(52px,1fr))`,
                    }}
                  >
                    {/* top-left corner spacer */}
                    <div className="eda-corr-corner" />
                    {/* column headers */}
                    {corrCols.map((c) => (
                      <div key={`h-${c}`} className="eda-corr-header" title={c}>
                        {c}
                      </div>
                    ))}
                    {/* data rows */}
                    {corrCols.map((rowCol) => (
                      <React.Fragment key={`row-${rowCol}`}>
                        <div className="eda-corr-row-label" title={rowCol}>
                          {rowCol}
                        </div>
                        {corrCols.map((colCol) => {
                          const val    = result.correlation_matrix[rowCol]?.[colCol] ?? null;
                          const isSelf = rowCol === colCol;
                          const isPos  = (val ?? 0) >= 0;
                          return (
                            <div
                              key={`${rowCol}×${colCol}`}
                              className={`eda-corr-cell${isSelf ? ' eda-corr-cell--self' : ''}`}
                              title={
                                val !== null
                                  ? `${rowCol} × ${colCol}: ${val.toFixed(3)}`
                                  : 'N/A'
                              }
                              style={{
                                '--eda-heat': corrHeat(val),
                                '--eda-heat-clr': isPos
                                  ? 'var(--accent)'
                                  : 'var(--accent-2)',
                              } as React.CSSProperties}
                            >
                              <span>{val !== null ? val.toFixed(2) : '—'}</span>
                            </div>
                          );
                        })}
                      </React.Fragment>
                    ))}
                  </div>
                </div>
              </>
            )}

            {/* ── Missing Value Profile ────────────────────── */}
            {colEntries.some(([, info]) => info.missing_pct > 0) && (
              <>
                <div className="eda-section-head" style={{ marginTop: 28 }}>
                  <span>Missing Value Profile</span>
                  <span className="eda-section-badge">
                    {colEntries.filter(([, info]) => info.missing_pct > 0).length} columns affected
                  </span>
                </div>
                <div className="eda-missing-list">
                  {colEntries
                    .filter(([, info]) => info.missing_pct > 0)
                    .sort((a, b) => b[1].missing_pct - a[1].missing_pct)
                    .map(([col, info]) => {
                      const severity =
                        info.missing_pct > 50
                          ? 'danger'
                          : info.missing_pct > 20
                          ? 'warn'
                          : 'low';
                      return (
                        <div key={col} className="eda-missing-row">
                          <span className="eda-missing-col">{col}</span>
                          <div className="eda-missing-track">
                            <div
                              className={`eda-missing-fill eda-missing-fill--${severity}`}
                              style={
                                { '--eda-pct': `${info.missing_pct}%` } as React.CSSProperties
                              }
                            />
                          </div>
                          <span className={`eda-missing-pct eda-missing-pct--${severity}`}>
                            {info.missing_pct.toFixed(1)}%
                          </span>
                        </div>
                      );
                    })}
                </div>
              </>
            )}

          </motion.div>
        )}
      </AnimatePresence>
    </section>
  );
}
