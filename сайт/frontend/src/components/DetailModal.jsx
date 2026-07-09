import { Sparkles, X } from 'lucide-react';

export default function DetailModal({ item, onClose }) {
  if (!item) return null;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-card border border-border max-w-lg w-full p-8 rounded-3xl shadow-2xl relative max-h-[90vh] overflow-y-auto">
        <button
          type="button"
          onClick={onClose}
          className="absolute top-5 right-5 text-muted-foreground hover:text-foreground transition"
        >
          <X size={22} />
        </button>

        <div className="flex items-center gap-3 mb-4 flex-wrap">
          <span className="text-3xl">{item.emoji}</span>
          <span className="text-xs font-bold uppercase tracking-widest text-primary">{item.label}</span>
          {item.isNew && (
            <span className="inline-flex items-center gap-1 text-[10px] px-2 py-1 rounded-md font-semibold bg-emerald-500/15 text-emerald-700 border border-emerald-500/25 dark:text-emerald-300">
              <Sparkles size={11} />
              Новое
            </span>
          )}
        </div>

        <h3 className="text-2xl font-bold mb-3 text-foreground">{item.title}</h3>
        <p className="text-sm text-muted-foreground mb-6 leading-relaxed">{item.description}</p>

        <div className="text-sm space-y-3 mb-8 text-foreground/90">
          <p>
            <span className="text-muted-foreground">Дедлайн:</span>{' '}
            {item.deadlineLabel || item.deadline}
          </p>
          <p>
            <span className="text-muted-foreground">Приз:</span>{' '}
            {item.cashPrizeLabel || (item.hasCashPrize ? 'Денежный приз' : 'Без денежного приза')}
          </p>
          <p>
            <span className="text-muted-foreground">Канал:</span> {item.sourceChannelName}
          </p>
          {item.requirements && (
            <p>
              <span className="text-muted-foreground">Требования:</span> {item.requirements}
            </p>
          )}
          {item.applicationUrl && (
            <p>
              <span className="text-muted-foreground">Заявка:</span>{' '}
              <a href={item.applicationUrl} className="text-primary hover:underline break-all" target="_blank" rel="noreferrer">
                Открыть
              </a>
            </p>
          )}
        </div>

        <button
          type="button"
          onClick={onClose}
          className="w-full py-3.5 rounded-xl bg-primary text-primary-foreground font-semibold hover:opacity-90 transition"
        >
          Закрыть
        </button>
      </div>
    </div>
  );
}
