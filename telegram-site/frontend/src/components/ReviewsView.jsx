import { useState } from 'react';
import { ExternalLink, MessageSquareQuote, Plus } from 'lucide-react';
import { addReview, loadReviews } from '../utils/localFeatures';
import { haptic } from '../api';

const EMPTY_FORM = { contest: '', title: '', body: '', link: '', author: '' };

export default function ReviewsView() {
  const [reviews, setReviews] = useState(() => loadReviews());
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);

  const submit = () => {
    if (!form.title.trim() || !form.body.trim()) return;
    haptic('light');
    const next = addReview({
      contest: form.contest.trim() || 'Без привязки к конкурсу',
      title: form.title.trim(),
      body: form.body.trim(),
      link: form.link.trim(),
      author: form.author.trim() || 'Аноним',
    });
    setReviews(next);
    setForm(EMPTY_FORM);
    setShowForm(false);
  };

  return (
    <div className="pb-8">
      <header className="mb-5 flex items-start justify-between gap-3">
        <div>
          <h1 className="text-[22px] font-bold mb-2">Отзывы</h1>
          <p className="text-[13px]" style={{ color: 'var(--lumo-text-muted)' }}>
            Как готовиться, что спрашивают на интервью
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            haptic('light');
            setShowForm((v) => !v);
          }}
          className="shrink-0 flex items-center gap-1.5 px-3 py-2 rounded-xl text-[12px] font-bold lumo-btn-primary"
        >
          <Plus size={16} />
          Добавить
        </button>
      </header>

      {showForm && (
        <div className="lumo-card p-4 mb-5 space-y-2.5">
          <input
            value={form.contest}
            onChange={(e) => setForm((p) => ({ ...p, contest: e.target.value }))}
            placeholder="Название конкурса"
            className="lumo-form-input"
          />
          <input
            value={form.title}
            onChange={(e) => setForm((p) => ({ ...p, title: e.target.value }))}
            placeholder="Заголовок — например «Как готовился к эссе» *"
            className="lumo-form-input"
          />
          <textarea
            value={form.body}
            onChange={(e) => setForm((p) => ({ ...p, body: e.target.value }))}
            rows={4}
            placeholder="Что помогло, что было на интервью, чего избегать *"
            className="lumo-form-input resize-none"
          />
          <input
            value={form.link}
            onChange={(e) => setForm((p) => ({ ...p, link: e.target.value }))}
            placeholder="Ссылка на источник — необязательно"
            className="lumo-form-input"
          />
          <input
            value={form.author}
            onChange={(e) => setForm((p) => ({ ...p, author: e.target.value }))}
            placeholder="Твоё имя"
            className="lumo-form-input"
          />
          <button
            type="button"
            onClick={submit}
            disabled={!form.title.trim() || !form.body.trim()}
            className="w-full py-3 rounded-xl font-bold text-[13px] lumo-btn-primary disabled:opacity-40"
          >
            Опубликовать
          </button>
        </div>
      )}

      <div className="space-y-3">
        {reviews.map((review) => (
          <article key={review.id} className="lumo-card p-4">
            <div className="flex items-center gap-2 mb-2">
              <MessageSquareQuote size={14} style={{ color: 'var(--lumo-text-muted)' }} />
              <span
                className="text-[11px] font-bold uppercase tracking-wide"
                style={{ color: 'var(--lumo-text-muted)' }}
              >
                {review.contest}
              </span>
            </div>
            <h3 className="text-[14px] font-bold mb-1.5">{review.title}</h3>
            <p className="text-[13px] leading-relaxed mb-3 whitespace-pre-line" style={{ color: 'var(--lumo-text-muted)' }}>
              {review.body}
            </p>
            <div className="flex items-center justify-between text-[12px]" style={{ color: 'var(--lumo-text-muted)' }}>
              <span>{review.author}</span>
              {review.link && (
                <a
                  href={review.link}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1"
                  style={{ color: 'var(--lumo-link)' }}
                >
                  Читать
                  <ExternalLink size={11} />
                </a>
              )}
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
