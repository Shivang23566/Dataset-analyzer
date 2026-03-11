import { clearAuth, getToken, saveAuth } from './authStore';
import type {
  ColumnResponse,
  CouponResponse,
  DashboardDataset,
  DashboardDownload,
  DashboardSession,
  DashboardSummary,
  DatasetHealthResponse,
  EdaResponse,
  LoginPayload,
  MLColumnMeta,
  ModelCard,
  ModelRecommendation,
  PaymentStatus,
  PipelineRunResponse,
  PreprocessColumnsResponse,
  ProfileData,
  SignupPayload,
  SubscriptionData,
  TaskDetectResponse,
  TokenResponse,
  TrainingResult,
  UploadedFileResponse,
  VisualizationResponse,
} from './types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

// Simple response cache to avoid redundant fetches on tab switches (TTL: 30s)
const _cache = new Map<string, { data: unknown; ts: number }>();
const CACHE_TTL_MS = 30_000;

function getCached<T>(key: string): T | undefined {
  const entry = _cache.get(key);
  if (entry && Date.now() - entry.ts < CACHE_TTL_MS) return entry.data as T;
  _cache.delete(key);
  return undefined;
}

function setCache(key: string, data: unknown) {
  _cache.set(key, { data, ts: Date.now() });
}

async function request<T>(path: string, init?: RequestInit, auth = false): Promise<T> {
  const headers = new Headers(init?.headers ?? {});

  if (auth) {
    const token = getToken();
    if (!token) {
      throw new Error('Not authenticated. Please login again.');
    }
    headers.set('Authorization', `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
  });

  if (!response.ok) {
    // Auto-logout on 401 (token expired or invalid)
    if (response.status === 401 && auth) {
      clearAuth();
      window.location.href = '/login';
      throw new Error('Session expired. Please login again.');
    }

    const text = await response.text();
    let message = text || `Request failed: ${response.status}`;

    try {
      const parsed = JSON.parse(text) as { detail?: string | Array<{ msg: string }> | { message?: string; error?: string } };
      if (parsed?.detail) {
        if (Array.isArray(parsed.detail)) {
          message = parsed.detail.map((d) => d.msg).join(', ');
        } else if (typeof parsed.detail === 'string') {
          message = parsed.detail;
        } else if (typeof parsed.detail === 'object' && parsed.detail !== null) {
          const det = parsed.detail as { message?: string; error?: string };
          message = det.message || det.error || JSON.stringify(parsed.detail);
        }
      }
    } catch {
      // Non-JSON error payloads fallback to raw text.
    }

    throw new Error(message);
  }

  return (await response.json()) as T;
}

export async function backendSignup(payload: SignupPayload) {
  return request('/auth/signup', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export async function backendLogin(payload: LoginPayload) {
  const body = new URLSearchParams();
  body.set('username', payload.email);
  body.set('password', payload.password);

  const data = await request<TokenResponse>('/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: body.toString(),
  });

  saveAuth(data.access_token, payload.email);
  return data;
}

export async function getCurrentUser() {
  return request('/auth/users/me', { method: 'GET' }, true);
}

export async function uploadDataset(file: File) {
  const form = new FormData();
  form.append('file', file);

  return request<UploadedFileResponse>(`/api/upload/`, {
    method: 'POST',
    body: form,
  }, true);
}

export async function analyzeDataset(filename: string) {
  const cacheKey = `eda:${filename}`;
  const cached = getCached<EdaResponse>(cacheKey);
  if (cached) return cached;
  const data = await request<EdaResponse>(`/api/eda/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filename }),
  }, true);
  setCache(cacheKey, data);
  return data;
}

export async function getColumns(filename: string) {
  const cacheKey = `vizcols:${filename}`;
  const cached = getCached<ColumnResponse>(cacheKey);
  if (cached) return cached;
  const data = await request<ColumnResponse>(`/api/visualization/columns`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filename }),
  }, true);
  setCache(cacheKey, data);
  return data;
}

export async function generateVisualization(params: {
  filename: string;
  chart_type: string;
  x_column: string;
  y_column?: string;
}) {
  return request<VisualizationResponse>(`/api/visualization/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  }, true);
}

export function logout() {
  clearAuth();
}

// ── Preprocessing API ──────────────────────────────────────────

export async function getDatasetHealth(filename: string) {
  return request<DatasetHealthResponse>('/api/preprocess/health', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filename }),
  }, true);
}

export async function getPreprocessColumns(filename: string) {
  return request<PreprocessColumnsResponse>('/api/preprocess/columns', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filename }),
  }, true);
}

export async function getImputationRecommendations(filename: string) {
  return request<{ recommendations: Record<string, string> }>('/api/preprocess/recommend-imputation', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filename }),
  }, true);
}

export async function detectOutliersApi(filename: string, method = 'iqr', threshold = 3.0) {
  return request<{ outliers: Record<string, { count: number; pct: number }> }>('/api/preprocess/detect-outliers', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filename, method, threshold }),
  }, true);
}

export async function runPipeline(filename: string, config: Record<string, unknown>) {
  return request<PipelineRunResponse>('/api/preprocess/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filename, config }),
  }, true);
}

export function getDownloadUrl(sessionKey: string, format: string): string {
  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
  return `${API_BASE_URL}/api/preprocess/download/${sessionKey}?format=${format}`;
}

export function getDownloadHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// ── ML API ────────────────────────────────────────────────────

export async function getMLColumns(filename: string) {
  return request<{ columns: MLColumnMeta[] }>('/api/ml/columns', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filename }),
  }, true);
}

export async function detectMLTask(filename: string, target_col: string) {
  return request<TaskDetectResponse>('/api/ml/detect-task', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filename, target_col }),
  }, true);
}

export async function getMLRecommendation(filename: string, target_col?: string) {
  return request<ModelRecommendation>('/api/ml/recommend', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filename, target_col }),
  }, true);
}

export async function getModelCards(task: string) {
  return request<{ cards: ModelCard[] }>('/api/ml/cards', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ task }),
  }, true);
}

export async function trainModel(params: {
  filename: string;
  model_id: string;
  target_col?: string;
  task: string;
  hyperparams?: Record<string, unknown>;
  auto_tune?: boolean;
  cv_folds?: number;
  test_size?: number;
  random_state?: number;
}) {
  return request<TrainingResult>('/api/ml/train', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  }, true);
}

export function getModelDownloadUrl(sessionKey: string): string {
  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
  return `${API_BASE_URL}/api/ml/download/${sessionKey}`;
}

export async function getInferenceCode(sessionKey: string): Promise<string> {
  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
  const token = getToken();
  const resp = await fetch(`${API_BASE_URL}/api/ml/inference-code/${sessionKey}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!resp.ok) throw new Error('Failed to fetch inference code');
  return resp.text();
}

export async function getModelCard(sessionKey: string): Promise<string> {
  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
  const token = getToken();
  const resp = await fetch(`${API_BASE_URL}/api/ml/model-card/${sessionKey}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!resp.ok) throw new Error('Failed to fetch model card');
  return resp.text();
}

// ── Dashboard API ─────────────────────────────────────────

export async function getDashboardSummary() {
  return request<DashboardSummary>('/dashboard/summary', {
    method: 'GET',
  }, true);
}

export async function getDashboardDatasets() {
  return request<{ datasets: DashboardDataset[]; total: number }>(
    '/dashboard/datasets',
    { method: 'GET' },
    true
  );
}

export async function getDashboardSessions() {
  return request<{ sessions: DashboardSession[]; total: number }>(
    '/dashboard/sessions',
    { method: 'GET' },
    true
  );
}

export async function getDashboardDownloads() {
  return request<{ downloads: DashboardDownload[]; total: number }>(
    '/dashboard/downloads',
    { method: 'GET' },
    true
  );
}

export async function deleteDataset(datasetId: number) {
  return request<{ message: string }>(
    `/dashboard/datasets/${datasetId}`,
    { method: 'DELETE' },
    true
  );
}

export async function getPaymentStatus() {
  return request<PaymentStatus>('/payments/status', {
    method: 'GET',
  }, true);
}

// ── Profile API ───────────────────────────────────────────

export async function fetchProfile() {
  return request<ProfileData>('/dashboard/profile', {
    method: 'GET',
  }, true);
}

export async function updateProfile(data: { full_name?: string; email?: string }) {
  return request<ProfileData>('/dashboard/profile', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }, true);
}

export async function updatePassword(data: { current_password: string; new_password: string }) {
  return request<{ message: string }>('/dashboard/password', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }, true);
}

// ── Subscription API ──────────────────────────────────────

export async function fetchSubscription() {
  return request<SubscriptionData>('/dashboard/subscription', {
    method: 'GET',
  }, true);
}

// ── Coupon API ────────────────────────────────────────────

export async function applyCoupon(code: string) {
  return request<CouponResponse>('/coupons/apply', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code }),
  }, true);
}

export async function getCouponStatus() {
  return request<{ active_coupon: unknown; history: unknown[] }>('/coupons/status', {
    method: 'GET',
  }, true);
}

// ── Payments API ──────────────────────────────────────────

export async function createPaymentOrder() {
  return request<{
    order_id: string;
    amount: number;
    currency: string;
    razorpay_key_id: string;
    user_email: string;
    user_name: string | null;
  }>('/payments/create-order', {
    method: 'POST',
  }, true);
}

export async function verifyPayment(data: {
  razorpay_order_id: string;
  razorpay_payment_id: string;
  razorpay_signature: string;
}) {
  return request<{ success: boolean; message: string }>('/payments/verify-payment', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }, true);
}
