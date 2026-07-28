import { ExternalLink, Sparkles, X } from 'lucide-react';
import { apiFetch } from '../api.js';

function trackClick(catalogId, type) {
  if (!catalogId) return;
  apiFetch('/lumo/track-click', {
    method: 'POST',
    body: JSON.stringify({ type, catalogId }),
  }).catch(() => {});
}

function openLink(url, catalogId, type) {
  if (!url) return;
  trackClick(catalogId, type);
  window.open(url, '_blank', 'noopener,noreferrer');
}

export default function DetailModal({ item, onClose }) {
  if (!item) return null;

  const telegramLink = item.messageLink || item.channelUrl;
  const hasApply = Boolean(item.applicationUrl);
  const hasTelegram = Boolean(telegramLink);

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white border border-neutral-200 max-w-lg w-full p-8 rounded-3xl shadow-2xl relative max-h-[90vh] overflow-y-auto">
        <button
          type="button"
          onClick={onClose}
          className="absolute top-5 right-5 text-neutral-400 hover:text-neutral-900 transition"
        >
          <X size={22} />
        </button>

        <div className="flex items-center gap-3 mb-4 flex-wrap">
          <span className="text-3xl">{item.emoji}</span>
          <span className="text-xs font-bold uppercase tracking-widest text-neutral-600">{item.label}</span>
          {item.isNew && (
            <span className="inline-flex items-center gap-1 text-[10px] px-2 py-1 rounded-md font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
              <Sparkles size={11} />
              Новое
            </span>
          )}
        </div>

        <h3 className="text-2xl font-bold mb-3 text-neutral-900">{item.title}</h3>
        <p className="text-sm text-neutral-500 mb-6 leading-relaxed">{item.description}</p>

        <div className="text-sm space-y-3 mb-6 text-neutral-800">
          <p>
            <span className="text-neutral-500">Для кого:</span> {item.country || 'Глобальная'}
          </p>
          <p>
            <span className="text-neutral-500">Дедлайн:</span> {item.deadlineLabel || item.deadline || 'не указан'}
          </p>
          <p>
            <span className="text-neutral-500">Приз:</span>{' '}
            {item.cashPrizeLabel || (item.hasCashPrize ? 'Денежный приз' : 'Без денежного приза')}
          </p>
          <p>
            <span className="text-neutral-500">Канал:</span> {item.sourceChannelName}
            {item.channelUrl && (
              <>
                {' '}
                <a
                  href={item.channelUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="text-sky-700 hover:underline"
                  onClick={() => trackClick(item.id, 'telegram')}
                >
                  @{item.channelUrl.split('/').pop()}
                </a>
              </>
            )}
          </p>
          {item.requirements && (
            <p>
              <span className="text-neutral-500">Требования:</span> {item.requirements}
            </p>
          )}
        </div>

        {(hasApply || hasTelegram) && (
          <div className={`grid gap-2 mb-4 ${hasApply && hasTelegram ? 'grid-cols-2' : 'grid-cols-1'}`}>
            {hasApply && (
              <button
                type="button"
                onClick={() => openLink(item.applicationUrl, item.id, 'apply')}
                className="inline-flex items-center justify-center gap-2 py-3.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold transition-colors"
              >
                <ExternalLink size={16} />
                Подать заявку
              </button>
            )}
            {hasTelegram && (
              <button
                type="button"
                onClick={() => openLink(telegramLink, item.id, 'telegram')}
                className="inline-flex items-center justify-center gap-2 py-3.5 rounded-xl bg-sky-50 hover:bg-sky-100 text-sky-800 border border-sky-200 text-sm font-semibold transition-colors"
              >
                <ExternalLink size={16} />
                {item.messageLink ? 'Пост в Telegram' : 'Канал в Telegram'}
              </button>
            )}
          </div>
        )}

        {!hasApply && !hasTelegram && (
          <p className="text-sm text-neutral-400 mb-4 rounded-xl bg-neutral-50 border border-neutral-100 px-4 py-3">
            Прямая ссылка на заявку не найдена в посте. Открой канал-источник в Telegram — там обычно есть регистрация.
          </p>
        )}

        <button
          type="button"
          onClick={onClose}
          className="w-full py-3.5 rounded-xl bg-neutral-900 text-white font-semibold hover:bg-neutral-800 transition"
        >
          Закрыть
        </button>
      </div>
    </div>
  );
}
