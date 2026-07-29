import { CHECK_ALARM_NAME, CHECK_INTERVAL_MINUTES, NEW_CHECK_LIMIT } from './config.js';
import { fetchOpportunities, ApiError } from './api.js';
import {
  getAuth,
  getKnownIds,
  setKnownIds,
  getNewIds,
  setNewIds,
  setLastCheckedAt,
} from './storage.js';

async function updateBadge() {
  const newIds = await getNewIds();
  if (newIds.size > 0) {
    chrome.action.setBadgeText({ text: newIds.size > 99 ? '99+' : String(newIds.size) });
    chrome.action.setBadgeBackgroundColor({ color: '#fb923c' });
  } else {
    chrome.action.setBadgeText({ text: '' });
  }
}

export async function checkForNewOpportunities({ notify = true } = {}) {
  const { token } = await getAuth();
  if (!token) return { skipped: true };

  // Newest-first (not deadline-first) so freshly added contests with a distant
  // deadline are still caught, instead of only what's due soonest.
  let data;
  try {
    data = await fetchOpportunities({ sort: 'newest', limit: NEW_CHECK_LIMIT });
  } catch (err) {
    console.warn('[Lumo] catalog check failed', err instanceof ApiError ? err.message : err);
    return { skipped: true, error: true };
  }

  const items = data.items || [];
  const currentIds = items.map((item) => item.id);
  const knownIds = await getKnownIds();
  const isFirstRun = knownIds.size === 0;

  const freshItems = isFirstRun ? [] : items.filter((item) => !knownIds.has(item.id));

  if (freshItems.length > 0) {
    const existingNew = await getNewIds();
    freshItems.forEach((item) => existingNew.add(item.id));
    await setNewIds(existingNew);

    if (notify && freshItems.length > 0) {
      const titles = freshItems.slice(0, 2).map((item) => item.title).join('\n');
      const extra = freshItems.length > 2 ? `\nи ещё ${freshItems.length - 2}...` : '';
      chrome.notifications.create(`lumo-new-${Date.now()}`, {
        type: 'basic',
        iconUrl: chrome.runtime.getURL('icons/icon128.png'),
        title: freshItems.length === 1 ? 'Новый конкурс в Lumo' : `Новые возможности в Lumo (${freshItems.length})`,
        message: `${titles}${extra}`,
        priority: 1,
      });
    }
  }

  const merged = new Set(knownIds);
  currentIds.forEach((id) => merged.add(id));
  await setKnownIds(merged);
  await setLastCheckedAt(new Date().toISOString());
  await updateBadge();

  return { newCount: freshItems.length, total: data.total ?? currentIds.length };
}

export async function markAllSeen() {
  await setNewIds(new Set());
  await updateBadge();
}

chrome.runtime.onInstalled.addListener(() => {
  chrome.alarms.create(CHECK_ALARM_NAME, { periodInMinutes: CHECK_INTERVAL_MINUTES, delayInMinutes: 1 });
  updateBadge();
});

chrome.runtime.onStartup.addListener(() => {
  chrome.alarms.create(CHECK_ALARM_NAME, { periodInMinutes: CHECK_INTERVAL_MINUTES, delayInMinutes: 1 });
  updateBadge();
});

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === CHECK_ALARM_NAME) {
    checkForNewOpportunities({ notify: true });
  }
});

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type === 'lumo:check-now') {
    checkForNewOpportunities({ notify: false }).then(sendResponse);
    return true;
  }
  if (message?.type === 'lumo:mark-seen') {
    markAllSeen().then(() => sendResponse({ ok: true }));
    return true;
  }
  if (message?.type === 'lumo:refresh-badge') {
    updateBadge().then(() => sendResponse({ ok: true }));
    return true;
  }
  return false;
});
