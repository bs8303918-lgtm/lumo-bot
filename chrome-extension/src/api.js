import { API } from './config.js';
import { getAuth, clearAuth } from './storage.js';

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function request(path, { method = 'GET', body, auth = true } = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (auth) {
    const { token } = await getAuth();
    if (!token) throw new ApiError('Не авторизован', 401);
    headers.Authorization = `Bearer ${token}`;
  }

  let res;
  try {
    res = await fetch(`${API}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (err) {
    throw new ApiError('Нет связи с сервером Lumo. Проверь интернет.', 0);
  }

  const text = await res.text();
  let data = {};
  if (text.trim()) {
    try {
      data = JSON.parse(text);
    } catch {
      throw new ApiError(`Некорректный ответ сервера (HTTP ${res.status})`, res.status);
    }
  }

  if (res.status === 401 && auth) {
    await clearAuth();
  }

  if (!res.ok) {
    const message = data?.detail || data?.message || `Ошибка сервера (HTTP ${res.status})`;
    throw new ApiError(typeof message === 'string' ? message : 'Ошибка сервера', res.status);
  }

  return data;
}

export function register(email, password, name) {
  return request('/auth/register', { method: 'POST', auth: false, body: { email, password, name } });
}

export function login(email, password) {
  return request('/auth/login', { method: 'POST', auth: false, body: { email, password } });
}

export function fetchMeta() {
  return request('/lumo/meta', { auth: false });
}

export function fetchOpportunities({ types, q, offset = 0, limit = 20, sort = 'deadline' } = {}) {
  const params = new URLSearchParams();
  if (types && types.length) params.set('types', types.join(','));
  if (q) params.set('q', q);
  params.set('offset', String(offset));
  params.set('limit', String(limit));
  params.set('sort', sort);
  return request(`/lumo/opportunities?${params.toString()}`);
}

export { ApiError };
