import { useCallback, useEffect, useRef, useState } from 'react';
import { Loader2, Plus, Search, SlidersHorizontal } from 'lucide-react';
import { apiFetch, haptic } from '../api';
import OpportunityCard from './OpportunityCard';
import AddOpportunityModal from './AddOpportunityModal';
import { loadFavorites, toggleFavorite } from '../utils/localFeatures';

const PAGE_SIZE = 20;

const SORT_OPTIONS = [
  { id: 'relevance', label: 'По совпадению' },
  { id: 'newest', label: 'Новые' },
  { id: 'deadline', label: 'Дедлайн' },
];
const DEADLINE_OPTIONS = [
  { id: 'any', label: 'Любой срок' },
  { id: '3', label: 'До 3 дней' },
  { id: '7', label: 'До недели' },
  { id: '14', label: 'До 2 недель' },
];
const FORMAT_OPTIONS = [
  { id: 'any', label: 'Любой формат' },
  { id: 'online', label: 'Онлайн' },
  { id: 'offline', label: 'Офлайн' },
];
const TEAM_OPTIONS = [
  { id: 'any', label: 'Неважно' },
  { id: 'team', label: 'Команда' },
  { id: 'solo', label: 'Соло' },
];
const DEFAULT_FILTERS = { sort: 'deadline', deadlineWithinDays: 'any', format: 'any', team: 'any' };

function FilterSheet({ open, onClose, filters, onApply }) {
  const [draft, setDraft] = useState(filters);
  useEffect(() => {
    if (open) setDraft(filters);
  }, [open, filters]);
  if (!open) return null;

  const Group = ({ label, options, value, onChange }) => (
    <div className="mb-5">
      <p className="text-[11px] font-bold uppercase tracking-widest mb-2.5" style={{ color: 'var(--lumo-text-muted)' }}>
        {label}
      </p>
      <div className="flex flex-wrap gap-2">
        {options.map((o) => (
          <button
            key={o.id}
            type="button"
            onClick={() => {
              haptic('light');
              onChange(o.id);
            }}
            className={`px-3.5 py-2 rounded-xl text-[13px] font-semibold ${value === o.id ? 'lumo-filter-active' : 'lumo-filter-inactive'}`}
          >
            {o.label}
          </button>
        ))}
      </div>
    </div>
  );

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <div
        className="lumo-card w-full max-w-lg max-h-[85vh] overflow-y-auto rounded-t-[24px] p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <p className="text-[17px] font-bold mb-5">Фильтры</p>
        <Group label="Сортировка" options={SORT_OPTIONS} value={draft.sort} onChange={(v) => setDraft((p) => ({ ...p, sort: v }))} />
        <Group
          label="Дедлайн"
          options={DEADLINE_OPTIONS}
          value={draft.deadlineWithinDays}
          onChange={(v) => setDraft((p) => ({ ...p, deadlineWithinDays: v }))}
        />
        <Group label="Формат" options={FORMAT_OPTIONS} value={draft.format} onChange={(v) => setDraft((p) => ({ ...p, format: v }))} />
        <Group label="Команда" options={TEAM_OPTIONS} value={draft.team} onChange={(v) => setDraft((p) => ({ ...p, team: v }))} />
        <div className="flex gap-2 mt-2">
          <button
            type="button"
            onClick={() => {
              haptic('light');
              onApply(DEFAULT_FILTERS);
              onClose();
            }}
            className="flex-1 py-3 rounded-xl font-bold text-[13px]"
            style={{ background: 'var(--lumo-surface-muted)', color: 'var(--lumo-text)', border: '1px solid var(--lumo-border)' }}
          >
            Сбросить
          </button>
          <button
            type="button"
            onClick={() => {
              haptic('medium');
              onApply(draft);
              onClose();
            }}
            className="flex-1 py-3 rounded-xl font-bold text-[13px] text-white lumo-btn-primary"
          >
            Применить
          </button>
        </div>
      </div>
    </div>
  );
}

export default function CatalogView({ onOpenItem }) {
  const [categories, setCategories] = useState([]);
  const [items, setItems] = useState([]);
  const [activeCategory, setActiveCategory] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [filterSheetOpen, setFilterSheetOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [total, setTotal] = useState(0);
  const [addOpen, setAddOpen] = useState(false);
  const [favorites, setFavorites] = useState(() => loadFavorites());
  const favoriteIds = new Set(favorites.map((f) => f.id));
  const loadMoreRef = useRef(null);
  const requestIdRef = useRef(0);
  const bootstrappedRef = useRef(false);
  const activeFilterCount = Object.entries(filters).filter(([k, v]) => v !== DEFAULT_FILTERS[k]).length;

  const fetchPage = useCallback(async (offset, append, category = activeCategory, query = searchQuery) => {
    const requestId = ++requestIdRef.current;
    if (append) setLoadingMore(true);
    else setLoading(true);

    const params = new URLSearchParams();
    params.set('limit', String(PAGE_SIZE));
    params.set('offset', String(offset));
    params.set('sort', filters.sort);
    if (filters.deadlineWithinDays !== 'any') params.set('deadline_within_days', filters.deadlineWithinDays);
    if (filters.format !== 'any') params.set('format', filters.format);
    if (filters.team !== 'any') params.set('team', filters.team);
    if (category !== 'all') params.set('category', category);
    if (query.trim()) params.set('q', query.trim());

    try {
      const data = await apiFetch(`/lumo/opportunities?${params}`);
      if (requestId !== requestIdRef.current) return 0;

      const nextItems = data.items || [];
      setItems((prev) => (append ? [...prev, ...nextItems] : nextItems));
      setTotal(data.total ?? nextItems.length);
      setHasMore(Boolean(data.hasMore));
      return nextItems.length;
    } catch {
      if (requestId !== requestIdRef.current) return 0;
      if (!append) {
        setItems([]);
        setTotal(0);
        setHasMore(false);
      }
      return 0;
    } finally {
      if (requestId === requestIdRef.current) {
        setLoading(false);
        setLoadingMore(false);
      }
    }
  }, [activeCategory, searchQuery, filters]);

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      setLoading(true);
      setLoadError(null);
      try {
        const data = await apiFetch(`/lumo/catalog-bootstrap?limit=${PAGE_SIZE}`, {
          timeoutMs: 25000,
        });
        if (cancelled) return;
        setCategories(data.categories || []);
        setItems(data.items || []);
        setTotal(data.total ?? 0);
        setHasMore(Boolean(data.hasMore));
        bootstrappedRef.current = true;
      } catch (err) {
        if (!cancelled) {
          const fallbackCount = await fetchPage(0, false, 'all', '');
          if (fallbackCount > 0) {
            setLoadError(null);
          } else {
            setLoadError(err.message || 'Не удалось загрузить каталог');
          }
          try {
            const cats = await apiFetch('/lumo/categories');
            if (!cancelled) setCategories(cats);
          } catch {
            /* ignore */
          }
          bootstrappedRef.current = true;
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    bootstrap();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!bootstrappedRef.current) return undefined;
    const timer = setTimeout(() => {
      fetchPage(0, false);
    }, 120);
    return () => clearTimeout(timer);
  }, [activeCategory, searchQuery, filters, fetchPage]);

  useEffect(() => {
    const node = loadMoreRef.current;
    if (!node || !hasMore || loading || loadingMore) return undefined;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) {
          fetchPage(items.length, true);
        }
      },
      { root: null, rootMargin: '120px', threshold: 0 },
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, [fetchPage, hasMore, items.length, loading, loadingMore]);

  const visibleCategories = categories.filter((cat) => cat.type === 'all' || cat.count > 0);

  return (
    <div className="pb-8">
      <header className="mb-5 flex items-start justify-between gap-3">
        <div>
          <h1 className="text-[22px] font-bold mb-2">Каталог</h1>
          <p className="text-[13px]" style={{ color: 'var(--lumo-text-muted)' }}>
            Актуальные возможности из твоих каналов
            {!loading && total > 0 ? ` · ${total}` : ''}
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            haptic('light');
            setAddOpen(true);
          }}
          className="shrink-0 flex items-center gap-1.5 px-3 py-2 rounded-xl text-[12px] font-bold lumo-btn-primary"
        >
          <Plus size={16} />
          Добавить
        </button>
      </header>

      <div className="flex items-center gap-2 mb-4">
        <div className="relative flex-1">
          <input
            type="text"
            placeholder="Поиск по названию или теме..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-xl py-3 pl-10 pr-4 text-[14px] border focus:outline-none focus:border-[var(--lumo-accent)] transition-colors"
            style={{ background: 'var(--lumo-surface)', borderColor: 'var(--lumo-border)', color: 'var(--lumo-text)' }}
          />
          <Search
            className="absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none"
            size={16}
            style={{ color: 'var(--lumo-text-muted)' }}
          />
        </div>
        <button
          type="button"
          onClick={() => {
            haptic('light');
            setFilterSheetOpen(true);
          }}
          className="relative shrink-0 w-11 h-11 rounded-xl flex items-center justify-center border"
          style={{ background: 'var(--lumo-surface)', borderColor: 'var(--lumo-border)', color: 'var(--lumo-text)' }}
          aria-label="Фильтры"
        >
          <SlidersHorizontal size={17} />
          {activeFilterCount > 0 && (
            <span
              className="absolute -top-1 -right-1 w-4 h-4 rounded-full text-[9px] font-bold flex items-center justify-center text-white"
              style={{ background: 'var(--lumo-accent)' }}
            >
              {activeFilterCount}
            </span>
          )}
        </button>
      </div>

      <div className="flex gap-2 overflow-x-auto pb-1 mb-5 -mx-1 px-1 scrollbar-none">
        {visibleCategories.map((cat) => {
          const active = activeCategory === cat.type;
          return (
            <button
              key={cat.type}
              type="button"
              onClick={() => setActiveCategory(cat.type)}
              className={`shrink-0 px-4 py-2 rounded-full text-[13px] font-semibold transition ${
                active ? 'lumo-filter-active' : 'lumo-filter-inactive'
              }`}
            >
              {cat.type === 'all' ? 'Все' : cat.label}
            </button>
          );
        })}
      </div>

      {loadError && !loading && items.length === 0 && (
        <p className="text-center py-3 text-[12px] text-red-400 mb-2">{loadError}</p>
      )}

      {loading ? (
        <p className="text-center py-12 text-[13px]" style={{ color: 'var(--lumo-text-muted)' }}>
          Загрузка…
        </p>
      ) : items.length === 0 ? (
        <p className="text-center py-12 text-[13px]" style={{ color: 'var(--lumo-text-muted)' }}>
          Пока пусто — задай профиль во вкладке AI-поиск или добавь каналы в боте
        </p>
      ) : (
        <div className="grid grid-cols-1 gap-3">
          {items.map((item) => (
            <OpportunityCard
              key={item.id}
              item={item}
              onOpen={onOpenItem}
              isFavorite={favoriteIds.has(item.id)}
              onToggleFavorite={(it) => setFavorites(toggleFavorite(it))}
            />
          ))}
        </div>
      )}

      {!loading && items.length > 0 && (
        <div ref={loadMoreRef} className="py-6 flex justify-center min-h-[48px]">
          {loadingMore && (
            <div className="flex items-center gap-2 text-[13px]" style={{ color: 'var(--lumo-text-muted)' }}>
              <Loader2 size={16} className="animate-spin" />
              Загрузка…
            </div>
          )}
          {!loadingMore && !hasMore && (
            <p className="text-[12px]" style={{ color: 'var(--lumo-text-muted)' }}>
              Все {total} {total === 1 ? 'возможность' : total < 5 ? 'возможности' : 'возможностей'}
            </p>
          )}
        </div>
      )}

      <AddOpportunityModal open={addOpen} onClose={() => setAddOpen(false)} />
      <FilterSheet
        open={filterSheetOpen}
        onClose={() => setFilterSheetOpen(false)}
        filters={filters}
        onApply={setFilters}
      />
    </div>
  );
}
