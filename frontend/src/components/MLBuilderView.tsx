import React, { useEffect, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Activity,
  AlertCircle,
  Award,
  BarChart2,
  Brain,
  Check,
  CheckCircle,
  ChevronDown,
  Copy,
  Database,
  Download,
  Loader2,
  RefreshCw,
  Star,
  Target,
  TrendingUp,
  X,
  Zap,
} from 'lucide-react';
import {
  getMLColumns,
  detectMLTask,
  getMLRecommendation,
  getModelCards,
  trainModel,
  getModelDownloadUrl,
  getInferenceCode,
  getModelCard,
  getDownloadHeaders,
} from '../lib/api';
import type {
  MLColumnMeta,
  TaskDetectResponse,
  ModelRecommendation,
  ModelCard,
  TrainingResult,
} from '../lib/types';

// ── Constants ─────────────────────────────────────────────────
const NO_TARGET = '__NO_TARGET__';

const TASK_LABELS: Record<string, string> = {
  binary_classification:    'Binary Classification',
  multiclass_classification:'Multiclass Classification',
  regression:               'Regression',
  clustering:               'Clustering',
  unknown:                  'Unknown',
};

const TASK_COLORS: Record<string, string> = {
  binary_classification:     '#6366F1',
  multiclass_classification: '#38BDF8',
  regression:                '#F59E0B',
  clustering:                '#10B981',
  unknown:                   '#475569',
};

const CLUSTER_COLORS = ['#6366F1','#10B981','#F59E0B','#F43F5E','#38BDF8','#A855F7','#06B6D4','#84CC16'];

const MODEL_ICON_MAP: Record<string, React.ReactNode> = {
  tree:           <Activity size={20} />,
  forest:         <BarChart2 size={20} />,
  gradient_boost: <TrendingUp size={20} />,
  xgboost:        <Zap size={20} />,
  logistic:       <Activity size={20} />,
  linear:         <TrendingUp size={20} />,
  svm:            <Zap size={20} />,
  knn:            <Target size={20} />,
  neural:         <Brain size={20} />,
  ridge:          <TrendingUp size={20} />,
  lasso:          <TrendingUp size={20} />,
  kmeans:         <BarChart2 size={20} />,
  dbscan:         <Activity size={20} />,
};

function getModelIcon(iconStr: string): React.ReactNode {
  return MODEL_ICON_MAP[iconStr.toLowerCase()] ?? <Brain size={20} />;
}

// ── Helpers ───────────────────────────────────────────────────
function getMetric(
  metrics: Record<string, number | Record<string, unknown>>,
  key: string,
): number {
  const v = metrics[key];
  return typeof v === 'number' ? v : 0;
}

function fmtPct(v: number) {
  return (v * 100).toFixed(2) + '%';
}

function fmtNum(v: number, decimals = 4) {
  return v.toFixed(decimals);
}

// ── DotProgress (replaces Stars) ─────────────────────────────
function DotProgress({ count, max = 5 }: { count: number; max?: number }) {
  return (
    <span className="ml-dots">
      {Array.from({ length: max }, (_, i) => (
        <span
          key={i}
          className={`ml-dot ${i < count ? 'ml-dot--filled' : 'ml-dot--empty'}`}
        />
      ))}
    </span>
  );
}

// ── Task badge ────────────────────────────────────────────────
function TaskBadge({ task }: { task: string }) {
  const taskClass = task === 'binary_classification' ? 'ml-task-badge--binary'
    : task === 'multiclass_classification' ? 'ml-task-badge--multiclass'
    : task === 'regression' ? 'ml-task-badge--regression'
    : task === 'clustering' ? 'ml-task-badge--clustering'
    : 'ml-task-badge--unknown';

  return (
    <span className={`ml-task-badge ${taskClass}`}>
      {TASK_LABELS[task] ?? task}
    </span>
  );
}

// ── Metric card ───────────────────────────────────────────────
function MetricCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="ml-metric-card">
      <div className="ml-metric-label">{label}</div>
      <div className="ml-metric-value">{value}</div>
      {sub && <div className="ml-metric-sub">{sub}</div>}
    </div>
  );
}

// ── ROC Curve SVG ─────────────────────────────────────────────
function RocChart({ fpr, tpr, auc }: { fpr: number[]; tpr: number[]; auc: number }) {
  const W = 260, H = 180, PL = 30, PT = 10;
  const sx = (v: number) => PL + v * W;
  const sy = (v: number) => PT + H - v * H;

  const pts = fpr.map((x, i) => `${sx(x)},${sy(tpr[i])}`).join(' ');

  return (
    <div className="ml-chart-wrap" style={{ flex: 1, minWidth: 280 }}>
      <div className="ml-chart-title">
        ROC Curve — AUC: {auc.toFixed(3)}
      </div>
      <svg
        viewBox={`0 0 ${W + PL + 10} ${H + PT + 20}`}
        style={{ width: '100%', height: 'auto', display: 'block' }}
        aria-label={`ROC Curve AUC ${auc.toFixed(3)}`}
      >
        {/* Axes */}
        <line x1={PL} y1={PT} x2={PL} y2={PT + H} stroke="rgba(255,255,255,0.1)" strokeWidth={1} />
        <line x1={PL} y1={PT + H} x2={PL + W} y2={PT + H} stroke="rgba(255,255,255,0.1)" strokeWidth={1} />
        {/* Grid lines */}
        {[0.25, 0.5, 0.75].map((t) => (
          <React.Fragment key={t}>
            <line x1={PL} y1={sy(t)} x2={PL + W} y2={sy(t)} stroke="rgba(255,255,255,0.06)" strokeWidth={0.5} strokeDasharray="3,3" />
            <line x1={sx(t)} y1={PT} x2={sx(t)} y2={PT + H} stroke="rgba(255,255,255,0.06)" strokeWidth={0.5} strokeDasharray="3,3" />
          </React.Fragment>
        ))}
        {/* Diagonal ref */}
        <line x1={sx(0)} y1={sy(0)} x2={sx(1)} y2={sy(1)} stroke="rgba(255,255,255,0.15)" strokeWidth={1} strokeDasharray="4,3" />
        {/* Curve fill */}
        <polyline
          points={`${sx(0)},${sy(0)} ${pts} ${sx(1)},${sy(0)}`}
          fill="var(--accent-primary)"
          fillOpacity={0.15}
          stroke="none"
        />
        {/* Curve */}
        <polyline
          points={pts}
          fill="none"
          stroke="var(--accent-primary)"
          strokeWidth={2}
          strokeLinejoin="round"
        />
        {/* Axis labels */}
        <text x={PL + W / 2} y={PT + H + 16} textAnchor="middle" fontSize={10} fill="var(--text-muted)" fontFamily="var(--font-mono)">FPR</text>
        <text x={6} y={PT + H / 2} textAnchor="middle" fontSize={10} fill="var(--text-muted)" fontFamily="var(--font-mono)" transform={`rotate(-90, 6, ${PT + H / 2})`}>TPR</text>
      </svg>
    </div>
  );
}

// ── Residual Scatter SVG ──────────────────────────────────────
function ResidualChart({ y_pred, residuals }: { y_pred: number[]; residuals: number[] }) {
  const W = 260, H = 170, PL = 30, PT = 10;
  const xMin = y_pred.reduce((a, b) => Math.min(a, b), Infinity);
  const xMax = y_pred.reduce((a, b) => Math.max(a, b), -Infinity);
  const yMin = residuals.reduce((a, b) => Math.min(a, b), Infinity);
  const yMax = residuals.reduce((a, b) => Math.max(a, b), -Infinity);
  const sx = (v: number) => PL + ((v - xMin) / (xMax - xMin || 1)) * W;
  const sy = (v: number) => PT + H - ((v - yMin) / (yMax - yMin || 1)) * H;
  const zeroY = sy(0);
  const pts   = y_pred.slice(0, 500);

  return (
    <div className="ml-chart-wrap" style={{ flex: 1, minWidth: 280 }}>
      <div className="ml-chart-title">Residual Plot</div>
      <svg
        viewBox={`0 0 ${W + PL + 10} ${H + PT + 20}`}
        style={{ width: '100%', height: 'auto', display: 'block' }}
        aria-label="Residual scatter plot"
      >
        <line x1={PL} y1={PT} x2={PL} y2={PT + H} stroke="rgba(255,255,255,0.1)" strokeWidth={1} />
        <line x1={PL} y1={PT + H} x2={PL + W} y2={PT + H} stroke="rgba(255,255,255,0.1)" strokeWidth={1} />
        {/* Zero line */}
        {zeroY >= PT && zeroY <= PT + H && (
          <line x1={PL} y1={zeroY} x2={PL + W} y2={zeroY} stroke="rgba(255,255,255,0.15)" strokeWidth={1} strokeDasharray="4,3" />
        )}
        {pts.map((x, i) => (
          <circle
            key={i}
            cx={sx(x)}
            cy={sy(residuals[i])}
            r={2.5}
            fill="var(--accent-primary)"
            fillOpacity={0.6}
          />
        ))}
        <text x={PL + W / 2} y={PT + H + 16} textAnchor="middle" fontSize={10} fill="var(--text-muted)" fontFamily="var(--font-mono)">Predicted</text>
        <text x={8} y={PT + H / 2} textAnchor="middle" fontSize={10} fill="var(--text-muted)" fontFamily="var(--font-mono)" transform={`rotate(-90, 8, ${PT + H / 2})`}>Residual</text>
      </svg>
    </div>
  );
}

// ── Cluster Scatter SVG ───────────────────────────────────────
function ClusterScatter({ data }: { data: Array<{ x: number; y: number; cluster: number }> }) {
  const W = 260, H = 190, PL = 20, PT = 10;
  const pts  = data.slice(0, 600);
  const xMin = pts.reduce((a, b) => Math.min(a, b.x), Infinity);
  const xMax = pts.reduce((a, b) => Math.max(a, b.x), -Infinity);
  const yMin = pts.reduce((a, b) => Math.min(a, b.y), Infinity);
  const yMax = pts.reduce((a, b) => Math.max(a, b.y), -Infinity);
  const sx   = (v: number) => PL + ((v - xMin) / (xMax - xMin || 1)) * W;
  const sy   = (v: number) => PT + H - ((v - yMin) / (yMax - yMin || 1)) * H;

  return (
    <div className="ml-chart-wrap" style={{ flex: 1, minWidth: 280 }}>
      <div className="ml-chart-title">Cluster Visualization (2D projection)</div>
      <svg
        viewBox={`0 0 ${W + PL + 10} ${H + PT + 10}`}
        style={{ width: '100%', height: 'auto', display: 'block' }}
        aria-label="Cluster 2D scatter"
      >
        <line x1={PL} y1={PT} x2={PL} y2={PT + H} stroke="rgba(255,255,255,0.1)" strokeWidth={1} />
        <line x1={PL} y1={PT + H} x2={PL + W} y2={PT + H} stroke="rgba(255,255,255,0.1)" strokeWidth={1} />
        {pts.map((pt, i) => (
          <circle
            key={i}
            cx={sx(pt.x)}
            cy={sy(pt.y)}
            r={3}
            fill={CLUSTER_COLORS[pt.cluster % CLUSTER_COLORS.length]}
            fillOpacity={0.7}
          />
        ))}
      </svg>
    </div>
  );
}

// ── Confusion Matrix ──────────────────────────────────────────
function ConfusionMatrix({ matrix, labels }: { matrix: number[][]; labels: string[] }) {
  const flat   = matrix.flat();
  const maxVal = flat.reduce((a, b) => Math.max(a, b), 0) || 1;

  return (
    <div className="ml-chart-wrap" style={{ flex: 1, minWidth: 280 }}>
      <div className="ml-chart-title">Confusion Matrix</div>
      <div className="ml-confusion-scroll">
        <table className="ml-confusion-matrix">
          <thead>
            <tr>
              <th className="ml-cm-corner">pred &rarr;</th>
              {labels.map((l) => (
                <th key={l} className="ml-cm-col-label">{l}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {matrix.map((row, i) => (
              <tr key={i}>
                <th className="ml-cm-row-label">{labels[i]}</th>
                {row.map((val, j) => {
                  const intensity = val / maxVal;
                  const isDiag    = i === j;
                  return (
                    <td
                      key={j}
                      className={`ml-cm-cell ${isDiag ? 'ml-cm-cell--diag' : ''}`}
                      style={{
                        backgroundColor: isDiag
                          ? `rgba(99, 102, 241, ${0.15 + intensity * 0.6})`
                          : `rgba(244, 63, 94, ${intensity * 0.45})`,
                      }}
                      title={`Actual: ${labels[i]}, Predicted: ${labels[j]}: ${val}`}
                    >
                      {val}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Feature Importance ────────────────────────────────────────
function FeatureImportanceChart({ features }: { features: Array<{ feature: string; importance: number }> }) {
  const top    = features.slice(0, 15);
  const maxImp = top.reduce((a, b) => Math.max(a, b.importance), 0) || 1;

  return (
    <div className="ml-chart-wrap ml-chart-wrap--full">
      <div className="ml-chart-title">Feature Importance (Top {top.length})</div>
      <div className="ml-feat-list">
        {top.map((f, i) => (
          <div key={f.feature} className="ml-feat-bar">
            <div className="ml-feat-rank">{i + 1}</div>
            <div className="ml-feat-name" title={f.feature}>{f.feature}</div>
            <div className="ml-feat-track">
              <div
                className="ml-feat-fill"
                style={{ width: `${(f.importance / maxImp) * 100}%` }}
              />
            </div>
            <div className="ml-feat-val">{f.importance.toFixed(4)}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Cluster Bar Chart ─────────────────────────────────────────
function ClusterDistChart({ distribution }: { distribution: Record<string, number> }) {
  const entries  = Object.entries(distribution);
  const maxCount = entries.reduce((a, [, v]) => Math.max(a, v), 0) || 1;

  return (
    <div className="ml-chart-wrap" style={{ flex: 1, minWidth: 280 }}>
      <div className="ml-chart-title">Cluster Distribution</div>
      <div className="ml-cluster-bars">
        {entries.map(([cluster, count], i) => (
          <div key={cluster} className="ml-cluster-bar-row">
            <div className="ml-cluster-label">Cluster {cluster}</div>
            <div className="ml-cluster-track">
              <div
                className="ml-cluster-fill"
                style={{
                  width: `${(count / maxCount) * 100}%`,
                  backgroundColor: CLUSTER_COLORS[i % CLUSTER_COLORS.length],
                }}
              />
            </div>
            <div className="ml-cluster-count">{count.toLocaleString()}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────
export default function MLBuilderView({ filename }: { filename: string }) {

  // ── Column / task state ───────────────────────────────────
  const [mlColumns,     setMlColumns]     = useState<MLColumnMeta[]>([]);
  const [colsLoading,   setColsLoading]   = useState(false);
  const [colsError,     setColsError]     = useState('');
  const [targetCol,     setTargetCol]     = useState('');
  const [taskInfo,      setTaskInfo]      = useState<TaskDetectResponse | null>(null);
  const [taskLoading,   setTaskLoading]   = useState(false);
  const [recommendation,setRecommendation]= useState<ModelRecommendation | null>(null);
  const [recLoading,    setRecLoading]    = useState(false);

  // ── Model cards state ─────────────────────────────────────
  const [cards,         setCards]         = useState<ModelCard[]>([]);
  const [cardsLoading,  setCardsLoading]  = useState(false);
  const [selectedCard,  setSelectedCard]  = useState<ModelCard | null>(null);

  // ── Hyperparams state ─────────────────────────────────────
  const [hyperparams,   setHyperparams]   = useState<Record<string, unknown>>({});
  const [autoTune,      setAutoTune]      = useState(false);
  const [cvFolds,       setCvFolds]       = useState(5);
  const [testSize,      setTestSize]      = useState(0.2);

  // ── Training state ────────────────────────────────────────
  const [training,      setTraining]      = useState(false);
  const [trainResult,   setTrainResult]   = useState<TrainingResult | null>(null);
  const [trainError,    setTrainError]    = useState('');

  // ── Export state ──────────────────────────────────────────
  const [inferenceCode, setInferenceCode] = useState('');
  const [modelCardText, setModelCardText] = useState('');
  const [showInference, setShowInference] = useState(false);
  const [showModelCard, setShowModelCard] = useState(false);
  const [codeCopied,    setCodeCopied]    = useState(false);
  const [downloading,   setDownloading]   = useState(false);
  const [exportLoading, setExportLoading] = useState<'inference' | 'card' | null>(null);

  // ── Load columns on mount ─────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setColsLoading(true);
      setColsError('');
      try {
        const data = await getMLColumns(filename);
        if (!cancelled) setMlColumns(data.columns);
      } catch (err) {
        if (!cancelled)
          setColsError(err instanceof Error ? err.message : 'Failed to load columns');
      } finally {
        if (!cancelled) setColsLoading(false);
      }
    };
    load();
    return () => { cancelled = true; };
  }, [filename]);

  // ── Target column change handler ──────────────────────────
  const handleTargetChange = useCallback(async (col: string) => {
    setTargetCol(col);
    setTaskInfo(null);
    setRecommendation(null);
    setCards([]);
    setSelectedCard(null);
    setHyperparams({});
    setTrainResult(null);
    setTrainError('');

    if (!col) return;

    const isClustering = col === NO_TARGET;

    if (isClustering) {
      const clusterTask: TaskDetectResponse = { task: 'clustering' };
      setTaskInfo(clusterTask);
    } else {
      setTaskLoading(true);
      try {
        const task = await detectMLTask(filename, col);
        setTaskInfo(task);
      } catch (e) {
        console.error('Task detection failed:', e);
        setTaskLoading(false);
        return;
      } finally {
        setTaskLoading(false);
      }
    }

    // Fetch recommendation + model cards in parallel
    const task = isClustering ? 'clustering' : null;
    setRecLoading(true);
    setCardsLoading(true);

    try {
      const [rec, cardsData] = await Promise.all([
        getMLRecommendation(filename, isClustering ? undefined : col),
        getModelCards(task ?? 'regression'), // temp; will be updated after task detection
      ]);
      setRecommendation(rec);
      setCards(cardsData.cards);
    } catch (e) {
      console.error('Recommendation/cards fetch failed:', e);
    } finally {
      setRecLoading(false);
      setCardsLoading(false);
    }
  }, [filename]);

  // Re-fetch model cards once task is actually known (not clustering path)
  useEffect(() => {
    if (!taskInfo || taskInfo.task === 'clustering') return;
    let cancelled = false;
    const fetchCards = async () => {
      setCardsLoading(true);
      try {
        const data = await getModelCards(taskInfo.task);
        if (!cancelled) setCards(data.cards);
      } catch (e) {
        console.error('Cards fetch failed:', e);
      } finally {
        if (!cancelled) setCardsLoading(false);
      }
    };
    fetchCards();
    return () => { cancelled = true; };
  }, [taskInfo?.task]); // eslint-disable-line react-hooks/exhaustive-deps

  // Init hyperparams when a card is selected
  const handleSelectCard = (card: ModelCard) => {
    setSelectedCard(card);
    const init: Record<string, unknown> = {};
    Object.entries(card.hyperparams).forEach(([key, def]) => {
      init[key] = def.default;
    });
    setHyperparams(init);
    setTrainResult(null);
    setTrainError('');
  };

  // ── Train handler ─────────────────────────────────────────
  const handleTrain = async () => {
    if (!selectedCard || !taskInfo) return;
    setTraining(true);
    setTrainError('');
    setTrainResult(null);
    try {
      const result = await trainModel({
        filename,
        model_id:   selectedCard.id,
        target_col: targetCol === NO_TARGET ? undefined : targetCol,
        task:       taskInfo.task,
        hyperparams,
        auto_tune:  autoTune,
        cv_folds:   autoTune ? cvFolds : undefined,
        test_size:  testSize,
        random_state: 42,
      });
      setTrainResult(result);
    } catch (err) {
      setTrainError(err instanceof Error ? err.message : 'Training failed');
    } finally {
      setTraining(false);
    }
  };

  // ── Export handlers ───────────────────────────────────────
  const handleDownloadModel = async () => {
    if (!trainResult) return;
    setDownloading(true);
    try {
      const url     = getModelDownloadUrl(trainResult.session_key);
      const headers = getDownloadHeaders();
      const resp    = await fetch(url, { headers });
      if (!resp.ok) throw new Error('Model download failed');
      const blob    = await resp.blob();
      const a       = document.createElement('a');
      a.href        = URL.createObjectURL(blob);
      a.download    = `model_${trainResult.model_id}.pkl`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(a.href);
    } catch (e) {
      console.error(e);
    } finally {
      setDownloading(false);
    }
  };

  const handleViewInference = async () => {
    if (!trainResult) return;
    setExportLoading('inference');
    try {
      const code = await getInferenceCode(trainResult.session_key);
      setInferenceCode(code);
      setShowInference(true);
      setShowModelCard(false);
    } catch (e) {
      console.error(e);
    } finally {
      setExportLoading(null);
    }
  };

  const handleViewModelCard = async () => {
    if (!trainResult) return;
    setExportLoading('card');
    try {
      const card = await getModelCard(trainResult.session_key);
      setModelCardText(card);
      setShowModelCard(true);
      setShowInference(false);
    } catch (e) {
      console.error(e);
    } finally {
      setExportLoading(null);
    }
  };

  const handleCopyCode = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(inferenceCode);
      setCodeCopied(true);
      setTimeout(() => setCodeCopied(false), 2000);
    } catch {
      console.error('Clipboard copy failed');
    }
  }, [inferenceCode]);

  // ── Derived ───────────────────────────────────────────────
  const currentTask    = taskInfo?.task ?? '';
  const isClassification = currentTask === 'binary_classification' || currentTask === 'multiclass_classification';
  const isRegression     = currentTask === 'regression';
  const isClustering     = currentTask === 'clustering';

  // ── Render ────────────────────────────────────────────────
  return (
    <section className="ml-panel">

      {/* Header ─────────────────────────────────────────────── */}
      <div className="ml-rec-header" style={{ gap: 18, alignItems: 'flex-start' }}>
        <div className="ml-step-num" style={{
          width: 52, height: 52, borderRadius: 16,
          background: 'linear-gradient(135deg, rgba(99,102,241,0.2), rgba(99,102,241,0.08))',
          border: '1px solid rgba(99,102,241,0.25)',
          boxShadow: '0 0 24px rgba(99,102,241,0.15)',
        }}>
          <Brain size={26} color="var(--accent-primary)" />
        </div>
        <div>
          <h2 className="ml-title">ML Model Builder</h2>
          <p className="ml-subtitle" style={{ marginTop: 4 }}>
            AI-powered model selection, training &amp; evaluation
          </p>
          <div className="ml-loading-row" style={{ marginTop: 8 }}>
            <Database size={12} />
            {filename}
          </div>
        </div>
      </div>

      {colsError && (
        <motion.div
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          className="ml-error-banner"
        >
          <AlertCircle size={15} /> {colsError}
        </motion.div>
      )}

      {/* ── STEP 1: Target Column ─────────────────────────── */}
      <motion.div className="ml-step" animate={{ opacity: [0, 1] }} transition={{ duration: 0.4 }}>
        <div className="ml-step-head">
          <span className="ml-step-num">01</span>
          <span className="ml-step-label">Select Target Column</span>
        </div>

        {colsLoading ? (
          <div className="ml-loading-row">
            <Loader2 size={14} className="viz-spin" /> Loading columns...
          </div>
        ) : (
          <div className="ml-target-row">
            <div style={{ position: 'relative', flex: '1 1 320px', maxWidth: 480 }}>
              <select
                value={targetCol}
                onChange={(e) => handleTargetChange(e.target.value)}
                className="ml-select"
                style={{ width: '100%' }}
              >
                <option value="">-- choose target column --</option>
                <option value={NO_TARGET}>No target -- Clustering</option>
                {mlColumns.map((col) => (
                  <option key={col.name} value={col.name}>
                    {col.name} ({col.dtype}, {col.n_unique} unique)
                  </option>
                ))}
              </select>
              <ChevronDown
                size={16}
                style={{
                  position: 'absolute',
                  right: 14,
                  top: '50%',
                  transform: 'translateY(-50%)',
                  color: 'var(--text-muted)',
                  pointerEvents: 'none',
                }}
              />
            </div>

            {taskLoading && (
              <span className="ml-loading-row">
                <Loader2 size={14} className="viz-spin" /> Detecting task...
              </span>
            )}

            {taskInfo && !taskLoading && (
              <TaskBadge task={taskInfo.task} />
            )}
          </div>
        )}

        {/* Task details */}
        {taskInfo && !taskLoading && (
          <AnimatePresence>
            <motion.div
              key="task-detail"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              className="ml-task-detail"
            >
              {taskInfo.n_classes !== undefined && (
                <span className="ml-task-chip">
                  {taskInfo.n_classes} classes
                </span>
              )}
              {taskInfo.class_labels && taskInfo.class_labels.length > 0 &&
                taskInfo.class_labels.slice(0, 5).map((label, idx) => (
                  <span key={idx} className="ml-task-chip"
                    style={{
                      background: `${TASK_COLORS[currentTask] ?? 'var(--text-muted)'}12`,
                      borderColor: `${TASK_COLORS[currentTask] ?? 'var(--text-muted)'}30`,
                      color: TASK_COLORS[currentTask] ?? 'var(--text-secondary)',
                    }}
                  >
                    {label}
                  </span>
                ))
              }
              {taskInfo.class_labels && taskInfo.class_labels.length > 5 && (
                <span className="ml-loading-row">
                  +{taskInfo.class_labels.length - 5} more
                </span>
              )}
              {taskInfo.target_range && (
                <span className="ml-task-chip">
                  range: [{taskInfo.target_range[0].toFixed(2)}, {taskInfo.target_range[1].toFixed(2)}]
                </span>
              )}
            </motion.div>
          </AnimatePresence>
        )}

        {/* AI Recommendation card */}
        <AnimatePresence>
          {(recLoading || recommendation) && (
            <motion.div
              key="rec-card"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className="ml-rec-card"
            >
              <div className="ml-rec-header">
                <span className="ml-rec-title">
                  &#10022; AI Recommendation
                </span>
              </div>
              {recLoading ? (
                <div className="ml-loading-row">
                  <Loader2 size={13} className="viz-spin" /> Analyzing dataset...
                </div>
              ) : recommendation ? (
                <>
                  <div className="ml-rec-model">{recommendation.recommended_model}</div>
                  <p className="ml-rec-reason">{recommendation.reason}</p>
                  {recommendation.analysis_factors.length > 0 && (
                    <ul className="ml-rec-factors">
                      {recommendation.analysis_factors.map((f, i) => (
                        <li key={i}><Check size={10} /> {f}</li>
                      ))}
                    </ul>
                  )}
                  <div className="ml-rec-summary">
                    <span className="ml-rec-chip">
                      {recommendation.dataset_summary.n_samples.toLocaleString()} samples
                    </span>
                    <span className="ml-rec-chip">
                      {recommendation.dataset_summary.n_features} features
                    </span>
                    {recommendation.dataset_summary.is_imbalanced && (
                      <span className="ml-rec-chip ml-rec-chip--warn">imbalanced</span>
                    )}
                    {recommendation.dataset_summary.high_dimensionality && (
                      <span className="ml-rec-chip ml-rec-chip--warn">high-dim</span>
                    )}
                  </div>
                </>
              ) : null}
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>

      {/* ── STEP 2: Model Selection ───────────────────────── */}
      <AnimatePresence>
        {(cardsLoading || cards.length > 0) && taskInfo && (
          <motion.div
            key="step2"
            className="ml-step"
            animate={{ opacity: [0, 1] }}
            transition={{ duration: 0.4 }}
          >
            <div className="ml-step-head">
              <span className="ml-step-num">02</span>
              <span className="ml-step-label">Select Model</span>
            </div>

            {cardsLoading ? (
              <div className="ml-loading-row">
                <Loader2 size={14} className="viz-spin" /> Loading model options...
              </div>
            ) : (
              <div className="ml-model-grid">
                {cards.map((card) => {
                  const isRecommended = recommendation?.recommended_model === card.name;
                  const isSelected    = selectedCard?.id === card.id;
                  return (
                    <div
                      key={card.id}
                      role="button"
                      tabIndex={0}
                      onClick={() => handleSelectCard(card)}
                      onKeyDown={(e) => e.key === 'Enter' && handleSelectCard(card)}
                      className={`ml-model-card${isSelected ? ' ml-model-card--selected' : ''}${isRecommended ? ' ml-model-card--recommended' : ''}`}
                    >
                      {isRecommended && (
                        <div className="ml-ai-badge">
                          <Star size={10} fill="var(--accent-warning)" /> AI Pick
                        </div>
                      )}

                      <div className="ml-model-icon">
                        {card.icon ? <span>{card.icon}</span> : getModelIcon(card.id)}
                      </div>

                      <div className="ml-model-name">{card.name}</div>
                      <div className="ml-model-best">Best for: {card.best_for}</div>

                      {card.pros.length > 0 && (
                        <ul className="ml-model-pros">
                          {card.pros.slice(0, 3).map((p, i) => (
                            <li key={i}>
                              <Check size={12} className="ml-pro-icon" /> {p}
                            </li>
                          ))}
                        </ul>
                      )}

                      {card.cons.length > 0 && (
                        <ul className="ml-model-cons">
                          {card.cons.slice(0, 2).map((c, i) => (
                            <li key={i}>
                              <X size={12} className="ml-con-icon" /> {c}
                            </li>
                          ))}
                        </ul>
                      )}

                      <div className="ml-model-stats">
                        <div className="ml-model-stat">
                          <span className="ml-stat-label">Interpretability</span>
                          <DotProgress count={card.interpretability} />
                        </div>
                        <div className="ml-model-stat">
                          <span className="ml-stat-label">Speed</span>
                          <DotProgress count={card.speed} />
                        </div>
                      </div>

                      <button
                        className={`ml-export-btn${isSelected ? ' ml-export-btn--primary' : ''}`}
                        style={{ width: '100%', justifyContent: 'center' }}
                        onClick={(e) => { e.stopPropagation(); handleSelectCard(card); }}
                      >
                        {isSelected ? 'Selected' : 'Select'}
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── STEP 3: Hyperparameter Config ────────────────── */}
      <AnimatePresence>
        {selectedCard && (
          <motion.div
            key="step3"
            className="ml-step"
            animate={{ opacity: [0, 1] }}
            transition={{ duration: 0.35 }}
          >
            <div className="ml-step-head">
              <span className="ml-step-num">03</span>
              <span className="ml-step-label">
                Configure Hyperparameters — <span style={{ color: 'var(--text-accent)' }}>{selectedCard.name}</span>
              </span>
            </div>

            <div className="ml-params-grid">
              {Object.entries(selectedCard.hyperparams).map(([key, def]) => {
                const val = hyperparams[key] ?? def.default;
                return (
                  <div key={key} className="ml-param-row" style={{
                    background: 'var(--bg-elevated)',
                    borderRadius: 12,
                    padding: '14px 16px',
                    border: '1px solid var(--border-default)',
                  }}>
                    <label className="ml-param-label">
                      {def.label}
                      {def.tooltip && (
                        <span className="ml-param-tip" title={def.tooltip}>?</span>
                      )}
                    </label>

                    {def.type === 'bool' && (
                      <div
                        onClick={() =>
                          setHyperparams((p) => ({ ...p, [key]: !Boolean(val) }))
                        }
                        style={{
                          width: 44,
                          height: 24,
                          borderRadius: 12,
                          background: Boolean(val) ? 'var(--accent-primary)' : 'var(--bg-muted)',
                          cursor: 'pointer',
                          position: 'relative',
                          transition: 'background 0.2s ease',
                          flexShrink: 0,
                        }}
                      >
                        <div style={{
                          width: 18,
                          height: 18,
                          borderRadius: '50%',
                          background: '#fff',
                          position: 'absolute',
                          top: 3,
                          left: Boolean(val) ? 23 : 3,
                          transition: 'left 0.2s ease',
                          boxShadow: '0 1px 3px rgba(0,0,0,0.3)',
                        }} />
                      </div>
                    )}

                    {(def.type === 'int' || def.type === 'float') && (
                      <input
                        type="number"
                        min={def.min}
                        max={def.max}
                        step={def.type === 'float' ? 0.001 : 1}
                        value={Number(val)}
                        onChange={(e) =>
                          setHyperparams((p) => ({
                            ...p,
                            [key]: def.type === 'float'
                              ? parseFloat(e.target.value)
                              : parseInt(e.target.value),
                          }))
                        }
                        className="ml-input"
                        style={{ width: '100%' }}
                      />
                    )}

                    {def.type === 'select' && (
                      <div style={{ position: 'relative' }}>
                        <select
                          value={String(val ?? '')}
                          onChange={(e) =>
                            setHyperparams((p) => ({ ...p, [key]: e.target.value }))
                          }
                          className="ml-select"
                          style={{ width: '100%' }}
                        >
                          {def.options?.map((opt) => (
                            <option key={opt} value={opt}>{opt}</option>
                          ))}
                        </select>
                        <ChevronDown
                          size={14}
                          style={{
                            position: 'absolute',
                            right: 10,
                            top: '50%',
                            transform: 'translateY(-50%)',
                            color: 'var(--text-muted)',
                            pointerEvents: 'none',
                          }}
                        />
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* CV + test size options */}
            <div className="ml-train-options">
              <label className="ml-checkbox-label">
                <div
                  onClick={() => setAutoTune(!autoTune)}
                  style={{
                    width: 44,
                    height: 24,
                    borderRadius: 12,
                    background: autoTune ? 'var(--accent-primary)' : 'var(--bg-muted)',
                    cursor: 'pointer',
                    position: 'relative',
                    transition: 'background 0.2s ease',
                    flexShrink: 0,
                  }}
                >
                  <div style={{
                    width: 18,
                    height: 18,
                    borderRadius: '50%',
                    background: '#fff',
                    position: 'absolute',
                    top: 3,
                    left: autoTune ? 23 : 3,
                    transition: 'left 0.2s ease',
                    boxShadow: '0 1px 3px rgba(0,0,0,0.3)',
                  }} />
                </div>
                Auto-tune with cross-validation
              </label>

              {autoTune && (
                <div className="ml-cv-row" style={{ flexDirection: 'column', alignItems: 'stretch' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <label className="ml-param-label">CV Folds</label>
                    <span className="ml-metric-value" style={{ fontSize: 14 }}>{cvFolds}</span>
                  </div>
                  <input
                    type="range"
                    min={3}
                    max={10}
                    step={1}
                    value={cvFolds}
                    onChange={(e) => setCvFolds(parseInt(e.target.value))}
                    className="ml-slider"
                  />
                </div>
              )}

              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <label className="ml-param-label">Test size</label>
                  <span className="ml-metric-value" style={{ fontSize: 14 }}>
                    {Math.round(testSize * 100)}%
                  </span>
                </div>
                <input
                  type="range"
                  min={0.10}
                  max={0.40}
                  step={0.01}
                  value={testSize}
                  onChange={(e) => setTestSize(parseFloat(e.target.value))}
                  className="ml-slider"
                />
              </div>
            </div>

          </motion.div>
        )}
      </AnimatePresence>

      {/* ── STEP 4: Train ────────────────────────────────── */}
      <AnimatePresence>
        {selectedCard && taskInfo && (
          <motion.div
            key="step4"
            className="ml-step"
            animate={{ opacity: [0, 1] }}
            transition={{ duration: 0.35 }}
          >
            <div className="ml-step-head">
              <span className="ml-step-num">04</span>
              <span className="ml-step-label">Train Model</span>
            </div>

            <button
              onClick={handleTrain}
              disabled={training}
              className="ml-train-btn"
            >
              {training
                ? <><Loader2 size={16} className="viz-spin" /> Training...</>
                : <><RefreshCw size={16} /> Train {selectedCard.name}</>}
            </button>

            {trainError && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="ml-error-banner"
              >
                <AlertCircle size={14} /> {trainError}
              </motion.div>
            )}

            {/* Training spinner */}
            {training && (
              <motion.div
                animate={{ opacity: [0, 1] }}
                transition={{ duration: 0.3 }}
                className="ml-training-overlay"
              >
                <div className="ml-big-spinner" />
                <p className="ml-subtitle">
                  Training {selectedCard.name} — this may take a moment...
                </p>
              </motion.div>
            )}

            {/* ── Results ── */}
            <AnimatePresence>
              {trainResult && !training && (
                <motion.div
                  key="train-results"
                  animate={{ opacity: [0, 1] }}
                  transition={{ duration: 0.5 }}
                  className="ml-results"
                >
                  {/* Training meta */}
                  <div className="ml-train-meta">
                    <span className="ml-meta-chip" style={{
                      background: 'rgba(16,185,129,0.1)',
                      border: '1px solid rgba(16,185,129,0.2)',
                      color: 'var(--accent-success)',
                    }}>
                      <CheckCircle size={13} /> Training complete in {trainResult.training_time_seconds.toFixed(2)}s
                    </span>
                    {trainResult.n_train_samples !== undefined && (
                      <span className="ml-meta-chip">
                        {trainResult.n_train_samples.toLocaleString()} train samples
                      </span>
                    )}
                    {trainResult.n_test_samples !== undefined && (
                      <span className="ml-meta-chip">
                        {trainResult.n_test_samples.toLocaleString()} test samples
                      </span>
                    )}
                  </div>

                  {/* CV score */}
                  {trainResult.cv_score_mean !== undefined && (
                    <div className="ml-cv-score">
                      <strong>{trainResult.cv_metric ?? 'CV'}:</strong>{' '}
                      {trainResult.cv_score_mean.toFixed(4)}
                      {trainResult.cv_score_std !== undefined &&
                        ` \u00B1 ${trainResult.cv_score_std.toFixed(4)}`}
                    </div>
                  )}

                  {/* Best params from auto-tune */}
                  {trainResult.best_params && Object.keys(trainResult.best_params).length > 0 && (
                    <div className="ml-best-params">
                      <div className="ml-section-mini-head">
                        Best Parameters (auto-tuned)
                      </div>
                      <div className="ml-params-chips">
                        {Object.entries(trainResult.best_params).map(([k, v]) => (
                          <span key={k} className="ml-param-chip">
                            {k}: {String(v)}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* ── Classification metrics ── */}
                  {isClassification && (
                    <>
                      <div className="ml-section-mini-head">Performance Metrics</div>
                      <div className="ml-metrics-grid">
                        <MetricCard label="Accuracy" value={fmtPct(getMetric(trainResult.metrics, 'accuracy'))} />
                        <MetricCard label="Precision" value={fmtPct(getMetric(trainResult.metrics, 'precision'))} />
                        <MetricCard label="Recall" value={fmtPct(getMetric(trainResult.metrics, 'recall'))} />
                        <MetricCard label="F1 Score" value={fmtPct(getMetric(trainResult.metrics, 'f1'))} />
                        {getMetric(trainResult.metrics, 'roc_auc') > 0 && (
                          <MetricCard label="ROC-AUC" value={fmtNum(getMetric(trainResult.metrics, 'roc_auc'), 4)} />
                        )}
                      </div>
                      <div className="ml-charts-row">
                        {trainResult.plots?.confusion_matrix && (
                          <ConfusionMatrix
                            matrix={trainResult.plots.confusion_matrix.matrix}
                            labels={trainResult.plots.confusion_matrix.labels}
                          />
                        )}
                        {trainResult.plots?.roc_curve && (
                          <RocChart
                            fpr={trainResult.plots.roc_curve.fpr}
                            tpr={trainResult.plots.roc_curve.tpr}
                            auc={trainResult.plots.roc_curve.auc}
                          />
                        )}
                      </div>
                    </>
                  )}

                  {/* ── Regression metrics ── */}
                  {isRegression && (
                    <>
                      <div className="ml-section-mini-head">Performance Metrics</div>
                      <div className="ml-metrics-grid">
                        <MetricCard label="MAE"        value={fmtNum(getMetric(trainResult.metrics, 'mae'))} />
                        <MetricCard label="RMSE"       value={fmtNum(getMetric(trainResult.metrics, 'rmse'))} />
                        <MetricCard label="R&#178;"         value={fmtNum(getMetric(trainResult.metrics, 'r2'), 4)} />
                        <MetricCard label="Adj. R&#178;"    value={fmtNum(getMetric(trainResult.metrics, 'adjusted_r2'), 4)} />
                      </div>
                      {trainResult.plots?.residual_plot && (
                        <div className="ml-charts-row">
                          <ResidualChart
                            y_pred={trainResult.plots.residual_plot.y_pred}
                            residuals={trainResult.plots.residual_plot.residuals}
                          />
                        </div>
                      )}
                    </>
                  )}

                  {/* ── Clustering metrics ── */}
                  {isClustering && (
                    <>
                      <div className="ml-section-mini-head">Clustering Metrics</div>
                      <div className="ml-metrics-grid">
                        <MetricCard
                          label="Silhouette Score"
                          value={fmtNum(getMetric(trainResult.metrics, 'silhouette_score'), 4)}
                          sub="higher is better"
                        />
                        <MetricCard
                          label="Davies-Bouldin"
                          value={fmtNum(getMetric(trainResult.metrics, 'davies_bouldin'), 4)}
                          sub="lower is better"
                        />
                        <MetricCard
                          label="Calinski-Harabasz"
                          value={fmtNum(getMetric(trainResult.metrics, 'calinski_harabasz'), 2)}
                          sub="higher is better"
                        />
                        {trainResult.n_clusters !== undefined && (
                          <MetricCard label="Clusters" value={String(trainResult.n_clusters)} />
                        )}
                      </div>
                      <div className="ml-charts-row">
                        {trainResult.cluster_distribution && (
                          <ClusterDistChart distribution={trainResult.cluster_distribution} />
                        )}
                        {trainResult.visualization_data && trainResult.visualization_data.length > 0 && (
                          <ClusterScatter data={trainResult.visualization_data} />
                        )}
                      </div>
                    </>
                  )}

                  {/* Feature importance */}
                  {trainResult.feature_importance.length > 0 && (
                    <FeatureImportanceChart features={trainResult.feature_importance} />
                  )}

                </motion.div>
              )}
            </AnimatePresence>

          </motion.div>
        )}
      </AnimatePresence>

      {/* ── STEP 5: Export ───────────────────────────────── */}
      <AnimatePresence>
        {trainResult && !training && (
          <motion.div
            key="step5"
            className="ml-step"
            animate={{ opacity: [0, 1] }}
            transition={{ duration: 0.4 }}
          >
            <div className="ml-step-head">
              <span className="ml-step-num">05</span>
              <span className="ml-step-label">Export</span>
            </div>

            <div className="ml-export-btns">
              <button
                onClick={handleDownloadModel}
                disabled={downloading}
                className="ml-export-btn ml-export-btn--primary"
              >
                {downloading
                  ? <Loader2 size={14} className="viz-spin" />
                  : <Download size={14} />}
                {downloading ? 'Downloading...' : 'Download Model (.pkl)'}
              </button>

              <button
                onClick={handleViewInference}
                disabled={exportLoading === 'inference'}
                className="ml-export-btn"
              >
                {exportLoading === 'inference'
                  ? <Loader2 size={14} className="viz-spin" />
                  : <Zap size={14} />}
                View Inference Code
              </button>

              <button
                onClick={handleViewModelCard}
                disabled={exportLoading === 'card'}
                className="ml-export-btn"
              >
                {exportLoading === 'card'
                  ? <Loader2 size={14} className="viz-spin" />
                  : <Star size={14} />}
                View Model Card
              </button>
            </div>

            {/* Inference code block */}
            <AnimatePresence>
              {showInference && inferenceCode && (
                <motion.div
                  key="inference-code"
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="ml-code-block"
                >
                  <div className="ml-code-header">
                    <span>Inference Code</span>
                    <button onClick={handleCopyCode} className="ml-copy-btn">
                      {codeCopied ? <CheckCircle size={12} /> : <Copy size={12} />}
                      {codeCopied ? 'Copied!' : 'Copy'}
                    </button>
                  </div>
                  <pre className="ml-code-pre">
                    {inferenceCode}
                  </pre>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Model card block */}
            <AnimatePresence>
              {showModelCard && modelCardText && (
                <motion.div
                  key="model-card"
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="ml-model-card-block"
                >
                  <div className="ml-code-header">
                    <span>Model Card</span>
                    <button
                      onClick={async () => {
                        try { await navigator.clipboard.writeText(modelCardText); } catch {}
                      }}
                      className="ml-copy-btn"
                    >
                      <Copy size={12} /> Copy
                    </button>
                  </div>
                  <div className="ml-model-card-scroll">
                    <pre className="ml-code-pre">
                      {modelCardText}
                    </pre>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

          </motion.div>
        )}
      </AnimatePresence>

      {/* Empty state */}
      {!colsLoading && mlColumns.length === 0 && !colsError && (
        <motion.div
          animate={{ opacity: [0, 1] }}
          transition={{ duration: 0.4 }}
          className="ml-empty"
        >
          <div className="ml-empty-icon">
            <Database size={32} color="var(--text-muted)" />
          </div>
          <p className="ml-subtitle" style={{ textAlign: 'center' }}>
            No columns found in dataset. Please check the file is valid.
          </p>
        </motion.div>
      )}

    </section>
  );
}
