import { CATEGORY_DISPLAY, FILTER_TYPES, DEFAULT_BOT_USERNAME } from './config.js';
import * as api from './api.js';
import { getAuth, setAuth, clearAuth, getTracked, upsertTracked, removeTracked } from './storage.js';

const els = {
  statusLine: document.getElementById('statusLine'),
  refreshBtn: document.getElementById('refreshBtn'),
  authView: document.getElementById('authView'),
  mainView: document.getElementById('mainView'),
  authTabs: document.querySelectorAll('.auth-tab'),
  authForm: document.getElementById('authForm'),
  authEmail: document.getElementById('authEmail'),
  authName: document.getElementById('authName'),
  authPassword: document.getElementById('authPassword'),
  authError: document.getElementById('authError'),
  authSubmit: document.getElementById('authSubmit'),
  nameField: document.getElementById('nameField'),
  searchInput: document.getElementById('searchInput'),
  filterRow: document.getElementById('filterRow'),
  viewTabs: document.querySelectorAll('.view-tab'),
  trackedCount: document.getElementById('trackedCount'),
  listContainer: document.getElementById('listContainer'),
  loadingState: document.getElementById('loadingState'),
  emptyState: document.getElementById('emptyState'),
  itemsList: document.getElementById('itemsList'),
  loadMoreBtn: document.getElementById('loadMoreBtn'),
  openBotBtn: document.getElementById('openBotBtn'),
  logoutBtn: document.getElementById('logoutBtn'),
};

let authMode = 'login';
let activeType = 'all';
let activeSubTab = 'catalog';
let searchQuery = '';
let searchDebounce = null;
let catalogOffset = 0;
let catalogHasMore = false;
let catalogItems = [];
let trackedMap = {};

function fmtEmojiLabel(type) {
  return CATEGORY_DISPLAY[type] || ['📌', type || 'Другое'];
}

async function init() {
  buildFilterRow();
  bindEvents();
  const { token } = await getAuth();
  if (token) {
    showMain();
    await refreshAll();
  } else {
    showAuth();
  }
}

function buildFilterRow() {
  const all = document.createElement('button');
  all.className = 'filter-chip active';
  all.textContent = 'Все';
  all.dataset.type = 'all';
  els.filterRow.appendChild(all);

  FILTER_TYPES.forEach((type) => {
    const [emoji, label] = fmtEmojiLabel(type);
    const chip = document.createElement('button');
    chip.className = 'filter-chip';
    chip.dataset.type = type;
    chip.textContent = `${emoji} ${label}`;
    els.filterRow.appendChild(chip);
  });

  els.filterRow.addEventListener('click', (e) => {
    const btn = e.target.closest('.filter-chip');
    if (!btn) return;
    activeType = btn.dataset.type;
    [...els.filterRow.children].forEach((c) => c.classList.toggle('active', c === btn));
    catalogOffset = 0;
    loadCatalog({ reset: true });
  });
}

function bindEvents() {
  els.authTabs.forEach((tab) =>
    tab.addEventListener('click', () => {
      authMode = tab.dataset.mode;
      els.authTabs.forEach((t) => t.classList.toggle('active', t === tab));
      els.nameField.hidden = authMode !== 'register';
      els.authSubmit.textContent = authMode === 'register' ? 'Создать аккаунт' : 'Войти';
      els.authError.classList.add('hidden');
    })
  );

  els.authForm.addEventListener('submit', onAuthSubmit);

  els.refreshBtn.addEventListener('click', async () => {
    els.refreshBtn.classList.add('spinning');
    await refreshAll();
    els.refreshBtn.classList.remove('spinning');
  });

  els.searchInput.addEventListener('input', () => {
    clearTimeout(searchDebounce);
    searchDebounce = setTimeout(() => {
      searchQuery = els.searchInput.value.trim();
      catalogOffset = 0;
      loadCatalog({ reset: true });
    }, 350);
  });

  els.viewTabs.forEach((tab) =>
    tab.addEventListener('click', () => {
      activeSubTab = tab.dataset.tab;
      els.viewTabs.forEach((t) => t.classList.toggle('active', t === tab));
      els.loadMoreBtn.classList.toggle('hidden', activeSubTab !== 'catalog');
      render();
    })
  );

  els.loadMoreBtn.addEventListener('click', () => loadCatalog({ reset: false }));

  els.logoutBtn.addEventListener('click', async () => {
    await clearAuth();
    showAuth();
  });

  els.openBotBtn.addEventListener('click', async () => {
    let username = DEFAULT_BOT_USERNAME;
    try {
      const meta = await api.fetchMeta();
      username = meta.botUsername || username;
    } catch {
      // ignore, use default
    }
    chrome.tabs.create({ url: `https://t.me/${username}` });
  });
}

async function onAuthSubmit(e) {
  e.preventDefault();
  els.authError.classList.add('hidden');
  els.authSubmit.disabled = true;
  const prevLabel = els.authSubmit.textContent;
  els.authSubmit.textContent = 'Подождите...';

  const email = els.authEmail.value.trim();
  const password = els.authPassword.value;
  const name = els.authName.value.trim();

  try {
    const data =
      authMode === 'register' ? await api.register(email, password, name) : await api.login(email, password);
    await setAuth(data.token, { email: data.email, name: data.name });
    showMain();
    await refreshAll();
  } catch (err) {
    els.authError.textContent = err.message || 'Что-то пошло не так';
    els.authError.classList.remove('hidden');
  } finally {
    els.authSubmit.disabled = false;
    els.authSubmit.textContent = prevLabel;
  }
}

function showAuth() {
  els.authView.classList.remove('hidden');
  els.mainView.classList.add('hidden');
  els.statusLine.textContent = 'войди, чтобы видеть каталог';
}

function showMain() {
  els.authView.classList.add('hidden');
  els.mainView.classList.remove('hidden');
}

async function refreshAll() {
  els.statusLine.textContent = 'проверяю...';
  trackedMap = await getTracked();
  updateTrackedCount();
  await Promise.all([loadCatalog({ reset: true }), checkBackground()]);
}

async function checkBackground() {
  try {
    await chrome.runtime.sendMessage({ type: 'lumo:check-now' });
  } catch {
    // background may be asleep momentarily; ignore
  }
  try {
    await chrome.runtime.sendMessage({ type: 'lumo:mark-seen' });
  } catch {
    // ignore
  }
}

async function loadCatalog({ reset }) {
  if (reset) {
    catalogOffset = 0;
    catalogItems = [];
    els.itemsList.innerHTML = '';
  }
  toggleLoading(true);
  try {
    const types = activeType === 'all' ? undefined : [activeType];
    const data = await api.fetchOpportunities({ types, q: searchQuery, offset: catalogOffset, limit: 20 });
    catalogItems = reset ? data.items : catalogItems.concat(data.items);
    catalogOffset = data.offset + data.items.length;
    catalogHasMore = Boolean(data.hasMore);
    els.statusLine.textContent = `найдено ${data.total} · обновлено сейчас`;
    els.loadMoreBtn.classList.toggle('hidden', !catalogHasMore || activeSubTab !== 'catalog');
  } catch (err) {
    els.statusLine.textContent = err.message || 'Ошибка загрузки';
    if (err.status === 401) showAuth();
  } finally {
    toggleLoading(false);
    render();
  }
}

function toggleLoading(isLoading) {
  els.loadingState.classList.toggle('hidden', !isLoading || catalogItems.length > 0);
}

function updateTrackedCount() {
  const n = Object.keys(trackedMap).length;
  els.trackedCount.textContent = String(n);
  els.trackedCount.classList.toggle('hidden', n === 0);
}

function render() {
  const items = activeSubTab === 'catalog' ? catalogItems : sortedTrackedItems();
  els.itemsList.innerHTML = '';
  els.emptyState.classList.toggle('hidden', items.length > 0);
  els.emptyState.textContent =
    activeSubTab === 'catalog' ? 'Ничего не найдено' : 'Пока нет отслеживаемых конкурсов — жми на ★ у карточки';

  items.forEach((item) => {
    els.itemsList.appendChild(activeSubTab === 'catalog' ? buildCatalogCard(item) : buildTrackedCard(item));
  });
}

function sortedTrackedItems() {
  return Object.values(trackedMap)
    .slice()
    .sort((a, b) => {
      if (a.item.deadlineUrgent !== b.item.deadlineUrgent) return a.item.deadlineUrgent ? -1 : 1;
      return 0;
    })
    .map((entry) => entry.item);
}

function buildCardShell(item) {
  const li = document.createElement('li');
  li.className = 'card';

  const [emoji, label] = fmtEmojiLabel(item.type);

  const top = document.createElement('div');
  top.className = 'card-top';

  const title = document.createElement('div');
  title.className = 'card-title';
  title.textContent = item.title;

  const badges = document.createElement('div');
  badges.className = 'card-badges';

  if (item.isNew) {
    const newBadge = document.createElement('span');
    newBadge.className = 'new-badge';
    newBadge.textContent = 'NEW';
    badges.appendChild(newBadge);
  }

  const typeChip = document.createElement('span');
  typeChip.className = 'type-chip';
  typeChip.textContent = `${item.emoji || emoji} ${item.label || label}`;
  badges.appendChild(typeChip);

  const starBtn = document.createElement('button');
  starBtn.className = 'star-btn';
  const isTracked = Boolean(trackedMap[item.id]);
  starBtn.classList.toggle('active', isTracked);
  starBtn.innerHTML = starIcon(isTracked);
  starBtn.addEventListener('click', async (e) => {
    e.stopPropagation();
    if (trackedMap[item.id]) {
      trackedMap = await removeTracked(item.id);
    } else {
      trackedMap = await upsertTracked(item, 'want');
    }
    updateTrackedCount();
    render();
  });
  badges.appendChild(starBtn);

  top.appendChild(title);
  top.appendChild(badges);
  li.appendChild(top);

  const desc = document.createElement('p');
  desc.className = 'card-desc';
  desc.textContent = item.description || '';
  li.appendChild(desc);

  const bottom = document.createElement('div');
  bottom.className = 'card-bottom';

  const deadline = document.createElement('div');
  deadline.className = `deadline${item.deadlineUrgent ? ' urgent' : ''}`;
  deadline.innerHTML = `${item.deadlineUrgent ? clockIcon() : calendarIcon()}<span>${
    item.deadlineLabel || 'Без дедлайна'
  }</span>`;
  bottom.appendChild(deadline);

  const source = document.createElement('div');
  source.className = 'source';
  source.textContent = item.country || item.sourceChannelName || '';
  bottom.appendChild(source);

  li.appendChild(bottom);

  li.addEventListener('click', () => {
    const url = item.applicationUrl || item.messageLink;
    if (url) chrome.tabs.create({ url });
  });

  return li;
}

function buildCatalogCard(item) {
  return buildCardShell(item);
}

function buildTrackedCard(item) {
  const li = buildCardShell(item);
  const status = trackedMap[item.id]?.status || 'want';

  const row = document.createElement('div');
  row.className = 'tracked-status-row';

  const wantBtn = document.createElement('button');
  wantBtn.className = `status-btn${status === 'want' ? ' active' : ''}`;
  wantBtn.dataset.status = 'want';
  wantBtn.textContent = 'Хочу подать';

  const appliedBtn = document.createElement('button');
  appliedBtn.className = `status-btn${status === 'applied' ? ' active' : ''}`;
  appliedBtn.dataset.status = 'applied';
  appliedBtn.textContent = 'Подано';

  const removeBtn = document.createElement('button');
  removeBtn.className = 'status-btn remove';
  removeBtn.textContent = '✕';

  [wantBtn, appliedBtn].forEach((btn) => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      trackedMap = await upsertTracked(item, btn.dataset.status);
      render();
    });
  });

  removeBtn.addEventListener('click', async (e) => {
    e.stopPropagation();
    trackedMap = await removeTracked(item.id);
    updateTrackedCount();
    render();
  });

  row.appendChild(wantBtn);
  row.appendChild(appliedBtn);
  row.appendChild(removeBtn);
  li.appendChild(row);
  return li;
}

function starIcon(active) {
  return `<svg width="14" height="14" viewBox="0 0 24 24" fill="${active ? 'currentColor' : 'none'}" stroke="currentColor" stroke-width="2"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>`;
}

function clockIcon() {
  return '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>';
}

function calendarIcon() {
  return '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/></svg>';
}

init();
