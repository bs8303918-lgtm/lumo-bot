function normalizeApiBase(raw) {
  const text = (raw || '').trim();
  if (!text) return '';
  try {
    const url = new URL(text.startsWith('http') ? text : `https://${text}`);
    return url.origin;
  } catch {
    return text.replace(/\/$/, '').replace(/\/api(\/.*)?$/, '');
  }
}

const PRODUCTION_API = 'https://lumo-bot-production-9903.up.railway.app';
const API_BASE = normalizeApiBase(import.meta.env.VITE_API_URL || (import.meta.env.PROD ? PRODUCTION_API : ''));
const API = API_BASE ? `${API_BASE}/api` : '/api';

const TELEGRAM_LOGIN_KEY = 'lumo-telegram-login';
const GOOGLE_AUTH_KEY = 'lumo-google-auth';
const WEB_AUTH_KEY = 'lumo-web-auth';
const ROOM_STUDENT_KEY = 'lumo-active-room-student-id';
const ROOM_STUDENT_NAME_KEY = 'lumo-active-room-student-name';

export function getActiveRoomStudentId() {
  const raw = localStorage.getItem(ROOM_STUDENT_KEY);
  if (!raw) return null;
  const id = Number(raw);
  return Number.isFinite(id) && id > 0 ? id : null;
}

export function getActiveRoomStudentName() {
  return localStorage.getItem(ROOM_STUDENT_NAME_KEY) || null;
}

export function setActiveRoom(studentId, studentName) {
  if (studentId) {
    localStorage.setItem(ROOM_STUDENT_KEY, String(studentId));
    if (studentName) localStorage.setItem(ROOM_STUDENT_NAME_KEY, studentName);
  }
}

export function clearActiveRoom() {
  localStorage.removeItem(ROOM_STUDENT_KEY);
  localStorage.removeItem(ROOM_STUDENT_NAME_KEY);
}

function decodeJwtPayload(token) {
  try {
    return JSON.parse(atob(token.split('.')[1]));
  } catch {
    return null;
  }
}

function isTokenFresh(token) {
  const payload = decodeJwtPayload(token);
  if (!payload?.exp) return true;
  return payload.exp * 1000 > Date.now() + 60_000;
}

export function getTelegram() {
  return window.Telegram?.WebApp ?? null;
}

export function getStoredLogin() {
  try {
    const raw = localStorage.getItem(TELEGRAM_LOGIN_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function getStoredGoogleAuth() {
  try {
    const raw = localStorage.getItem(GOOGLE_AUTH_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function getStoredWebAuth() {
  try {
    const raw = localStorage.getItem(WEB_AUTH_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function saveTelegramLogin(user) {
  localStorage.removeItem(GOOGLE_AUTH_KEY);
  localStorage.removeItem(WEB_AUTH_KEY);
  localStorage.setItem(TELEGRAM_LOGIN_KEY, JSON.stringify(user));
  window.dispatchEvent(new Event('lumo-auth-changed'));
}

export function saveGoogleAuth(payload) {
  localStorage.removeItem(TELEGRAM_LOGIN_KEY);
  localStorage.removeItem(WEB_AUTH_KEY);
  localStorage.setItem(GOOGLE_AUTH_KEY, JSON.stringify(payload));
  window.dispatchEvent(new Event('lumo-auth-changed'));
}

export function saveWebAuth(payload) {
  localStorage.removeItem(TELEGRAM_LOGIN_KEY);
  localStorage.removeItem(GOOGLE_AUTH_KEY);
  localStorage.setItem(WEB_AUTH_KEY, JSON.stringify(payload));
  window.dispatchEvent(new Event('lumo-auth-changed'));
}

export function clearAuth() {
  localStorage.removeItem(TELEGRAM_LOGIN_KEY);
  localStorage.removeItem(GOOGLE_AUTH_KEY);
  localStorage.removeItem(WEB_AUTH_KEY);
  window.dispatchEvent(new Event('lumo-auth-changed'));
}

export function clearTelegramLogin() {
  clearAuth();
}

export function isAuthenticated() {
  const tg = getTelegram();
  if (tg?.initData) return true;
  if (getStoredLogin()?.hash) return true;
  const google = getStoredGoogleAuth();
  if (google?.idToken && isTokenFresh(google.idToken)) return true;
  const web = getStoredWebAuth();
  if (web?.token) return true;
  return false;
}

export function apiHeaders(roomStudentId = null) {
  const headers = { 'Content-Type': 'application/json' };
  const roomId = roomStudentId ?? getActiveRoomStudentId();
  if (roomId) headers['X-Room-Student-Id'] = String(roomId);
  const tg = getTelegram();
  if (tg?.initData) {
    headers['X-Telegram-Init-Data'] = tg.initData;
    return headers;
  }

  const web = getStoredWebAuth();
  if (web?.token) {
    headers.Authorization = `Bearer ${web.token}`;
    return headers;
  }

  const google = getStoredGoogleAuth();
  if (google?.idToken && isTokenFresh(google.idToken)) {
    headers['X-Google-Id-Token'] = google.idToken;
    return headers;
  }

  const login = getStoredLogin();
  if (login?.hash) {
    headers['X-Telegram-Login-Data'] = JSON.stringify(login);
  } else if (import.meta.env.DEV) {
    const devId = localStorage.getItem('lumo-dev-telegram-id');
    if (devId) headers['X-Dev-Telegram-Id'] = devId;
  }
  return headers;
}

async function readJsonResponse(res) {
  const text = await res.text();
  if (!text.trim()) return {};
  const looksHtml = text.trimStart().startsWith('<!') || text.trimStart().startsWith('<html');
  if (looksHtml) {
    throw new Error(
      'Сайт получил HTML вместо JSON. На Vercel задай VITE_API_URL=https://твой-проект.up.railway.app и redeploy.',
    );
  }
  try {
    return JSON.parse(text);
  } catch {
    throw new Error(`Ответ API не JSON (HTTP ${res.status})`);
  }
}

export async function apiFetch(path, options = {}) {
  if (!API_BASE && import.meta.env.PROD) {
    throw new Error('VITE_API_URL не задан на Vercel. Укажи URL Railway и redeploy.');
  }

  const { timeoutMs, auth = true, roomStudentId = null, ...fetchOptions } = options;
  const url = `${API}${path}`;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs ?? 20000);

  try {
    const res = await fetch(url, {
      ...fetchOptions,
      signal: controller.signal,
      headers: {
        ...(auth ? apiHeaders(roomStudentId) : { 'Content-Type': 'application/json' }),
        ...fetchOptions.headers,
      },
    });
    const data = await readJsonResponse(res);
    if (!res.ok) {
      if (res.status === 401) {
        const detail = data.detail || 'Нужен вход';
        const err = new Error(
          detail.includes('Telegram or provide dev auth')
            ? 'Бэкенд на Railway ещё старый — нужен redeploy lumo-bot с Google/email auth.'
            : detail,
        );
        err.status = 401;
        err.needsAuth = true;
        throw err;
      }
      if (res.status === 429) {
        const err = new Error(data.detail || 'Лимит запросов исчерпан');
        err.status = 429;
        err.showPricing = true;
        throw err;
      }
      if (res.status === 409) {
        throw new Error(data.detail || 'Аккаунт с этим email уже есть');
      }
      if (res.status === 503) {
        throw new Error(data.detail || 'Сервер не настроен для регистрации');
      }
      if (res.status === 404 && path.startsWith('/auth/')) {
        throw new Error('Регистрация на сервере ещё не включена. Подожди redeploy Railway.');
      }
      throw new Error(data.detail || `HTTP ${res.status}`);
    }
    return data;
  } catch (err) {
    if (err?.name === 'AbortError') {
      throw new Error('Запрос занял слишком долго. Проверь Railway и VITE_API_URL.');
    }
    if (err instanceof TypeError && String(err.message).includes('fetch')) {
      throw new Error('Failed to fetch');
    }
    if (err?.message && !err.needsAuth) throw err;
    if (API_BASE) {
      throw new Error(
        `${err.message || 'Ошибка API'}. Проверь, что Railway запущен и VITE_API_URL указан верно.`,
      );
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

export async function webRegister({ email, password, name }) {
  const data = await apiFetch('/auth/register', {
    method: 'POST',
    auth: false,
    body: JSON.stringify({ email, password, name: name || undefined }),
  });
  saveWebAuth({ token: data.token, email: data.email, name: data.name });
  return data;
}

export async function webLogin({ email, password }) {
  const data = await apiFetch('/auth/login', {
    method: 'POST',
    auth: false,
    body: JSON.stringify({ email, password }),
  });
  saveWebAuth({ token: data.token, email: data.email, name: data.name });
  return data;
}

export async function syncSession() {
  if (!isAuthenticated()) return null;
  try {
    return await apiFetch('/users/me');
  } catch (err) {
    if (err.needsAuth || err.status === 401) {
      clearAuth();
    }
    throw err;
  }
}

export function initTelegramApp() {
  const tg = getTelegram();
  if (!tg) return null;
  tg.ready();
  tg.expand();
  return tg;
}

export function authDisplayName() {
  const web = getStoredWebAuth();
  if (web?.name) return web.name;
  if (web?.email) return web.email.split('@')[0];
  const google = getStoredGoogleAuth();
  if (google?.name) return google.name;
  if (google?.email) return google.email.split('@')[0];
  const login = getStoredLogin();
  if (login?.username) return `@${login.username}`;
  if (login?.first_name) return login.first_name;
  return 'Аккаунт';
}

export { API, API_BASE };
