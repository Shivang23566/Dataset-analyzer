export type SignupPayload = {
  email: string;
  password: string;
};

export type LoginPayload = {
  email: string;
  password: string;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
};

export type UploadedFileResponse = {
  message: string;
  saved_as: string;
};

export type EdaResponse = {
  shape: { rows: number; columns: number };
  column_info: Record<string, { dtype: string; missing_pct: number; unique: number }>;
  numeric_summary: Record<string, { mean: number; median: number; std: number; min: number; max: number }>;
  correlation_matrix: Record<string, Record<string, number | null>>;
  missing_summary: { total_missing: number };
};

export type ColumnMeta = {
  name: string;
  type: 'numeric' | 'categorical' | 'datetime';
  dtype: string;
};

export type ColumnResponse = {
  columns: ColumnMeta[];
  numeric_columns: string[];
  categorical_columns: string[];
  datetime_columns?: string[];
};

export type VisualizationResponse = {
  success: boolean;
  image?: string;
  chart_type?: string;
  error?: string;
  code?: string;
};

// ── Preprocessing Types ──────────────────────────────────────

export type MissingColInfo = {
  pct: number;
  color: 'green' | 'yellow' | 'red';
  count: number;
};

export type DatasetHealthResponse = {
  rows: number;
  columns: number;
  memory_mb: number;
  dtype_breakdown: { numeric: number; categorical: number; datetime: number; boolean: number };
  missing_per_col: Record<string, MissingColInfo>;
  duplicate_count: number;
  constant_columns: string[];
  near_constant_columns: string[];
  skewness_summary: Record<string, number>;
  kurtosis_summary: Record<string, number>;
  cardinality: Record<string, number>;
};

export type PreprocessColumnMeta = {
  name: string;
  dtype: string;
  missing_pct: number;
  nunique: number;
};

export type PreprocessColumnsResponse = {
  columns: PreprocessColumnMeta[];
};

export type PipelineStepResult = Record<string, unknown>;

export type DatasetStats = {
  rows: number;
  columns: number;
  memory_mb: number;
  total_missing: number;
  dtype_counts: Record<string, number>;
};

export type PipelineRunResponse = {
  success: boolean;
  steps: Record<string, PipelineStepResult>;
  before_stats: DatasetStats;
  after_stats: DatasetStats;
  preview: Record<string, unknown>[];
  columns: Array<{ name: string; dtype: string }>;
  session_key: string;
};

// ── ML Types ─────────────────────────────────────────────────

export type MLColumnMeta = {
  name: string;
  dtype: string;
  is_numeric: boolean;
  n_unique: number;
};

export type TaskDetectResponse = {
  task: 'binary_classification' | 'multiclass_classification' | 'regression' | 'clustering' | 'unknown';
  n_classes?: number;
  class_labels?: string[];
  target_range?: [number, number];
};

export type ModelRecommendation = {
  recommended_model: string;
  reason: string;
  analysis_factors: string[];
  dataset_summary: {
    n_samples: number;
    n_features: number;
    has_mixed_features: boolean;
    is_imbalanced: boolean;
    high_dimensionality: boolean;
    missing_ratio: number;
  };
  task_info: TaskDetectResponse;
};

export type HyperparmDef = {
  type: 'float' | 'int' | 'bool' | 'select';
  default: unknown;
  min?: number;
  max?: number;
  options?: string[];
  label: string;
  tooltip?: string;
};

export type ModelCard = {
  id: string;
  name: string;
  icon: string;
  best_for: string;
  pros: string[];
  cons: string[];
  interpretability: number;
  speed: number;
  hyperparams: Record<string, HyperparmDef>;
};

export type ConfusionMatrix = {
  matrix: number[][];
  labels: string[];
};

export type RocCurve = {
  fpr: number[];
  tpr: number[];
  auc: number;
};

export type ResidualPlot = {
  y_pred: number[];
  residuals: number[];
  y_actual: number[];
};

export type FeatureImportance = {
  feature: string;
  importance: number;
};

export type TrainingResult = {
  success: boolean;
  session_key: string;
  model_id: string;
  task: string;
  training_time_seconds: number;
  cv_score_mean?: number;
  cv_score_std?: number;
  cv_metric?: string;
  best_params?: Record<string, unknown>;
  metrics: Record<string, number | Record<string, unknown>>;
  plots?: {
    confusion_matrix?: ConfusionMatrix;
    roc_curve?: RocCurve;
    pr_curve?: { precision: number[]; recall: number[]; avg_precision: number };
    residual_plot?: ResidualPlot;
  };
  feature_importance: FeatureImportance[];
  n_train_samples?: number;
  n_test_samples?: number;
  cluster_distribution?: Record<string, number>;
  n_clusters?: number;
  visualization_data?: Array<{ x: number; y: number; cluster: number }>;
};

