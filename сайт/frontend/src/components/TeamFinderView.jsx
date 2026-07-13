import { useCallback, useEffect, useState } from 'react';
import { Loader2, Plus, Sparkles, Trash2, Users } from 'lucide-react';

import { apiFetch } from '../api.js';

const DEFAULT_FORM = {
  mode: 'seeking_team',
  displayName: '',
  prompt: '',
  telegram: '',
};

function ProfileCard({ item }) {
  const initials = (item.displayName || '?').slice(0, 2).toUpperCase();

  return (
    <article className="rounded-2xl border border-border bg-card p-5 flex flex-col gap-4 shadow-sm">
      <div className="flex items-start gap-3">
        <div className="w-11 h-11 rounded-full bg-primary/10 text-primary flex items-center justify-center text-sm font-bold shrink-0">
          {initials}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="font-semibold text-foreground truncate">{item.displayName}</h3>
            <span className="text-[11px] px-2 py-0.5 rounded-full bg-muted text-muted-foreground">
              {item.modeLabel}
            </span>
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            {item.roleLabel} · {item.cityLabel}
          </p>
        </div>
      </div>

      <div className="flex flex-wrap gap-1.5">
        {(item.skillLabels || []).slice(0, 8).map((label) => (
          <span
            key={label}
            className="text-[11px] px-2 py-1 rounded-lg bg-primary/10 text-primary border border-primary/15"
          >
            {label}
          </span>
        ))}
      </div>

      <p className="text-sm text-muted-foreground leading-relaxed line-clamp-4">{item.description}</p>

      {item.telegramUrl ? (
        <a
          href={item.telegramUrl}
          target="_blank"
          rel="noreferrer"
          className="mt-auto w-full text-center py-2.5 rounded-xl bg-primary text-primary-foreground text-sm font-semibold hover:opacity-90 transition-opacity"
        >
          Написать в Telegram
        </a>
      ) : (
        <div className="mt-auto text-xs text-muted-foreground text-center py-2">Контакт не указан</div>
      )}
    </article>
  );
}

export default function TeamFinderView({ authed, onNeedsAuth, profile }) {
  const [meta, setMeta] = useState(null);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filters, setFilters] = useState({ mode: '', role: '', city: '' });
  const [searchMessage, setSearchMessage] = useState(null);

  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(DEFAULT_FORM);
  const [myProfile, setMyProfile] = useState(null);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState(null);
  const [saveResult, setSaveResult] = useState(null);

  useEffect(() => {
    apiFetch('/team/meta')
      .then(setMeta)
      .catch(() => {});
  }, []);

  const loadMyProfile = useCallback(async () => {
    if (!authed) return;
    try {
      const data = await apiFetch('/team/profile/me');
      setMyProfile(data.profile);
      if (data.profile) {
        setForm({
          mode: data.profile.mode,
          displayName: data.profile.displayName || '',
          prompt: data.profile.description || '',
          telegram: data.profile.telegramContact || '',
        });
      }
    } catch {
      setMyProfile(null);
    }
  }, [authed]);

  const loadProfiles = useCallback(async () => {
    if (!authed) return;
    setLoading(true);
    setError(null);
    const params = new URLSearchParams();
    if (filters.mode) params.set('mode', filters.mode);
    if (filters.role) params.set('role', filters.role);
    if (filters.city) params.set('city', filters.city);
    if (searchQuery.trim()) params.set('query', searchQuery.trim());
    try {
      const data = await apiFetch(`/team/profiles?${params.toString()}`);
      setItems(data.items || []);
      setSearchMessage(data.searchMessage || null);
    } catch (err) {
      setError(err.message);
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [authed, filters, searchQuery]);

  useEffect(() => {
    if (authed) loadMyProfile();
  }, [authed, loadMyProfile]);

  useEffect(() => {
    if (!authed) return;
    const timer = setTimeout(loadProfiles, 250);
    return () => clearTimeout(timer);
  }, [authed, loadProfiles]);

  useEffect(() => {
    if (profile?.username && !form.telegram) {
      setForm((prev) => ({ ...prev, telegram: profile.username }));
    }
  }, [profile?.username, form.telegram]);

  const submitProfile = async () => {
    if (!authed) {
      onNeedsAuth?.();
      return;
    }
    const prompt = form.prompt.trim();
    if (prompt.length < 10) {
      setFormError('Опиши себя хотя бы в 10 символов — ИИ разметит навыки');
      return;
    }
    setSaving(true);
    setFormError(null);
    setSaveResult(null);
    try {
      const data = await apiFetch('/team/profile', {
        method: 'POST',
        body: JSON.stringify({
          prompt,
          mode: form.mode,
          displayName: form.displayName.trim() || undefined,
          telegram: form.telegram.trim() || undefined,
        }),
      });
      setMyProfile(data.profile);
      setSaveResult(data);
      setShowForm(false);
      loadProfiles();
    } catch (err) {
      setFormError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const removeProfile = async () => {
    if (!window.confirm('Удалить анкету из ленты?')) return;
    try {
      await apiFetch('/team/profile/me', { method: 'DELETE' });
      setMyProfile(null);
      setForm(DEFAULT_FORM);
      loadProfiles();
    } catch (err) {
      setFormError(err.message);
    }
  };

  if (!authed) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center px-4 text-center">
        <Users size={40} className="text-muted-foreground mb-4" />
        <h1 className="text-xl font-semibold mb-2">Поиск команды</h1>
        <p className="text-muted-foreground mb-6 max-w-md text-sm">
          Напиши промпт — ИИ разметит навыки и покажет людей для хакатонов и проектов
        </p>
        <button
          type="button"
          onClick={onNeedsAuth}
          className="px-5 py-2.5 rounded-full bg-foreground text-background text-sm font-semibold"
        >
          Войти
        </button>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 md:px-8 py-8">
      <div className="max-w-6xl mx-auto">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
          <div>
            <h1 className="text-xl font-semibold mb-1">Поиск команды</h1>
            <p className="text-muted-foreground text-sm">
              Опиши себя или кого ищешь — Lumo ИИ сам разметит роль и навыки
            </p>
          </div>
          <div className="flex gap-2">
            {myProfile && (
              <button
                type="button"
                onClick={removeProfile}
                className="px-4 py-2 rounded-xl border border-border text-sm text-muted-foreground hover:text-foreground inline-flex items-center gap-2"
              >
                <Trash2 size={16} />
                Удалить анкету
              </button>
            )}
            <button
              type="button"
              onClick={() => setShowForm((v) => !v)}
              className="px-4 py-2 rounded-xl bg-primary text-primary-foreground text-sm font-semibold inline-flex items-center gap-2"
            >
              <Plus size={16} />
              {myProfile ? 'Редактировать' : 'Анкета'}
            </button>
          </div>
        </div>

        {showForm && (
          <div className="mb-8 rounded-2xl border border-border bg-card p-5 md:p-6 space-y-4">
            <div className="flex gap-2">
              {(meta?.modes || []).map((m) => (
                <button
                  key={m.id}
                  type="button"
                  onClick={() => setForm((prev) => ({ ...prev, mode: m.id }))}
                  className={`flex-1 py-2.5 rounded-xl text-sm font-medium border transition-colors ${
                    form.mode === m.id
                      ? 'border-primary bg-primary/10 text-primary'
                      : 'border-border text-muted-foreground'
                  }`}
                >
                  {m.label}
                </button>
              ))}
            </div>

            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">Имя / ник (до 20)</label>
                <input
                  value={form.displayName}
                  onChange={(e) => setForm((p) => ({ ...p, displayName: e.target.value }))}
                  placeholder="Например: Данияр"
                  maxLength={20}
                  className="w-full px-4 py-3 rounded-xl border border-border bg-background"
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">Telegram</label>
                <input
                  value={form.telegram}
                  onChange={(e) => setForm((p) => ({ ...p, telegram: e.target.value }))}
                  placeholder="@username"
                  className="w-full px-4 py-3 rounded-xl border border-border bg-background"
                />
              </div>
            </div>

            <div>
              <label className="text-xs text-muted-foreground mb-1 block">
                Промпт — ИИ сам выберет роль и навыки (до 300 симв.)
              </label>
              <textarea
                value={form.prompt}
                onChange={(e) => setForm((p) => ({ ...p, prompt: e.target.value }))}
                maxLength={300}
                rows={4}
                placeholder="Например: 16 лет, знаю Python и React, ищу команду на хакатон в Алматы"
                className="w-full px-4 py-3 rounded-xl border border-border bg-background resize-none"
              />
              <p className="text-xs text-muted-foreground mt-1 text-right">{form.prompt.length}/300</p>
            </div>

            {formError && <p className="text-sm text-red-500">{formError}</p>}

            <button
              type="button"
              onClick={submitProfile}
              disabled={saving}
              className="w-full md:w-auto px-6 py-3 rounded-xl bg-primary text-primary-foreground font-semibold inline-flex items-center justify-center gap-2 disabled:opacity-60"
            >
              {saving ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
              {saving ? 'ИИ размечает…' : 'Сохранить — ИИ разметит навыки'}
            </button>
          </div>
        )}

        {saveResult?.parsed && (
          <div className="mb-6 rounded-xl border border-primary/20 bg-primary/5 px-4 py-3 text-sm">
            <span className="text-muted-foreground">ИИ разметил: </span>
            <span className="font-medium">{saveResult.profile.roleLabel}</span>
            {(saveResult.profile.skillLabels || []).length > 0 && (
              <span className="text-muted-foreground">
                {' '}
                · {(saveResult.profile.skillLabels || []).join(', ')}
              </span>
            )}
          </div>
        )}

        <div className="rounded-2xl border border-border bg-card/50 p-4 mb-6 space-y-4">
          <div>
            <label className="text-xs text-muted-foreground mb-1 block flex items-center gap-1">
              <Sparkles size={12} /> Поиск по промпту — кого ищешь?
            </label>
            <input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Например: backend на Python для хакатона"
              className="w-full px-4 py-3 rounded-xl border border-border bg-background"
            />
            {searchMessage && <p className="text-xs text-primary mt-2">{searchMessage}</p>}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <select
              value={filters.mode}
              onChange={(e) => setFilters((p) => ({ ...p, mode: e.target.value }))}
              className="px-3 py-2.5 rounded-xl border border-border bg-background text-sm"
            >
              <option value="">Все типы</option>
              {(meta?.modes || []).map((m) => (
                <option key={m.id} value={m.id}>
                  {m.label}
                </option>
              ))}
            </select>
            <select
              value={filters.role}
              onChange={(e) => setFilters((p) => ({ ...p, role: e.target.value }))}
              className="px-3 py-2.5 rounded-xl border border-border bg-background text-sm"
            >
              <option value="">Все роли</option>
              {(meta?.roles || []).map((r) => (
                <option key={r.id} value={r.id}>
                  {r.label}
                </option>
              ))}
            </select>
            <select
              value={filters.city}
              onChange={(e) => setFilters((p) => ({ ...p, city: e.target.value }))}
              className="px-3 py-2.5 rounded-xl border border-border bg-background text-sm"
            >
              <option value="">Все города</option>
              {(meta?.cities || []).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {error && <p className="text-red-500 text-sm mb-4">{error}</p>}

        {loading ? (
          <p className="text-muted-foreground text-center py-16">Загрузка…</p>
        ) : items.length === 0 ? (
          <p className="text-muted-foreground text-center py-16">
            Пока никого нет — создай первую анкету
          </p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {items.map((item) => (
              <ProfileCard key={item.id} item={item} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
