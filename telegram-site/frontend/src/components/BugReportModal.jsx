import { useState } from 'react';
import { Bug, Lightbulb, X } from 'lucide-react';
import { apiFetch, haptic, openBugReport } from '../api';

export default function BugReportModal({ open, onClose, supportContact }) {
  const [message, setMessage] = useState('');
  const [kind, setKind] = useState('bug');
  const [sent, setSent] = useState(false);
  const [saving, setSaving] = useState(false);

  if (!open) return null;

  const submit = async () => {
    if (message.trim().length < 5 || saving) return;
    haptic('medium');
    setSaving(true);
    try {
      await apiFetch('/feedback', {
        method: 'POST',
        body: JSON.stringify({ kind, message: message.trim() }),
      });
      openBugReport(`[${kind === 'bug' ? 'Баг' : 'Идея'}] ${message}`, supportContact);
      setSent(true);
    } catch {
      openBugReport(message, supportContact);
      setSent(true);
    } finally {
      setSaving(false);
    }
  };

  const close = () => {
    setMessage('');
    setKind('bug');
    setSent(false);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/60 backdrop-blur-sm">
      <div className="lumo-card w-full max-w-lg rounded-t-[24px] p-5">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            {kind === 'bug' ? (
              <Bug size={18} style={{ color: 'var(--lumo-accent)' }} />
            ) : (
              <Lightbulb size={18} style={{ color: 'var(--lumo-accent)' }} />
            )}
            <h3 className="font-bold">Баг или идея</h3>
          </div>
          <button type="button" onClick={close} className="opacity-50">
            <X size={18} />
          </button>
        </div>

        {sent ? (
          <div className="py-4 text-center">
            <p className="text-sm mb-4" style={{ color: 'var(--lumo-text-muted)' }}>
              Спасибо! Сохранено и отправлено в поддержку.
            </p>
            <button type="button" onClick={close} className="w-full py-3 rounded-xl font-bold lumo-btn-primary">
              Готово
            </button>
          </div>
        ) : (
          <>
            <div className="flex gap-2 mb-3">
              {[
                { id: 'bug', label: 'Баг' },
                { id: 'idea', label: 'Идея' },
              ].map((opt) => (
                <button
                  key={opt.id}
                  type="button"
                  onClick={() => setKind(opt.id)}
                  className={`flex-1 py-2 rounded-xl text-[13px] font-semibold border transition ${
                    kind === opt.id ? 'lumo-btn-primary border-transparent' : ''
                  }`}
                  style={
                    kind !== opt.id
                      ? { borderColor: 'var(--lumo-border)', background: 'var(--lumo-surface-muted)' }
                      : undefined
                  }
                >
                  {opt.label}
                </button>
              ))}
            </div>
            <textarea
              rows={3}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Что произошло или что улучшить?"
              className="w-full rounded-xl p-3 text-sm border mb-3 resize-none focus:outline-none"
              style={{ borderColor: 'var(--lumo-border)', background: 'var(--lumo-surface-muted)' }}
            />
            <button
              type="button"
              onClick={submit}
              disabled={message.trim().length < 5 || saving}
              className="w-full py-3 rounded-xl font-bold lumo-btn-primary disabled:opacity-40"
            >
              {saving ? 'Отправка…' : 'Отправить'}
            </button>
          </>
        )}
      </div>
    </div>
  );
}
