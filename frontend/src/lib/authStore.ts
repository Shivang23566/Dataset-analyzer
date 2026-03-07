const TOKEN_KEY = 'dataset_analyzer_jwt';
const EMAIL_KEY = 'dataset_analyzer_email';

export function saveAuth(token: string, email: string) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(EMAIL_KEY, email);
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(EMAIL_KEY);
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) ?? '';
}

export function hasToken() {
  return Boolean(getToken());
}

export function getLoggedInEmail() {
  return localStorage.getItem(EMAIL_KEY) ?? '';
}
