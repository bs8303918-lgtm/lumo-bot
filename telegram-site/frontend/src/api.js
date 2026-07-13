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

  const { timeoutMs, ...fetchOptions } = options;
  let res;
  const url = `${API}${path}`;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs ?? 15000);
  try {
    res = await fetch(url, {
      ...fetchOptions,
      signal: controller.signal,
      headers: { ...apiHeaders(), ...fetchOptions.headers },
    });
  } catch (err) {
    if (err?.name === 'AbortError') {
      throw new Error('Запрос занял слишком долго (>15 сек). Проверь Railway и VITE_API_URL.');
    }
    const hint = API_BASE ? ` (${url})` : '';
    let extra = '';
    if (API_BASE) {
      try {
        const hc = new AbortController();
        const ht = setTimeout(() => hc.abort(), 5000);
        const healthRes = await fetch(`${API}/health`, { signal: hc.signal });
        clearTimeout(ht);
        if (healthRes.ok) {
          const health = await healthRes.json();
          if (health?.db === 'error') {
            extra = ' API online, но база недоступна — проверь DATABASE_URL / SUPABASE_POOLER_HOST на Railway.';
          } else if (getTelegram()?.initData) {
            extra = ' API online — повтори через несколько секунд или потяни экран вниз.';
          } else {
            extra = ' API online — открой Mini App из Telegram (кнопка Open), не из браузера.';
          }
        }
      } catch {
        extra = ' Railway API не отвечает — проверь деплой и домен в VITE_API_URL.';
      }
    }
    throw new Error(
      `Не удалось связаться с API${hint}.${extra} Redeploy после смены переменных.`
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
    const err = new Error(data.detail || `HTTP ${res.status}`);
    err.status = res.status;
    err.showPricing = res.status === 429 || res.headers.get('X-Lumo-Show-Pricing') === '1';
    throw err;
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
  const tg = getTelegram();
  const hapticApi = tg?.HapticFeedback;
  if (!hapticApi) return;

  try {
    if (type === 'success' || type === 'error' || type === 'warning') {
      hapticApi.notificationOccurred?.(type);
      return;
    }
    const impact = ['light', 'medium', 'heavy', 'rigid', 'soft'].includes(type) ? type : 'light';
    hapticApi.impactOccurred?.(impact);
  } catch {
    // Telegram WebApp may reject unsupported haptic styles on some clients.
  }
}
