const REFRESH_TOKEN_KEY = 'dataset_analyzer_refresh';
const EMAIL_KEY = 'dataset_analyzer_email';

// Access token kept in memory only (not localStorage) to limit XSS exposure
let _accessToken = '';

export function saveAuth(accessToken: string, email: string, refreshToken?: string) {
  _accessToken = accessToken;
  localStorage.setItem(EMAIL_KEY, email);
  if (refreshToken) {
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
  }
}

export function clearAuth() {
  _accessToken = '';
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem(EMAIL_KEY);
}

export function getToken() {
  return _accessToken;
}

export function hasToken() {
  // Consider authenticated if we have an access token OR a refresh token to restore from
  return Boolean(_accessToken) || Boolean(localStorage.getItem(REFRESH_TOKEN_KEY));
}

export function getRefreshToken() {
  return localStorage.getItem(REFRESH_TOKEN_KEY) ?? '';
}

export function setAccessToken(token: string) {
  _accessToken = token;
}

export function getLoggedInEmail() {
  return localStorage.getItem(EMAIL_KEY) ?? '';
}
