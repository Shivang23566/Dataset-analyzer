import { useState, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  BarChart2,
  TrendingUp,
  Activity,
  PieChart,
  Layers,
  AlignLeft,
  Download,
  RefreshCw,
  ChevronDown,
  AlertCircle,
  Grid3x3,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  ScatterChart,
  Scatter,
  PieChart as RechartsPieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { getColumns, generateVisualization } from '../lib/api';
import type { DatasetColumn } from '../lib/types';
import { extractErrorMessage } from '../lib/errorUtils';

// ═══════════════════════════════════════════════════════════════
// TYPES & CONSTANTS
// ═══════════════════════════════════════════════════════════════

type VisualizationViewProps = {
  filename: string;
};

type ColumnType = 'quantitative' | 'categorical' | 'datetime';

interface ParsedColumn {
  name: string;
  type: ColumnType;
  dtype: string;
}

interface ChartConfig {
  id: string;
  label: string;
  icon: React.ReactNode;
  xAccepts: ColumnType[];
  yAccepts: ColumnType[];
  yLabel: string;
  hideYAxis?: boolean;
}

const CHART_CONFIGS: ChartConfig[] = [
  {
    id: 'bar',
    label: 'Bar',
    icon: <BarChart2 size={14} />,
    xAccepts: ['categorical'],
    yAccepts: ['quantitative'],
    yLabel: 'Select Y Axis',
  },
  {
    id: 'line',
    label: 'Line',
    icon: <TrendingUp size={14} />,
    xAccepts: ['datetime', 'quantitative'],
    yAccepts: ['quantitative'],
    yLabel: 'Select Y Axis',
  },
  {
    id: 'scatter',
    label: 'Scatter',
    icon: <Activity size={14} />,
    xAccepts: ['quantitative'],
    yAccepts: ['quantitative'],
    yLabel: 'Select Y Axis',
  },
  {
    id: 'histogram',
    label: 'Histogram',
    icon: <AlignLeft size={14} />,
    xAccepts: ['quantitative'],
    yAccepts: [],
    yLabel: 'Frequency',
    hideYAxis: true,
  },
  {
    id: 'pie',
    label: 'Pie',
    icon: <PieChart size={14} />,
    xAccepts: ['categorical'],
    yAccepts: ['quantitative'],
    yLabel: 'Select Value',
  },
  {
    id: 'boxplot',
    label: 'Box Plot',
    icon: <Layers size={14} />,
    xAccepts: ['categorical'],
    yAccepts: ['quantitative'],
    yLabel: 'Select Y Axis',
  },
  {
    id: 'heatmap',
    label: 'Heatmap',
    icon: <Grid3x3 size={14} />,
    xAccepts: ['categorical'],
    yAccepts: ['categorical'],
    yLabel: 'Select Y Axis',
  },
];

const CHART_COLORS = ['#2eb8a0', '#c9a84c', '#b8973f', '#10B981', '#F59E0B', '#F43F5E'];

type AggregationType = 'sum' | 'avg' | 'count' | 'max' | 'min';

// ═══════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════

export default function VisualizationView({ filename }: VisualizationViewProps) {
  // State
  const [columns, setColumns] = useState<ParsedColumn[]>([]);
  const [rawData, setRawData] = useState<any[]>([]);
  const [chartType, setChartType] = useState('bar');
  const [xColumn, setXColumn] = useState('');
  const [yColumn, setYColumn] = useState('');
  const [aggregation, setAggregation] = useState<AggregationType>('sum');
  const [loading, setLoading] = useState(false);
  const [loadingChart, setLoadingChart] = useState(false);
  const [error, setError] = useState('');
  const [chartGenerated, setChartGenerated] = useState(false);
  const [generatedChartImage, setGeneratedChartImage] = useState(''); // Backend-generated chart
  const [xDropdownOpen, setXDropdownOpen] = useState(false);
  const [yDropdownOpen, setYDropdownOpen] = useState(false);

  const chartConfig = CHART_CONFIGS.find((c) => c.id === chartType) ?? CHART_CONFIGS[0];

  // ═══════════════════════════════════════════════════════════════
  // DATA LOADING & COLUMN PARSING
  // ═══════════════════════════════════════════════════════════════

  useEffect(() => {
    let cancelled = false;

    const loadData = async () => {
      setLoading(true);
      setError('');
      setChartGenerated(false);

      try {
        console.log('[VisualizationView] Loading columns for:', filename);
        const response = await getColumns(filename);
        if (cancelled) return;

        console.log('[VisualizationView] Received columns:', response.columns?.length);

        // BUG FIX 1: Parse columns and infer types
        const parsedColumns: ParsedColumn[] = response.columns.map((col: DatasetColumn) => {
          let inferredType: ColumnType = 'categorical';

          if (col.inferred_type === 'numeric') {
            inferredType = 'quantitative';
          } else if (col.inferred_type === 'datetime') {
            inferredType = 'datetime';
          } else if (
            col.inferred_type === 'categorical' ||
            col.inferred_type === 'high_cardinality'
          ) {
            inferredType = 'categorical';
          }

          return {
            name: col.column_name,
            type: inferredType,
            dtype: col.dtype,
          };
        });

        console.log('[VisualizationView] Parsed columns:', parsedColumns);
        setColumns(parsedColumns);

        // Store raw preview data if available
        if (response.preview_data) {
          setRawData(response.preview_data);
        }

        // BUG FIX 1: Set default X and Y based on CURRENT chart type
        const currentConfig = CHART_CONFIGS.find((c) => c.id === chartType) ?? CHART_CONFIGS[0];
        const firstValidX = parsedColumns.find((c) => currentConfig.xAccepts.includes(c.type));
        const firstValidY = parsedColumns.find((c) => currentConfig.yAccepts.includes(c.type));

        console.log('[VisualizationView] Auto-selected X:', firstValidX?.name, 'Y:', firstValidY?.name);

        if (firstValidX) {
          setXColumn(firstValidX.name);
        } else {
          console.warn('[VisualizationView] No valid X column found for chart type:', chartType);
          setXColumn('');
        }

        if (firstValidY && !currentConfig.hideYAxis) {
          setYColumn(firstValidY.name);
        } else if (!currentConfig.hideYAxis) {
          console.warn('[VisualizationView] No valid Y column found for chart type:', chartType);
          setYColumn('');
        }
      } catch (err: unknown) {
        if (!cancelled) {
          console.error('[VisualizationView] Error loading columns:', err);
          setError(extractErrorMessage(err));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    loadData();

    return () => {
      cancelled = true;
    };
  }, [filename, chartType]);

  // ═══════════════════════════════════════════════════════════════
  // FILTERED OPTIONS FOR DROPDOWNS
  // ═══════════════════════════════════════════════════════════════

  const xOptions = useMemo(() => {
    const options = columns.filter((c) => chartConfig.xAccepts.includes(c.type));
    console.log('[VisualizationView] X Options filtered:', options.length, 'from', columns.length, 'columns for chart type', chartConfig.id);
    console.log('[VisualizationView] X Options:', options.map(o => `${o.name}(${o.type})`).join(', '));
    return options;
  }, [columns, chartConfig]);

  const yOptions = useMemo(() => {
    if (chartConfig.hideYAxis) return [];
    const options = columns.filter((c) => chartConfig.yAccepts.includes(c.type));
    console.log('[VisualizationView] Y Options filtered:', options.length, 'from', columns.length, 'columns for chart type', chartConfig.id);
    console.log('[VisualizationView] Y Options:', options.map(o => `${o.name}(${o.type})`).join(', '));
    return options;
  }, [columns, chartConfig]);

  // Auto-select first valid option when chart type changes
  useEffect(() => {
    console.log('[VisualizationView] Chart type changed to:', chartType);
    console.log('[VisualizationView] Current X:', xColumn, 'Y:', yColumn);
    console.log('[VisualizationView] Available columns:', columns.length);
    console.log('[VisualizationView] X Options count:', xOptions.length, 'Y Options count:', yOptions.length);
    console.log('[VisualizationView] xOptions:', xOptions.length, 'yOptions:', yOptions.length);

    if (xOptions.length > 0 && !xOptions.find((c) => c.name === xColumn)) {
      const newX = xOptions[0].name;
      console.log('[VisualizationView] Auto-selecting new X:', newX);
      setXColumn(newX);
    }
    if (yOptions.length > 0 && !yOptions.find((c) => c.name === yColumn)) {
      const newY = yOptions[0].name;
      console.log('[VisualizationView] Auto-selecting new Y:', newY);
      setYColumn(newY);
    }
    // Clear chart when type changes
    setChartGenerated(false);
    setGeneratedChartImage('');
  }, [chartType, xOptions, yOptions]);

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as HTMLElement;
      if (!target.closest('.viz-dropdown')) {
        setXDropdownOpen(false);
        setYDropdownOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // ═══════════════════════════════════════════════════════════════
  // CHART GENERATION
  // ═══════════════════════════════════════════════════════════════

  const handleGenerate = async () => {
    // BUG FIX 1: Frontend validation guard
    if (!xColumn || xColumn.trim() === '') {
      setError('Please select an X axis column');
      console.error('[VisualizationView] Generate blocked: X column is empty');
      return;
    }

    if (!chartConfig.hideYAxis && (!yColumn || yColumn.trim() === '')) {
      setError('Please select a Y axis column');
      console.error('[VisualizationView] Generate blocked: Y column is empty');
      return;
    }

    console.log('[VisualizationView] Generating chart:', {
      chartType,
      xColumn,
      yColumn,
      filename,
    });

    setLoadingChart(true);
    setError('');

    try {
      // Actually call the backend API to generate visualization
      const result = await generateVisualization({
        filename: filename,
        chart_type: chartType,
        x_column: xColumn,
        y_column: yColumn || undefined,
      });

      if (result.success) {
        console.log('[VisualizationView] Chart generated successfully');
        setGeneratedChartImage(result.image || '');
        setChartGenerated(true);
      } else {
        const errorMsg = result.error || 'Failed to generate chart';
        console.error('[VisualizationView] Generation failed:', errorMsg);
        setError(errorMsg);
      }
    } catch (err: unknown) {
      const errorMsg = extractErrorMessage(err);
      console.error('[VisualizationView] Generation error:', err);
      setError(errorMsg);
    } finally {
      setLoadingChart(false);
    }
  };

  // ═══════════════════════════════════════════════════════════════
  // CHART DATA PREPARATION
  // ═══════════════════════════════════════════════════════════════

  const prepareChartData = () => {
    if (!rawData || rawData.length === 0) {
      // Generate sample data for demonstration
      return generateSampleData();
    }

    // Process real data based on chart type
    switch (chartType) {
      case 'bar':
        return prepareBarData(rawData);
      case 'line':
        return prepareLineData(rawData);
      case 'scatter':
        return prepareScatterData(rawData);
      case 'histogram':
        return rawData; // Will be binned in prepareHistogramData
      case 'pie':
        return preparePieData(rawData);
      default:
        return rawData.slice(0, 20);
    }
  };

  const prepareBarData = (data: any[]) => {
    // Group by X column and aggregate Y column
    const grouped: Record<string, number[]> = {};
    
    data.forEach((row) => {
      const xVal = String(row[xColumn]);
      const yVal = parseFloat(row[yColumn]);
      
      if (!isNaN(yVal)) {
        if (!grouped[xVal]) {
          grouped[xVal] = [];
        }
        grouped[xVal].push(yVal);
      }
    });

    // Aggregate and sort by value
    const result = Object.entries(grouped)
      .map(([key, values]) => ({
        [xColumn]: key,
        [yColumn]: values.reduce((a, b) => a + b, 0) / values.length, // Average
      }))
      .sort((a, b) => (b[yColumn] as number) - (a[yColumn] as number))
      .slice(0, 15); // Top 15

    return result;
  };

  const prepareLineData = (data: any[]) => {
    // Sort by X axis
    const sorted = data
      .filter((row) => row[xColumn] !== null && row[yColumn] !== null)
      .map((row) => ({
        [xColumn]: row[xColumn],
        [yColumn]: parseFloat(row[yColumn]) || 0,
      }))
      .slice(0, 50); // Limit for performance

    return sorted;
  };

  const prepareScatterData = (data: any[]) => {
    return data
      .filter((row) => {
        const xVal = parseFloat(row[xColumn]);
        const yVal = parseFloat(row[yColumn]);
        return !isNaN(xVal) && !isNaN(yVal);
      })
      .map((row) => ({
        [xColumn]: parseFloat(row[xColumn]),
        [yColumn]: parseFloat(row[yColumn]),
      }))
      .slice(0, 100); // Limit to 100 points
  };

  const preparePieData = (data: any[]) => {
    // Group by X column and sum Y values
    const grouped: Record<string, number> = {};
    
    data.forEach((row) => {
      const xVal = String(row[xColumn]);
      const yVal = parseFloat(row[yColumn]);
      
      if (!isNaN(yVal)) {
        grouped[xVal] = (grouped[xVal] || 0) + yVal;
      }
    });

    // Sort and take top 8
    return Object.entries(grouped)
      .map(([key, value]) => ({
        [xColumn]: key,
        [yColumn]: value,
      }))
      .sort((a, b) => (b[yColumn] as number) - (a[yColumn] as number))
      .slice(0, 8);
  };

  const generateSampleData = () => {
    const data: any[] = [];
    const numPoints = chartType === 'pie' ? 5 : chartType === 'histogram' ? 50 : 12;

    for (let i = 0; i < numPoints; i++) {
      const xValue =
        chartType === 'histogram' || chartType === 'scatter'
          ? Math.random() * 100
          : chartType === 'pie' || chartType === 'bar' || chartType === 'boxplot' || chartType === 'heatmap'
          ? `Category ${String.fromCharCode(65 + i)}`
          : i * 10;

      data.push({
        [xColumn]: xValue,
        [yColumn]: Math.random() * 80 + 20,
      });
    }

    return data;
  };

  const chartData = useMemo(() => {
    if (!chartGenerated) return [];
    return prepareChartData();
  }, [chartGenerated, xColumn, yColumn, rawData, chartType]);

  // ═══════════════════════════════════════════════════════════════
  // DOWNLOAD HANDLER
  // ═══════════════════════════════════════════════════════════════

  const handleDownload = () => {
    if (!generatedChartImage) {
      console.warn('[VisualizationView] No chart image to download');
      return;
    }

    try {
      const link = document.createElement('a');
      link.href = `data:image/png;base64,${generatedChartImage}`;
      link.download = `${chartType}-${xColumn}-chart.png`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      console.log('[VisualizationView] Chart downloaded successfully');
    } catch (err) {
      console.error('[VisualizationView] Download failed:', err);
      setError('Failed to download chart');
    }
  };

  // ═══════════════════════════════════════════════════════════════
  // CHART RENDERING FUNCTIONS
  // ═══════════════════════════════════════════════════════════════

  const renderChart = () => {
    if (!chartGenerated) {
      return (
        <div className="viz-empty">
          <BarChart2 size={48} className="viz-empty-icon" />
          <p className="viz-empty-text">
            Configure the options above and click <strong>Generate</strong>
          </p>
        </div>
      );
    }

    // If we have a backend-generated image, show it
    if (generatedChartImage) {
      return (
        <div style={{ width: '100%', display: 'flex', justifyContent: 'center', padding: '20px' }}>
          <img
            src={`data:image/png;base64,${generatedChartImage}`}
            alt="Generated Chart"
            style={{
              maxWidth: '100%',
              height: 'auto',
              borderRadius: '12px',
              boxShadow: '0 4px 6px rgba(0, 0, 0, 0.3)',
            }}
          />
        </div>
      );
    }

    // Otherwise show "chart data not available" (chartData might be empty)
    if (chartData.length === 0) {
      return (
        <div className="viz-empty">
          <AlertCircle size={48} className="viz-empty-icon" />
          <p className="viz-empty-text">No data available to display</p>
        </div>
      );
    }

    const commonProps = {
      data: chartData,
      margin: { top: 20, right: 30, left: 20, bottom: 60 },
    };

    switch (chartType) {
      case 'bar':
        return (
          <ResponsiveContainer width="100%" height={500}>
            <BarChart {...commonProps}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1F2A3D" opacity={0.3} />
              <XAxis
                dataKey={xColumn}
                tick={{ fill: '#8B9CB8', fontSize: 12 }}
                angle={-45}
                textAnchor="end"
                height={80}
              />
              <YAxis tick={{ fill: '#8B9CB8', fontSize: 12 }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#0D1221',
                  border: '1px solid #1F2A3D',
                  borderRadius: '8px',
                  color: '#EFF2F7',
                }}
              />
              <Legend wrapperStyle={{ paddingTop: '20px' }} />
              <Bar dataKey={yColumn} fill={CHART_COLORS[0]} radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        );

      case 'line':
        return (
          <ResponsiveContainer width="100%" height={500}>
            <LineChart {...commonProps}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1F2A3D" opacity={0.3} />
              <XAxis
                dataKey={xColumn}
                tick={{ fill: '#8B9CB8', fontSize: 12 }}
                angle={-45}
                textAnchor="end"
                height={80}
              />
              <YAxis tick={{ fill: '#8B9CB8', fontSize: 12 }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#0D1221',
                  border: '1px solid #1F2A3D',
                  borderRadius: '8px',
                  color: '#EFF2F7',
                }}
              />
              <Legend wrapperStyle={{ paddingTop: '20px' }} />
              <Line
                type="monotone"
                dataKey={yColumn}
                stroke={CHART_COLORS[0]}
                strokeWidth={3}
                dot={{ fill: CHART_COLORS[1], r: 5 }}
                activeDot={{ r: 8 }}
              />
            </LineChart>
          </ResponsiveContainer>
        );

      case 'scatter':
        return (
          <ResponsiveContainer width="100%" height={500}>
            <ScatterChart {...commonProps}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1F2A3D" opacity={0.3} />
              <XAxis
                dataKey={xColumn}
                type="number"
                tick={{ fill: '#8B9CB8', fontSize: 12 }}
                name={xColumn}
              />
              <YAxis
                dataKey={yColumn}
                type="number"
                tick={{ fill: '#8B9CB8', fontSize: 12 }}
                name={yColumn}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#0D1221',
                  border: '1px solid #1F2A3D',
                  borderRadius: '8px',
                  color: '#EFF2F7',
                }}
                cursor={{ strokeDasharray: '3 3' }}
              />
              <Legend wrapperStyle={{ paddingTop: '20px' }} />
              <Scatter name={`${yColumn} vs ${xColumn}`} fill={CHART_COLORS[0]} />
            </ScatterChart>
          </ResponsiveContainer>
        );

      case 'histogram':
        // For histogram, we need to bin the data
        const histogramData = prepareHistogramData(chartData, xColumn);
        return (
          <ResponsiveContainer width="100%" height={500}>
            <BarChart
              data={histogramData}
              margin={{ top: 20, right: 30, left: 20, bottom: 60 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#1F2A3D" opacity={0.3} />
              <XAxis
                dataKey="bin"
                tick={{ fill: '#8B9CB8', fontSize: 12 }}
                angle={-45}
                textAnchor="end"
                height={80}
                label={{
                  value: xColumn,
                  position: 'insideBottom',
                  offset: -10,
                  fill: '#EFF2F7',
                }}
              />
              <YAxis
                tick={{ fill: '#8B9CB8', fontSize: 12 }}
                label={{
                  value: 'Frequency',
                  angle: -90,
                  position: 'insideLeft',
                  fill: '#EFF2F7',
                }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#0D1221',
                  border: '1px solid #1F2A3D',
                  borderRadius: '8px',
                  color: '#EFF2F7',
                }}
              />
              <Bar dataKey="frequency" fill={CHART_COLORS[2]} radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        );

      case 'pie':
        return (
          <ResponsiveContainer width="100%" height={500}>
            <RechartsPieChart>
              <Pie
                data={chartData.slice(0, 8)} // Limit to 8 slices
                dataKey={yColumn}
                nameKey={xColumn}
                cx="50%"
                cy="50%"
                outerRadius={150}
                label={(entry: any) => `${entry[xColumn]}: ${entry[yColumn].toFixed(1)}`}
                labelLine={{ stroke: '#8B9CB8' }}
              >
                {chartData.slice(0, 8).map((_, index) => (
                  <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: '#0D1221',
                  border: '1px solid #1F2A3D',
                  borderRadius: '8px',
                  color: '#EFF2F7',
                }}
              />
              <Legend />
            </RechartsPieChart>
          </ResponsiveContainer>
        );

      case 'boxplot':
        // Boxplot requires custom implementation or different library
        // For now, show message
        return (
          <div className="viz-empty">
            <Layers size={48} className="viz-empty-icon" />
            <p className="viz-empty-text">Box Plot visualization requires backend processing</p>
          </div>
        );

      case 'heatmap':
        // Heatmap requires matrix data and custom implementation
        return (
          <div className="viz-empty">
            <Grid3x3 size={48} className="viz-empty-icon" />
            <p className="viz-empty-text">Heatmap visualization requires backend processing</p>
          </div>
        );

      default:
        return null;
    }
  };

  const prepareHistogramData = (data: any[], column: string) => {
    const values = data.map((d) => parseFloat(d[column])).filter((v) => !isNaN(v));
    const min = Math.min(...values);
    const max = Math.max(...values);
    const binCount = 10;
    const binSize = (max - min) / binCount;

    const bins = Array.from({ length: binCount }, (_, i) => ({
      bin: `${(min + i * binSize).toFixed(1)}-${(min + (i + 1) * binSize).toFixed(1)}`,
      frequency: 0,
    }));

    values.forEach((value) => {
      const binIndex = Math.min(Math.floor((value - min) / binSize), binCount - 1);
      bins[binIndex].frequency++;
    });

    return bins;
  };

  // ═══════════════════════════════════════════════════════════════
  // RENDER
  // ═══════════════════════════════════════════════════════════════

  return (
    <section className="panel viz-panel">
      {/* Header */}
      <div className="viz-header">
        <div>
          <h2 className="viz-title">
            <em>Visualization Builder</em>
          </h2>
          <div className="viz-title-underline" />
          <p className="viz-subtitle">{filename}</p>
        </div>
      </div>

      {/* Toolbar */}
      <div className="viz-toolbar">
        {/* Chart Type Selector */}
        <div className="viz-pill-strip" role="radiogroup" aria-label="Chart type">
          {CHART_CONFIGS.map((config) => (
            <button
              key={config.id}
              type="button"
              role="radio"
              aria-checked={chartType === config.id}
              className={`viz-pill${chartType === config.id ? ' viz-pill--active' : ''}`}
              onClick={() => setChartType(config.id)}
            >
              {config.icon}
              <span>{config.label}</span>
            </button>
          ))}
        </div>

        {/* Axis Controls */}
        <div className="viz-toolbar-right">
          {loading ? (
            <span className="viz-loading-cols">Loading columns…</span>
          ) : columns.length === 0 ? (
            <span className="viz-loading-cols" style={{ color: '#F43F5E' }}>
              Failed to load columns - check console
            </span>
          ) : xOptions.length === 0 ? (
            <span className="viz-loading-cols" style={{ color: '#F59E0B' }}>
              No valid columns for {chartConfig.label} chart (needs {chartConfig.xAccepts.join('/')})
            </span>
          ) : (
            <>
              {/* X Axis Dropdown */}
              <div className="viz-token-wrap">
                <span className="viz-token-label">X Axis</span>
                <div className="viz-dropdown">
                  <button
                    type="button"
                    className={`viz-token${xDropdownOpen ? ' viz-token--open' : ''}`}
                    onClick={() => {
                      setXDropdownOpen(!xDropdownOpen);
                      setYDropdownOpen(false);
                    }}
                    disabled={xOptions.length === 0}
                  >
                    <span className="viz-token-name">{xColumn || 'Select…'}</span>
                    {xColumn && (
                      <span className="viz-token-dtype">
                        {columns.find((c) => c.name === xColumn)?.dtype || ''}
                      </span>
                    )}
                    <ChevronDown
                      size={11}
                      className={`viz-token-chevron${xDropdownOpen ? ' open' : ''}`}
                    />
                  </button>
                  <AnimatePresence>
                    {xDropdownOpen && (
                      <motion.div
                        className="viz-drop-panel"
                        initial={{ opacity: 0, y: -4, scale: 0.97 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: -4, scale: 0.97 }}
                        transition={{ duration: 0.14 }}
                      >
                        {xOptions.map((col) => (
                          <button
                            key={col.name}
                            type="button"
                            className={`viz-drop-item${xColumn === col.name ? ' active' : ''}`}
                            onClick={() => {
                              console.log('[VisualizationView] User selected X column:', col.name);
                              setXColumn(col.name);
                              setXDropdownOpen(false);
                              setChartGenerated(false);
                              setGeneratedChartImage('');
                            }}
                          >
                            <span className="viz-drop-name">{col.name}</span>
                            <span className="viz-drop-badge">{col.dtype}</span>
                          </button>
                        ))}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              </div>

              {/* Y Axis Dropdown */}
              {!chartConfig.hideYAxis && (
                <div className="viz-token-wrap">
                  <span className="viz-token-label">{chartConfig.yLabel}</span>
                  <div className="viz-dropdown">
                    <button
                      type="button"
                      className={`viz-token${yDropdownOpen ? ' viz-token--open' : ''}`}
                      onClick={() => {
                        setYDropdownOpen(!yDropdownOpen);
                        setXDropdownOpen(false);
                      }}
                      disabled={yOptions.length === 0}
                    >
                      <span className="viz-token-name">{yColumn || 'Select…'}</span>
                      {yColumn && (
                        <span className="viz-token-dtype">
                          {columns.find((c) => c.name === yColumn)?.dtype || ''}
                        </span>
                      )}
                      <ChevronDown
                        size={11}
                        className={`viz-token-chevron${yDropdownOpen ? ' open' : ''}`}
                      />
                    </button>
                    <AnimatePresence>
                      {yDropdownOpen && (
                        <motion.div
                          className="viz-drop-panel"
                          initial={{ opacity: 0, y: -4, scale: 0.97 }}
                          animate={{ opacity: 1, y: 0, scale: 1 }}
                          exit={{ opacity: 0, y: -4, scale: 0.97 }}
                          transition={{ duration: 0.14 }}
                        >
                          {yOptions.map((col) => (
                            <button
                              key={col.name}
                              type="button"
                              className={`viz-drop-item${yColumn === col.name ? ' active' : ''}`}
                              onClick={() => {
                                console.log('[VisualizationView] User selected Y column:', col.name);
                                setYColumn(col.name);
                                setYDropdownOpen(false);
                                setGeneratedChartImage('');
                                setChartGenerated(false);
                              }}
                            >
                              <span className="viz-drop-name">{col.name}</span>
                              <span className="viz-drop-badge">{col.dtype}</span>
                            </button>
                          ))}
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                </div>
              )}
            </>
          )}

          {/* Generate Button */}
          <button
            type="button"
            className="btn btn-primary viz-gen-btn"
            onClick={handleGenerate}
            disabled={
              loading ||
              loadingChart ||
              !xColumn ||
              xColumn.trim() === '' ||
              (!chartConfig.hideYAxis && (!yColumn || yColumn.trim() === ''))
            }
            title={
              !xColumn || xColumn.trim() === ''
                ? 'Please select X axis column'
                : !chartConfig.hideYAxis && (!yColumn || yColumn.trim() === '')
                ? 'Please select Y axis column'
                : ''
            }
          >
            {loadingChart ? (
              <>
                <RefreshCw size={13} className="viz-spin" /> Generating…
              </>
            ) : (
              <>
                <BarChart2 size={13} /> Generate
              </>
            )}
          </button>
        </div>
      </div>

      {/* Error Display */}
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

      {/* Chart Area */}
      <div className="viz-canvas-wrap" style={{ minHeight: '400px', marginTop: '24px' }}>
        <AnimatePresence mode="wait">
          {loadingChart ? (
            <motion.div
              key="loading"
              className="viz-empty"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <RefreshCw size={48} className="viz-empty-icon viz-spin" />
              <p className="viz-empty-text">Generating chart...</p>
            </motion.div>
          ) : (
            <motion.div
              key="chart"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.35 }}
              style={{ width: '100%' }}
            >
              {renderChart()}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Download Button */}
        {chartGenerated && generatedChartImage && !loadingChart && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="viz-export-strip"
          >
            <div className="viz-export-btns">
              <button type="button" className="viz-export-btn" onClick={handleDownload}>
                <Download size={11} /> Download PNG
              </button>
            </div>
          </motion.div>
        )}
      </div>
    </section>
  );
}
