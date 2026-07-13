import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Moon, Sun } from 'lucide-react';
import {
  apiFetch,
  authDisplayName,
  clearAuth,
  initTelegramApp,
  isAuthenticated,
  syncSession,
} from './api.js';
import AppSidebar from './components/AppSidebar.jsx';
import AuthModal from './components/AuthModal.jsx';
import ChatView from './components/ChatView.jsx';
import DetailModal from './components/DetailModal.jsx';
import OpportunityCard from './components/OpportunityCard.jsx';
import CatalogFilters, { DEFAULT_CATALOG_FILTERS } from './components/CatalogFilters.jsx';
import TractionView from './components/TractionView.jsx';
import TeamFinderView from './components/TeamFinderView.jsx';
import { buildCatalogQuery } from './constants/catalogFilters.js';
import { LUMO_PRICING_PLANS, Pricing } from '@/components/ui/pricing';

const CATALOG_PAGE_SIZE = 24;

function CatalogPanel({ onOpenItem, authed, onNeedsAuth }) {
  const [items, setItems] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');
  const [error, setError] = useState(null);
  const [total, setTotal] = useState(0);
  const [draftFilters, setDraftFilters] = useState(DEFAULT_CATALOG_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState(DEFAULT_CATALOG_FILTERS);

  useEffect(() => {
    if (!authed) {
      setCategories([]);
      return;
    }
    apiFetch('/lumo/categories')
      .then((data) => setCategories(Array.isArray(data) ? data : []))
      .catch(() => setCategories([]));
  }, [authed]);

  useEffect(() => {
    if (!authed) {
      setItems([]);
      setLoading(false);
      return;
    }

    const timer = setTimeout(async () => {
      setLoading(true);
      setError(null);
      const qs = buildCatalogQuery({
        query,
        types: appliedFilters.types,
        sort: appliedFilters.sort,
        cashPrize: appliedFilters.cashPrize,
        pageSize: CATALOG_PAGE_SIZE,
      });
      try {
        const data = await apiFetch(`/lumo/opportunities?${qs}`);
        setItems(data.items ?? []);
        setTotal(data.total ?? 0);
      } catch (err) {
        if (err.needsAuth) onNeedsAuth();
        setError(err.message);
        setItems([]);
        setTotal(0);
      } finally {
        setLoading(false);
      }
    }, 200);
    return () => clearTimeout(timer);
  }, [query, appliedFilters, authed, onNeedsAuth]);

  const applyFilters = () => setAppliedFilters({ ...draftFilters });

  const resetFilters = () => {
    setDraftFilters(DEFAULT_CATALOG_FILTERS);
    setAppliedFilters(DEFAULT_CATALOG_FILTERS);
  };

  if (!authed) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center px-4 text-center">
        <h1 className="text-xl font-semibold mb-2">Каталог</h1>
        <p className="text-muted-foreground mb-6 max-w-md text-sm">Войди, чтобы открыть базу конкурсов</p>
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
        <div className="mb-6">
          <h1 className="text-xl font-semibold mb-2">Каталог</h1>
          <p className="text-muted-foreground text-sm">
            Актуальные возможности из базы Lumo · сначала самые новые
          </p>
        </div>

        <div className="flex flex-col lg:flex-row gap-6 lg:gap-8">
          <div className="lg:w-72 shrink-0">
            <CatalogFilters
              categories={categories}
              draft={draftFilters}
              onDraftChange={setDraftFilters}
              onApply={applyFilters}
              onReset={resetFilters}
            />
          </div>

          <div className="flex-1 min-w-0">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Поиск по возможностям…"
              className="w-full mb-4 px-4 py-3 rounded-2xl border border-border bg-card text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/40"
            />

            <p className="text-sm text-muted-foreground mb-6">
              {loading ? 'Загрузка…' : `Показано ${items.length} из ${total} возможностей`}
            </p>

            {error && <p className="text-red-500 text-sm mb-4">{error}</p>}

            {loading ? (
              <p className="text-muted-foreground text-center py-16">Загрузка…</p>
            ) : items.length === 0 ? (
              <p className="text-muted-foreground text-center py-16">Ничего не найдено</p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                {items.map((item) => (
                  <OpportunityCard key={item.id} item={item} onOpen={onOpenItem} />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function PricingPanel() {
  return (
    <div className="flex-1 overflow-y-auto">
      <Pricing
        plans={LUMO_PRICING_PLANS}
        title="Тарифы Lumo"
        description={'Начни бесплатно с 3 запросами.\nПереходи на платный план, когда нужно больше.'}
      />
    </div>
  );
}

export default function LumoApp() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const signupMode = searchParams.get('signup') === '1';

  const [view, setView] = useState('chat');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [dark, setDark] = useState(() => localStorage.getItem('lumo-theme') !== 'light');
  const [selected, setSelected] = useState(null);
  const [chatKey, setChatKey] = useState(0);
  const [authed, setAuthed] = useState(false);
  const [authModal, setAuthModal] = useState(false);
  const [profile, setProfile] = useState(null);
  const [sessionReady, setSessionReady] = useState(false);

  useEffect(() => {
    initTelegramApp();
    document.documentElement.classList.toggle('dark', dark);
    localStorage.setItem('lumo-theme', dark ? 'dark' : 'light');
  }, [dark]);

  useEffect(() => {
    const sync = () => {
      setProfile(null);
      setAuthed(false);
      setSessionReady(false);
      verifySession();
    };
    window.addEventListener('lumo-auth-changed', sync);
    return () => window.removeEventListener('lumo-auth-changed', sync);
  }, []);

  const verifySession = useCallback(async () => {
    if (!isAuthenticated()) {
      setAuthed(false);
      setProfile(null);
      setSessionReady(true);
      return false;
    }
    try {
      const me = await syncSession();
      setProfile(me);
      setAuthed(true);
      setSessionReady(true);
      return true;
    } catch {
      setAuthed(false);
      setProfile(null);
      setSessionReady(true);
      return false;
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const ok = await verifySession();
      if (cancelled) return;
      if (!ok && signupMode) setAuthModal(true);
    })();
    return () => {
      cancelled = true;
    };
  }, [signupMode, verifySession]);

  useEffect(() => {
    if (authed && signupMode) {
      navigate('/app', { replace: true });
    }
  }, [authed, signupMode, navigate]);

  const openItem = async (item) => {
    const detail = await apiFetch(`/lumo/opportunities/${item.id}`);
    setSelected(detail);
  };

  const newChat = () => {
    setView('chat');
    setChatKey((k) => k + 1);
  };

  const handleAuthed = useCallback(async () => {
    const ok = await verifySession();
    if (ok) setAuthModal(false);
  }, [verifySession]);

  if (!sessionReady) {
    return (
      <div className="h-dvh flex items-center justify-center bg-background text-muted-foreground text-sm">
        Загрузка…
      </div>
    );
  }

  return (
    <div className="h-dvh flex bg-background text-foreground overflow-hidden">
      <AppSidebar
        active={view}
        onChange={setView}
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed((v) => !v)}
        onNewChat={newChat}
        authed={authed}
        displayName={authed ? authDisplayName() : 'Гость'}
        onLogout={() => {
          clearAuth();
          setAuthed(false);
          setProfile(null);
          navigate('/');
        }}
        isAdmin={Boolean(profile?.isAdmin)}
      />

      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-12 shrink-0 flex items-center justify-end gap-2 px-4 border-b border-border/60">
          {authed && profile && (
            <span className="text-xs text-muted-foreground hidden md:inline mr-auto">
              {profile.aiSearchRemaining ?? '—'} / {profile.aiSearchLimit ?? 3} запросов сегодня
            </span>
          )}
          <button
            type="button"
            onClick={() => setDark((v) => !v)}
            className="w-8 h-8 rounded-full flex items-center justify-center text-muted-foreground hover:bg-muted transition-colors"
            aria-label="Тема"
          >
            {dark ? <Sun size={15} /> : <Moon size={15} />}
          </button>
          {!authed ? (
            <button
              type="button"
              onClick={() => setAuthModal(true)}
              className="text-sm text-muted-foreground hover:text-foreground px-3 py-1.5"
            >
              Войти
            </button>
          ) : (
            <button
              type="button"
              onClick={() => {
                clearAuth();
                setAuthed(false);
                setProfile(null);
                navigate('/');
              }}
              className="text-sm text-muted-foreground hover:text-foreground px-3 py-1.5 hidden sm:inline"
            >
              Выйти
            </button>
          )}
        </header>

        <main className="flex-1 flex flex-col min-h-0">
          {view === 'chat' && (
            <ChatView
              key={chatKey}
              onOpenItem={openItem}
              onOpenPricing={() => setView('pricing')}
              onNeedsAuth={() => setAuthModal(true)}
            />
          )}
          {view === 'catalog' && (
            <CatalogPanel
              onOpenItem={openItem}
              authed={authed}
              onNeedsAuth={() => setAuthModal(true)}
            />
          )}
          {view === 'team' && (
            <TeamFinderView
              authed={authed}
              profile={profile}
              onNeedsAuth={() => setAuthModal(true)}
            />
          )}
          {view === 'pricing' && <PricingPanel />}
          {view === 'traction' && profile?.isAdmin && <TractionView />}
        </main>
      </div>

      <AuthModal
        open={authModal}
        onClose={() => setAuthModal(false)}
        onAuthed={handleAuthed}
        signup={signupMode && !authed}
      />
      <DetailModal item={selected} onClose={() => setSelected(null)} />
    </div>
  );
}
