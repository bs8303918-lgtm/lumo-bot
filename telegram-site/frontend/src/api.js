const API_BASE = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');
const API = API_BASE ? `${API_BASE}/api` : '/api';

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
  let res;
  try {
    res = await fetch(`${API}${path}`, {
      ...options,
      headers: { ...apiHeaders(), ...options.headers },
    });
  } catch {
    throw new Error(
      'Не удалось связаться с API. Проверь, что бэкенд (Railway) запущен и VITE_API_URL указан верно.'
    );
  }
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    if (res.status === 530) {
      throw new Error(
        'API недоступен. Проверь Railway и переменную VITE_API_URL на Vercel.'
      );
    }
    throw new Error(data.detail || `HTTP ${res.status}`);
  }
  return res.json();
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
