import { tagStyle } from '../utils/categories';

export default function TagChips({ tags, className = '' }) {
  if (!tags?.length) return null;

  return (
    <div className={`flex flex-wrap gap-1.5 justify-end ${className}`}>
      {tags.map((tag) => {
        const style = tagStyle(tag);
        const key = typeof tag === 'object' ? tag.type : tag;
        return (
          <span
            key={key}
            className="text-[10px] font-semibold px-2 py-0.5 rounded-full shrink-0"
            style={{ background: style.bg, color: style.text }}
          >
            {style.label}
          </span>
        );
      })}
    </div>
  );
}
