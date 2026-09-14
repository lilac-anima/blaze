/**
 * API Client — configurable base URL, auto-attaches JWT, handles 401 refresh.
 */
import { getToken, setToken, clearTokens, isTokenExpired } from '../auth/token.js';

const DEFAULT_BASE_URL = 'http://localhost:8000';

let baseUrl = DEFAULT_BASE_URL;

export function setBaseUrl(url) {
  baseUrl = url.replace(/\/+$/, '');
}

export function getBaseUrl() {
  return baseUrl;
}

let refreshPromise = null;

/**
 * Attempt to refresh the access token using the stored refresh token.
 */
async function refreshAccessToken() {
  const rt = localStorage.getItem('refresh_token');
  if (!rt) return false;

  try {
    const res = await fetch(`${baseUrl}/api/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: rt }),
    });
    if (!res.ok) {
      clearTokens();
      return false;
    }
    const data = await res.json();
    setToken(data.access_token);
    if (data.refresh_token) {
      localStorage.setItem('refresh_token', data.refresh_token);
    }
    return true;
  } catch {
    clearTokens();
    return false;
  }
}

/**
 * Core request function.
 * @param {string} path — e.g. '/api/auth/login'
 * @param {object} opts — fetch options (method, body, headers, etc.)
 */
export async function apiRequest(path, opts = {}) {
  const { headers = {}, ...rest } = opts;

  const token = getToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const url = `${baseUrl}${path}`;
  let res = await fetch(url, { headers, ...rest });

  // Handle 401 — attempt token refresh once
  if (res.status === 401 && token) {
    if (!refreshPromise) {
      refreshPromise = refreshAccessToken();
    }
    const refreshed = await refreshPromise;
    refreshPromise = null;

    if (refreshed) {
      const newToken = getToken();
      headers['Authorization'] = `Bearer ${newToken}`;
      res = await fetch(url, { headers, ...rest });
    }
  }

  return res;
}

/**
 * Convenience helpers.
 */
export const api = {
  get(path, opts = {}) {
    return apiRequest(path, { method: 'GET', ...opts });
  },
  post(path, body, opts = {}) {
    return apiRequest(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...opts.headers },
      body: JSON.stringify(body),
      ...opts,
    });
  },
  put(path, body, opts = {}) {
    return apiRequest(path, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', ...opts.headers },
      body: JSON.stringify(body),
      ...opts,
    });
  },
  del(path, opts = {}) {
    return apiRequest(path, { method: 'DELETE', ...opts });
  },
};
