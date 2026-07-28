import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { FileDown, Loader2 } from 'lucide-react';
import LumoLogo from './components/LumoLogo.jsx';

const API_BASE = (import.meta.env.VITE_API_URL || 'https://lumo-bot-production-9903.up.railway.app').replace(/\/$/, '');

async function fetchShortlist(slug) {
  const res = await fetch(`${API_BASE}/api/workspace/shortlist/${slug}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Подборка не найдена');
  }
  return res.json();
}

export default function ShortlistPublicPage() {
  const { slug } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const payload = await fetchShortlist(slug);
        if (!cancelled) setData(payload);
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [slug]);

  if (loading) {
    return (
      <div className="min-h-dvh flex items-center justify-center text-neutral-400">
        <Loader2 className="animate-spin" size={24} />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-dvh flex flex-col items-center justify-center px-4 text-center">
        <p className="text-neutral-600 mb-4">{error || 'Подборка не найдена'}</p>
        <Link to="/" className="text-sm text-neutral-900 underline">
          На главную
        </Link>
      </div>
    );
  }

  return (
    <div className="shortlist-page min-h-dvh bg-white text-neutral-900">
      <header className="shortlist-no-print border-b border-neutral-200 px-5 py-4 flex items-center justify-between gap-4">
        <Link to="/">
          <LumoLogo theme="light" size="sm" />
        </Link>
        <button
          type="button"
          onClick={() => window.print()}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-neutral-900 text-white text-sm font-medium"
        >
          <FileDown size={16} />
          Сохранить PDF
        </button>
      </header>

      <main className="max-w-3xl mx-auto px-5 py-10 md:py-14">
        <div className="shortlist-brand mb-10 pb-8 border-b border-neutral-200">
          <p className="text-xs uppercase tracking-[0.2em] text-neutral-400 mb-2">Персональная подборка</p>
          <h1 className="text-3xl md:text-4xl font-bold tracking-tight mb-2">{data.title}</h1>
          <p className="text-lg text-neutral-600">{data.agencyName}</p>
          <p className="text-sm text-neutral-400 mt-4">
            {data.total} {data.total === 1 ? 'программа' : data.total < 5 ? 'программы' : 'программ'}
          </p>
        </div>

        <div className="space-y-6">
          {data.items.map((item, index) => (
            <article
              key={item.id}
              className="shortlist-item rounded-2xl border border-neutral-200 p-5 break-inside-avoid"
            >
              <div className="flex items-start gap-3">
                <span className="text-2xl shrink-0">{item.emoji}</span>
                <div className="min-w-0 flex-1">
                  <p className="text-xs text-neutral-400 mb-1">
                    {index + 1}. {item.label}
                  </p>
                  <h2 className="text-lg font-semibold leading-snug mb-2">{item.title}</h2>
                  {item.description && (
                    <p className="text-sm text-neutral-600 leading-relaxed mb-3">{item.description}</p>
                  )}
                  <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-neutral-500">
                    {item.country && <span>Для кого: {item.country}</span>}
                    <span>Дедлайн: {item.deadlineLabel}</span>
                    {item.sourceChannelName && <span>Источник: {item.sourceChannelName}</span>}
                  </div>
                  {item.requirements && (
                    <p className="text-sm text-neutral-500 mt-3">
                      <span className="font-medium text-neutral-700">Требования: </span>
                      {item.requirements}
                    </p>
                  )}
                  {item.applicationUrl && (
                    <a
                      href={item.applicationUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="shortlist-link inline-block mt-4 text-sm font-medium text-neutral-900 underline"
                    >
                      Подать заявку →
                    </a>
                  )}
                </div>
              </div>
            </article>
          ))}
        </div>

        <footer className="shortlist-footer mt-12 pt-6 border-t border-neutral-100 text-center text-xs text-neutral-400">
          Подготовлено в Lumo · lumo.ai
        </footer>
      </main>
    </div>
  );
}
