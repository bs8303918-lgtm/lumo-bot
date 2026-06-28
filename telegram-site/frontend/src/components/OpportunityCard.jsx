import { Calendar, Clock } from 'lucide-react';
import { formatDeadlineMeta, sourceHandle } from '../utils/deadline';
import { itemTags } from '../utils/categories';
import TagChips from './TagChips';
import { CardMatchFeedback } from './SearchFeedback';

export default function OpportunityCard({ item, onOpen, feedbackQuery, feedbackCategories }) {
  const tags = itemTags(item);
  const deadline = formatDeadlineMeta(item.deadline);
  const handle = sourceHandle(item);

  return (
    <article
      className="lumo-card p-4 cursor-pointer active:scale-[0.99] transition-transform"
      onClick={() => onOpen(item)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onOpen(item)}
    >
      <div className="flex items-start justify-between gap-3 mb-2.5">
        <h2 className="text-[15px] font-bold leading-snug line-clamp-2 flex-1">{item.title}</h2>
        <TagChips tags={tags} className="max-w-[48%]" />
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
        {handle && (
          <span className="shrink-0 font-medium truncate max-w-[45%]" style={{ color: 'var(--lumo-link)' }}>
            {handle}
          </span>
        )}
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
