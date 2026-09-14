/**
 * JWT token storage helpers.
 */

const ACCESS_TOKEN_KEY = 'burner_access_token';

export function getToken() {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function setToken(token) {
  localStorage.setItem(ACCESS_TOKEN_KEY, token);
}

export function clearTokens() {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem('refresh_token');
}

export function isTokenExpired(token) {
  if (!token) return true;
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    return payload.exp * 1000 < Date.now();
  } catch {
    return true;
  }
}

export function isAuthenticated() {
  const token = getToken();
  return !!token && !isTokenExpired(token);
}

export function getTokenPayload() {
  const token = getToken();
  if (!token) return null;
  try {
    return JSON.parse(atob(token.split('.')[1]));
  } catch {
    return null;
  }
}
