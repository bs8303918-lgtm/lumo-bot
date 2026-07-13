import { useCallback, useEffect, useState } from 'react';
import { Loader2, Plus, Sparkles, Trash2 } from 'lucide-react';

import { apiFetch, haptic } from '../api';

const DEFAULT_FORM = {
  mode: 'seeking_team',
  displayName: '',
  prompt: '',
  telegram: '',
};

function ProfileCard({ item, isOwn = false }) {
  const initials = (item.displayName || '?').slice(0, 2).toUpperCase();

  return (
    <article
      className="lumo-card p-4 flex flex-col gap-3"
      style={isOwn ? { borderColor: 'var(--lumo-accent)', boxShadow: '0 0 0 1px color-mix(in srgb, var(--lumo-accent) 35%, transparent)' } : undefined}
    >
      {isOwn && (
        <p className="text-[10px] font-semibold uppercase tracking-wide" style={{ color: 'var(--lumo-accent)' }}>
          Твоя анкета
        </p>
      )}
      <div className="flex items-start gap-3">
        <div
          className="w-10 h-10 rounded-full flex items-center justify-center text-xs font-bold shrink-0"
          style={{ background: 'color-mix(in srgb, var(--lumo-accent) 18%, transparent)', color: 'var(--lumo-accent)' }}
        >
          {initials}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="font-semibold text-[15px] truncate">{item.displayName}</h3>
            <span className="text-[10px] px-2 py-0.5 rounded-full" style={{ background: 'var(--lumo-border)', color: 'var(--lumo-text-muted)' }}>
              {item.modeLabel}
            </span>
          </div>
          <p className="text-[11px] mt-0.5" style={{ color: 'var(--lumo-text-muted)' }}>
            {item.roleLabel} · {item.cityLabel}
          </p>
        </div>
      </div>

      <div className="flex flex-wrap gap-1.5">
        {(item.skillLabels || []).slice(0, 6).map((label) => (
          <span
            key={label}
            className="text-[10px] px-2 py-1 rounded-lg"
            style={{
              background: 'color-mix(in srgb, var(--lumo-accent) 12%, transparent)',
              color: 'var(--lumo-accent)',
            }}
          >
            {label}
          </span>
        ))}
      </div>

      <p className="text-[13px] leading-relaxed line-clamp-4" style={{ color: 'var(--lumo-text-muted)' }}>
        {item.description}
      </p>

      {item.telegramUrl ? (
        <a
          href={item.telegramUrl}
          target="_blank"
          rel="noreferrer"
          onClick={() => haptic('light')}
          className="mt-auto w-full text-center py-2.5 rounded-xl text-[13px] font-semibold text-white"
          style={{ background: 'var(--lumo-accent)' }}
        >
          Написать в Telegram
        </a>
      ) : null}
    </article>
  );
}

export default function TeamFinderView({ profile, onProfileRefresh }) {
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
  const [saveTags, setSaveTags] = useState(null);

  useEffect(() => {
    apiFetch('/team/meta').then(setMeta).catch(() => {});
  }, []);

  const loadMyProfile = useCallback(async () => {
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
  }, []);

  const loadProfiles = useCallback(async () => {
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
  }, [filters, searchQuery]);

  useEffect(() => {
    loadMyProfile();
  }, [loadMyProfile]);

  useEffect(() => {
    const timer = setTimeout(loadProfiles, 250);
    return () => clearTimeout(timer);
  }, [loadProfiles]);

  useEffect(() => {
    if (profile?.username && !form.telegram) {
      setForm((prev) => ({ ...prev, telegram: profile.username }));
    }
  }, [profile?.username, form.telegram]);

  const submitProfile = async () => {
    const prompt = form.prompt.trim();
    if (prompt.length < 10) {
      setFormError('Минимум 10 символов в описании');
      return;
    }
    setSaving(true);
    setFormError(null);
    haptic('light');
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
      setSaveTags(data.profile);
      setShowForm(false);
      onProfileRefresh?.();
      await loadMyProfile();
      await loadProfiles();
      haptic('success');
    } catch (err) {
      setFormError(err.message);
      haptic('error');
    } finally {
      setSaving(false);
    }
  };

  const removeProfile = async () => {
    try {
      await apiFetch('/team/profile/me', { method: 'DELETE' });
      setMyProfile(null);
      setForm(DEFAULT_FORM);
      loadProfiles();
      haptic('light');
    } catch (err) {
      setFormError(err.message);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-[17px] font-bold">Поиск команды</h2>
          <p className="text-[12px] mt-1" style={{ color: 'var(--lumo-text-muted)' }}>
            Промпт → ИИ разметит навыки
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            haptic('light');
            setShowForm((v) => !v);
          }}
          className="shrink-0 px-3 py-2 rounded-xl text-[12px] font-semibold text-white inline-flex items-center gap-1"
          style={{ background: 'var(--lumo-accent)' }}
        >
          <Plus size={14} />
          {myProfile ? 'Правка' : 'Анкета'}
        </button>
      </div>

      {showForm && (
        <div className="lumo-card p-4 space-y-3">
          <div className="flex gap-2">
            {(meta?.modes || []).map((m) => (
              <button
                key={m.id}
                type="button"
                onClick={() => setForm((prev) => ({ ...prev, mode: m.id }))}
                className="flex-1 py-2 rounded-xl text-[11px] font-semibold border"
                style={{
                  borderColor: form.mode === m.id ? 'var(--lumo-accent)' : 'var(--lumo-border)',
                  color: form.mode === m.id ? 'var(--lumo-accent)' : 'var(--lumo-text-muted)',
                }}
              >
                {m.label}
              </button>
            ))}
          </div>

          <input
            value={form.displayName}
            onChange={(e) => setForm((p) => ({ ...p, displayName: e.target.value }))}
            placeholder="Имя / ник"
            maxLength={20}
            className="lumo-input w-full"
          />
          <input
            value={form.telegram}
            onChange={(e) => setForm((p) => ({ ...p, telegram: e.target.value }))}
            placeholder="@telegram"
            className="lumo-input w-full"
          />
          <textarea
            value={form.prompt}
            onChange={(e) => setForm((p) => ({ ...p, prompt: e.target.value }))}
            maxLength={300}
            rows={4}
            placeholder="16 лет, Python, ищу команду на хакатон в Алматы"
            className="lumo-input w-full resize-none"
          />

          {formError && <p className="text-[12px] text-red-400">{formError}</p>}

          <button
            type="button"
            onClick={submitProfile}
            disabled={saving}
            className="w-full py-3 rounded-xl text-[13px] font-semibold text-white inline-flex items-center justify-center gap-2 disabled:opacity-60"
            style={{ background: 'var(--lumo-accent)' }}
          >
            {saving ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
            {saving ? 'ИИ размечает…' : 'Сохранить'}
          </button>

          {myProfile && (
            <button type="button" onClick={removeProfile} className="w-full text-[12px] text-red-400 inline-flex items-center justify-center gap-1">
              <Trash2 size={14} /> Удалить анкету
            </button>
          )}
        </div>
      )}

      {saveTags && (
        <div className="lumo-card p-3 text-[12px]">
          ИИ: <strong>{saveTags.roleLabel}</strong>
          {(saveTags.skillLabels || []).length > 0 && ` · ${saveTags.skillLabels.join(', ')}`}
        </div>
      )}

      <div className="lumo-card p-3 space-y-3">
        <input
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Кого ищешь? backend Python…"
          className="lumo-input w-full"
        />
        {searchMessage && <p className="text-[11px]" style={{ color: 'var(--lumo-accent)' }}>{searchMessage}</p>}

        <div className="grid grid-cols-3 gap-2">
          <select value={filters.mode} onChange={(e) => setFilters((p) => ({ ...p, mode: e.target.value }))} className="lumo-input text-[11px] py-2">
            <option value="">Тип</option>
            {(meta?.modes || []).map((m) => (
              <option key={m.id} value={m.id}>{m.label}</option>
            ))}
          </select>
          <select value={filters.role} onChange={(e) => setFilters((p) => ({ ...p, role: e.target.value }))} className="lumo-input text-[11px] py-2">
            <option value="">Роль</option>
            {(meta?.roles || []).map((r) => (
              <option key={r.id} value={r.id}>{r.label}</option>
            ))}
          </select>
          <select value={filters.city} onChange={(e) => setFilters((p) => ({ ...p, city: e.target.value }))} className="lumo-input text-[11px] py-2">
            <option value="">Город</option>
            {(meta?.cities || []).map((c) => (
              <option key={c.id} value={c.id}>{c.label}</option>
            ))}
          </select>
        </div>
      </div>

      {error && <p className="text-[12px] text-red-400">{error}</p>}

      {loading ? (
        <p className="text-center py-10 text-[13px]" style={{ color: 'var(--lumo-text-muted)' }}>Загрузка…</p>
      ) : !myProfile && items.length === 0 ? (
        <p className="text-center py-10 text-[13px]" style={{ color: 'var(--lumo-text-muted)' }}>
          Пока пусто — создай анкету
        </p>
      ) : (
        <div className="space-y-3">
          {myProfile && <ProfileCard item={myProfile} isOwn />}
          {items.map((item) => (
            <ProfileCard key={item.id} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}
