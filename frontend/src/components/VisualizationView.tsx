import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  BarChart2,
  TrendingUp,
  Activity,
  PieChart,
  Layers,
  AlignLeft,
  Download,
  Copy,
  Clock,
  RefreshCw,
  ChevronDown,
  AlertCircle,
  Grid3x3,
} from 'lucide-react';
import { generateVisualization, getColumns } from '../lib/api';
import type { ColumnMeta } from '../lib/types';

type VisualizationViewProps = { filename: string };

// ─── Chart type definitions ───────────────────────────────
type ChartDef = {
  id: string;
  label: string;
  icon: React.ReactNode;
  /** X column must be numeric */
  xNumericOnly: boolean;
  /** Whether to show a Y axis selector */
  showY: boolean;
};

const CHART_DEFS: ChartDef[] = [
  { id: 'bar',       label: 'Bar',       icon: <BarChart2 size={14} />,  xNumericOnly: false, showY: true  },
  { id: 'line',      label: 'Line',      icon: <TrendingUp size={14} />, xNumericOnly: true,  showY: true  },
  { id: 'scatter',   label: 'Scatter',   icon: <Activity size={14} />,   xNumericOnly: true,  showY: true  },
  { id: 'histogram', label: 'Histogram', icon: <AlignLeft size={14} />,  xNumericOnly: true,  showY: false },
  { id: 'pie',       label: 'Pie',       icon: <PieChart size={14} />,   xNumericOnly: false, showY: false },
  { id: 'boxplot',   label: 'Box Plot',  icon: <Layers size={14} />,     xNumericOnly: false, showY: true  },
  { id: 'heatmap',   label: 'Heatmap',   icon: <Grid3x3 size={14} />,    xNumericOnly: false, showY: false },
];

type HistoryEntry = { img: string; type: string; title: string };

export default function VisualizationView({ filename }: VisualizationViewProps) {
  const [columns,       setColumns]       = useState<ColumnMeta[]>([]);
  const [chartType,     setChartType]     = useState('bar');
  const [xColumn,       setXColumn]       = useState('');
  const [yColumn,       setYColumn]       = useState('');
  const [loadingCols,   setLoadingCols]   = useState(false);
  const [loadingChart,  setLoadingChart]  = useState(false);
  const [error,         setError]         = useState('');
  const [imageBase64,   setImageBase64]   = useState('');
  const [chartHistory,  setChartHistory]  = useState<HistoryEntry[]>([]);
  const [xOpen,         setXOpen]         = useState(false);
  const [yOpen,         setYOpen]         = useState(false);
  const [chartTitle,    setChartTitle]    = useState('Generated Chart');

  const titleRef  = useRef<HTMLDivElement>(null);
  const xDropRef  = useRef<HTMLDivElement>(null);
  const yDropRef  = useRef<HTMLDivElement>(null);

  const chartDef = CHART_DEFS.find((c) => c.id === chartType) ?? CHART_DEFS[0];

  // ── Load columns ─────────────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setLoadingCols(true);
      setError('');
      try {
        const res = await getColumns(filename);
        if (cancelled) return;
        setColumns(res.columns);
        setXColumn(res.columns[0]?.name ?? '');
        setYColumn(res.numeric_columns[0] ?? '');
      } catch (err) {
        if (!cancelled)
          setError(err instanceof Error ? err.message : 'Could not load columns');
      } finally {
        if (!cancelled) setLoadingCols(false);
      }
    };
    load();
    return () => { cancelled = true; };
  }, [filename]);

  // ── Close dropdowns on outside click ─────────────────────
  useEffect(() => {
    const h = (e: MouseEvent) => {
      if (xDropRef.current && !xDropRef.current.contains(e.target as Node)) setXOpen(false);
      if (yDropRef.current && !yDropRef.current.contains(e.target as Node)) setYOpen(false);
    };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, []);

  // ── Sync contentEditable title when state changes ─────────
  useEffect(() => {
    if (titleRef.current && titleRef.current.textContent !== chartTitle) {
      titleRef.current.textContent = chartTitle;
    }
  }, [chartTitle]);

  // ── Smart column filtering per chart type ─────────────────
  const xOptions = useMemo(() => {
    if (chartType === 'heatmap') {
      // Heatmap doesn't need specific columns
      return columns.filter((c) => c.type === 'numeric').slice(0, 1);
    }
    if (chartType === 'boxplot' && yColumn) {
      // For boxplot with Y axis: X should be categorical, Y should be numeric
      return columns.filter((c) => c.type === 'categorical' || c.type === 'datetime');
    }
    return chartDef.xNumericOnly
      ? columns.filter((c) => c.type === 'numeric')
      : columns;
  }, [chartDef, columns, chartType, yColumn]);

  const yOptions = useMemo(() => {
    if (chartType === 'boxplot') {
      // For boxplot: Y must be numeric
      return columns.filter((c) => c.type === 'numeric');
    }
    return columns.filter((c) => c.type === 'numeric');
  }, [columns, chartType]);

  // Reset x when it's no longer valid for the new chart type
  useEffect(() => {
    if (xOptions.length && !xOptions.find((c) => c.name === xColumn)) {
      setXColumn(xOptions[0]?.name ?? '');
    }
  }, [xOptions]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Chart type change handler ────────────────────────────
  const handleChartType = (id: string) => {
    setChartType(id);
    setXOpen(false);
    setYOpen(false);
    // If new type shows Y and current Y is empty, set default
    const def = CHART_DEFS.find((c) => c.id === id)!;
    if (def.showY && !yColumn && yOptions.length > 0) {
      setYColumn(yOptions[0].name);
    }
  };

  // ── Generate chart ────────────────────────────────────────
  const onGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (chartType !== 'heatmap' && !xColumn) return;
    setLoadingChart(true);
    setError('');
    try {
      const res = await generateVisualization({
        filename,
        chart_type: chartType,
        x_column: xColumn || (columns[0]?.name ?? ''),
        y_column: chartDef.showY && yColumn ? yColumn : undefined,
      });
      if (!res.success || !res.image) throw new Error(res.error ?? 'Generation failed');

      const title = `${chartType[0].toUpperCase() + chartType.slice(1)}${
        chartDef.showY && yColumn ? ` — ${xColumn} × ${yColumn}` : ` — ${xColumn}`
      }`;
      setImageBase64(res.image);
      setChartTitle(title);
      setChartHistory((prev) => [
        { img: res.image!, type: chartType, title },
        ...prev.slice(0, 2),
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Visualization failed');
    } finally {
      setLoadingChart(false);
    }
  };

  // ── Export handlers ───────────────────────────────────────
  const exportPNG = useCallback(() => {
    if (!imageBase64) return;
    const a = document.createElement('a');
    a.href  = `data:image/png;base64,${imageBase64}`;
    a.download = `${chartType}-chart.png`;
    a.click();
  }, [imageBase64, chartType]);

  const copyImage = useCallback(async () => {
    if (!imageBase64) return;
    try {
      const blob = await fetch(`data:image/png;base64,${imageBase64}`).then((r) => r.blob());
      await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })]);
    } catch {
      await navigator.clipboard.writeText(`data:image/png;base64,${imageBase64}`);
    }
  }, [imageBase64]);

  // ── Axis token dropdown component (DRY helper) ────────────
  const AxisToken = ({
    label,
    value,
    options,
    open,
    onOpen,
    onSelect,
    dropRef,
  }: {
    label: string;
    value: string;
    options: ColumnMeta[];
    open: boolean;
    onOpen: () => void;
    onSelect: (name: string) => void;
    dropRef: React.RefObject<HTMLDivElement>;
  }) => (
    <div className="viz-token-wrap" ref={dropRef}>
      <span className="viz-token-label">{label}</span>
      <button
        type="button"
        className={`viz-token${open ? ' viz-token--open' : ''}`}
        onClick={onOpen}
        disabled={loadingCols || options.length === 0}
      >
        <span className="viz-token-name">{value || 'select…'}</span>
        {value && (
          <span className="viz-token-dtype">
            {columns.find((c) => c.name === value)?.dtype ?? ''}
          </span>
        )}
        <ChevronDown size={11} className={`viz-token-chevron${open ? ' open' : ''}`} />
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            className="viz-drop-panel"
            initial={{ opacity: 0, y: -4, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -4, scale: 0.97 }}
            transition={{ duration: 0.14 }}
          >
            {options.map((col) => (
              <button
                key={col.name}
                type="button"
                className={`viz-drop-item${value === col.name ? ' active' : ''}`}
                onClick={() => { onSelect(col.name); }}
              >
                <span className="viz-drop-name">{col.name}</span>
                <span className="viz-drop-badge">{col.dtype}</span>
              </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );

  return (
    <section className="panel viz-panel">

      {/* ── Header ───────────────────────────────────────── */}
      <div className="viz-header">
        <div>
          <h2 className="viz-title"><em>Visualization Builder</em></h2>
          <div className="viz-title-underline" />
          <p className="viz-subtitle">{filename}</p>
        </div>
      </div>

      <form onSubmit={onGenerate}>
        {/* ── Sticky toolbar ───────────────────────────── */}
        <div className="viz-toolbar">

          {/* Chart-type pill strip */}
          <div className="viz-pill-strip" role="radiogroup" aria-label="Chart type">
            {CHART_DEFS.map((def) => (
              <button
                key={def.id}
                type="button"
                role="radio"
                aria-checked={chartType === def.id}
                className={`viz-pill${chartType === def.id ? ' viz-pill--active' : ''}`}
                onClick={() => handleChartType(def.id)}
              >
                {def.icon}
                <span>{def.label}</span>
              </button>
            ))}
          </div>

          {/* Axis controls + generate */}
          <div className="viz-toolbar-right">
            {loadingCols ? (
              <span className="viz-loading-cols">Loading columns…</span>
            ) : chartType === 'heatmap' ? (
              <span className="viz-loading-cols" style={{ color: 'var(--color-text-muted)' }}>
                Heatmap uses all numeric columns
              </span>
            ) : (
              <>
                <AxisToken
                  label="X Axis"
                  value={xColumn}
                  options={xOptions}
                  open={xOpen}
                  onOpen={() => { setXOpen((p) => !p); setYOpen(false); }}
                  onSelect={(n) => { setXColumn(n); setXOpen(false); }}
                  dropRef={xDropRef}
                />

                {chartDef.showY && (
                  <AxisToken
                    label="Y Axis"
                    value={yColumn}
                    options={yOptions}
                    open={yOpen}
                    onOpen={() => { setYOpen((p) => !p); setXOpen(false); }}
                    onSelect={(n) => { setYColumn(n); setYOpen(false); }}
                    dropRef={yDropRef}
                  />
                )}
              </>
            )}

            <button
              type="submit"
              className="btn btn-primary viz-gen-btn"
              disabled={loadingChart || (chartType !== 'heatmap' && !xColumn) || loadingCols}
            >
              {loadingChart ? (
                <><RefreshCw size={13} className="viz-spin" /> Generating…</>
              ) : (
                <><BarChart2 size={13} /> Generate</>
              )}
            </button>
          </div>
        </div>

        {error && (
          <motion.div
            className="error-banner"
            style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 12 }}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <AlertCircle size={14} /> {error}
          </motion.div>
        )}
      </form>

      {/* ── Chart area ───────────────────────────────────── */}
      <AnimatePresence mode="wait">
        {imageBase64 ? (
          <motion.div
            key="chart"
            className="viz-canvas-wrap"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35 }}
          >
            <div className="viz-canvas-area">
              {/* Editable title */}
              <div
                ref={titleRef}
                className="viz-chart-title"
                contentEditable
                suppressContentEditableWarning
                onBlur={(e) => setChartTitle(e.currentTarget.textContent ?? '')}
              />

              {/* Graph-paper canvas */}
              <div className="viz-chart-paper">
                <img
                  src={`data:image/png;base64,${imageBase64}`}
                  alt={chartTitle}
                  className="viz-chart-img"
                />
              </div>
            </div>

            {/* Export + history strip */}
            <div className="viz-export-strip">
              <div className="viz-export-btns">
                <button type="button" className="viz-export-btn" onClick={exportPNG}>
                  <Download size={11} /> PNG
                </button>
                <button type="button" className="viz-export-btn" onClick={copyImage}>
                  <Copy size={11} /> Copy
                </button>
              </div>

              {chartHistory.length > 1 && (
                <div className="viz-history">
                  <span className="viz-history-label">
                    <Clock size={11} /> History
                  </span>
                  {chartHistory.map((h, i) => (
                    <button
                      key={i}
                      type="button"
                      className={`viz-history-thumb${i === 0 ? ' active' : ''}`}
                      onClick={() => {
                        setImageBase64(h.img);
                        setChartTitle(h.title);
                        setChartType(h.type);
                      }}
                      title={h.title}
                    >
                      <img
                        src={`data:image/png;base64,${h.img}`}
                        alt={`History ${i + 1}`}
                      />
                    </button>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        ) : !loadingChart ? (
          <motion.div
            key="empty"
            className="viz-empty"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            <BarChart2 size={36} className="viz-empty-icon" />
            <p>Configure the options above and click <strong>Generate</strong></p>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </section>
  );
}
