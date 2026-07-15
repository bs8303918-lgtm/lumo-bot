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
  compact = false,
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

  if (compact) {
    return (
      <div className="flex flex-wrap items-center gap-2 w-full">
        {typeOptions.map((cat) => {
          const active = draft.types.includes(cat.type);
          return (
            <button
              key={cat.type}
              type="button"
              onClick={() => toggleType(cat.type)}
              className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
                active
                  ? 'bg-neutral-900 text-white border-neutral-900'
                  : 'bg-white text-neutral-600 border-neutral-200 hover:border-neutral-400'
              }`}
            >
              {cat.label || CATALOG_TYPE_LABELS[cat.type] || cat.type}
            </button>
          );
        })}
        <button
          type="button"
          onClick={onApply}
          className="ml-auto inline-flex items-center gap-1.5 px-4 py-1.5 rounded-full bg-neutral-900 text-white text-xs font-semibold"
        >
          <Filter size={14} />
          Применить
        </button>
        <button
          type="button"
          onClick={onReset}
          className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-full border border-neutral-200 text-xs text-neutral-600 hover:bg-neutral-50"
        >
          <RotateCcw size={14} />
          Сбросить
        </button>
      </div>
    );
  }

  return (
    <aside className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm">
      <h2 className="text-base font-semibold text-neutral-900 mb-5">Фильтры</h2>

      <div className="mb-6">
        <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500 mb-3">Тип</p>
        <div className="max-h-56 overflow-y-auto space-y-2 pr-1">
          {typeOptions.map((cat) => (
            <label
              key={cat.type}
              className="flex items-center gap-2.5 text-sm text-neutral-800 cursor-pointer select-none"
            >
              <input
                type="checkbox"
                checked={draft.types.includes(cat.type)}
                onChange={() => toggleType(cat.type)}
                className="h-4 w-4 rounded border-neutral-300 accent-neutral-900"
              />
              <span className="flex-1">{cat.label || CATALOG_TYPE_LABELS[cat.type] || cat.type}</span>
              {cat.count > 0 && (
                <span className="text-xs text-neutral-400 tabular-nums">{cat.count}</span>
              )}
            </label>
          ))}
        </div>
      </div>

      <div className="mb-6">
        <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500 mb-3">Сортировка</p>
        <div className="space-y-2">
          {CATALOG_SORT_OPTIONS.map((option) => (
            <label
              key={option.id}
              className="flex items-center gap-2.5 text-sm text-neutral-800 cursor-pointer select-none"
            >
              <input
                type="radio"
                name="catalog-sort"
                checked={draft.sort === option.id}
                onChange={() => onDraftChange({ ...draft, sort: option.id })}
                className="h-4 w-4 border-neutral-300 accent-neutral-900"
              />
              <span>{option.label}</span>
            </label>
          ))}
        </div>
      </div>

      <div className="mb-6">
        <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500 mb-3">Приз</p>
        <div className="space-y-2">
          {CATALOG_PRIZE_OPTIONS.map((option) => (
            <label
              key={option.id}
              className="flex items-center gap-2.5 text-sm text-neutral-800 cursor-pointer select-none"
            >
              <input
                type="radio"
                name="catalog-prize"
                checked={draft.cashPrize === option.id}
                onChange={() => onDraftChange({ ...draft, cashPrize: option.id })}
                className="h-4 w-4 border-neutral-300 accent-neutral-900"
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
          className="w-full inline-flex items-center justify-center gap-2 py-3 rounded-xl bg-neutral-900 text-white text-sm font-semibold hover:bg-neutral-800 transition-colors"
        >
          <Filter size={16} />
          Применить
        </button>
        <button
          type="button"
          onClick={onReset}
          className="w-full inline-flex items-center justify-center gap-2 py-3 rounded-xl border border-neutral-200 bg-white text-sm font-medium text-neutral-600 hover:bg-neutral-50 transition-colors"
        >
          <RotateCcw size={15} />
          Сбросить всё
        </button>
      </div>
    </aside>
  );
}

export { DEFAULT_CATALOG_FILTERS };
