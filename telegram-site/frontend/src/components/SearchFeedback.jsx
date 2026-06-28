import { useState } from 'react';
import { ThumbsDown, ThumbsUp } from 'lucide-react';
import { apiFetch, haptic } from '../api';

export function SearchResultsFeedback({ query, items, categories, disabled }) {
  const [sent, setSent] = useState(null);

  if (!items?.length || disabled) return null;

  const submit = async (helpful) => {
    if (sent !== null) return;
    haptic('light');
    setSent(helpful);
    const catTypes = (categories || []).map((c) => c.type).filter(Boolean);
    try {
      await apiFetch('/lumo/match-feedback/batch', {
        method: 'POST',
        body: JSON.stringify({
          query,
          helpful,
          catalogIds: items.map((i) => i.id),
          categories: catTypes,
        }),
      });
    } catch {
      setSent(null);
    }
  };

  return (
    <div
      className="rounded-xl px-4 py-3 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2"
      style={{ background: 'var(--lumo-surface-muted)' }}
    >
      <p className="text-[12px] font-medium" style={{ color: 'var(--lumo-text-muted)' }}>
        {sent === null
          ? 'Результаты попали в запрос?'
          : sent
            ? 'Спасибо — учту для подбора'
            : 'Спасибо — это поможет точнее искать'}
      </p>
      {sent === null && (
        <div className="flex gap-2 shrink-0">
          <button
            type="button"
            onClick={() => submit(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-semibold"
            style={{ background: 'var(--lumo-accent-soft)', color: 'var(--lumo-accent)' }}
          >
            <ThumbsUp size={14} />
            Да
          </button>
          <button
            type="button"
            onClick={() => submit(false)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-semibold"
            style={{ background: 'var(--lumo-surface)', color: 'var(--lumo-text-muted)' }}
          >
            <ThumbsDown size={14} />
            Нет
          </button>
        </div>
      )}
    </div>
  );
}

export function CardMatchFeedback({ query, item, categories, disabled }) {
  const [sent, setSent] = useState(null);

  if (disabled) return null;

  const submit = async (helpful, e) => {
    e.stopPropagation();
    e.preventDefault();
    if (sent !== null) return;
    haptic('light');
    setSent(helpful);
    const catTypes = (categories || []).map((c) => c.type).filter(Boolean);
    try {
      await apiFetch('/lumo/match-feedback', {
        method: 'POST',
        body: JSON.stringify({
          query,
          catalogId: item.id,
          helpful,
          categories: catTypes,
        }),
      });
    } catch {
      setSent(null);
    }
  };

  return (
    <div
      className="flex items-center justify-end gap-1.5 pt-2 mt-2 border-t"
      style={{ borderColor: 'var(--lumo-border)' }}
      onClick={(e) => e.stopPropagation()}
    >
      <span className="text-[11px] mr-1" style={{ color: 'var(--lumo-text-muted)' }}>
        {sent === null ? 'Совпало?' : sent ? '✓' : 'записано'}
      </span>
      <button
        type="button"
        disabled={sent !== null}
        onClick={(e) => submit(true, e)}
        className="p-1.5 rounded-lg disabled:opacity-40"
        aria-label="Совпало"
      >
        <ThumbsUp size={14} style={{ color: sent === true ? 'var(--lumo-accent)' : 'var(--lumo-text-muted)' }} />
      </button>
      <button
        type="button"
        disabled={sent !== null}
        onClick={(e) => submit(false, e)}
        className="p-1.5 rounded-lg disabled:opacity-40"
        aria-label="Не совпало"
      >
        <ThumbsDown size={14} style={{ color: sent === false ? '#f87171' : 'var(--lumo-text-muted)' }} />
      </button>
    </div>
  );
}
