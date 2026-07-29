import { useState } from 'react';
import { ShieldCheck } from 'lucide-react';
import { apiFetch, getTelegram } from '../api';
import GoogleLoginButton from './GoogleLoginButton';
import LumoLogo from './LumoLogo';

export default function GoogleAuthGate({ onLinked }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const inTelegram = Boolean(getTelegram()?.initData);

  const handleCredential = async (idToken) => {
    setError(null);
    setLoading(true);
    try {
      await apiFetch('/auth/link-google', {
        method: 'POST',
        body: JSON.stringify({ idToken }),
      });
      onLinked?.();
    } catch (err) {
      setError(err.message || 'Не получилось подтвердить Google-аккаунт. Попробуй ещё раз.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-40 flex flex-col items-center justify-center px-6"
      style={{ background: 'var(--lumo-bg)', color: 'var(--lumo-text)' }}
    >
      <div className="mb-6">
        <LumoLogo />
      </div>

      <div
        className="w-11 h-11 rounded-2xl flex items-center justify-center mb-4"
        style={{ background: 'color-mix(in srgb, var(--lumo-accent) 15%, transparent)' }}
      >
        <ShieldCheck size={22} style={{ color: 'var(--lumo-accent)' }} />
      </div>

      <h1 className="text-xl font-bold text-center mb-2">Подтверди аккаунт через Google</h1>
      <p className="text-[13px] text-center mb-7 max-w-xs" style={{ color: 'var(--lumo-text-muted)' }}>
        Один шаг регистрации — и откроется доступ к каталогу, AI-поиску и остальным разделам Lumo.
      </p>

      {!inTelegram && (
        <p
          className="mb-4 text-[12px] text-center max-w-xs px-3 py-2 rounded-xl"
          style={{ background: 'rgba(239,68,68,0.1)', color: '#ef4444' }}
        >
          Открой Mini App из Telegram — вне Telegram привязка аккаунта недоступна.
        </p>
      )}

      {error && (
        <p
          className="mb-4 text-[12px] text-center max-w-xs px-3 py-2 rounded-xl"
          style={{ background: 'rgba(239,68,68,0.1)', color: '#ef4444' }}
        >
          {error}
        </p>
      )}

      {loading ? (
        <p className="text-[13px]" style={{ color: 'var(--lumo-text-muted)' }}>
          Подтверждаем…
        </p>
      ) : (
        <GoogleLoginButton onCredential={handleCredential} width={260} />
      )}
    </div>
  );
}
