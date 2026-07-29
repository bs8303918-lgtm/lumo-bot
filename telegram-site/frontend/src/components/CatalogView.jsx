import { useCallback, useEffect, useRef, useState } from 'react';
import { Loader2, Plus, Search } from 'lucide-react';
import { apiFetch, haptic } from '../api';
import OpportunityCard from './OpportunityCard';
import AddOpportunityModal from './AddOpportunityModal';
import { loadFavorites, toggleFavorite } from '../utils/localFeatures';

const PAGE_SIZE = 20;

export default function CatalogView({ onOpenItem }) {
  const [categories, setCategories] = useState([]);
  const [items, setItems] = useState([]);
  const [activeCategory, setActiveCategory] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
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

  const fetchPage = useCallback(async (offset, append, category = activeCategory, query = searchQuery) => {
    const requestId = ++requestIdRef.current;
    if (append) setLoadingMore(true);
    else setLoading(true);

    const params = new URLSearchParams();
    params.set('limit', String(PAGE_SIZE));
    params.set('offset', String(offset));
    params.set('sort', 'deadline');
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
  }, [activeCategory, searchQuery]);

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
    if (activeCategory === 'all' && !searchQuery.trim()) return undefined;
    const timer = setTimeout(() => {
      fetchPage(0, false);
    }, 120);
    return () => clearTimeout(timer);
  }, [activeCategory, searchQuery, fetchPage]);

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

      <div className="relative mb-4">
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
    </div>
  );
}
