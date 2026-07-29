const KEYS = {
  token: 'lumo_auth_token',
  account: 'lumo_auth_account',
  knownIds: 'lumo_known_ids',
  newIds: 'lumo_new_ids',
  lastCheckedAt: 'lumo_last_checked_at',
  tracked: 'lumo_tracked',
};

function get(keys) {
  return new Promise((resolve) => chrome.storage.local.get(keys, resolve));
}

function set(items) {
  return new Promise((resolve) => chrome.storage.local.set(items, resolve));
}

export async function getAuth() {
  const data = await get([KEYS.token, KEYS.account]);
  return { token: data[KEYS.token] || null, account: data[KEYS.account] || null };
}

export async function setAuth(token, account) {
  await set({ [KEYS.token]: token, [KEYS.account]: account });
}

export async function clearAuth() {
  await new Promise((resolve) => chrome.storage.local.remove([KEYS.token, KEYS.account], resolve));
}

export async function getKnownIds() {
  const data = await get([KEYS.knownIds]);
  return new Set(data[KEYS.knownIds] || []);
}

export async function setKnownIds(idSet) {
  await set({ [KEYS.knownIds]: Array.from(idSet) });
}

export async function getNewIds() {
  const data = await get([KEYS.newIds]);
  return new Set(data[KEYS.newIds] || []);
}

export async function setNewIds(idSet) {
  await set({ [KEYS.newIds]: Array.from(idSet) });
}

export async function getLastCheckedAt() {
  const data = await get([KEYS.lastCheckedAt]);
  return data[KEYS.lastCheckedAt] || null;
}

export async function setLastCheckedAt(iso) {
  await set({ [KEYS.lastCheckedAt]: iso });
}

export async function getTracked() {
  const data = await get([KEYS.tracked]);
  return data[KEYS.tracked] || {};
}

export async function setTracked(map) {
  await set({ [KEYS.tracked]: map });
}

export async function upsertTracked(item, status) {
  const map = await getTracked();
  map[item.id] = { item, status, updatedAt: new Date().toISOString() };
  await setTracked(map);
  return map;
}

export async function removeTracked(id) {
  const map = await getTracked();
  delete map[id];
  await setTracked(map);
  return map;
}
