import { useEffect, useState } from 'react';
import { ExternalLink, MessageSquareQuote } from 'lucide-react';
import { apiFetch } from '../api';

export default function ReviewsView() {
  const [reviews, setReviews] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch('/lumo/reviews')
      .then((data) => setReviews(data.items || []))
      .catch(() => setReviews([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="pb-8">
      <header className="mb-5">
        <h1 className="text-[22px] font-bold mb-2">Отзывы</h1>
        <p className="text-[13px]" style={{ color: 'var(--lumo-text-muted)' }}>
          Как готовиться, что спрашивают на интервью. Чтобы поделиться своим — открой карточку конкурса.
        </p>
      </header>

      {loading ? (
        <p className="text-center py-10 text-[13px]" style={{ color: 'var(--lumo-text-muted)' }}>
          Загрузка…
        </p>
      ) : reviews.length === 0 ? (
        <p className="text-center py-10 text-[13px]" style={{ color: 'var(--lumo-text-muted)' }}>
          Пока нет отзывов — открой конкурс и стань первым
        </p>
      ) : (
        <div className="space-y-3">
          {reviews.map((review) => (
            <article key={review.id} className="lumo-card p-4">
              <div className="flex items-center gap-2 mb-2">
                <MessageSquareQuote size={14} style={{ color: 'var(--lumo-text-muted)' }} />
                <span className="text-[11px] font-bold uppercase tracking-wide" style={{ color: 'var(--lumo-text-muted)' }}>
                  {review.contest || 'Конкурс'}
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
      )}
    </div>
  );
}
