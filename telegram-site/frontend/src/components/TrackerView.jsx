import { useState } from 'react';
import { CalendarPlus, ChevronDown, ChevronUp, Plus, Square, CheckSquare, Trash2 } from 'lucide-react';
import {
  KANBAN_STAGES,
  addCard,
  googleCalendarUrl,
  loadCards,
  removeCard,
  toggleChecklistItem,
  updateCard,
} from '../utils/localFeatures';
import { haptic } from '../api';

const EMPTY_FORM = { title: '', org: '', deadline: '', link: '' };

function CardRow({ card, expanded, onToggleExpand, onChangeStage, onToggleItem, onRemove }) {
  const doneCount = card.checklist.filter((i) => i.done).length;

  return (
    <div className="lumo-card p-4">
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="min-w-0 flex-1">
          <h3 className="text-[14px] font-bold leading-snug truncate">{card.title}</h3>
          {card.org && (
            <p className="text-[12px] truncate" style={{ color: 'var(--lumo-text-muted)' }}>
              {card.org}
            </p>
          )}
        </div>
        <button
          type="button"
          onClick={() => onRemove(card.id)}
          className="w-7 h-7 rounded-full flex items-center justify-center shrink-0"
          style={{ color: 'var(--lumo-text-muted)' }}
          aria-label="Удалить"
        >
          <Trash2 size={14} />
        </button>
      </div>

      {card.deadline && (
        <p className="text-[12px] mb-3" style={{ color: 'var(--lumo-text-muted)' }}>
          Дедлайн: {card.deadline}
        </p>
      )}

      <div className="flex gap-1.5 overflow-x-auto scrollbar-none -mx-1 px-1 mb-3">
        {KANBAN_STAGES.map((stage) => {
          const active = card.stage === stage.id;
          return (
            <button
              key={stage.id}
              type="button"
              onClick={() => onChangeStage(card.id, stage.id)}
              className={`shrink-0 px-3 py-1.5 rounded-full text-[11px] font-semibold transition ${
                active ? 'lumo-filter-active' : 'lumo-filter-inactive'
              }`}
            >
              {stage.label}
            </button>
          );
        })}
      </div>

      <button
        type="button"
        onClick={() => onToggleExpand(card.id)}
        className="w-full flex items-center justify-between text-[12px] font-semibold"
        style={{ color: 'var(--lumo-text-muted)' }}
      >
        <span>
          Документы {doneCount}/{card.checklist.length}
        </span>
        {expanded ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
      </button>

      {expanded && (
        <div className="mt-2.5 space-y-1.5">
          {card.checklist.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => onToggleItem(card.id, item.id)}
              className="w-full flex items-center gap-2 text-left text-[13px] py-1"
              style={{ color: item.done ? 'var(--lumo-text-muted)' : 'var(--lumo-text)' }}
            >
              {item.done ? (
                <CheckSquare size={16} style={{ color: 'var(--lumo-accent)' }} className="shrink-0" />
              ) : (
                <Square size={16} className="shrink-0" style={{ color: 'var(--lumo-text-muted)' }} />
              )}
              <span className={item.done ? 'line-through' : ''}>{item.label}</span>
            </button>
          ))}
        </div>
      )}

      {card.link && (
        <a
          href={card.link}
          target="_blank"
          rel="noreferrer"
          className="mt-3 inline-block text-[12px] font-medium underline"
          style={{ color: 'var(--lumo-link)' }}
        >
          Открыть ссылку
        </a>
      )}
    </div>
  );
}

export default function TrackerView() {
  const [cards, setCards] = useState(() => loadCards());
  const [stageFilter, setStageFilter] = useState('all');
  const [expandedId, setExpandedId] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);

  const filtered = stageFilter === 'all' ? cards : cards.filter((c) => c.stage === stageFilter);
  const upcoming = cards.filter((c) => c.deadline).slice(0, 5);

  const submitForm = () => {
    if (!form.title.trim()) return;
    haptic('light');
    const next = addCard({
      title: form.title.trim(),
      org: form.org.trim(),
      deadline: form.deadline.trim(),
      link: form.link.trim(),
    });
    setCards(next);
    setForm(EMPTY_FORM);
    setShowForm(false);
  };

  return (
    <div className="pb-8">
      <header className="mb-5 flex items-start justify-between gap-3">
        <div>
          <h1 className="text-[22px] font-bold mb-2">Заявки</h1>
          <p className="text-[13px]" style={{ color: 'var(--lumo-text-muted)' }}>
            Трекер подач и дедлайнов
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            haptic('light');
            setShowForm((v) => !v);
          }}
          className="shrink-0 flex items-center gap-1.5 px-3 py-2 rounded-xl text-[12px] font-bold lumo-btn-primary"
        >
          <Plus size={16} />
          Добавить
        </button>
      </header>

      {showForm && (
        <div className="lumo-card p-4 mb-5 space-y-2.5">
          <input
            value={form.title}
            onChange={(e) => setForm((p) => ({ ...p, title: e.target.value }))}
            placeholder="Название конкурса / гранта *"
            className="lumo-form-input"
          />
          <input
            value={form.org}
            onChange={(e) => setForm((p) => ({ ...p, org: e.target.value }))}
            placeholder="Организатор — необязательно"
            className="lumo-form-input"
          />
          <input
            value={form.deadline}
            onChange={(e) => setForm((p) => ({ ...p, deadline: e.target.value }))}
            placeholder="Дедлайн, например 15.08.2026"
            className="lumo-form-input"
          />
          <input
            value={form.link}
            onChange={(e) => setForm((p) => ({ ...p, link: e.target.value }))}
            placeholder="Ссылка на заявку — необязательно"
            className="lumo-form-input"
          />
          <button
            type="button"
            onClick={submitForm}
            disabled={!form.title.trim()}
            className="w-full py-3 rounded-xl font-bold text-[13px] lumo-btn-primary disabled:opacity-40"
          >
            Сохранить
          </button>
        </div>
      )}

      {upcoming.length > 0 && (
        <div className="lumo-card p-4 mb-5">
          <p className="text-[12px] font-bold uppercase tracking-wide mb-2.5" style={{ color: 'var(--lumo-text-muted)' }}>
            Ближайшие дедлайны
          </p>
          <div className="space-y-2">
            {upcoming.map((c) => (
              <div key={c.id} className="flex items-center justify-between gap-2 text-[13px]">
                <span className="truncate">{c.title} · {c.deadline}</span>
                <a
                  href={googleCalendarUrl({ title: c.title, date: c.deadline, note: c.link })}
                  target="_blank"
                  rel="noreferrer"
                  className="shrink-0 flex items-center gap-1 text-[11px] font-semibold"
                  style={{ color: 'var(--lumo-link)' }}
                >
                  <CalendarPlus size={13} />
                  В календарь
                </a>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="flex gap-1.5 overflow-x-auto scrollbar-none -mx-1 px-1 mb-4">
        <button
          type="button"
          onClick={() => setStageFilter('all')}
          className={`shrink-0 px-3.5 py-2 rounded-full text-[12px] font-semibold transition ${
            stageFilter === 'all' ? 'lumo-filter-active' : 'lumo-filter-inactive'
          }`}
        >
          Все
        </button>
        {KANBAN_STAGES.map((stage) => (
          <button
            key={stage.id}
            type="button"
            onClick={() => setStageFilter(stage.id)}
            className={`shrink-0 px-3.5 py-2 rounded-full text-[12px] font-semibold transition ${
              stageFilter === stage.id ? 'lumo-filter-active' : 'lumo-filter-inactive'
            }`}
          >
            {stage.label}
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <p className="text-center py-12 text-[13px]" style={{ color: 'var(--lumo-text-muted)' }}>
          Пока пусто — добавь заявку вручную или нажми «В заявки» в карточке конкурса
        </p>
      ) : (
        <div className="space-y-3">
          {filtered.map((card) => (
            <CardRow
              key={card.id}
              card={card}
              expanded={expandedId === card.id}
              onToggleExpand={(id) => setExpandedId((cur) => (cur === id ? null : id))}
              onChangeStage={(id, stage) => setCards(updateCard(id, { stage }))}
              onToggleItem={(cardId, itemId) => setCards(toggleChecklistItem(cardId, itemId))}
              onRemove={(id) => setCards(removeCard(id))}
            />
          ))}
        </div>
      )}
    </div>
  );
}
