import { useCallback, useEffect, useMemo, useState } from 'react';
import { RefreshCw, Search } from 'lucide-react';
import { apiFetch, haptic } from '../api';

function userRef(item) {
  if (item.username) return `@${item.username}`;
  if (item.telegramId != null) return `id${item.telegramId}`;
  return '?';
}

function formatUpdated(iso) {
  if (!iso) return '';
  const dt = new Date(iso);
  const now = new Date();
  const diffDays = Math.floor((now - dt) / (1000 * 60 * 60 * 24));
  if (diffDays <= 0) return 'сегодня';
  if (diffDays === 1) return 'вчера';
  return `${diffDays} дн назад`;
}

function TagBadge({ tag, muted = false }) {
  return (
    <span
      className="text-[10px] font-semibold px-2 py-0.5 rounded-full shrink-0 inline-flex items-center gap-0.5"
      style={
        muted
          ? { background: 'var(--lumo-surface-muted)', color: 'var(--lumo-text-muted)' }
          : { background: 'var(--lumo-admin-soft)', color: 'var(--lumo-admin-accent)' }
      }
    >
      <span>{tag.emoji}</span>
      <span>{tag.label}</span>
    </span>
  );
}

function PromptCard({ item }) {
  const tags = [...(item.types || []), ...(item.domains || [])];

  return (
    <article
      className="lumo-card p-4 space-y-2.5"
      style={{ borderLeft: item.isBroad ? '3px solid #f97316' : undefined }}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-[14px] font-bold truncate">{userRef(item)}</p>
          <p className="text-[11px]" style={{ color: 'var(--lumo-text-muted)' }}>
            db {item.id}
            {item.updatedAt ? ` · ${formatUpdated(item.updatedAt)}` : ''}
          </p>
        </div>
        {item.isBroad && (
          <span
            className="text-[10px] font-bold px-2 py-0.5 rounded-full shrink-0"
            style={{ background: 'rgba(249, 115, 22, 0.15)', color: '#f97316' }}
          >
            широкий
          </span>
        )}
      </div>

      <p className="text-[13px] leading-relaxed whitespace-pre-wrap break-words">{item.query}</p>

      {(tags.length > 0 || item.formats?.length > 0) && (
        <div className="flex flex-wrap gap-1.5 pt-0.5">
          {tags.map((tag) => (
            <TagBadge key={`${tag.kind}-${tag.key}`} tag={tag} />
          ))}
          {(item.formats || []).map((fmt) => (
            <TagBadge
              key={`fmt-${fmt.key}`}
              tag={{ emoji: fmt.key === 'online' ? '🌐' : '📍', label: fmt.label }}
              muted
            />
          ))}
        </div>
      )}
    </article>
  );
}

export default function InterestPromptsView() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [draftSearch, setDraftSearch] = useState('');
  const [category, setCategory] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (search.trim()) params.set('search', search.trim());
      if (category) params.set('category', category);
      const qs = params.toString();
      setData(await apiFetch(`/admin/interest-prompts${qs ? `?${qs}` : ''}`));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [search, category]);

  useEffect(() => {
    load();
  }, [load]);

  const summary = useMemo(() => data?.categorySummary || [], [data]);

  const applySearch = () => {
    haptic('light');
    setSearch(draftSearch);
  };

  return (
    <div className="space-y-4 pb-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-[18px] font-bold">Промпты интересов</h2>
          <p className="text-[12px]" style={{ color: 'var(--lumo-text-muted)' }}>
            {data ? `${data.withInterest} профилей · показано ${data.total}` : 'Загрузка…'}
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            haptic('light');
            load();
          }}
          className="w-9 h-9 rounded-xl flex items-center justify-center"
          style={{ color: 'var(--lumo-text-muted)' }}
          aria-label="Обновить"
        >
          <RefreshCw size={16} />
        </button>
      </div>

      <div className="flex gap-2">
        <div
          className="flex-1 flex items-center gap-2 px-3 py-2.5 rounded-xl"
          style={{ background: 'var(--lumo-surface-muted)' }}
        >
          <Search size={15} style={{ color: 'var(--lumo-text-muted)' }} />
          <input
            type="search"
            value={draftSearch}
            onChange={(e) => setDraftSearch(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') applySearch();
            }}
            placeholder="Поиск по тексту, @username, db id…"
            className="flex-1 bg-transparent text-[13px] outline-none min-w-0"
            style={{ color: 'var(--lumo-text)' }}
          />
        </div>
        <button
          type="button"
          onClick={applySearch}
          className="px-3 py-2.5 rounded-xl text-[12px] font-bold text-white shrink-0"
          style={{ background: 'var(--lumo-admin-accent)' }}
        >
          Найти
        </button>
      </div>

      {summary.length > 0 && (
        <div className="flex gap-2 overflow-x-auto scrollbar-none -mx-1 px-1 pb-1">
          <button
            type="button"
            onClick={() => {
              haptic('light');
              setCategory('');
            }}
            className="shrink-0 px-3 py-1.5 rounded-full text-[11px] font-semibold"
            style={
              !category
                ? { background: 'var(--lumo-admin-accent)', color: '#fff' }
                : { background: 'var(--lumo-surface-muted)', color: 'var(--lumo-text-muted)' }
            }
          >
            Все
          </button>
          {summary.map((row) => (
            <button
              key={row.key}
              type="button"
              onClick={() => {
                haptic('light');
                setCategory(row.key);
              }}
              className="shrink-0 px-3 py-1.5 rounded-full text-[11px] font-semibold whitespace-nowrap"
              style={
                category === row.key
                  ? { background: 'var(--lumo-admin-accent)', color: '#fff' }
                  : { background: 'var(--lumo-surface-muted)', color: 'var(--lumo-text-muted)' }
              }
            >
              {row.emoji} {row.label} · {row.count}
            </button>
          ))}
        </div>
      )}

      {loading && !data && (
        <p className="text-center py-12 text-[13px]" style={{ color: 'var(--lumo-text-muted)' }}>
          Загрузка промптов…
        </p>
      )}

      {error && (
        <div className="text-center py-12">
          <p className="text-red-400 text-[13px] mb-3">{error}</p>
          <button
            type="button"
            onClick={load}
            className="text-[13px] font-semibold"
            style={{ color: 'var(--lumo-admin-accent)' }}
          >
            Повторить
          </button>
        </div>
      )}

      {data && !error && (
        <div className="space-y-3">
          {data.items.length === 0 ? (
            <p className="text-center py-12 text-[13px]" style={{ color: 'var(--lumo-text-muted)' }}>
              Ничего не найдено
            </p>
          ) : (
            data.items.map((item) => <PromptCard key={item.id} item={item} />)
          )}
        </div>
      )}
    </div>
  );
}
