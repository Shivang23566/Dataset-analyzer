import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  AlertCircle,
  AlertTriangle,
  BarChart2,
  CheckCircle,
  ChevronDown,
  ChevronUp,
  Database,
  Download,
  Droplet,
  GitBranch,
  Layers,
  Loader2,
  Minimize2,
  Play,
  Settings,
  Sparkles,
  Trash2,
  Activity,
  Zap,
} from 'lucide-react';
import {
  getDatasetHealth,
  getPreprocessColumns,
  getImputationRecommendations,
  detectOutliersApi,
  runPipeline,
  getDownloadUrl,
  getDownloadHeaders,
} from '../lib/api';
import type {
  DatasetHealthResponse,
  PreprocessColumnMeta,
  PipelineRunResponse,
} from '../lib/types';

// ── Step config types ─────────────────────────────────────────
type DupConfig = {
  enabled: boolean;
  keep: 'first' | 'last' | 'none';
};
type MissingConfig = {
  enabled: boolean;
  strategies: Record<string, string>;
};
type OutlierConfig = {
  enabled: boolean;
  method: 'iqr' | 'zscore';
  threshold: number;
  treatment: 'cap' | 'remove' | 'median' | 'flag';
};
type TypeConfig = {
  enabled: boolean;
  auto_detect: boolean;
  extract_datetime: boolean;
};
type FeatureConfig = {
  enabled: boolean;
  log_transform: string[];
  sqrt_transform: string[];
  encoding: Record<string, string>;
};
type ScalingConfig = {
  enabled: boolean;
  method: string;
};
type ImbalanceConfig = {
  enabled: boolean;
  target_col: string;
  method: string;
};
type DimConfig = {
  enabled: boolean;
  method: string;
  corr_threshold: number;
  pca_components: number;
};
type SplitConfig = {
  enabled: boolean;
  test_size: number;
  stratify_col: string;
  random_state: number;
};

// ── Constants ─────────────────────────────────────────────────
const MISSING_STRATEGIES = [
  'drop_rows', 'mean', 'median', 'mode',
  'knn', 'forward_fill', 'backward_fill', 'unknown',
];
const SCALE_METHODS   = ['standard', 'minmax', 'robust', 'maxabs', 'log', 'power'];
const SCALE_DESCS: Record<string, string> = {
  standard: 'Standardize to zero mean, unit variance (Z-score).',
  minmax:   'Scale values to the [0, 1] range.',
  robust:   'Scale using median and IQR — robust to outliers.',
  maxabs:   'Scale to [−1, 1] by dividing by max absolute value.',
  log:      'Apply log(1 + x) transformation.',
  power:    'Yeo-Johnson power transformation for normality.',
};
const IMBALANCE_METHODS = ['smote', 'adasyn', 'over', 'under', 'smotetomek'];
const DIM_METHODS       = ['remove_correlated', 'pca', 'remove_low_variance'];
const DOWNLOAD_FORMATS  = [
  { format: 'csv',     ext: 'csv',     label: 'CSV'     },
  { format: 'excel',   ext: 'xlsx',    label: 'Excel'   },
  { format: 'parquet', ext: 'parquet', label: 'Parquet' },
  { format: 'json',    ext: 'json',    label: 'JSON'    },
];

const isNumericDtype = (dtype: string) =>
  /int|float|double|decimal|numeric/i.test(dtype);

// ── Skeleton ──────────────────────────────────────────────────
function Skeleton({ rows = 1, height = 40 }: { rows?: number; height?: number }) {
  return (
    <div className="pp-dk-skeleton-wrap">
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="pp-dk-skeleton"
          style={{ height, borderRadius: 8 }}
        />
      ))}
    </div>
  );
}

// ── Step Card ─────────────────────────────────────────────────
type StepCardProps = {
  index: number;
  title: string;
  description: string;
  icon: React.ReactNode;
  enabled: boolean;
  onToggle: () => void;
  expanded: boolean;
  onExpand: () => void;
  status: 'idle' | 'configured' | 'done';
  children: React.ReactNode;
};

function StepCard({
  index, title, description, icon, enabled, onToggle,
  expanded, onExpand, status, children,
}: StepCardProps) {
  const accentClass =
    status === 'done' ? 'pp-dk-step--done' :
    status === 'configured' ? 'pp-dk-step--configured' :
    'pp-dk-step--idle';

  return (
    <div className={`pp-dk-step-card ${accentClass}`}>
      {/* Left accent bar */}
      <div className="pp-dk-step-accent" />

      {/* Header row */}
      <div className="pp-dk-step-card-inner">
        <div
          className="pp-dk-step-header"
          role="button"
          tabIndex={0}
          onClick={onExpand}
          onKeyDown={(e) => e.key === 'Enter' && onExpand()}
        >
          <div className="pp-dk-step-header-left">
            <span className="pp-dk-step-num">{String(index).padStart(2, '0')}</span>
            <span className="pp-dk-step-icon">{icon}</span>
            <div className="pp-dk-step-info">
              <div className="pp-dk-step-title">{title}</div>
              <div className="pp-dk-step-desc">{description}</div>
            </div>
          </div>

          <div className="pp-dk-step-header-right">
            {/* Status badge */}
            <span className={`pp-dk-step-badge pp-dk-step-badge--${status}`}>
              {status === 'done' && <CheckCircle size={10} />}
              {status}
            </span>

            {/* Custom toggle switch */}
            <div
              className={`pp-dk-toggle ${enabled ? 'pp-dk-toggle--on' : ''}`}
              role="switch"
              aria-checked={enabled}
              tabIndex={0}
              onClick={(e) => { e.stopPropagation(); onToggle(); }}
              onKeyDown={(e) => { e.stopPropagation(); if (e.key === 'Enter') onToggle(); }}
            >
              <div className="pp-dk-toggle-thumb" />
            </div>

            {/* Expand chevron */}
            <span className={`pp-dk-step-chevron ${expanded ? 'pp-dk-step-chevron--open' : ''}`}>
              <ChevronDown size={16} />
            </span>
          </div>
        </div>

        {/* Collapsible body */}
        <AnimatePresence>
          {expanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.22, ease: 'easeInOut' }}
              style={{ overflow: 'hidden' }}
            >
              <div className="pp-dk-step-content">{children}</div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────
export default function PreprocessingView({ filename, onProcessed }: { filename: string; onProcessed?: (filename: string) => void }) {

  // ── Phase 1 state ─────────────────────────────────────────
  const [health,        setHealth]        = useState<DatasetHealthResponse | null>(null);
  const [healthLoading, setHealthLoading] = useState(false);
  const [healthError,   setHealthError]   = useState('');
  const [columns,       setColumns]       = useState<PreprocessColumnMeta[]>([]);

  // ── Phase 2 state ─────────────────────────────────────────
  const [expandedStep, setExpandedStep] = useState<number | null>(null);

  const [dupConfig,      setDupConfig]      = useState<DupConfig>({ enabled: false, keep: 'first' });
  const [missingConfig,  setMissingConfig]  = useState<MissingConfig>({ enabled: false, strategies: {} });
  const [outlierConfig,  setOutlierConfig]  = useState<OutlierConfig>({ enabled: false, method: 'iqr', threshold: 3.0, treatment: 'cap' });
  const [typeConfig,     setTypeConfig]     = useState<TypeConfig>({ enabled: false, auto_detect: true, extract_datetime: true });
  const [featureConfig,  setFeatureConfig]  = useState<FeatureConfig>({ enabled: false, log_transform: [], sqrt_transform: [], encoding: {} });
  const [scalingConfig,  setScalingConfig]  = useState<ScalingConfig>({ enabled: false, method: 'standard' });
  const [imbalanceConfig,setImbalanceConfig]= useState<ImbalanceConfig>({ enabled: false, target_col: '', method: 'smote' });
  const [dimConfig,      setDimConfig]      = useState<DimConfig>({ enabled: false, method: 'remove_correlated', corr_threshold: 0.95, pca_components: 10 });
  const [splitConfig,    setSplitConfig]    = useState<SplitConfig>({ enabled: true,  test_size: 0.2, stratify_col: '', random_state: 42 });

  const [outlierResults,  setOutlierResults]  = useState<Record<string, { count: number; pct: number }> | null>(null);
  const [outlierLoading,  setOutlierLoading]  = useState(false);
  const [aiRecLoading,    setAiRecLoading]    = useState(false);

  // ── Phase 3 state ─────────────────────────────────────────
  const [pipelineRunning, setPipelineRunning] = useState(false);
  const [pipelineResult,  setPipelineResult]  = useState<PipelineRunResponse | null>(null);
  const [pipelineError,   setPipelineError]   = useState('');
  const [downloading,     setDownloading]     = useState('');

  // ── Load health + columns on mount ───────────────────────
  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setHealthLoading(true);
      setHealthError('');
      try {
        const [h, c] = await Promise.all([
          getDatasetHealth(filename),
          getPreprocessColumns(filename),
        ]);
        if (cancelled) return;
        setHealth(h);
        setColumns(c.columns);

        // Init missing strategies for columns that have nulls
        const strategies: Record<string, string> = {};
        c.columns.forEach((col) => {
          if (col.missing_pct > 0) strategies[col.name] = 'median';
        });
        setMissingConfig((prev) => ({ ...prev, strategies }));

        // Init encoding map for categorical columns
        const encoding: Record<string, string> = {};
        c.columns.forEach((col) => {
          if (!isNumericDtype(col.dtype)) encoding[col.name] = 'label';
        });
        setFeatureConfig((prev) => ({ ...prev, encoding }));
      } catch (err) {
        if (!cancelled)
          setHealthError(err instanceof Error ? err.message : 'Failed to load dataset health');
      } finally {
        if (!cancelled) setHealthLoading(false);
      }
    };
    load();
    return () => { cancelled = true; };
  }, [filename]);

  // ── Derived lists ─────────────────────────────────────────
  const numericCols     = columns.filter((c) => isNumericDtype(c.dtype));
  const categoricalCols = columns.filter((c) => !isNumericDtype(c.dtype));
  const missingCols     = columns.filter((c) => c.missing_pct > 0);

  const allStepConfigs = [
    dupConfig, missingConfig, outlierConfig, typeConfig,
    featureConfig, scalingConfig, imbalanceConfig, dimConfig, splitConfig,
  ];
  const enabledCount = allStepConfigs.filter((c) => c.enabled).length;

  // ── Handlers ─────────────────────────────────────────────
  const toggleExpand = (i: number) =>
    setExpandedStep((prev) => (prev === i ? null : i));

  const stepStatus = (enabled: boolean): 'idle' | 'configured' | 'done' => {
    if (pipelineResult && enabled) return 'done';
    if (enabled) return 'configured';
    return 'idle';
  };

  const toggleFeatureCol = (
    field: 'log_transform' | 'sqrt_transform',
    colName: string,
  ) => {
    setFeatureConfig((prev) => ({
      ...prev,
      [field]: prev[field].includes(colName)
        ? prev[field].filter((n) => n !== colName)
        : [...prev[field], colName],
    }));
  };

  const handleAiRec = async () => {
    setAiRecLoading(true);
    try {
      const data = await getImputationRecommendations(filename);
      setMissingConfig((prev) => ({
        ...prev,
        strategies: { ...prev.strategies, ...data.recommendations },
      }));
    } catch (e) {
      console.error('AI recommendation failed:', e);
    } finally {
      setAiRecLoading(false);
    }
  };

  const handleDetectOutliers = async () => {
    setOutlierLoading(true);
    try {
      const data = await detectOutliersApi(
        filename,
        outlierConfig.method,
        outlierConfig.threshold,
      );
      setOutlierResults(data.outliers);
    } catch (e) {
      console.error('Outlier detection failed:', e);
    } finally {
      setOutlierLoading(false);
    }
  };

  const handleRunPipeline = async () => {
    setPipelineRunning(true);
    setPipelineError('');
    try {
      const config: Record<string, unknown> = {
        duplicate_removal: dupConfig.enabled ? { keep: dupConfig.keep } : null,
        missing_values: missingConfig.enabled
          ? { strategies: missingConfig.strategies } : null,
        outlier_treatment: outlierConfig.enabled
          ? { method: outlierConfig.method, threshold: outlierConfig.threshold, treatment: outlierConfig.treatment }
          : null,
        type_correction: typeConfig.enabled
          ? { auto_detect: typeConfig.auto_detect, extract_datetime: typeConfig.extract_datetime }
          : null,
        feature_engineering: featureConfig.enabled
          ? { log_transform: featureConfig.log_transform, sqrt_transform: featureConfig.sqrt_transform, encoding: featureConfig.encoding }
          : null,
        scaling: scalingConfig.enabled ? { method: scalingConfig.method } : null,
        class_imbalance: imbalanceConfig.enabled
          ? { target_col: imbalanceConfig.target_col, method: imbalanceConfig.method }
          : null,
        dimensionality_reduction: dimConfig.enabled
          ? { method: dimConfig.method, corr_threshold: dimConfig.corr_threshold, pca_components: dimConfig.pca_components }
          : null,
        train_test_split: splitConfig.enabled
          ? { test_size: splitConfig.test_size, stratify_col: splitConfig.stratify_col || null, random_state: splitConfig.random_state }
          : null,
      };
      const result = await runPipeline(filename, config);
      setPipelineResult(result);
      // Notify parent so ML tab automatically uses the processed file
      if (result.processed_filename) {
        onProcessed?.(result.processed_filename);
      }
    } catch (err) {
      setPipelineError(err instanceof Error ? err.message : 'Pipeline run failed');
    } finally {
      setPipelineRunning(false);
    }
  };

  const handleDownload = async (format: string, ext: string) => {
    if (!pipelineResult) return;
    setDownloading(format);
    try {
      const url     = getDownloadUrl(pipelineResult.session_key, format);
      const headers = getDownloadHeaders();
      const resp    = await fetch(url, { headers });
      if (!resp.ok) throw new Error('Download request failed');
      const blob = await resp.blob();
      const a    = document.createElement('a');
      a.href     = URL.createObjectURL(blob);
      a.download = `processed_${filename.replace(/\.[^.]+$/, '')}.${ext}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(a.href);
    } catch (e) {
      console.error('Download failed:', e);
    } finally {
      setDownloading('');
    }
  };

  // ── Missing col entries from health ───────────────────────
  const missingHeatEntries = health
    ? Object.entries(health.missing_per_col)
        .filter(([, v]) => v.pct > 0)
        .sort((a, b) => b[1].pct - a[1].pct)
    : [];

  // ── Helper: heatmap bar color ─────────────────────────────
  const heatBarColor = (pct: number) => {
    if (pct > 80) return 'var(--accent-danger)';
    if (pct > 40) return 'var(--accent-warning)';
    if (pct > 20) return '#F97316';
    if (pct > 5)  return 'var(--accent-info)';
    return 'var(--accent-success)';
  };

  const heatBarGlow = (pct: number) => {
    if (pct > 80) return '0 0 8px rgba(244,63,94,0.5)';
    return 'none';
  };

  // ── Helper: dtype badge color ─────────────────────────────
  const dtypeBadgeClass = (dtype: string) => {
    if (/int/i.test(dtype)) return 'pp-dk-dtype-badge--int';
    if (/float|double|decimal/i.test(dtype)) return 'pp-dk-dtype-badge--float';
    return 'pp-dk-dtype-badge--str';
  };

  // ── Render ────────────────────────────────────────────────
  return (
    <section className="pp-dk-panel">

      {/* ═══ Header ═══════════════════════════════════════════ */}
      <div className="pp-dk-header">
        <div className="pp-dk-header-top">
          <div className="pp-dk-header-title-row">
            <div className="pp-dk-icon-circle">
              <Settings size={18} />
            </div>
            <div>
              <h2 className="pp-dk-title">Preprocessing Pipeline</h2>
              <p className="pp-dk-subtitle">Automated data cleaning &amp; transform</p>
            </div>
          </div>
          <div className="pp-dk-filename">
            <Database size={13} />
            <span>{filename}</span>
          </div>
        </div>
        {health && (
          <div className="pp-dk-meta-chips">
            <span className="pp-dk-meta-chip">
              <span className="pp-dk-meta-chip-label">Rows</span>
              <span className="pp-dk-meta-chip-value">{health.rows.toLocaleString()}</span>
            </span>
            <span className="pp-dk-meta-chip">
              <span className="pp-dk-meta-chip-label">Cols</span>
              <span className="pp-dk-meta-chip-value">{health.columns}</span>
            </span>
            <span className="pp-dk-meta-chip">
              <span className="pp-dk-meta-chip-label">Memory</span>
              <span className="pp-dk-meta-chip-value">{health.memory_mb.toFixed(2)} MB</span>
            </span>
            <span className="pp-dk-meta-chip pp-dk-meta-chip--accent">
              <span className="pp-dk-meta-chip-label">Active</span>
              <span className="pp-dk-meta-chip-value">{enabledCount} step{enabledCount !== 1 ? 's' : ''}</span>
            </span>
          </div>
        )}
      </div>

      {/* ═══ Error banner ═════════════════════════════════════ */}
      {healthError && (
        <motion.div
          className="pp-dk-error-banner"
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <AlertCircle size={15} />
          <span>{healthError}</span>
        </motion.div>
      )}

      {/* ═══ Health loading skeleton ══════════════════════════ */}
      {healthLoading && (
        <motion.div animate={{ opacity: [0, 1] }} transition={{ duration: 0.3 }}>
          <Skeleton rows={1} height={24} />
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5,1fr)', gap: 12, marginTop: 16 }}>
            {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} height={100} />)}
          </div>
        </motion.div>
      )}

      {/* ═══ PHASE 1 -- Health Dashboard ═════════════════════ */}
      <AnimatePresence>
        {health && !healthLoading && (
          <motion.div key="health-dashboard" animate={{ opacity: [0, 1] }} transition={{ duration: 0.45 }}>

            <div className="pp-dk-section-head">
              <span className="pp-dk-section-label">Dataset Health</span>
              <span className="pp-dk-section-badge">on-load snapshot</span>
            </div>

            {/* ── 5-column stat card grid ── */}
            <div className="pp-dk-health-grid">

              {/* Shape */}
              <div className="pp-dk-stat-card pp-dk-stat-card--info">
                <div className="pp-dk-stat-icon pp-dk-stat-icon--info">
                  <Database size={18} />
                </div>
                <div className="pp-dk-stat-value">
                  {health.rows.toLocaleString()}
                  <span className="pp-dk-stat-x">{' x '}</span>
                  {health.columns}
                </div>
                <div className="pp-dk-stat-sub">rows x columns</div>
                <div className="pp-dk-stat-label">SHAPE</div>
              </div>

              {/* Memory */}
              <div className="pp-dk-stat-card pp-dk-stat-card--primary">
                <div className="pp-dk-stat-icon pp-dk-stat-icon--primary">
                  <Layers size={18} />
                </div>
                <div className="pp-dk-stat-value">{health.memory_mb.toFixed(2)}</div>
                <div className="pp-dk-stat-sub">MB in memory</div>
                <div className="pp-dk-stat-label">MEMORY</div>
              </div>

              {/* Duplicates */}
              <div className={`pp-dk-stat-card ${health.duplicate_count > 0 ? 'pp-dk-stat-card--warning' : 'pp-dk-stat-card--success'}`}>
                <div className={`pp-dk-stat-icon ${health.duplicate_count > 0 ? 'pp-dk-stat-icon--warning' : 'pp-dk-stat-icon--success'}`}>
                  <Trash2 size={18} />
                </div>
                <div className="pp-dk-stat-value">{health.duplicate_count.toLocaleString()}</div>
                <div className="pp-dk-stat-sub">duplicate rows</div>
                <div className="pp-dk-stat-label">DUPLICATES</div>
              </div>

              {/* Dtypes */}
              <div className="pp-dk-stat-card pp-dk-stat-card--primary">
                <div className="pp-dk-stat-icon pp-dk-stat-icon--primary">
                  <Settings size={18} />
                </div>
                <div className="pp-dk-stat-dtypes">
                  {health.dtype_breakdown.numeric > 0 && (
                    <span className="pp-dk-dtype-chip pp-dk-dtype-chip--num">{health.dtype_breakdown.numeric} numeric</span>
                  )}
                  {health.dtype_breakdown.categorical > 0 && (
                    <span className="pp-dk-dtype-chip pp-dk-dtype-chip--cat">{health.dtype_breakdown.categorical} cat</span>
                  )}
                  {health.dtype_breakdown.datetime > 0 && (
                    <span className="pp-dk-dtype-chip pp-dk-dtype-chip--dt">{health.dtype_breakdown.datetime} date</span>
                  )}
                  {health.dtype_breakdown.boolean > 0 && (
                    <span className="pp-dk-dtype-chip pp-dk-dtype-chip--bool">{health.dtype_breakdown.boolean} bool</span>
                  )}
                </div>
                <div className="pp-dk-stat-label">DTYPES</div>
              </div>

              {/* Missing Cols */}
              <div className={`pp-dk-stat-card ${missingHeatEntries.length > 0 ? 'pp-dk-stat-card--danger' : 'pp-dk-stat-card--success'}`}>
                <div className={`pp-dk-stat-icon ${missingHeatEntries.length > 0 ? 'pp-dk-stat-icon--danger' : 'pp-dk-stat-icon--success'}`}>
                  <AlertTriangle size={18} />
                </div>
                <div className="pp-dk-stat-value">{missingHeatEntries.length}</div>
                <div className="pp-dk-stat-sub">columns with nulls</div>
                <div className="pp-dk-stat-label">MISSING COLS</div>
              </div>

            </div>

            {/* ── Missing Value Heatmap ── */}
            {missingHeatEntries.length > 0 && (
              <div className="pp-dk-missing-heatmap">
                <div className="pp-dk-section-head" style={{ marginTop: 24, marginBottom: 14 }}>
                  <span className="pp-dk-section-label">Missing Value Heatmap</span>
                  <span className="pp-dk-section-badge">{missingHeatEntries.length} columns affected</span>
                </div>
                <div className="pp-dk-heatmap-list">
                  {missingHeatEntries.map(([col, info]) => (
                    <div
                      key={col}
                      className="pp-dk-heatmap-row"
                      title={`${col}: ${info.pct.toFixed(1)}% missing (${info.count} values)`}
                    >
                      <span className="pp-dk-heatmap-col-name">{col}</span>
                      <div className="pp-dk-heatmap-bar-track">
                        <motion.div
                          className="pp-dk-heatmap-bar-fill"
                          initial={{ width: 0 }}
                          animate={{ width: `${Math.max(2, info.pct)}%` }}
                          transition={{ duration: 0.6, ease: 'easeOut' }}
                          style={{
                            background: heatBarColor(info.pct),
                            boxShadow: heatBarGlow(info.pct),
                          }}
                        />
                      </div>
                      <span
                        className="pp-dk-heatmap-pct"
                        style={{ color: heatBarColor(info.pct) }}
                      >
                        {info.pct.toFixed(0)}%
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* ── Constant / Near-constant Warnings ── */}
            {health.constant_columns.length > 0 && (
              <div className="pp-dk-warn-banner pp-dk-warn-banner--danger">
                <AlertTriangle size={14} />
                <div className="pp-dk-warn-content">
                  <strong>Constant columns</strong>
                  <div className="pp-dk-warn-chips">
                    {health.constant_columns.map((col) => (
                      <span key={col} className="pp-dk-warn-chip">{col}</span>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {health.near_constant_columns.length > 0 && (
              <div className="pp-dk-warn-banner pp-dk-warn-banner--warning">
                <AlertTriangle size={14} />
                <div className="pp-dk-warn-content">
                  <strong>Near-constant columns</strong>
                  <div className="pp-dk-warn-chips">
                    {health.near_constant_columns.map((col) => (
                      <span key={col} className="pp-dk-warn-chip">{col}</span>
                    ))}
                  </div>
                </div>
              </div>
            )}

          </motion.div>
        )}
      </AnimatePresence>

      {/* ═══ PHASE 2 -- Pipeline Steps ═══════════════════════ */}
      <AnimatePresence>
        {health && !healthLoading && (
          <motion.div key="pipeline-steps" animate={{ opacity: [0, 1] }} transition={{ duration: 0.4, delay: 0.1 }}>

            <div className="pp-dk-section-head" style={{ marginTop: 32 }}>
              <span className="pp-dk-section-label">Pipeline Steps</span>
              <span className="pp-dk-section-badge">9 configurable steps</span>
            </div>

            {/* ── Step 1: Duplicate Removal ── */}
            <StepCard
              index={1}
              title="Duplicate Removal"
              description="Remove repeated rows from the dataset"
              icon={<Trash2 size={15} />}
              enabled={dupConfig.enabled}
              onToggle={() => setDupConfig((p) => ({ ...p, enabled: !p.enabled }))}
              expanded={expandedStep === 1}
              onExpand={() => toggleExpand(1)}
              status={stepStatus(dupConfig.enabled)}
            >
              <div className="pp-dk-field-row">
                <label className="pp-dk-field-label">Keep strategy</label>
                <select
                  className="pp-dk-select"
                  value={dupConfig.keep}
                  onChange={(e) =>
                    setDupConfig((p) => ({ ...p, keep: e.target.value as DupConfig['keep'] }))
                  }
                >
                  <option value="first">first -- keep first occurrence</option>
                  <option value="last">last -- keep last occurrence</option>
                  <option value="none">none -- drop all duplicate rows</option>
                </select>
              </div>
              {health.duplicate_count > 0 ? (
                <div className="pp-dk-info-note pp-dk-info-note--warn">
                  <AlertTriangle size={13} />
                  {health.duplicate_count.toLocaleString()} duplicate rows detected
                </div>
              ) : (
                <div className="pp-dk-info-note pp-dk-info-note--ok">
                  <CheckCircle size={13} /> No duplicate rows found
                </div>
              )}
            </StepCard>

            {/* ── Step 2: Missing Values ── */}
            <StepCard
              index={2}
              title="Missing Values"
              description="Impute or drop missing values per column"
              icon={<Droplet size={15} />}
              enabled={missingConfig.enabled}
              onToggle={() => setMissingConfig((p) => ({ ...p, enabled: !p.enabled }))}
              expanded={expandedStep === 2}
              onExpand={() => toggleExpand(2)}
              status={stepStatus(missingConfig.enabled)}
            >
              <div className="pp-dk-ai-row">
                <button
                  className="pp-dk-ai-btn"
                  onClick={handleAiRec}
                  disabled={aiRecLoading}
                >
                  {aiRecLoading
                    ? <Loader2 size={13} className="viz-spin" />
                    : <Sparkles size={13} />}
                  {aiRecLoading ? 'Analyzing...' : 'AI Recommendations'}
                </button>
                <span className="pp-dk-ai-hint">Auto-fill strategies using model analysis</span>
              </div>

              {missingCols.length === 0 ? (
                <div className="pp-dk-info-note pp-dk-info-note--ok">
                  <CheckCircle size={13} /> No missing values -- nothing to impute
                </div>
              ) : (
                <div className="pp-dk-col-strategy-list">
                  {missingCols.map((col) => (
                    <div key={col.name} className="pp-dk-col-strategy-row">
                      <div className="pp-dk-col-strategy-name">
                        <span className="pp-dk-col-name-text">{col.name}</span>
                        <span
                          className={`pp-dk-miss-badge pp-dk-miss-badge--${
                            health.missing_per_col[col.name]?.color ?? 'yellow'
                          }`}
                        >
                          {col.missing_pct.toFixed(1)}%
                        </span>
                      </div>
                      <select
                        className="pp-dk-select pp-dk-select--sm"
                        value={missingConfig.strategies[col.name] ?? 'median'}
                        onChange={(e) =>
                          setMissingConfig((p) => ({
                            ...p,
                            strategies: { ...p.strategies, [col.name]: e.target.value },
                          }))
                        }
                      >
                        {MISSING_STRATEGIES.map((s) => (
                          <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
                        ))}
                      </select>
                    </div>
                  ))}
                </div>
              )}
            </StepCard>

            {/* ── Step 3: Outlier Treatment ── */}
            <StepCard
              index={3}
              title="Outlier Treatment"
              description="Detect and treat outliers in numeric columns"
              icon={<AlertTriangle size={15} />}
              enabled={outlierConfig.enabled}
              onToggle={() => setOutlierConfig((p) => ({ ...p, enabled: !p.enabled }))}
              expanded={expandedStep === 3}
              onExpand={() => toggleExpand(3)}
              status={stepStatus(outlierConfig.enabled)}
            >
              <div className="pp-dk-fields-grid">
                <div className="pp-dk-field-row">
                  <label className="pp-dk-field-label">Detection method</label>
                  <select
                    className="pp-dk-select"
                    value={outlierConfig.method}
                    onChange={(e) =>
                      setOutlierConfig((p) => ({
                        ...p,
                        method: e.target.value as 'iqr' | 'zscore',
                      }))
                    }
                  >
                    <option value="iqr">IQR (Interquartile Range)</option>
                    <option value="zscore">Z-Score</option>
                  </select>
                </div>

                <div className="pp-dk-field-row">
                  <label className="pp-dk-field-label">Treatment action</label>
                  <select
                    className="pp-dk-select"
                    value={outlierConfig.treatment}
                    onChange={(e) =>
                      setOutlierConfig((p) => ({
                        ...p,
                        treatment: e.target.value as OutlierConfig['treatment'],
                      }))
                    }
                  >
                    <option value="cap">Cap (Winsorize)</option>
                    <option value="remove">Remove rows</option>
                    <option value="median">Replace with median</option>
                    <option value="flag">Flag only (add column)</option>
                  </select>
                </div>

                <div className="pp-dk-field-row pp-dk-field-row--full">
                  <label className="pp-dk-field-label">
                    Threshold: <strong>{outlierConfig.threshold.toFixed(1)}</strong>
                  </label>
                  <input
                    type="range"
                    className="pp-dk-slider"
                    min={1}
                    max={6}
                    step={0.1}
                    value={outlierConfig.threshold}
                    onChange={(e) =>
                      setOutlierConfig((p) => ({
                        ...p,
                        threshold: parseFloat(e.target.value),
                      }))
                    }
                  />
                </div>
              </div>

              <div className="pp-dk-detect-row">
                <button
                  className="pp-dk-detect-btn"
                  onClick={handleDetectOutliers}
                  disabled={outlierLoading}
                >
                  {outlierLoading
                    ? <Loader2 size={13} className="viz-spin" />
                    : <Activity size={13} />}
                  {outlierLoading ? 'Detecting...' : 'Detect Outliers Now'}
                </button>
              </div>

              {outlierResults && (
                <div className="pp-dk-outlier-results">
                  {Object.keys(outlierResults).length === 0 ? (
                    <div className="pp-dk-info-note pp-dk-info-note--ok">
                      <CheckCircle size={13} /> No outliers detected with current settings
                    </div>
                  ) : (
                    Object.entries(outlierResults).map(([col, data]) => (
                      <div key={col} className="pp-dk-outlier-row">
                        <span className="pp-dk-outlier-col">{col}</span>
                        <div className="pp-dk-outlier-track">
                          <div
                            className="pp-dk-outlier-fill"
                            style={{ width: `${Math.min(100, data.pct * 4)}%` }}
                          />
                        </div>
                        <span className="pp-dk-outlier-count">
                          {data.count} ({data.pct.toFixed(1)}%)
                        </span>
                      </div>
                    ))
                  )}
                </div>
              )}
            </StepCard>

            {/* ── Step 4: Data Type Correction ── */}
            <StepCard
              index={4}
              title="Data Type Correction"
              description="Auto-detect and cast columns to correct types"
              icon={<Settings size={15} />}
              enabled={typeConfig.enabled}
              onToggle={() => setTypeConfig((p) => ({ ...p, enabled: !p.enabled }))}
              expanded={expandedStep === 4}
              onExpand={() => toggleExpand(4)}
              status={stepStatus(typeConfig.enabled)}
            >
              <div className="pp-dk-check-row">
                <label className="pp-dk-checkbox-label">
                  <input
                    type="checkbox"
                    checked={typeConfig.auto_detect}
                    onChange={(e) =>
                      setTypeConfig((p) => ({ ...p, auto_detect: e.target.checked }))
                    }
                  />
                  Auto-detect and cast numeric columns stored as strings
                </label>
              </div>
              <div className="pp-dk-check-row">
                <label className="pp-dk-checkbox-label">
                  <input
                    type="checkbox"
                    checked={typeConfig.extract_datetime}
                    onChange={(e) =>
                      setTypeConfig((p) => ({ ...p, extract_datetime: e.target.checked }))
                    }
                  />
                  Extract datetime features (year, month, day, weekday, hour)
                </label>
              </div>
            </StepCard>

            {/* ── Step 5: Feature Engineering ── */}
            <StepCard
              index={5}
              title="Feature Engineering"
              description="Transform numeric features and encode categoricals"
              icon={<Zap size={15} />}
              enabled={featureConfig.enabled}
              onToggle={() => setFeatureConfig((p) => ({ ...p, enabled: !p.enabled }))}
              expanded={expandedStep === 5}
              onExpand={() => toggleExpand(5)}
              status={stepStatus(featureConfig.enabled)}
            >
              {numericCols.length > 0 && (
                <>
                  <div className="pp-dk-field-label pp-dk-field-label--section">
                    Log Transform (select columns)
                  </div>
                  <div className="pp-dk-chip-grid">
                    {numericCols.map((col) => {
                      const selected = featureConfig.log_transform.includes(col.name);
                      return (
                        <button
                          key={col.name}
                          type="button"
                          className={`pp-dk-chip-select ${selected ? 'pp-dk-chip-select--active' : ''}`}
                          onClick={() => toggleFeatureCol('log_transform', col.name)}
                        >
                          {col.name}
                        </button>
                      );
                    })}
                  </div>
                  <div className="pp-dk-field-label pp-dk-field-label--section" style={{ marginTop: 14 }}>
                    Sqrt Transform (select columns)
                  </div>
                  <div className="pp-dk-chip-grid">
                    {numericCols.map((col) => {
                      const selected = featureConfig.sqrt_transform.includes(col.name);
                      return (
                        <button
                          key={col.name}
                          type="button"
                          className={`pp-dk-chip-select ${selected ? 'pp-dk-chip-select--active' : ''}`}
                          onClick={() => toggleFeatureCol('sqrt_transform', col.name)}
                        >
                          {col.name}
                        </button>
                      );
                    })}
                  </div>
                </>
              )}
              {categoricalCols.length > 0 && (
                <>
                  <div className="pp-dk-field-label pp-dk-field-label--section" style={{ marginTop: 16 }}>
                    Categorical Encoding
                  </div>
                  <div className="pp-dk-encoding-table">
                    <div className="pp-dk-encoding-header">
                      <span>Column</span>
                      <span>Unique</span>
                      <span>Encoding</span>
                    </div>
                    {categoricalCols.map((col, idx) => (
                      <div key={col.name} className={`pp-dk-encoding-row ${idx % 2 === 0 ? '' : 'pp-dk-encoding-row--alt'}`}>
                        <span className="pp-dk-encoding-col">{col.name}</span>
                        <span className={`pp-dk-encoding-uniq ${col.nunique > 20 ? 'pp-dk-encoding-uniq--high' : col.nunique > 5 ? 'pp-dk-encoding-uniq--med' : 'pp-dk-encoding-uniq--low'}`}>
                          {col.nunique}
                        </span>
                        <select
                          className="pp-dk-select pp-dk-select--sm"
                          value={featureConfig.encoding[col.name] ?? 'label'}
                          onChange={(e) =>
                            setFeatureConfig((p) => ({
                              ...p,
                              encoding: { ...p.encoding, [col.name]: e.target.value },
                            }))
                          }
                        >
                          <option value="label">Label Encoding</option>
                          <option value="onehot">One-Hot Encoding</option>
                          <option value="frequency">Frequency Encoding</option>
                        </select>
                      </div>
                    ))}
                  </div>
                </>
              )}
              {numericCols.length === 0 && categoricalCols.length === 0 && (
                <div className="pp-dk-info-note">No columns available for feature engineering.</div>
              )}
            </StepCard>

            {/* ── Step 6: Scaling ── */}
            <StepCard
              index={6}
              title="Feature Scaling"
              description="Normalize or standardize numeric feature values"
              icon={<Layers size={15} />}
              enabled={scalingConfig.enabled}
              onToggle={() => setScalingConfig((p) => ({ ...p, enabled: !p.enabled }))}
              expanded={expandedStep === 6}
              onExpand={() => toggleExpand(6)}
              status={stepStatus(scalingConfig.enabled)}
            >
              <div className="pp-dk-field-row">
                <label className="pp-dk-field-label">Scaling method</label>
                <select
                  className="pp-dk-select"
                  value={scalingConfig.method}
                  onChange={(e) =>
                    setScalingConfig((p) => ({ ...p, method: e.target.value }))
                  }
                >
                  {SCALE_METHODS.map((m) => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
              </div>
              <div className="pp-dk-method-desc">
                {SCALE_DESCS[scalingConfig.method] ?? ''}
              </div>
            </StepCard>

            {/* ── Step 7: Class Imbalance ── */}
            <StepCard
              index={7}
              title="Class Imbalance"
              description="Resample to address imbalanced class distributions"
              icon={<BarChart2 size={15} />}
              enabled={imbalanceConfig.enabled}
              onToggle={() => setImbalanceConfig((p) => ({ ...p, enabled: !p.enabled }))}
              expanded={expandedStep === 7}
              onExpand={() => toggleExpand(7)}
              status={stepStatus(imbalanceConfig.enabled)}
            >
              <div className="pp-dk-fields-grid">
                <div className="pp-dk-field-row">
                  <label className="pp-dk-field-label">Target column</label>
                  <select
                    className="pp-dk-select"
                    value={imbalanceConfig.target_col}
                    onChange={(e) =>
                      setImbalanceConfig((p) => ({ ...p, target_col: e.target.value }))
                    }
                  >
                    <option value="">-- select target column --</option>
                    {columns.map((col) => (
                      <option key={col.name} value={col.name}>{col.name}</option>
                    ))}
                  </select>
                </div>
                <div className="pp-dk-field-row">
                  <label className="pp-dk-field-label">Resampling method</label>
                  <select
                    className="pp-dk-select"
                    value={imbalanceConfig.method}
                    onChange={(e) =>
                      setImbalanceConfig((p) => ({ ...p, method: e.target.value }))
                    }
                  >
                    {IMBALANCE_METHODS.map((m) => (
                      <option key={m} value={m}>{m.toUpperCase()}</option>
                    ))}
                  </select>
                </div>
              </div>
            </StepCard>

            {/* ── Step 8: Dimensionality Reduction ── */}
            <StepCard
              index={8}
              title="Dimensionality Reduction"
              description="Remove redundant features or apply PCA"
              icon={<Minimize2 size={15} />}
              enabled={dimConfig.enabled}
              onToggle={() => setDimConfig((p) => ({ ...p, enabled: !p.enabled }))}
              expanded={expandedStep === 8}
              onExpand={() => toggleExpand(8)}
              status={stepStatus(dimConfig.enabled)}
            >
              <div className="pp-dk-field-row">
                <label className="pp-dk-field-label">Reduction method</label>
                <select
                  className="pp-dk-select"
                  value={dimConfig.method}
                  onChange={(e) => setDimConfig((p) => ({ ...p, method: e.target.value }))}
                >
                  {DIM_METHODS.map((m) => (
                    <option key={m} value={m}>{m.replace(/_/g, ' ')}</option>
                  ))}
                </select>
              </div>
              {dimConfig.method === 'remove_correlated' && (
                <div className="pp-dk-field-row" style={{ marginTop: 12 }}>
                  <label className="pp-dk-field-label">
                    Correlation threshold: <strong>{dimConfig.corr_threshold.toFixed(2)}</strong>
                  </label>
                  <input
                    type="range"
                    className="pp-dk-slider"
                    min={0.7}
                    max={1.0}
                    step={0.01}
                    value={dimConfig.corr_threshold}
                    onChange={(e) =>
                      setDimConfig((p) => ({
                        ...p,
                        corr_threshold: parseFloat(e.target.value),
                      }))
                    }
                  />
                </div>
              )}
              {dimConfig.method === 'pca' && (
                <div className="pp-dk-field-row" style={{ marginTop: 12 }}>
                  <label className="pp-dk-field-label">
                    PCA components: <strong>{dimConfig.pca_components}</strong>
                  </label>
                  <input
                    type="range"
                    className="pp-dk-slider"
                    min={2}
                    max={Math.min(numericCols.length || 50, 50)}
                    step={1}
                    value={dimConfig.pca_components}
                    onChange={(e) =>
                      setDimConfig((p) => ({
                        ...p,
                        pca_components: parseInt(e.target.value),
                      }))
                    }
                  />
                </div>
              )}
            </StepCard>

            {/* ── Step 9: Train/Test Split ── */}
            <StepCard
              index={9}
              title="Train / Test Split"
              description="Split processed data into training and test sets"
              icon={<GitBranch size={15} />}
              enabled={splitConfig.enabled}
              onToggle={() => setSplitConfig((p) => ({ ...p, enabled: !p.enabled }))}
              expanded={expandedStep === 9}
              onExpand={() => toggleExpand(9)}
              status={stepStatus(splitConfig.enabled)}
            >
              <div className="pp-dk-fields-grid">
                <div className="pp-dk-field-row pp-dk-field-row--full">
                  <label className="pp-dk-field-label">
                    Test size: <strong>{Math.round(splitConfig.test_size * 100)}%</strong>
                    <span className="pp-dk-field-hint"> (train: {Math.round((1 - splitConfig.test_size) * 100)}%)</span>
                  </label>
                  <input
                    type="range"
                    className="pp-dk-slider"
                    min={0.10}
                    max={0.40}
                    step={0.01}
                    value={splitConfig.test_size}
                    onChange={(e) =>
                      setSplitConfig((p) => ({
                        ...p,
                        test_size: parseFloat(e.target.value),
                      }))
                    }
                  />
                </div>
                <div className="pp-dk-field-row">
                  <label className="pp-dk-field-label">Stratify column</label>
                  <select
                    className="pp-dk-select"
                    value={splitConfig.stratify_col}
                    onChange={(e) =>
                      setSplitConfig((p) => ({ ...p, stratify_col: e.target.value }))
                    }
                  >
                    <option value="">-- none (random split) --</option>
                    {columns.map((col) => (
                      <option key={col.name} value={col.name}>{col.name}</option>
                    ))}
                  </select>
                </div>
                <div className="pp-dk-field-row">
                  <label className="pp-dk-field-label">Random state</label>
                  <input
                    type="number"
                    className="pp-dk-input"
                    min={0}
                    max={9999}
                    value={splitConfig.random_state}
                    onChange={(e) =>
                      setSplitConfig((p) => ({
                        ...p,
                        random_state: parseInt(e.target.value) || 42,
                      }))
                    }
                  />
                </div>
              </div>
            </StepCard>

            {/* ── Run Pipeline Section ── */}
            <div className="pp-dk-run-section">
              {pipelineError && (
                <motion.div
                  className="pp-dk-error-banner"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  style={{ marginBottom: 16 }}
                >
                  <AlertCircle size={15} /> {pipelineError}
                </motion.div>
              )}
              <button
                className="pp-dk-run-btn"
                onClick={handleRunPipeline}
                disabled={pipelineRunning || enabledCount === 0}
              >
                {pipelineRunning
                  ? <><Loader2 size={16} className="viz-spin" /> Running Pipeline...</>
                  : <><Play size={16} /> Run Full Pipeline</>}
              </button>
              <span className="pp-dk-run-sub">{enabledCount} step{enabledCount !== 1 ? 's' : ''} configured</span>
              {enabledCount === 0 && (
                <div className="pp-dk-run-hint">Enable at least one step above to run the pipeline.</div>
              )}
            </div>

          </motion.div>
        )}
      </AnimatePresence>

      {/* ═══ Pipeline running skeleton ════════════════════════ */}
      {pipelineRunning && (
        <motion.div animate={{ opacity: [0, 1] }} transition={{ duration: 0.3 }}>
          <div className="pp-dk-section-head"><span className="pp-dk-section-label">Processing dataset...</span></div>
          <Skeleton rows={4} height={44} />
        </motion.div>
      )}

      {/* ═══ PHASE 3 -- Results ══════════════════════════════ */}
      <AnimatePresence>
        {pipelineResult && !pipelineRunning && (
          <motion.div
            key="pipeline-results"
            animate={{ opacity: [0, 1] }}
            transition={{ duration: 0.5 }}
          >
            {/* Success banner */}
            <div className="pp-dk-success-banner">
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ type: 'spring', stiffness: 300, damping: 20 }}
              >
                <CheckCircle size={20} />
              </motion.div>
              <span>Pipeline completed successfully</span>
            </div>

            <div className="pp-dk-section-head" style={{ marginTop: 24 }}>
              <span className="pp-dk-section-label">Pipeline Results</span>
              <span className="pp-dk-section-badge pp-dk-section-badge--success">
                <CheckCircle size={10} /> complete
              </span>
            </div>

            {/* Before / After comparison */}
            <div className="pp-dk-compare-grid">
              <div className="pp-dk-compare-panel pp-dk-compare-panel--before">
                <div className="pp-dk-compare-panel-header">Before</div>
              </div>
              <div className="pp-dk-compare-panel pp-dk-compare-panel--after">
                <div className="pp-dk-compare-panel-header">After</div>
              </div>
            </div>
            <div className="pp-dk-compare-wrap">
              <table className="pp-dk-compare-table">
                <thead>
                  <tr>
                    <th>Metric</th>
                    <th>Before</th>
                    <th>After</th>
                    <th>Change</th>
                  </tr>
                </thead>
                <tbody>
                  {([
                    { label: 'Rows',           before: pipelineResult.before_stats.rows,          after: pipelineResult.after_stats.rows,          fmt: (v: number) => v.toLocaleString() },
                    { label: 'Columns',        before: pipelineResult.before_stats.columns,       after: pipelineResult.after_stats.columns,       fmt: (v: number) => String(v) },
                    { label: 'Memory (MB)',    before: pipelineResult.before_stats.memory_mb,     after: pipelineResult.after_stats.memory_mb,     fmt: (v: number) => v.toFixed(2) },
                    { label: 'Missing Values', before: pipelineResult.before_stats.total_missing, after: pipelineResult.after_stats.total_missing, fmt: (v: number) => v.toLocaleString() },
                  ] as { label: string; before: number; after: number; fmt: (v: number) => string }[]).map((row) => {
                    const delta = row.after - row.before;
                    const pct   = row.before !== 0 ? (delta / row.before) * 100 : 0;
                    const dir   = delta < 0 ? 'neg' : delta > 0 ? 'pos' : 'neu';
                    return (
                      <tr key={row.label}>
                        <td className="pp-dk-compare-label">{row.label}</td>
                        <td className="pp-dk-compare-before">{row.fmt(row.before)}</td>
                        <td className="pp-dk-compare-after">{row.fmt(row.after)}</td>
                        <td className={`pp-dk-compare-delta pp-dk-delta--${dir}`}>
                          {delta === 0
                            ? '--'
                            : `${delta > 0 ? '+' : ''}${pct.toFixed(1)}%`}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Preview table */}
            {pipelineResult.preview.length > 0 && (
              <>
                <div className="pp-dk-section-head" style={{ marginTop: 28 }}>
                  <span className="pp-dk-section-label">Data Preview</span>
                  <span className="pp-dk-section-badge">
                    first {Math.min(20, pipelineResult.preview.length)} rows
                  </span>
                </div>
                <div className="pp-dk-preview-scroll">
                  <table className="pp-dk-preview-table">
                    <thead>
                      <tr>
                        {pipelineResult.columns.map((col) => (
                          <th key={col.name}>
                            <div className="pp-dk-preview-col-name">{col.name}</div>
                            <div className={`pp-dk-dtype-badge ${dtypeBadgeClass(col.dtype)}`}>{col.dtype}</div>
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {pipelineResult.preview.slice(0, 20).map((row, i) => (
                        <tr key={i}>
                          {pipelineResult.columns.map((col) => (
                            <td key={col.name}>
                              {row[col.name] === null || row[col.name] === undefined
                                ? <span className="pp-dk-null-cell">null</span>
                                : String(row[col.name])}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}

            {/* Downloads */}
            <div className="pp-dk-section-head" style={{ marginTop: 28 }}>
              <span className="pp-dk-section-label">Download Processed Dataset</span>
            </div>
            <div className="pp-dk-download-container">
              <div className="pp-dk-download-grid">
                {DOWNLOAD_FORMATS.map(({ format, ext, label }) => (
                  <button
                    key={format}
                    className="pp-dk-download-btn"
                    onClick={() => handleDownload(format, ext)}
                    disabled={!!downloading}
                  >
                    {downloading === format
                      ? <Loader2 size={15} className="viz-spin" />
                      : <Download size={15} />}
                    {downloading === format ? 'Downloading...' : `Download ${label}`}
                  </button>
                ))}
              </div>
            </div>

          </motion.div>
        )}
      </AnimatePresence>

    </section>
  );
}
