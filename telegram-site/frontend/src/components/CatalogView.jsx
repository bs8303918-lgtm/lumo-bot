import { useEffect, useState } from 'react';
import { Plus, Search } from 'lucide-react';
import { apiFetch, haptic } from '../api';
import OpportunityCard from './OpportunityCard';
import AddOpportunityModal from './AddOpportunityModal';

export default function CatalogView({ onOpenItem }) {
  const [categories, setCategories] = useState([]);
  const [items, setItems] = useState([]);
  const [activeCategory, setActiveCategory] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [addOpen, setAddOpen] = useState(false);

  useEffect(() => {
    apiFetch('/lumo/categories').then(setCategories).catch(() => {});
  }, []);

  useEffect(() => {
    const timer = setTimeout(async () => {
      setLoading(true);
      const params = new URLSearchParams();
      if (activeCategory !== 'all') params.set('category', activeCategory);
      if (searchQuery.trim()) params.set('q', searchQuery.trim());
      const qs = params.toString();
      try {
        setItems(await apiFetch(`/lumo/opportunities${qs ? `?${qs}` : ''}`));
      } catch {
        setItems([]);
      } finally {
        setLoading(false);
      }
    }, 200);
    return () => clearTimeout(timer);
  }, [activeCategory, searchQuery]);

  const visibleCategories = categories.filter((cat) => cat.type === 'all' || cat.count > 0);

  return (
    <div className="pb-8">
      <header className="mb-5 flex items-start justify-between gap-3">
        <div>
          <h1 className="text-[22px] font-bold mb-2">Каталог</h1>
          <p className="text-[13px]" style={{ color: 'var(--lumo-text-muted)' }}>
            Актуальные возможности из твоих каналов
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
            <OpportunityCard key={item.id} item={item} onOpen={onOpenItem} />
          ))}
        </div>
      )}
      <AddOpportunityModal open={addOpen} onClose={() => setAddOpen(false)} />
    </div>
  );
}
