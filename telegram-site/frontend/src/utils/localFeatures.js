import { apiFetch } from '../api';
import { loadJSON, makeId, saveJSON } from './localStore';

// ---- Best-effort backend sync (SavedOpportunity) — never blocks the local-first UI ----

function syncSaveToServer(catalogId, status) {
  if (!catalogId) return;
  apiFetch('/lumo/saved', { method: 'POST', body: JSON.stringify({ catalogId, status }) }).catch(() => {});
}

function syncStatusToServer(catalogId, status) {
  if (!catalogId) return;
  apiFetch(`/lumo/saved/${catalogId}`, { method: 'PATCH', body: JSON.stringify({ status }) }).catch(() => {});
}

function syncChecklistToServer(catalogId, checklist) {
  if (!catalogId) return;
  apiFetch(`/lumo/saved/${catalogId}`, { method: 'PATCH', body: JSON.stringify({ checklist }) }).catch(() => {});
}

function syncRemoveFromServer(catalogId) {
  if (!catalogId) return;
  apiFetch(`/lumo/saved/${catalogId}`, { method: 'DELETE' }).catch(() => {});
}

/** Забирает сохранённые с сервера (другие устройства/бот) и добавляет недостающие карточки локально. */
export async function pullSavedFromServer() {
  let data;
  try {
    data = await apiFetch('/lumo/saved');
  } catch {
    return loadCards();
  }
  const existing = loadCards();
  const existingSourceIds = new Set(existing.map((c) => c.sourceId).filter(Boolean));
  const additions = (data.items || [])
    .filter((entry) => !existingSourceIds.has(entry.id))
    .map((entry) => ({
      id: makeId('card'),
      sourceId: entry.id,
      title: entry.title || 'Без названия',
      org: entry.sourceChannelName || '',
      deadline: entry.deadline || '',
      link: entry.applicationUrl || entry.messageLink || '',
      stage: entry.savedStatus || 'interested',
      checklist: entry.checklist?.length ? entry.checklist : buildChecklist(),
      createdAt: entry.savedAt || new Date().toISOString(),
    }));
  if (additions.length) {
    const next = [...additions, ...existing];
    saveCards(next);
    return next;
  }
  return existing;
}

// ---- Favorite opportunities ----

export function loadFavorites() {
  return loadJSON('favorites', []);
}

export function isFavorite(id) {
  return loadFavorites().some((f) => f.id === id);
}

export function toggleFavorite(item) {
  const favorites = loadFavorites();
  const exists = favorites.some((f) => f.id === item.id);
  const next = exists ? favorites.filter((f) => f.id !== item.id) : [...favorites, item];
  saveJSON('favorites', next);
  return next;
}

// ---- Application tracker (Kanban stages + checklist + deadlines) ----

export const KANBAN_STAGES = [
  { id: 'interested', label: 'Интересно' },
  { id: 'applied', label: 'Подано' },
  { id: 'interview', label: 'Интервью' },
  { id: 'result', label: 'Результат' },
];

export const DEFAULT_CHECKLIST_ITEMS = [
  'Эссе / мотивационное письмо',
  'Рекомендательные письма',
  'Портфолио или резюме',
  'Транскрипт / табель',
];

function buildChecklist() {
  return DEFAULT_CHECKLIST_ITEMS.map((label) => ({ id: makeId('doc'), label, done: false }));
}

export function loadCards() {
  return loadJSON('kanban-cards', []);
}

export function saveCards(cards) {
  saveJSON('kanban-cards', cards);
}

export function addCard({
  title,
  org = '',
  deadline = '',
  link = '',
  sourceId = null,
  stage = 'interested',
  checklistLabels = null,
}) {
  const cards = loadCards();
  if (sourceId && cards.some((c) => c.sourceId === sourceId)) {
    return cards;
  }
  const card = {
    id: makeId('card'),
    sourceId,
    title: title || 'Без названия',
    org,
    deadline,
    link,
    stage,
    checklist: checklistLabels?.length
      ? checklistLabels.map((label) => ({ id: makeId('doc'), label, done: false }))
      : buildChecklist(),
    createdAt: new Date().toISOString(),
  };
  const next = [card, ...cards];
  saveCards(next);
  syncSaveToServer(sourceId, stage);
  return next;
}

export function hasCardForSource(sourceId) {
  if (!sourceId) return false;
  return loadCards().some((c) => c.sourceId === sourceId);
}

export function updateCard(id, patch) {
  const next = loadCards().map((c) => (c.id === id ? { ...c, ...patch } : c));
  saveCards(next);
  if (patch.stage) {
    const card = next.find((c) => c.id === id);
    syncStatusToServer(card?.sourceId, patch.stage);
  }
  return next;
}

export function removeCard(id) {
  const card = loadCards().find((c) => c.id === id);
  const next = loadCards().filter((c) => c.id !== id);
  saveCards(next);
  syncRemoveFromServer(card?.sourceId);
  return next;
}

export function toggleChecklistItem(cardId, itemId) {
  const next = loadCards().map((c) => {
    if (c.id !== cardId) return c;
    return {
      ...c,
      checklist: c.checklist.map((item) => (item.id === itemId ? { ...item, done: !item.done } : item)),
    };
  });
  saveCards(next);
  const card = next.find((c) => c.id === cardId);
  syncChecklistToServer(card?.sourceId, card?.checklist);
  return next;
}

export function googleCalendarUrl({ title, date, note = '' }) {
  const start = date ? date.replace(/-/g, '') : '';
  const params = new URLSearchParams({
    action: 'TEMPLATE',
    text: title || 'Дедлайн конкурса',
    dates: start ? `${start}/${start}` : '',
    details: note,
  });
  return `https://calendar.google.com/calendar/render?${params.toString()}`;
}

// Отзывы/советы (UGC) теперь полностью на бэкенде — см. /lumo/reviews и /lumo/opportunities/{id}/reviews.
