import { Calendar, Clock, Heart } from 'lucide-react';
import { formatDeadlineMeta, sourceHandle } from '../utils/deadline';
import { itemTags } from '../utils/categories';
import TagChips from './TagChips';
import { CardMatchFeedback } from './SearchFeedback';
import { haptic } from '../api';

export default function OpportunityCard({
  item,
  onOpen,
  feedbackQuery,
  feedbackCategories,
  isFavorite = false,
  onToggleFavorite,
}) {
  const tags = itemTags(item);
  const deadline = item.deadlineLabel
    ? {
        label: item.deadlineLabel,
        urgent: Boolean(item.deadlineUrgent),
        icon: item.deadlineUrgent ? 'clock' : 'calendar',
      }
    : formatDeadlineMeta(item.deadline);
  const handle = sourceHandle(item);

  return (
    <article
      className="lumo-card p-4 cursor-pointer active:scale-[0.99] transition-transform relative"
      onClick={() => onOpen(item)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onOpen(item)}
    >
      <div className="flex items-start justify-between gap-3 mb-2.5">
        <h2 className="text-[15px] font-bold leading-snug line-clamp-2 flex-1 pr-1">{item.title}</h2>
        <div className="flex items-center gap-1.5 shrink-0">
          <TagChips tags={tags} className="max-w-[140px]" />
          {onToggleFavorite && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                haptic('light');
                onToggleFavorite(item);
              }}
              className="w-7 h-7 rounded-full flex items-center justify-center shrink-0"
              aria-label={isFavorite ? 'Убрать из избранного' : 'В избранное'}
            >
              <Heart
                size={16}
                fill={isFavorite ? 'var(--lumo-urgent)' : 'none'}
                style={{ color: isFavorite ? 'var(--lumo-urgent)' : 'var(--lumo-text-muted)' }}
              />
            </button>
          )}
        </div>
      </div>

      <p className="text-[13px] leading-relaxed line-clamp-3 mb-3" style={{ color: 'var(--lumo-text-muted)' }}>
        {item.description}
      </p>

      <div className="flex items-center justify-between gap-2 text-[12px]">
        <div
          className="flex items-center gap-1.5 min-w-0"
          style={{ color: deadline.urgent ? 'var(--lumo-urgent)' : 'var(--lumo-text-muted)' }}
        >
          {deadline.icon === 'clock' ? <Clock size={13} className="shrink-0" /> : <Calendar size={13} className="shrink-0" />}
          <span className="truncate">{deadline.label}</span>
        </div>
        <div className="flex items-center gap-2 shrink-0 max-w-[55%] justify-end">
          {item.country && (
            <span className="font-medium truncate" style={{ color: 'var(--lumo-text-muted)' }}>
              {item.country}
            </span>
          )}
          {handle && (
            <span className="font-medium truncate" style={{ color: 'var(--lumo-link)' }}>
              {handle}
            </span>
          )}
        </div>
      </div>

      {feedbackQuery && (
        <CardMatchFeedback
          query={feedbackQuery}
          item={item}
          categories={feedbackCategories}
        />
      )}
    </article>
  );
}
