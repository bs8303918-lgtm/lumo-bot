import { useCallback, useEffect, useState } from 'react';
import { Moon, Sun, X } from 'lucide-react';
import AdminView from './components/AdminView';
import AiView from './components/AiView';
import CatalogView from './components/CatalogView';
import DetailModal from './components/DetailModal';
import LumoLogo from './components/LumoLogo';
import ProfileView from './components/ProfileView';
import PricingView from './components/PricingView';
import { resolvePlans } from './utils/pricing';
import { apiFetch, getTelegram, haptic, initTelegramApp } from './api';

function ViewTabs({ active, onChange, isAdmin }) {
  const tabs = [
    { id: 'ai', label: 'AI-поиск', prefix: '✦' },
    { id: 'catalog', label: 'Каталог', prefix: null },
    { id: 'pricing', label: 'Price', prefix: null },
    { id: 'profile', label: 'Профиль', prefix: '●' },
  ];
  if (isAdmin) {
    tabs.push({ id: 'admin', label: 'Админ', prefix: '⚙', admin: true });
  }

  return (
    <nav
      className="flex border-b overflow-x-auto scrollbar-none -mx-1 px-1"
      style={{ borderColor: 'var(--lumo-border)' }}
    >
      {tabs.map(({ id, label, prefix, admin }) => {
        const isActive = active === id;
        const accent = admin ? 'var(--lumo-admin-accent)' : 'var(--lumo-accent)';
        return (
          <button
            key={id}
            type="button"
            onClick={() => {
              haptic('light');
              onChange(id);
            }}
            className="relative shrink-0 px-3 py-3 text-[12px] font-semibold transition-colors whitespace-nowrap"
            style={{
              color: isActive ? accent : 'var(--lumo-text-muted)',
            }}
          >
            <span className="inline-flex items-center gap-1">
              {isActive && prefix && <span className="text-[10px]">{prefix}</span>}
              {label}
            </span>
            {isActive && (
              <span className="lumo-tab-indicator" style={admin ? { background: accent } : undefined} />
            )}
          </button>
        );
      })}
    </nav>
  );
}

export default function App() {
  const [view, setView] = useState('ai');
  const [dark, setDark] = useState(() => localStorage.getItem('lumo-theme') === 'dark');
  const [selected, setSelected] = useState(null);
  const [meta, setMeta] = useState(null);
  const [profile, setProfile] = useState(null);
  const [plans, setPlans] = useState([]);
  const [pricingLimitNotice, setPricingLimitNotice] = useState(false);
  const [authError, setAuthError] = useState(null);
  const inTelegram = Boolean(getTelegram()?.initData);
  const botUsername = meta?.botUsername || 'LumoAI1bot';

  const loadProfile = useCallback(async () => {
    try {
      setAuthError(null);
      const me = await apiFetch('/users/me');
      setProfile(me);
    } catch (err) {
      setAuthError(err.message);
    }
  }, []);

  useEffect(() => {
    initTelegramApp();
    apiFetch('/lumo/meta')
      .then((data) => {
        setMeta(data);
        if (data.plans?.length) setPlans(data.plans);
      })
      .catch(() => {});
    apiFetch('/lumo/subscription-plans')
      .then((data) => setPlans(data.plans || []))
      .catch(() => {});
    loadProfile();
  }, [loadProfile]);

  const resolvedPlans = resolvePlans(plans);

  const openPricing = useCallback(
    (reason = 'manual') => {
      if (reason === 'limit') {
        setPricingLimitNotice(true);
        setView('pricing');
      } else {
        setView('pricing');
      }
    },
    [],
  );

  useEffect(() => {
    const tg = getTelegram();
    if (tg?.colorScheme === 'dark') setDark(true);
    if (tg?.colorScheme === 'light') setDark(false);
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark);
    localStorage.setItem('lumo-theme', dark ? 'dark' : 'light');
    const tg = getTelegram();
    if (tg) {
      tg.setHeaderColor(dark ? '#0b0e14' : '#eef2f7');
      tg.setBackgroundColor(dark ? '#0b0e14' : '#eef2f7');
    }
  }, [dark]);

  const openItem = async (item) => {
    haptic('light');
    setSelected(await apiFetch(`/lumo/opportunities/${item.id}`));
  };

  const closeApp = () => {
    const tg = getTelegram();
    if (tg?.close) tg.close();
    else window.history.back();
  };

  return (
    <div className="min-h-screen flex flex-col" style={{ background: 'var(--lumo-bg)', color: 'var(--lumo-text)' }}>
      <header
        className="sticky top-0 z-30 backdrop-blur-md"
        style={{
          background: 'color-mix(in srgb, var(--lumo-bg) 94%, transparent)',
          paddingTop: 'env(safe-area-inset-top)',
        }}
      >
        <div className="max-w-lg mx-auto px-4 pt-3 pb-0">
          <div className="flex items-center justify-between gap-3 mb-1">
            <LumoLogo />
            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={() => {
                  haptic('light');
                  setDark((v) => !v);
                }}
                className="w-9 h-9 rounded-xl flex items-center justify-center"
                style={{ color: 'var(--lumo-text-muted)' }}
                aria-label="Тема"
              >
                {dark ? <Sun size={18} /> : <Moon size={18} />}
              </button>
              <button
                type="button"
                onClick={closeApp}
                className="w-9 h-9 rounded-xl flex items-center justify-center"
                style={{ color: 'var(--lumo-text-muted)' }}
                aria-label="Закрыть"
              >
                <X size={18} />
              </button>
            </div>
          </div>
          <ViewTabs
            active={view}
            onChange={(id) => {
              if (id !== 'pricing') setPricingLimitNotice(false);
              setView(id);
            }}
            isAdmin={profile?.isAdmin}
          />
        </div>
      </header>

      <main className="flex-1 max-w-lg mx-auto w-full px-4 py-5">
        {authError && (
          <div className="mb-4 p-3 rounded-xl text-xs text-red-400 bg-red-500/10 border border-red-500/20">
            {authError}
            {!inTelegram && (
              <span> — укажи Telegram ID во вкладке Профиль и включи API_ALLOW_DEV_AUTH=true</span>
            )}
          </div>
        )}

        {view === 'ai' && (
          <AiView
            onOpenItem={openItem}
            meta={meta}
            profile={profile}
            onProfileRefresh={loadProfile}
            onOpenPriceList={openPricing}
          />
        )}
        {view === 'catalog' && <CatalogView onOpenItem={openItem} />}
        {view === 'pricing' && (
          <PricingView
            meta={meta}
            profile={profile}
            plans={resolvedPlans}
            limitNotice={pricingLimitNotice}
            onDismissLimit={() => {
              setPricingLimitNotice(false);
              setView('catalog');
            }}
          />
        )}
        {view === 'profile' && (
          <ProfileView
            meta={meta}
            profile={profile}
            plans={resolvedPlans}
            onProfileRefresh={loadProfile}
            onOpenPriceList={openPricing}
          />
        )}
        {view === 'admin' && profile?.isAdmin && (
          <AdminView onExit={() => setView('ai')} />
        )}
        {view === 'admin' && !profile?.isAdmin && (
          <div className="lumo-card p-4 text-center">
            <p className="text-[14px] mb-2">Нет доступа к админке</p>
            <p className="text-[12px]" style={{ color: 'var(--lumo-text-muted)' }}>
              {profile?.telegramId
                ? `Твой ID: ${profile.telegramId}. Проверь TELEGRAM_ADMIN_CHAT_ID в .env`
                : 'Загрузка профиля… /whoami в боте'}
            </p>
          </div>
        )}
      </main>

      <footer className="py-4 text-center">
        <p className="text-[12px]" style={{ color: 'var(--lumo-text-muted)' }}>
          @{botUsername}
        </p>
      </footer>

      <DetailModal item={selected} onClose={() => setSelected(null)} />
    </div>
  );
}
