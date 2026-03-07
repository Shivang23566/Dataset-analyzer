import { clearAuth, getToken, saveAuth } from './authStore';
import type {
  ColumnResponse,
  EdaResponse,
  LoginPayload,
  SignupPayload,
  TokenResponse,
  UploadedFileResponse,
  VisualizationResponse,
} from './types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

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
    const text = await response.text();
    let message = text || `Request failed: ${response.status}`;

    try {
      const parsed = JSON.parse(text) as { detail?: string };
      if (parsed?.detail) {
        message = parsed.detail;
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
  });
}

export async function analyzeDataset(filename: string) {
  return request<EdaResponse>(`/api/eda/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filename }),
  }, true);
}

export async function getColumns(filename: string) {
  return request<ColumnResponse>(`/api/visualization/columns`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filename }),
  }, true);
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
