import { CheckCircle, ExternalLink, Sparkles } from 'lucide-react';

function deadlineClass(item) {
  if (item.isArchived) return 'bg-neutral-100 text-neutral-500 border-neutral-200';
  if (item.deadlineUrgent) return 'bg-red-50 text-red-600 border-red-200';
  return 'bg-sky-50 text-sky-700 border-sky-200';
}

function prizeClass(hasPrize) {
  return hasPrize
    ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
    : 'bg-neutral-100 text-neutral-500 border-neutral-200';
}

export default function OpportunityCard({ item, onOpen, primaryAction }) {
  const deadlineText = item.deadlineLabel || item.deadline || 'не указан';

  return (
    <article className="group rounded-2xl border border-neutral-200 bg-white overflow-hidden hover:border-neutral-300 hover:shadow-md hover:shadow-black/[0.04] transition-all">
      <div className="p-5 flex flex-col min-h-0">
        <div className="flex justify-between items-start gap-3 mb-3">
          <div className="flex items-center gap-2 min-w-0 flex-1">
            <span className="text-xl shrink-0">{item.emoji}</span>
            <span className="text-[11px] font-semibold uppercase tracking-wide text-neutral-500 truncate">
              {item.sourceChannelName}
            </span>
          </div>
          <span
            className={`text-[10px] px-2 py-1 rounded-lg font-semibold shrink-0 border ${deadlineClass(item)}`}
          >
            {deadlineText}
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-2 mb-2">
          <span className="text-[10px] px-2 py-1 rounded-md font-semibold bg-sky-50 text-sky-700 border border-sky-200">
            {item.label}
          </span>
          {item.country && (
            <span className="text-[10px] px-2 py-1 rounded-md font-semibold bg-amber-50 text-amber-800 border border-amber-200">
              {item.country}
            </span>
          )}
          {item.isNew && (
            <span className="inline-flex items-center gap-1 text-[10px] px-2 py-1 rounded-md font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
              <Sparkles size={11} />
              Новое
            </span>
          )}
          <span
            className={`text-[10px] px-2 py-1 rounded-md font-semibold border ${prizeClass(item.hasCashPrize)}`}
          >
            {item.cashPrizeLabel || (item.hasCashPrize ? 'Денежный приз' : 'Без денежного приза')}
          </span>
        </div>

        <h3 className="text-base font-semibold text-neutral-900 mb-2 line-clamp-2 group-hover:text-neutral-700 transition-colors">
          {item.title}
        </h3>
        <p className="text-sm text-neutral-500 line-clamp-3 mb-4 leading-relaxed flex-grow">
          {item.description || 'Описание не указано'}
        </p>

        {item.features?.length > 0 && (
          <div className="space-y-1.5 mt-auto">
            {item.features.slice(0, 2).map((feat) => (
              <div key={feat} className="flex items-start gap-2 text-sm text-neutral-700">
                <CheckCircle size={14} className="text-neutral-900 shrink-0 mt-0.5" />
                <span className="line-clamp-2">{feat}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {(item.applicationUrl || item.messageLink || item.channelUrl) && (
        <div className="px-5 pb-2 flex flex-wrap gap-2">
          {item.applicationUrl && (
            <a
              href={item.applicationUrl}
              target="_blank"
              rel="noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="inline-flex items-center gap-1 text-[11px] font-semibold px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-100"
            >
              <ExternalLink size={12} />
              Заявка
            </a>
          )}
          {(item.messageLink || item.channelUrl) && (
            <a
              href={item.messageLink || item.channelUrl}
              target="_blank"
              rel="noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="inline-flex items-center gap-1 text-[11px] font-semibold px-2.5 py-1 rounded-full bg-sky-50 text-sky-700 border border-sky-200 hover:bg-sky-100"
            >
              <ExternalLink size={12} />
              Telegram
            </a>
          )}
        </div>
      )}

      <div className={`px-5 pb-5 ${primaryAction && onOpen ? 'flex gap-2' : ''}`}>
        {primaryAction && (
          <button
            type="button"
            onClick={primaryAction.onClick}
            disabled={primaryAction.loading}
            className={`py-3 rounded-xl bg-neutral-900 hover:bg-neutral-800 text-white text-sm font-semibold transition-colors disabled:opacity-60 ${
              onOpen ? 'flex-1' : 'w-full'
            }`}
          >
            {primaryAction.loading ? 'Добавляем…' : primaryAction.label}
          </button>
        )}
        {onOpen && (
          <button
            type="button"
            onClick={() => onOpen(item)}
            className={`py-3 rounded-xl border border-neutral-200 bg-neutral-50 hover:bg-neutral-100 text-sm font-semibold text-neutral-800 transition-colors ${
              primaryAction ? 'flex-1' : 'w-full'
            }`}
          >
            Подробнее
          </button>
        )}
      </div>
    </article>
  );
}
