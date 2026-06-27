import { useEffect, useRef, useState } from 'react';
import {
  ArrowUp,
  CheckCircle,
  LayoutGrid,
  Lock,
  Search,
  Sparkles,
  X,
} from 'lucide-react';

const API = '/api';
const PAGE_SIZE = 20;

const EXAMPLES = [
  'Студент IT, ищу хакатоны и стажировки в AI',
  'Хочу стипендию на магистратуру за рубежом',
  'Ищу гранты для экологического проекта',
];

function deadlineBadgeClass(item) {
  if (item.isArchived) {
    return 'bg-slate-500/10 text-slate-400 border border-slate-500/20';
  }
  if (item.deadlineUrgent) {
    return 'bg-red-500/10 text-red-400 border border-red-500/20';
  }
  return 'bg-indigo-500/10 text-indigo-300 border border-indigo-500/20';
}

function OpportunityCard({ item, onOpen }) {
  const deadlineText = item.deadlineLabel || item.deadline;

  return (
    <article className="group bg-white/5 border border-white/5 rounded-3xl overflow-hidden flex flex-col hover:border-indigo-500/40 transition-all duration-300">
      <div className="p-7 flex-grow flex flex-col min-h-0">
        <div className="flex justify-between items-start mb-4 gap-3">
          <div className="flex items-center gap-2.5 min-w-0 flex-1">
            <span className="text-2xl shrink-0 leading-none">{item.emoji}</span>
            <span className="text-[11px] font-semibold uppercase tracking-wide text-slate-500 truncate">
              {item.sourceChannelName}
            </span>
          </div>
          <span
            className={`text-[10px] px-2.5 py-1 rounded-xl font-semibold shrink-0 max-w-[48%] text-right leading-snug ${deadlineBadgeClass(item)}`}
            title={item.deadline}
          >
            {deadlineText}
          </span>
        </div>

        <div className="mb-3 flex flex-wrap items-center gap-2">
          <span className="text-[10px] px-2.5 py-1 rounded-lg font-semibold bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
            {item.label}
          </span>
          {item.isArchived && (
            <span className="text-[10px] px-2.5 py-1 rounded-lg font-semibold bg-slate-500/10 text-slate-400 border border-slate-500/20">
              Архив
            </span>
          )}
        </div>

        <h2 className="text-lg font-bold mb-2.5 text-white group-hover:text-indigo-400 transition-colors line-clamp-2 break-words">
          {item.title}
        </h2>
        <p className="text-sm text-slate-400 line-clamp-3 mb-5 break-words leading-relaxed flex-grow">
          {item.description}
        </p>

        {item.features?.length > 0 && (
          <div className="space-y-2 mt-auto">
            {item.features.slice(0, 3).map((feat, i) => (
              <div key={i} className="flex items-start gap-2.5 text-sm text-slate-300">
                <CheckCircle size={15} className="text-indigo-500 shrink-0 mt-0.5" />
                <span className="line-clamp-2 break-words leading-snug">{feat}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="p-7 pt-0">
        <button
          type="button"
          onClick={() => onOpen(item)}
          className="w-full py-4 rounded-2xl bg-white/5 hover:bg-white/10 text-white font-bold transition border border-white/10"
        >
          Подробнее
        </button>
      </div>
    </article>
  );
}

function DetailModal({ selected, onClose }) {
  if (!selected) return null;

  return (
    <div className="fixed inset-0 bg-black/90 backdrop-blur-md z-50 flex items-center justify-center p-4">
      <div className="bg-[#0f172a] border border-indigo-500/40 max-w-lg w-full p-10 rounded-[40px] shadow-2xl relative">
        <button
          type="button"
          onClick={onClose}
          className="absolute top-6 right-6 text-slate-500 hover:text-white transition"
        >
          <X size={24} />
        </button>

        <div className="flex items-center gap-3 mb-4">
          <span className="text-3xl">{selected.emoji}</span>
          <span className="text-xs font-bold uppercase tracking-widest text-indigo-400">
            {selected.label}
          </span>
        </div>

        <h3 className="text-2xl font-bold mb-3 text-white">{selected.title}</h3>
        <p className="text-sm text-slate-400 mb-6 leading-relaxed">{selected.description}</p>

        <div className="text-sm text-slate-300 space-y-3 mb-8">
          <p>
            <span className="text-slate-500">Дедлайн:</span>{' '}
            {selected.deadlineLabel || selected.deadline}
          </p>
          <p>
            <span className="text-slate-500">Канал:</span> {selected.sourceChannelName}
          </p>
          {selected.requirements && (
            <p>
              <span className="text-slate-500">Требования:</span> {selected.requirements}
            </p>
          )}
          {selected.applicationUrl && (
            <p>
              <span className="text-slate-500">Заявка:</span>{' '}
              <a
                href={selected.applicationUrl}
                className="text-indigo-400 hover:underline break-all"
                target="_blank"
                rel="noreferrer"
              >
                {selected.applicationUrl}
              </a>
            </p>
          )}
          {selected.messageLink && (
            <p>
              <span className="text-slate-500">Пост:</span>{' '}
              <a
                href={selected.messageLink}
                className="text-indigo-400 hover:underline break-all"
                target="_blank"
                rel="noreferrer"
              >
                Открыть в Telegram
              </a>
            </p>
          )}
        </div>

        {selected.isPremium && (
          <div className="flex items-center gap-2 text-xs text-yellow-500/80 mb-4">
            <Lock size={14} />
            Есть прямая ссылка на заявку
          </div>
        )}

        <button
          type="button"
          onClick={onClose}
          className="w-full py-5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-2xl font-bold transition"
        >
          Закрыть
        </button>
      </div>
    </div>
  );
}

function PromptBox({ value, onChange, onSubmit, loading, placeholder }) {
  const canSend = value.trim().length >= 3 && !loading;

  const handleKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      if (canSend) onSubmit();
    }
  };

  return (
    <div className="relative bg-white/5 border border-white/10 rounded-[28px] shadow-2xl shadow-black/20 focus-within:border-indigo-500/50 transition-all">
      <textarea
        rows={4}
        placeholder={placeholder}
        className="w-full bg-transparent rounded-[28px] py-5 pl-6 pr-16 text-[15px] leading-relaxed text-white placeholder:text-slate-500 resize-none focus:outline-none"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
      />
      <button
        type="button"
        onClick={onSubmit}
        disabled={!canSend}
        className="absolute right-3 bottom-3 w-11 h-11 rounded-2xl flex items-center justify-center transition disabled:opacity-30 disabled:cursor-not-allowed bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/30"
      >
        <ArrowUp size={20} />
      </button>
    </div>
  );
}

function Pagination({ page, totalPages, total, onChange }) {
  if (totalPages <= 1) return null;

  const pages = [];
  const windowSize = 5;
  let start = Math.max(1, page - Math.floor(windowSize / 2));
  let end = Math.min(totalPages, start + windowSize - 1);
  start = Math.max(1, end - windowSize + 1);

  for (let i = start; i <= end; i += 1) {
    pages.push(i);
  }

  return (
    <nav className="flex flex-col sm:flex-row items-center justify-between gap-4 mt-8 pt-6 border-t border-white/5">
      <p className="text-sm text-slate-500 order-2 sm:order-1">
        {total} {total === 1 ? 'карточка' : total < 5 ? 'карточки' : 'карточек'} · стр. {page} из {totalPages}
      </p>
      <div className="flex items-center gap-1.5 order-1 sm:order-2">
        <button
          type="button"
          disabled={page <= 1}
          onClick={() => onChange(page - 1)}
          className="px-3 py-2 rounded-xl text-sm font-semibold bg-white/5 border border-white/10 text-slate-300 hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed transition"
        >
          Назад
        </button>
        {pages.map((n) => (
          <button
            key={n}
            type="button"
            onClick={() => onChange(n)}
            className={`min-w-[2.5rem] px-3 py-2 rounded-xl text-sm font-semibold transition border ${
              n === page
                ? 'bg-indigo-600 border-indigo-500 text-white'
                : 'bg-white/5 border-white/10 text-slate-300 hover:bg-white/10'
            }`}
          >
            {n}
          </button>
        ))}
        <button
          type="button"
          disabled={page >= totalPages}
          onClick={() => onChange(page + 1)}
          className="px-3 py-2 rounded-xl text-sm font-semibold bg-white/5 border border-white/10 text-slate-300 hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed transition"
        >
          Далее
        </button>
      </div>
    </nav>
  );
}

function CatalogBrowse({ onOpenItem }) {
  const [categories, setCategories] = useState([]);
  const [items, setItems] = useState([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [activeCategory, setActiveCategory] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch(`${API}/lumo/categories`)
      .then((r) => {
        if (!r.ok) throw new Error('Не удалось загрузить категории');
        return r.json();
      })
      .then(setCategories)
      .catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    setPage(1);
  }, [activeCategory, searchQuery]);

  useEffect(() => {
    const timer = setTimeout(async () => {
      setLoading(true);
      setError(null);
      const params = new URLSearchParams();
      if (activeCategory !== 'all') params.set('category', activeCategory);
      if (searchQuery.trim()) params.set('q', searchQuery.trim());
      params.set('page', String(page));
      params.set('page_size', String(PAGE_SIZE));
      try {
        const res = await fetch(`${API}/lumo/opportunities?${params}`);
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.detail || 'Не удалось загрузить посты — проверь, что бэкенд запущен');
        }
        const data = await res.json();
        setItems(data.items ?? []);
        setTotal(data.total ?? 0);
        setTotalPages(data.totalPages ?? 1);
      } catch (err) {
        setError(err.message);
        setItems([]);
        setTotal(0);
        setTotalPages(1);
      } finally {
        setLoading(false);
      }
    }, 200);
    return () => clearTimeout(timer);
  }, [activeCategory, searchQuery, page]);

  const activeLabel =
    categories.find((c) => c.type === activeCategory)?.label ?? 'Все';

  return (
    <section className="mb-16">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-8">
        <div>
          <div className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-slate-500 mb-3">
            <LayoutGrid size={14} />
            Каталог
          </div>
          <h2 className="text-2xl md:text-3xl font-bold text-white">
            Все возможности из базы
          </h2>
          <p className="text-slate-400 mt-2 text-sm">
            Актуальные и архивные возможности из базы Lumo
          </p>
        </div>

        <div className="relative w-full md:w-80">
          <input
            type="text"
            placeholder="Поиск..."
            className="w-full bg-white/5 border border-white/10 rounded-2xl py-3 px-12 text-sm focus:outline-none focus:border-indigo-500 transition-all"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
        </div>
      </div>

      <div className="flex flex-wrap gap-2 mb-6">
        {categories.map((cat) => (
          <button
            key={cat.type}
            type="button"
            onClick={() => setActiveCategory(cat.type)}
            className={`px-4 py-2.5 rounded-2xl text-sm font-bold transition border ${
              activeCategory === cat.type
                ? 'bg-indigo-600 border-indigo-500 text-white shadow-lg shadow-indigo-600/20'
                : 'bg-white/5 border-white/10 text-slate-300 hover:bg-white/10'
            }`}
          >
            {cat.emoji} {cat.label}
            <span className="ml-2 opacity-70">{cat.count}</span>
          </button>
        ))}
      </div>

      {error && (
        <div className="mb-6 p-4 rounded-2xl bg-red-500/10 border border-red-500/30 text-red-300 text-sm">
          {error}
        </div>
      )}

      <p className="text-sm text-slate-500 mb-6">
        {activeLabel}
        {!loading && ` · ${total} карточек`}
      </p>

      {loading ? (
        <div className="text-center text-slate-500 py-16">Загрузка...</div>
      ) : items.length === 0 ? (
        <div className="text-center text-slate-500 py-16">Ничего не найдено</div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
            {items.map((item) => (
              <OpportunityCard key={item.id} item={item} onOpen={onOpenItem} />
            ))}
          </div>
          <Pagination page={page} totalPages={totalPages} total={total} onChange={setPage} />
        </>
      )}
    </section>
  );
}

function ViewTabs({ active, onChange }) {
  return (
    <nav className="flex items-center gap-1 p-1 rounded-2xl bg-white/5 border border-white/10">
      <button
        type="button"
        onClick={() => onChange('ai')}
        className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-bold transition ${
          active === 'ai'
            ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/20'
            : 'text-slate-400 hover:text-white'
        }`}
      >
        <Sparkles size={16} />
        AI
      </button>
      <button
        type="button"
        onClick={() => onChange('catalog')}
        className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-bold transition ${
          active === 'catalog'
            ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/20'
            : 'text-slate-400 hover:text-white'
        }`}
      >
        <LayoutGrid size={16} />
        Каталог
      </button>
    </nav>
  );
}

export default function CatalogPreview() {
  const resultsRef = useRef(null);
  const [view, setView] = useState('catalog');
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [selected, setSelected] = useState(null);
  const [dbStatus, setDbStatus] = useState(null);

  useEffect(() => {
    fetch(`${API}/lumo/status`)
      .then((r) => r.json())
      .then(setDbStatus)
      .catch(() => setDbStatus({ connected: false, error: 'Бэкенд не запущен (порт 8000)' }));
  }, []);

  const openItem = async (item) => {
    const res = await fetch(`${API}/lumo/opportunities/${item.id}`);
    setSelected(await res.json());
  };

  const submitPrompt = async (text = prompt) => {
    const query = text.trim();
    if (query.length < 3 || loading) return;

    setLoading(true);
    setError(null);
    setPrompt(query);

    try {
      const res = await fetch(`${API}/lumo/match`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || 'Не удалось подобрать возможности');
      }
      const data = await res.json();
      setResult(data);
      setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const resetSearch = () => {
    setResult(null);
    setError(null);
    setPrompt('');
  };

  return (
    <div className="min-h-screen bg-[#0a0a0c] text-[#e2e8f0] font-sans">
      <header className="sticky top-0 z-40 border-b border-white/5 bg-[#0a0a0c]/90 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between gap-4">
          <h1 className="text-lg font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-purple-400 shrink-0">
            Lumo
          </h1>
          <ViewTabs active={view} onChange={setView} />
        </div>
        {dbStatus && (
          <div className="max-w-7xl mx-auto px-4 pb-3">
            {dbStatus.connected ? (
              <p className="text-xs text-emerald-400/90">
                База подключена · {dbStatus.total} карточек ({dbStatus.active} актуальных, {dbStatus.archived} в архиве)
              </p>
            ) : (
              <p className="text-xs text-red-400">
                {dbStatus.error || 'База не подключена'} — запусти бэкенд:{' '}
                <code className="text-red-300">сайт\backend → uvicorn main:app --port 8000</code>
              </p>
            )}
          </div>
        )}
      </header>

      <div className="max-w-7xl mx-auto px-4 py-8 md:py-12">
        {view === 'catalog' ? (
          <CatalogBrowse onOpenItem={openItem} />
        ) : (
          <section className="max-w-4xl mx-auto">
            <header className="text-center mb-10">
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-xs font-bold uppercase tracking-widest mb-6">
                <Sparkles size={14} />
                Lumo · подбор
              </div>
              <h2 className="text-3xl md:text-4xl font-bold text-white mb-4 tracking-tight">
                Что ты ищешь?
              </h2>
              <p className="text-slate-400 text-lg leading-relaxed">
                Напиши как в ChatGPT — Lumo подберёт из базы и покажет карточками
              </p>
            </header>

            <PromptBox
              value={prompt}
              onChange={setPrompt}
              onSubmit={() => submitPrompt()}
              loading={loading}
              placeholder="Например: Студент 3 курса, Python и ML. Ищу хакатоны, стажировки и гранты на AI-проекты..."
            />

            <div className="flex flex-wrap justify-center gap-2 mt-4">
              {EXAMPLES.map((example) => (
                <button
                  key={example}
                  type="button"
                  onClick={() => {
                    setPrompt(example);
                    submitPrompt(example);
                  }}
                  className="text-xs px-4 py-2 rounded-full bg-white/5 border border-white/10 text-slate-400 hover:text-white hover:bg-white/10 transition"
                >
                  {example}
                </button>
              ))}
            </div>

            {loading && (
              <div className="mt-10 text-center text-slate-500 animate-pulse">
                Lumo подбирает возможности...
              </div>
            )}

            {error && (
              <div className="mt-8 p-4 rounded-2xl bg-red-500/10 border border-red-500/30 text-red-300 text-sm text-center">
                {error}
              </div>
            )}

            {result && !loading && (
              <div ref={resultsRef} className="mt-12 space-y-8 pb-8">
                <div className="flex justify-end">
                  <div className="max-w-[85%] bg-indigo-600/20 border border-indigo-500/30 rounded-[24px] rounded-tr-md px-5 py-4 text-[15px] leading-relaxed text-white">
                    {result.query}
                  </div>
                </div>

                <div className="flex gap-4 items-start">
                  <div className="w-9 h-9 rounded-2xl bg-indigo-500/15 border border-indigo-500/30 flex items-center justify-center shrink-0">
                    <Sparkles size={18} className="text-indigo-400" />
                  </div>
                  <div className="flex-1 space-y-4">
                    <p className="text-[15px] text-slate-300 leading-relaxed">{result.message}</p>
                    {result.categories?.length > 0 && (
                      <div className="flex flex-wrap gap-2">
                        {result.categories.map((cat) => (
                          <span
                            key={cat.type}
                            className="text-xs px-3 py-1.5 rounded-full bg-white/5 border border-white/10 text-slate-300"
                          >
                            {cat.emoji} {cat.label}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                {result.items.length === 0 ? (
                  <div className="text-center text-slate-500 py-16 rounded-3xl bg-white/[0.02] border border-white/5">
                    Пока пусто — попробуй другую формулировку
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {result.items.map((item) => (
                      <OpportunityCard key={item.id} item={item} onOpen={openItem} />
                    ))}
                  </div>
                )}

                <button
                  type="button"
                  onClick={resetSearch}
                  className="w-full text-sm text-slate-500 hover:text-slate-300 transition"
                >
                  Новый запрос
                </button>
              </div>
            )}
          </section>
        )}
      </div>

      <DetailModal selected={selected} onClose={() => setSelected(null)} />
    </div>
  );
}
