import { useEffect, useState } from 'react';
import { Check, Heart, Layers, Loader2, MessageSquareQuote, Sparkles, UserCheck, Wand2, X } from 'lucide-react';

import { apiFetch, getTelegram, haptic } from '../api';

import { formatDeadlineMeta, sourceHandle } from '../utils/deadline';

import { itemTags } from '../utils/categories';
import TagChips from './TagChips';
import { addCard, hasCardForSource, isFavorite, toggleFavorite } from '../utils/localFeatures';

function trackClick(catalogId, type) {
  if (!catalogId) return;
  apiFetch('/lumo/track-click', {
    method: 'POST',
    body: JSON.stringify({ type, catalogId }),
  }).catch(() => {});
}

function openTrackedLink(url, catalogId, type) {
  if (!url) return;
  haptic('light');
  trackClick(catalogId, type);
  const tg = getTelegram();
  const isTelegram = /t\.me\/|telegram\.me\//i.test(url);
  if (isTelegram && tg?.openTelegramLink) tg.openTelegramLink(url);
  else if (tg?.openLink) tg.openLink(url);
  else window.open(url, '_blank');
}

const MENTOR_ADDON_PLANS = new Set(['plan_6m', 'plan_12m', 'unlimited']);

function AiBriefSection({ brief }) {
  if (!brief || (!brief.summary?.length && !brief.checklist?.length)) return null;
  return (
    <div className="lumo-card p-4 mb-4">
      <div className="flex items-center gap-2 mb-3">
        <Sparkles size={15} style={{ color: 'var(--lumo-accent)' }} />
        <p className="text-[13px] font-bold">Коротко о конкурсе</p>
      </div>
      {brief.summary?.length > 0 && (
        <ul className="space-y-1.5 mb-3">
          {brief.summary.map((line, i) => (
            <li key={i} className="text-[13px] leading-relaxed flex gap-2">
              <span style={{ color: 'var(--lumo-text-muted)' }}>•</span>
              <span>{line}</span>
            </li>
          ))}
        </ul>
      )}
      {brief.checklist?.length > 0 && (
        <div>
          <p className="text-[10px] font-bold uppercase tracking-widest mb-2" style={{ color: 'var(--lumo-text-muted)' }}>
            Что подготовить
          </p>
          <ul className="space-y-1">
            {brief.checklist.map((line, i) => (
              <li key={i} className="text-[13px] leading-relaxed flex gap-2">
                <Check size={13} className="mt-0.5 shrink-0" style={{ color: '#22c55e' }} />
                <span>{line}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function PeersRow({ itemId }) {
  const [peers, setPeers] = useState(null);
  useEffect(() => {
    let cancelled = false;
    apiFetch(`/lumo/opportunities/${itemId}/peers`)
      .then((data) => !cancelled && setPeers(data))
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [itemId]);
  if (!peers || peers.count === 0) return null;
  return (
    <p className="text-[12px] flex items-center gap-1.5 mb-4" style={{ color: 'var(--lumo-text-muted)' }}>
      <UserCheck size={13} />
      Ещё {peers.count} {peers.count === 1 ? 'человек смотрит' : 'человек смотрят'} этот конкурс
      {peers.sameRegionCount > 0 ? ` (${peers.sameRegionCount} из твоего региона)` : ''}
    </p>
  );
}

function SimilarSection({ itemId }) {
  const [similar, setSimilar] = useState([]);
  useEffect(() => {
    let cancelled = false;
    apiFetch(`/lumo/opportunities/${itemId}/similar`)
      .then((data) => !cancelled && setSimilar(data.items || []))
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [itemId]);
  if (!similar.length) return null;
  return (
    <div className="mb-4">
      <div className="flex items-center gap-2 mb-2.5">
        <Layers size={15} style={{ color: 'var(--lumo-text-muted)' }} />
        <p className="text-[13px] font-bold">Похожие конкурсы</p>
      </div>
      <div className="space-y-2">
        {similar.map((s) => (
          <div key={s.id} className="lumo-card p-3">
            <p className="text-[13px] font-semibold line-clamp-1">{s.title}</p>
            <p className="text-[11px]" style={{ color: 'var(--lumo-text-muted)' }}>
              {s.label} · {s.deadlineLabel || s.deadline}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

function MentorButton({ itemId, canRequestMentor }) {
  const [state, setState] = useState('idle');
  const request = async () => {
    haptic('medium');
    setState('loading');
    try {
      const data = await apiFetch(`/lumo/opportunities/${itemId}/request-mentor`, { method: 'POST' });
      setState(data.alreadyRequested ? 'already' : 'sent');
    } catch (err) {
      setState(err.status === 402 ? 'needs-plan' : 'error');
    }
  };
  if (state === 'sent' || state === 'already') {
    return (
      <p className="text-[12px] rounded-xl p-3 mb-3" style={{ background: 'rgba(34,197,94,0.1)', color: '#22c55e' }}>
        Заявка на ментора отправлена — свяжем тебя с ментором под этот конкурс.
      </p>
    );
  }
  return (
    <div className="mb-3">
      <button
        type="button"
        onClick={request}
        disabled={state === 'loading'}
        className="w-full py-3 rounded-xl font-bold text-[13px] flex items-center justify-center gap-2 disabled:opacity-60"
        style={{ background: 'var(--lumo-surface-muted)', color: 'var(--lumo-text)', border: '1px solid var(--lumo-border)' }}
      >
        {state === 'loading' ? <Loader2 size={15} className="animate-spin" /> : <UserCheck size={15} />}
        Запросить ментора
        {!canRequestMentor && (
          <span
            className="text-[9px] px-1.5 py-0.5 rounded-full font-bold"
            style={{ background: 'rgba(251,191,36,0.15)', color: '#d97706' }}
          >
            Premium
          </span>
        )}
      </button>
      {state === 'needs-plan' && (
        <p className="text-[11px] mt-1.5" style={{ color: 'var(--lumo-text-muted)' }}>
          Доступно на тарифах от 6 месяцев.
        </p>
      )}
    </div>
  );
}

function AssistantSection({ itemId, isPremium }) {
  const [message, setMessage] = useState('');
  const [advice, setAdvice] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const ask = async () => {
    if (message.trim().length < 3) return;
    haptic('medium');
    setLoading(true);
    setError('');
    try {
      const data = await apiFetch(`/lumo/opportunities/${itemId}/assistant`, {
        method: 'POST',
        body: JSON.stringify({ message: message.trim() }),
      });
      setAdvice(data.advice || '');
    } catch (err) {
      setError(err.status === 402 ? 'AI-ассистент доступен на платных тарифах.' : err.message || 'Ошибка');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="lumo-card p-4 mb-4">
      <div className="flex items-center gap-2 mb-2">
        <Wand2 size={15} style={{ color: 'var(--lumo-accent)' }} />
        <p className="text-[13px] font-bold">AI-ассистент по подаче</p>
        {!isPremium && (
          <span
            className="text-[9px] px-1.5 py-0.5 rounded-full font-bold"
            style={{ background: 'rgba(251,191,36,0.15)', color: '#d97706' }}
          >
            Premium
          </span>
        )}
      </div>
      <textarea
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        rows={2}
        placeholder="Например: помоги со структурой эссе"
        className="w-full rounded-xl p-3 text-[13px] border mb-2 resize-none"
        style={{ background: 'var(--lumo-surface-muted)', borderColor: 'var(--lumo-border)', color: 'var(--lumo-text)' }}
      />
      {error && <p className="text-[11px] text-red-400 mb-2">{error}</p>}
      <button
        type="button"
        onClick={ask}
        disabled={loading}
        className="px-4 py-2 rounded-xl font-bold text-[12px] text-white flex items-center gap-2 disabled:opacity-60 lumo-btn-primary"
      >
        {loading && <Loader2 size={13} className="animate-spin" />}
        Спросить AI
      </button>
      {advice && (
        <div className="mt-3 pt-3 text-[13px] leading-relaxed whitespace-pre-line" style={{ borderTop: '1px solid var(--lumo-border)' }}>
          {advice}
        </div>
      )}
    </div>
  );
}

function ReviewsSection({ itemId }) {
  const [reviews, setReviews] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ title: '', body: '' });
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    apiFetch(`/lumo/opportunities/${itemId}/reviews`)
      .then((data) => !cancelled && setReviews(data.items || []))
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [itemId]);

  const submit = async () => {
    if (!form.title.trim() || form.body.trim().length < 10) return;
    haptic('medium');
    setError('');
    try {
      const review = await apiFetch(`/lumo/opportunities/${itemId}/reviews`, {
        method: 'POST',
        body: JSON.stringify({ title: form.title.trim(), body: form.body.trim() }),
      });
      setReviews((prev) => [review, ...prev]);
      setForm({ title: '', body: '' });
      setShowForm(false);
    } catch (err) {
      setError(err.message || 'Не получилось опубликовать');
    }
  };

  return (
    <div className="mb-4">
      <div className="flex items-center justify-between mb-2.5">
        <div className="flex items-center gap-2">
          <MessageSquareQuote size={15} style={{ color: 'var(--lumo-text-muted)' }} />
          <p className="text-[13px] font-bold">Отзывы и советы</p>
        </div>
        <button
          type="button"
          onClick={() => {
            haptic('light');
            setShowForm((v) => !v);
          }}
          className="text-[12px] font-semibold"
          style={{ color: 'var(--lumo-link)' }}
        >
          Поделиться
        </button>
      </div>

      {showForm && (
        <div className="lumo-card p-3 mb-3 space-y-2">
          <input
            value={form.title}
            onChange={(e) => setForm((p) => ({ ...p, title: e.target.value }))}
            placeholder="Заголовок *"
            className="lumo-form-input"
          />
          <textarea
            value={form.body}
            onChange={(e) => setForm((p) => ({ ...p, body: e.target.value }))}
            rows={3}
            placeholder="Что помогло, что было на интервью *"
            className="lumo-form-input resize-none"
          />
          {error && <p className="text-[11px] text-red-400">{error}</p>}
          <button type="button" onClick={submit} className="w-full py-2.5 rounded-xl font-bold text-[12px] text-white lumo-btn-primary">
            Опубликовать
          </button>
        </div>
      )}

      {reviews.length === 0 ? (
        <p className="text-[12px]" style={{ color: 'var(--lumo-text-muted)' }}>
          Пока нет отзывов — стань первым
        </p>
      ) : (
        <div className="space-y-2">
          {reviews.map((r) => (
            <div key={r.id} className="lumo-card p-3">
              <p className="text-[13px] font-bold mb-1">{r.title}</p>
              <p className="text-[12px] leading-relaxed whitespace-pre-line" style={{ color: 'var(--lumo-text-muted)' }}>
                {r.body}
              </p>
              <p className="text-[11px] mt-1.5" style={{ color: 'var(--lumo-text-muted)' }}>
                {r.author}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function DetailModal({ item, profile, onClose }) {
  const [detail, setDetail] = useState(item);
  const [favorite, setFavorite] = useState(() => (item ? isFavorite(item.id) : false));
  const [inTracker, setInTracker] = useState(() => (item ? hasCardForSource(item.id) : false));

  useEffect(() => {
    setDetail(item);
    setFavorite(item ? isFavorite(item.id) : false);
    setInTracker(item ? hasCardForSource(item.id) : false);
    if (!item) return;
    let cancelled = false;
    apiFetch(`/lumo/opportunities/${item.id}`)
      .then((full) => !cancelled && setDetail(full))
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [item]);

  if (!item) return null;

  // `detail` is stale (or still null) for one render after `item` changes — the fetch above
  // updates it asynchronously via an effect, which runs after this render commits. Falling
  // back to `item` (never null past the guard above) avoids reading fields off a stale value.
  const view = detail && detail.id === item.id ? detail : item;

  const tags = itemTags(view);
  const deadline = formatDeadlineMeta(view.deadline);
  const handle = sourceHandle(view);
  const subscription = profile?.subscription;
  const isPremium = Boolean(subscription?.isPaid);
  const canRequestMentor = isPremium && MENTOR_ADDON_PLANS.has((subscription?.plan || '').toLowerCase());

  const addToTracker = () => {
    haptic('light');
    addCard({
      title: view.title,
      org: view.sourceChannelName || '',
      deadline: view.deadline || '',
      link: view.applicationUrl || view.messageLink || '',
      sourceId: view.id,
      checklistLabels: view.brief?.checklist,
    });
    setInTracker(true);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4 bg-black/60 backdrop-blur-sm">
      <div className="lumo-card w-full sm:max-w-lg max-h-[90vh] overflow-y-auto rounded-t-[24px] sm:rounded-[24px] p-6 relative">
        <button type="button" onClick={onClose} className="absolute top-5 right-5 opacity-60 hover:opacity-100" aria-label="Закрыть">
          <X size={22} />
        </button>

        <div className="flex items-start justify-between gap-3 mb-1 pr-8">
          <h3 className="text-xl font-bold leading-snug">{view.title}</h3>
          <div className="flex items-center gap-2 shrink-0">
            <TagChips tags={tags} />
            <button
              type="button"
              onClick={() => {
                haptic('light');
                toggleFavorite(detail);
                setFavorite((v) => !v);
              }}
              className="w-8 h-8 rounded-full flex items-center justify-center shrink-0"
              aria-label={favorite ? 'Убрать из избранного' : 'В избранное'}
            >
              <Heart
                size={18}
                fill={favorite ? 'var(--lumo-urgent)' : 'none'}
                style={{ color: favorite ? 'var(--lumo-urgent)' : 'var(--lumo-text-muted)' }}
              />
            </button>
          </div>
        </div>

        {typeof view.matchScore === 'number' && (
          <p
            className="inline-block text-[11px] font-bold px-2.5 py-1 rounded-full mb-3"
            style={{ background: 'var(--lumo-profile-chip-bg)', color: 'var(--lumo-profile-chip-text)' }}
          >
            🎯 {view.matchScore}% совпадение
          </p>
        )}

        <p className="text-[14px] mb-4 leading-relaxed" style={{ color: 'var(--lumo-text-muted)' }}>
          {view.fullText || view.description}
        </p>

        <AiBriefSection brief={view.brief} />
        <PeersRow itemId={view.id} />

        <div className="text-[14px] space-y-2.5 mb-5">
          <p className="flex items-center gap-2" style={{ color: deadline.urgent ? 'var(--lumo-urgent)' : 'var(--lumo-text)' }}>
            <span style={{ color: 'var(--lumo-text-muted)' }}>Дедлайн:</span> {deadline.label}
          </p>
          <p>
            <span style={{ color: 'var(--lumo-text-muted)' }}>Канал:</span> {view.sourceChannelName}
            {handle && (
              <span className="ml-2" style={{ color: 'var(--lumo-link)' }}>
                {handle}
              </span>
            )}
          </p>
          {view.requirements && (
            <p>
              <span style={{ color: 'var(--lumo-text-muted)' }}>Требования:</span> {view.requirements}
            </p>
          )}
          {view.applicationUrl && (
            <p>
              <span style={{ color: 'var(--lumo-text-muted)' }}>Заявка:</span>{' '}
              <button
                type="button"
                className="break-all text-left underline"
                style={{ color: 'var(--lumo-link)' }}
                onClick={() => openTrackedLink(view.applicationUrl, view.id, 'apply')}
              >
                Открыть
              </button>
            </p>
          )}
          {view.messageLink && (
            <p>
              <span style={{ color: 'var(--lumo-text-muted)' }}>Пост:</span>{' '}
              <button
                type="button"
                className="underline"
                style={{ color: 'var(--lumo-link)' }}
                onClick={() => openTrackedLink(view.messageLink, view.id, 'telegram')}
              >
                Telegram
              </button>
            </p>
          )}
        </div>

        <div className="grid grid-cols-2 gap-2 mb-2">
          {view.applicationUrl && (
            <button
              type="button"
              onClick={() => openTrackedLink(view.applicationUrl, view.id, 'apply')}
              className="py-3 rounded-xl font-bold text-white text-[13px]"
              style={{ background: 'linear-gradient(135deg, #22c55e, #16a34a)' }}
            >
              Подать заявку
            </button>
          )}
          {view.messageLink && (
            <button
              type="button"
              onClick={() => openTrackedLink(view.messageLink, view.id, 'telegram')}
              className={`py-3 rounded-xl font-bold text-[13px] ${view.applicationUrl ? '' : 'col-span-2'}`}
              style={{ background: 'var(--lumo-accent-soft)', color: 'var(--lumo-accent)' }}
            >
              Открыть в Telegram
            </button>
          )}
        </div>

        <button
          type="button"
          onClick={addToTracker}
          disabled={inTracker}
          className="w-full py-3 rounded-xl font-bold text-[13px] mb-3 disabled:opacity-50"
          style={{ background: 'var(--lumo-surface-muted)', color: 'var(--lumo-text)', border: '1px solid var(--lumo-border)' }}
        >
          {inTracker ? 'Уже в заявках' : '+ В мои заявки'}
        </button>

        <MentorButton itemId={view.id} canRequestMentor={canRequestMentor} />
        <AssistantSection itemId={view.id} isPremium={isPremium} />
        <SimilarSection itemId={view.id} />
        <ReviewsSection itemId={view.id} />

        <button type="button" onClick={onClose} className="w-full py-3.5 rounded-xl font-bold lumo-btn-primary">
          Закрыть
        </button>
      </div>
    </div>
  );
}
