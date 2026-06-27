import { useState } from 'react';
import { ArrowRight, Pencil, Satellite, X } from 'lucide-react';
import { apiFetch, haptic } from '../api';
import { TYPE_STYLES } from '../utils/categories';

const CATEGORY_OPTIONS = Object.entries(TYPE_STYLES)
  .filter(([key]) => key !== 'другое')
  .map(([value, style]) => ({ value, label: style.label }));

const EMPTY_FORM = {
  title: '',
  type: '',
  customType: '',
  description: '',
  deadline: '',
  location: '',
  link: '',
};

export default function AddOpportunityModal({ open, onClose }) {
  const [mode, setMode] = useState('manual');
  const [form, setForm] = useState(EMPTY_FORM);
  const [sent, setSent] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  if (!open) return null;

  const setField = (key, value) => {
    setForm((prev) => ({ ...prev, [key]: value }));
    setError(null);
  };

  const isCustomType = form.type === 'другое';
  const customTypeOk = !isCustomType || form.customType.trim().length >= 2;

  const canSubmit =
    mode === 'channel'
      ? form.link.trim().length >= 5
      : form.title.trim().length >= 3 && form.type && customTypeOk;

  const reset = () => {
    setMode('manual');
    setForm(EMPTY_FORM);
    setSent(false);
    setSaving(false);
    setError(null);
  };

  const close = () => {
    reset();
    onClose();
  };

  const submit = async () => {
    if (!canSubmit || saving) return;
    haptic('medium');
    setSaving(true);
    setError(null);
    try {
      await apiFetch('/lumo/submissions', {
        method: 'POST',
        body: JSON.stringify({
          sourceMode: mode,
          title: mode === 'manual' ? form.title.trim() : null,
          type: mode === 'manual' ? form.type : null,
          customType: mode === 'manual' && form.type === 'другое' ? form.customType.trim() : null,
          description: form.description.trim() || null,
          deadline: form.deadline || null,
          location: form.location.trim() || null,
          link: form.link.trim() || null,
        }),
      });
      setSent(true);
    } catch (err) {
      setError(err.message || 'Не удалось отправить');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/60 backdrop-blur-sm">
      <div
        className="lumo-card w-full max-w-lg rounded-t-[24px] p-5 max-h-[92vh] overflow-y-auto"
        style={{ background: 'var(--lumo-surface)' }}
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-[18px] font-bold">Добавить возможность</h3>
          <button type="button" onClick={close} className="opacity-50 p-1" aria-label="Закрыть">
            <X size={20} />
          </button>
        </div>

        {sent ? (
          <div className="py-6 text-center">
            <p className="text-[15px] font-semibold mb-2">Отправлено на проверку</p>
            <p className="text-[13px] mb-5" style={{ color: 'var(--lumo-text-muted)' }}>
              Мы проверим заявку и опубликуем в каталоге, если всё ок.
            </p>
            <button type="button" onClick={close} className="w-full py-3 rounded-xl font-bold lumo-btn-primary">
              Готово
            </button>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-2 gap-2 mb-5">
              {[
                { id: 'manual', label: 'Вручную', icon: Pencil },
                { id: 'channel', label: 'Из канала', icon: Satellite },
              ].map(({ id, label, icon: Icon }) => {
                const active = mode === id;
                return (
                  <button
                    key={id}
                    type="button"
                    onClick={() => setMode(id)}
                    className={`flex flex-col items-center justify-center gap-2 py-4 rounded-2xl text-[13px] font-semibold transition ${
                      active ? 'lumo-mode-active' : 'lumo-mode-inactive'
                    }`}
                  >
                    <Icon size={22} style={{ color: active ? '#fbbf24' : 'var(--lumo-text-muted)' }} />
                    {label}
                  </button>
                );
              })}
            </div>

            {mode === 'manual' ? (
              <div className="space-y-4">
                <div>
                  <label className="lumo-form-label block mb-2">Название *</label>
                  <input
                    type="text"
                    value={form.title}
                    onChange={(e) => setField('title', e.target.value)}
                    placeholder="Например: IT-хакатон в Астане 2024"
                    className="lumo-form-input"
                  />
                </div>

                <div>
                  <label className="lumo-form-label block mb-2">Категория *</label>
                  <select
                    value={form.type}
                    onChange={(e) => {
                      const value = e.target.value;
                      setForm((prev) => ({
                        ...prev,
                        type: value,
                        customType: value === 'другое' ? prev.customType : '',
                      }));
                      setError(null);
                    }}
                    className="lumo-form-input"
                  >
                    <option value="">— Выбери категорию —</option>
                    {CATEGORY_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                    <option value="другое">Другое — своя категория</option>
                  </select>
                  {isCustomType && (
                    <input
                      type="text"
                      value={form.customType}
                      onChange={(e) => setField('customType', e.target.value)}
                      placeholder="Например: волонтёрство, наука, спорт…"
                      className="lumo-form-input mt-2"
                      maxLength={32}
                    />
                  )}
                </div>

                <div>
                  <label className="lumo-form-label block mb-2">Ссылка</label>
                  <input
                    type="url"
                    inputMode="url"
                    value={form.link}
                    onChange={(e) => setField('link', e.target.value)}
                    placeholder="https://forms.google.com/… или https://t.me/channel/123"
                    className="lumo-form-input"
                  />
                  <p className="text-[11px] mt-1.5" style={{ color: 'var(--lumo-text-muted)' }}>
                    Ссылка на регистрацию, заявку или пост в Telegram
                  </p>
                </div>

                <div>
                  <label className="lumo-form-label block mb-2">Описание</label>
                  <textarea
                    rows={4}
                    value={form.description}
                    onChange={(e) => setField('description', e.target.value)}
                    placeholder="Кратко расскажи о возможности, требованиях, призах..."
                    className="lumo-form-input resize-none"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="lumo-form-label block mb-2">Дедлайн</label>
                    <input
                      type="date"
                      value={form.deadline}
                      onChange={(e) => setField('deadline', e.target.value)}
                      className="lumo-form-input"
                    />
                  </div>
                  <div>
                    <label className="lumo-form-label block mb-2">Страна / город</label>
                    <input
                      type="text"
                      value={form.location}
                      onChange={(e) => setField('location', e.target.value)}
                      placeholder="Казахстан"
                      className="lumo-form-input"
                    />
                  </div>
                </div>

              </div>
            ) : (
              <div className="space-y-4">
                <div>
                  <label className="lumo-form-label block mb-2">Ссылка на пост *</label>
                  <input
                    type="text"
                    value={form.link}
                    onChange={(e) => setField('link', e.target.value)}
                    placeholder="https://t.me/channel/123 или @channel"
                    className="lumo-form-input"
                  />
                </div>
                <div>
                  <label className="lumo-form-label block mb-2">Комментарий</label>
                  <textarea
                    rows={3}
                    value={form.description}
                    onChange={(e) => setField('description', e.target.value)}
                    placeholder="Почему это стоит добавить в каталог?"
                    className="lumo-form-input resize-none"
                  />
                </div>
                <p className="text-[12px]" style={{ color: 'var(--lumo-text-muted)' }}>
                  Мы проверим пост и добавим в каталог после модерации.
                </p>
              </div>
            )}

            {error && (
              <p className="text-[13px] text-red-400 mt-3">{error}</p>
            )}

            <button
              type="button"
              onClick={submit}
              disabled={!canSubmit || saving}
              className="w-full mt-5 py-3.5 rounded-xl font-bold lumo-btn-primary disabled:opacity-40 flex items-center justify-center gap-2"
            >
              {saving ? 'Отправка…' : 'Отправить на проверку'}
              {!saving && <ArrowRight size={18} />}
            </button>
          </>
        )}
      </div>
    </div>
  );
}
