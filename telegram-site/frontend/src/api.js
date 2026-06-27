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

const API_BASE = normalizeApiBase(import.meta.env.VITE_API_URL);
const API = API_BASE ? `${API_BASE}/api` : '/api';

async function readJsonResponse(res) {
  const text = await res.text();
  if (!text.trim()) return {};
  const looksHtml = text.trimStart().startsWith('<!') || text.trimStart().startsWith('<html');
  if (looksHtml) {
    throw new Error(
      'Mini App получил HTML вместо JSON. На Vercel задай VITE_API_URL=https://твой-проект.up.railway.app (Production), затем Redeploy.'
    );
  }
  try {
    return JSON.parse(text);
  } catch {
    throw new Error(`Ответ API не JSON (HTTP ${res.status})`);
  }
}

export function getTelegram() {
  return window.Telegram?.WebApp ?? null;
}

export function apiHeaders() {
  const headers = { 'Content-Type': 'application/json' };
  const tg = getTelegram();
  if (tg?.initData) {
    headers['X-Telegram-Init-Data'] = tg.initData;
  } else {
    const devId = localStorage.getItem('lumo-dev-telegram-id');
    if (devId) headers['X-Dev-Telegram-Id'] = devId;
  }
  return headers;
}

export async function apiFetch(path, options = {}) {
  if (!API_BASE && import.meta.env.PROD) {
    throw new Error(
      'VITE_API_URL не задан на Vercel. Variables → VITE_API_URL = URL Railway → Redeploy.'
    );
  }

  let res;
  const url = `${API}${path}`;
  const controller = new AbortController();
  const timeoutMs = 120000;
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    res = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: { ...apiHeaders(), ...options.headers },
    });
  } catch (err) {
    if (err?.name === 'AbortError') {
      throw new Error('Запрос занял слишком долго (>2 мин). Проверь Railway Logs и LLM ключ.');
    }
    const hint = API_BASE ? ` (${url})` : '';
    throw new Error(
      `Не удалось связаться с API${hint}. Проверь Railway Online, VITE_API_URL на Vercel и Redeploy после смены переменных.`
    );
  } finally {
    clearTimeout(timer);
  }
  const data = await readJsonResponse(res);
  if (!res.ok) {
    if (res.status === 404) {
      throw new Error(
        `API 404 Not Found (${url}). VITE_API_URL на Vercel = только домен Railway, без /api в конце.`
      );
    }
    if (res.status === 530) {
      throw new Error(
        'API недоступен. Проверь Railway и переменную VITE_API_URL на Vercel.'
      );
    }
    throw new Error(data.detail || `HTTP ${res.status}`);
  }
  return data;
}

export function initTelegramApp() {
  const tg = getTelegram();
  if (!tg) return null;
  tg.ready();
  tg.expand();
  return tg;
}

export function openBugReport(message, supportContact) {
  const tg = getTelegram();
  const handle = (supportContact || '@taton4i').replace('@', '');
  const text = encodeURIComponent(`🐛 Lumo Mini App\n\n${message.trim()}`);
  const url = `https://t.me/${handle}?text=${text}`;
  if (tg?.openTelegramLink) tg.openTelegramLink(url);
  else window.open(url, '_blank');
}

export function openBotCommand(botUsername, command) {
  const tg = getTelegram();
  const cmd = command.startsWith('/') ? command : `/${command}`;
  const url = `https://t.me/${botUsername}?text=${encodeURIComponent(cmd)}`;
  if (tg?.openTelegramLink) tg.openTelegramLink(url);
  else window.open(url, '_blank');
}

export function haptic(type = 'light') {
  getTelegram()?.HapticFeedback?.impactOccurred(type);
}
