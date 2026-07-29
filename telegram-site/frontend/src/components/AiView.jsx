import { useEffect, useRef, useState } from 'react';

import { Send } from 'lucide-react';

import { apiFetch, haptic } from '../api';

import AiPaywall from './AiPaywall';
import OpportunityCard from './OpportunityCard';
import { SearchResultsFeedback } from './SearchFeedback';
import { loadFavorites, toggleFavorite } from '../utils/localFeatures';

const FALLBACK_SUGGESTIONS = [
  { emoji: '🚀', text: 'Я стартапер. Ищу питчи, хакатоны и гранты для стартапов в Казахстане' },
  { emoji: '🎓', text: 'Стипендии за рубежом для магистратуры' },
  { emoji: '💻', text: 'IT-стажировки и хакатоны для разработчиков' },
  { emoji: '🏆', text: 'Конкурсы и олимпиады для школьников' },
];

const DEFAULT_PROMPT = '';

export default function AiView({ onOpenItem, meta, profile, onProfileRefresh, onOpenPriceList }) {
  const resultsRef = useRef(null);
  const [prompt, setPrompt] = useState(profile?.interestQuery || DEFAULT_PROMPT);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [favorites, setFavorites] = useState(() => loadFavorites());
  const favoriteIds = new Set(favorites.map((f) => f.id));

  const isAdmin = profile?.isAdmin;
  const hasAccess = isAdmin || profile?.hasAiAccess || profile?.subscription?.hasAiAccess || profile?.subscription?.isActive;
  const aiRemaining = profile?.aiSearchRemaining ?? null;
  const aiLimit = profile?.aiSearchLimit ?? meta?.aiSearchDailyLimit ?? 1;
  const minLen = meta?.interestMinLength ?? 25;
  const suggestions = meta?.searchSuggestions?.length ? meta.searchSuggestions : FALLBACK_SUGGESTIONS;

  useEffect(() => {
    if (profile?.interestQuery) setPrompt(profile.interestQuery);
  }, [profile?.interestQuery]);

  if (!hasAccess) {
    return <AiPaywall meta={meta} onOpenPriceList={onOpenPriceList} />;
  }

  const submit = async (text = prompt) => {
    const query = text.trim();
    if (query.length < 3 || loading) return;

    setLoading(true);
    setError(null);
    setPrompt(query);
    haptic('light');

    try {
      const willSaveProfile = query.length >= minLen;
      const data = await apiFetch('/lumo/match', {
        method: 'POST',
        body: JSON.stringify({
          query,
          saveInterest: willSaveProfile,
          limit: 12,
        }),
      });
      setResult({
        query,
        message: data.message,
        categories: data.categories,
        items: data.items,
        saved: willSaveProfile,
        noMatch: data.noMatch,
        suggestions: data.suggestions,
      });
      if (willSaveProfile) {
        setTimeout(() => onProfileRefresh?.(), 800);
      }
      setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: 'smooth' }), 80);
    } catch (err) {
      setError(err.message);
      if (err.showPricing || err.needsSubscription) onOpenPriceList?.('subscription');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="pb-8">
      <header className="mb-5">
        <h1 className="text-[22px] font-bold mb-2 leading-tight">Что ты ищешь?</h1>
        <p className="text-[13px] leading-relaxed" style={{ color: 'var(--lumo-text-muted)' }}>
          Короткий запрос — быстрый поиск. Длинный (от {minLen} символов) — сохраню профиль и буду присылать в бот.
        </p>
        {isAdmin && (
          <p className="text-[12px] mt-2 font-medium" style={{ color: 'var(--lumo-text-muted)' }}>
            Admin · без лимита · в каталоге {profile?.catalogCount ?? '…'} записей
          </p>
        )}
        {profile?.subscription?.isActive && !isAdmin && (
          <p className="text-[12px] mt-2 font-medium" style={{ color: 'var(--lumo-link)' }}>
            Подписка активна · {profile.subscription.planLabel || profile.subscription.plan}
          </p>
        )}
        {!isAdmin && !profile?.subscription?.isActive && aiRemaining != null && aiLimit > 0 && aiLimit < 999 && (
          <p className="text-[12px] mt-2 font-medium" style={{ color: 'var(--lumo-text-muted)' }}>
            Бесплатно · AI-поиск {aiRemaining > 0 ? `осталось ${aiRemaining} из ${aiLimit} сегодня` : 'на сегодня использован'}
          </p>
        )}
      </header>

      <div className="relative lumo-input-area mb-4">
        <textarea
          rows={5}
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
          placeholder="Например: стажировки для IT или подробно опиши себя…"
          className="w-full bg-transparent rounded-2xl py-4 pl-4 pr-14 text-[14px] leading-relaxed resize-none focus:outline-none"
        />
        <button
          type="button"
          onClick={() => submit()}
          disabled={prompt.trim().length < 3 || loading}
          className="absolute right-3 bottom-3 w-10 h-10 rounded-full flex items-center justify-center lumo-send-btn disabled:opacity-40 transition-opacity"
          aria-label="Отправить"
        >
          <Send size={16} className="text-white ml-0.5" />
        </button>
      </div>

      {!result && (
        <div className="mb-6">
          <p className="text-[12px] font-semibold mb-2" style={{ color: 'var(--lumo-text-muted)' }}>
            Примеры — нажми, чтобы подставить:
          </p>
          <div className="flex flex-col gap-2">
            {suggestions.map(({ emoji, text }) => (
              <button
                key={text}
                type="button"
                disabled={loading}
                onClick={() => setPrompt(text)}
                className="lumo-chip w-full text-left px-4 py-3 text-[13px] font-medium transition active:scale-[0.99] disabled:opacity-40"
              >
                {emoji} {text}
              </button>
            ))}
          </div>
        </div>
      )}

      {loading && (
        <p className="text-center text-[13px] animate-pulse mb-4" style={{ color: 'var(--lumo-text-muted)' }}>
          Ищу подходящие возможности…
        </p>
      )}

      {error && <p className="text-center text-[13px] text-red-400 mb-4">{error}</p>}

      {result && !loading && (
        <div ref={resultsRef} className="space-y-4">
          <div className="lumo-card p-4">
            <p className="text-[13px] mb-2" style={{ color: 'var(--lumo-text-muted)' }}>
              {result.message}
            </p>
            {result.saved && (
              <p className="text-[12px] font-medium mb-2" style={{ color: 'var(--lumo-link)' }}>
                Профиль сохранён · новые совпадения пришлю в бот
              </p>
            )}
            {!result.saved && (
              <p className="text-[12px] font-medium mb-2" style={{ color: 'var(--lumo-text-muted)' }}>
                Быстрый поиск — профиль не менялся
              </p>
            )}
            {result.categories?.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {result.categories.map((cat) => (
                  <span
                    key={cat.type}
                    className="text-[11px] px-2.5 py-1 rounded-full font-medium"
                    style={{ background: 'var(--lumo-profile-chip-bg)', color: 'var(--lumo-profile-chip-text)' }}
                  >
                    {cat.emoji} {cat.label}
                  </span>
                ))}
              </div>
            )}
          </div>

          {result.items?.length > 0 ? (
            <div className="space-y-3">
              <SearchResultsFeedback
                query={result.query}
                items={result.items}
                categories={result.categories}
                disabled={loading}
              />
              <div className="grid grid-cols-1 gap-3">
                {result.items.map((item) => (
                  <OpportunityCard
                    key={item.id}
                    item={item}
                    onOpen={onOpenItem}
                    feedbackQuery={result.query}
                    feedbackCategories={result.categories}
                    isFavorite={favoriteIds.has(item.id)}
                    onToggleFavorite={(it) => setFavorites(toggleFavorite(it))}
                  />
                ))}
              </div>
            </div>
          ) : result.noMatch ? (
            <div className="space-y-3">
              <p className="text-[13px] text-center" style={{ color: 'var(--lumo-text-muted)' }}>
                Могу предложить попробовать так:
              </p>
              <div className="flex flex-col gap-2">
                {(result.suggestions || suggestions).map(({ emoji, text }) => (
                  <button
                    key={text}
                    type="button"
                    disabled={loading}
                    onClick={() => {
                      setPrompt(text);
                      submit(text);
                    }}
                    className="lumo-chip w-full text-left px-4 py-3 text-[13px] font-medium transition active:scale-[0.99] disabled:opacity-40"
                  >
                    {emoji} {text}
                  </button>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}
