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
  type: 'numeric' | 'categorical';
  dtype: string;
};

export type ColumnResponse = {
  columns: ColumnMeta[];
  numeric_columns: string[];
  categorical_columns: string[];
};

export type VisualizationResponse = {
  success: boolean;
  image?: string;
  chart_type?: string;
  error?: string;
  code?: string;
};
