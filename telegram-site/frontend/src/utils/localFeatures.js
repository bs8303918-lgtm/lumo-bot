import { loadJSON, makeId, saveJSON } from './localStore';

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

export function addCard({ title, org = '', deadline = '', link = '', sourceId = null, stage = 'interested' }) {
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
    checklist: buildChecklist(),
    createdAt: new Date().toISOString(),
  };
  const next = [card, ...cards];
  saveCards(next);
  return next;
}

export function hasCardForSource(sourceId) {
  if (!sourceId) return false;
  return loadCards().some((c) => c.sourceId === sourceId);
}

export function updateCard(id, patch) {
  const next = loadCards().map((c) => (c.id === id ? { ...c, ...patch } : c));
  saveCards(next);
  return next;
}

export function removeCard(id) {
  const next = loadCards().filter((c) => c.id !== id);
  saveCards(next);
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

// ---- Reviews / advice feed (device-local demo feed, same as the site) ----

const SEED_REVIEWS = [
  {
    id: makeId('rev'),
    contest: 'National Merit Scholarship',
    title: 'Как готовился к эссе',
    body: 'Писал 5 черновиков, каждый раз показывал ментору. Главное — конкретные цифры и личная история, а не общие фразы.',
    link: '',
    author: 'Данияр К.',
    createdAt: new Date().toISOString(),
  },
  {
    id: makeId('rev'),
    contest: 'MIT Global Teen Hackathon',
    title: 'Что спрашивали на интервью',
    body: 'В основном про командную работу и почему именно эта тема проекта. Спрашивали, что бы поменял, если делать заново.',
    link: '',
    author: 'Аружан С.',
    createdAt: new Date().toISOString(),
  },
];

export function loadReviews() {
  return loadJSON('reviews-feed', SEED_REVIEWS);
}

export function addReview({ contest, title, body, link = '', author = 'Аноним' }) {
  const reviews = loadReviews();
  const next = [
    { id: makeId('rev'), contest, title, body, link, author, createdAt: new Date().toISOString() },
    ...reviews,
  ];
  saveJSON('reviews-feed', next);
  return next;
}
