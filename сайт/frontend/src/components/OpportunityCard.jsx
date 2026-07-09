import { CheckCircle, Sparkles } from 'lucide-react';

function deadlineClass(item) {
  if (item.isArchived) return 'bg-muted text-muted-foreground border-border';
  if (item.deadlineUrgent) return 'bg-red-500/10 text-red-500 border-red-500/20';
  return 'bg-sky-500/10 text-sky-600 border-sky-500/20 dark:text-sky-400';
}

function prizeClass(hasPrize) {
  return hasPrize
    ? 'bg-amber-500/15 text-amber-700 border-amber-500/25 dark:text-amber-300'
    : 'bg-muted text-muted-foreground border-border';
}

export default function OpportunityCard({ item, onOpen }) {
  const deadlineText = item.deadlineLabel || item.deadline;

  return (
    <article className="group rounded-2xl border border-border bg-card overflow-hidden hover:border-primary/40 transition-colors">
      <div className="p-5 flex flex-col min-h-0">
        <div className="flex justify-between items-start gap-3 mb-3">
          <div className="flex items-center gap-2 min-w-0 flex-1">
            <span className="text-xl shrink-0">{item.emoji}</span>
            <span className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground truncate">
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
          <span className="text-[10px] px-2 py-1 rounded-md font-semibold bg-sky-500/10 text-sky-600 border border-sky-500/20 dark:text-sky-400">
            {item.label}
          </span>
          {item.isNew && (
            <span className="inline-flex items-center gap-1 text-[10px] px-2 py-1 rounded-md font-semibold bg-emerald-500/15 text-emerald-700 border border-emerald-500/25 dark:text-emerald-300">
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

        <h3 className="text-base font-semibold text-foreground mb-2 line-clamp-2 group-hover:text-primary transition-colors">
          {item.title}
        </h3>
        <p className="text-sm text-muted-foreground line-clamp-3 mb-4 leading-relaxed flex-grow">
          {item.description}
        </p>

        {item.features?.length > 0 && (
          <div className="space-y-1.5 mt-auto">
            {item.features.slice(0, 2).map((feat) => (
              <div key={feat} className="flex items-start gap-2 text-sm text-foreground/80">
                <CheckCircle size={14} className="text-primary shrink-0 mt-0.5" />
                <span className="line-clamp-2">{feat}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="px-5 pb-5">
        <button
          type="button"
          onClick={() => onOpen(item)}
          className="w-full py-3 rounded-xl border border-border bg-muted/50 hover:bg-muted text-sm font-semibold transition-colors"
        >
          Подробнее
        </button>
      </div>
    </article>
  );
}
