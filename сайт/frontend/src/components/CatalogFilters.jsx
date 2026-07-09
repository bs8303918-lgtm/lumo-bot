import { Filter, RotateCcw } from 'lucide-react';
import {
  CATALOG_PRIZE_OPTIONS,
  CATALOG_SORT_OPTIONS,
  CATALOG_TYPE_LABELS,
  DEFAULT_CATALOG_FILTERS,
} from '../constants/catalogFilters.js';

export default function CatalogFilters({
  categories,
  draft,
  onDraftChange,
  onApply,
  onReset,
}) {
  const toggleType = (type) => {
    const next = draft.types.includes(type)
      ? draft.types.filter((item) => item !== type)
      : [...draft.types, type];
    onDraftChange({ ...draft, types: next });
  };

  const typeOptions = categories.length
    ? categories.filter((cat) => cat.type !== 'all')
    : Object.entries(CATALOG_TYPE_LABELS).map(([type, label]) => ({ type, label, count: 0 }));

  return (
    <aside className="rounded-2xl border border-border bg-card p-5 shadow-sm">
      <h2 className="text-base font-semibold text-foreground mb-5">Фильтры</h2>

      <div className="mb-6">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3">Тип</p>
        <div className="max-h-56 overflow-y-auto space-y-2 pr-1">
          {typeOptions.map((cat) => (
            <label
              key={cat.type}
              className="flex items-center gap-2.5 text-sm text-foreground cursor-pointer select-none"
            >
              <input
                type="checkbox"
                checked={draft.types.includes(cat.type)}
                onChange={() => toggleType(cat.type)}
                className="h-4 w-4 rounded border-border accent-primary"
              />
              <span className="flex-1">{cat.label || CATALOG_TYPE_LABELS[cat.type] || cat.type}</span>
              {cat.count > 0 && (
                <span className="text-xs text-muted-foreground tabular-nums">{cat.count}</span>
              )}
            </label>
          ))}
        </div>
      </div>

      <div className="mb-6">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3">Сортировка</p>
        <div className="space-y-2">
          {CATALOG_SORT_OPTIONS.map((option) => (
            <label
              key={option.id}
              className="flex items-center gap-2.5 text-sm text-foreground cursor-pointer select-none"
            >
              <input
                type="radio"
                name="catalog-sort"
                checked={draft.sort === option.id}
                onChange={() => onDraftChange({ ...draft, sort: option.id })}
                className="h-4 w-4 border-border accent-primary"
              />
              <span>{option.label}</span>
            </label>
          ))}
        </div>
      </div>

      <div className="mb-6">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3">Приз</p>
        <div className="space-y-2">
          {CATALOG_PRIZE_OPTIONS.map((option) => (
            <label
              key={option.id}
              className="flex items-center gap-2.5 text-sm text-foreground cursor-pointer select-none"
            >
              <input
                type="radio"
                name="catalog-prize"
                checked={draft.cashPrize === option.id}
                onChange={() => onDraftChange({ ...draft, cashPrize: option.id })}
                className="h-4 w-4 border-border accent-primary"
              />
              <span>{option.label}</span>
            </label>
          ))}
        </div>
      </div>

      <div className="space-y-2">
        <button
          type="button"
          onClick={onApply}
          className="w-full inline-flex items-center justify-center gap-2 py-3 rounded-xl bg-primary text-primary-foreground text-sm font-semibold hover:opacity-90 transition-opacity"
        >
          <Filter size={16} />
          Применить
        </button>
        <button
          type="button"
          onClick={onReset}
          className="w-full inline-flex items-center justify-center gap-2 py-3 rounded-xl border border-border bg-background text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
        >
          <RotateCcw size={15} />
          Сбросить всё
        </button>
      </div>
    </aside>
  );
}

export { DEFAULT_CATALOG_FILTERS };
