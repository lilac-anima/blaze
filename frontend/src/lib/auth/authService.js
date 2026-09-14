/**
 * Auth Service — login, register, forgot password, logout.
 */
import { api } from '../api/client.js';
import { setToken, clearTokens } from './token.js';

export async function login(loginId, password) {
  const res = await api.post('/api/auth/login', { login: loginId, password });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Login failed');
  setToken(data.access_token);
  if (data.refresh_token) {
    localStorage.setItem('refresh_token', data.refresh_token);
  }
  return data;
}

export async function register(username, burnerName, password) {
  const res = await api.post('/api/auth/register', {
    username,
    burner_name: burnerName,
    password,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Registration failed');
  return data;
}

export async function forgotPassword(email) {
  const res = await api.post('/api/auth/password-reset/request', { email });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Request failed');
  return data;
}

export async function resetPassword(token, newPassword) {
  const res = await api.post('/api/auth/password-reset/confirm', {
    token,
    new_password: newPassword,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Reset failed');
  return data;
}

export function logout() {
  clearTokens();
  // Navigate to login — caller handles redirect
}
