import { useState } from 'react';
import { Link } from 'react-router-dom';
import { X } from 'lucide-react';
import { syncSession } from '../api.js';
import EmailAuthForm from './EmailAuthForm.jsx';
import GoogleLoginButton from './GoogleLoginButton.jsx';
import LumoLogo from './LumoLogo.jsx';

export default function AuthModal({ open, onClose, onAuthed, signup = false }) {
  const [emailMode, setEmailMode] = useState(signup ? 'register' : 'login');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  if (!open) return null;

  const finish = async () => {
    setError('');
    setLoading(true);
    try {
      await syncSession();
      onAuthed?.();
    } catch (err) {
      setError(err.message || 'Не удалось войти. Проверь Railway и env на сервере.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div className="bg-card border border-border rounded-3xl p-6 sm:p-8 max-w-md w-full shadow-2xl relative">
        <button
          type="button"
          onClick={onClose}
          className="absolute top-4 right-4 text-muted-foreground hover:text-foreground"
          aria-label="Закрыть"
        >
          <X size={20} />
        </button>

        <div className="flex justify-center mb-5">
          <LumoLogo showText={false} size="lg" theme="auto" />
        </div>

        <h2 className="text-xl font-semibold text-center mb-1">
          {signup ? 'Создай аккаунт' : 'Вход в Lumo'}
        </h2>
        <p className="text-sm text-muted-foreground text-center mb-6">
          Email или Google — один аккаунт для поиска конкурсов
        </p>

        {error && (
          <p className="mb-4 text-sm text-red-500 bg-red-500/10 border border-red-500/20 rounded-xl px-3 py-2">
            {error}
          </p>
        )}

        {loading && (
          <p className="mb-4 text-sm text-muted-foreground text-center">Подключаем аккаунт…</p>
        )}

        <div className="space-y-4">
          <div className="flex gap-2 text-sm justify-center">
            <button
              type="button"
              onClick={() => setEmailMode('register')}
              className={emailMode === 'register' ? 'font-semibold text-foreground' : 'text-muted-foreground'}
            >
              Регистрация
            </button>
            <span className="text-muted-foreground">·</span>
            <button
              type="button"
              onClick={() => setEmailMode('login')}
              className={emailMode === 'login' ? 'font-semibold text-foreground' : 'text-muted-foreground'}
            >
              Вход
            </button>
          </div>

          <EmailAuthForm
            mode={emailMode}
            onSuccess={finish}
            onError={setError}
            onSuggestLogin={() => setEmailMode('login')}
          />

          <div className="relative py-2">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-border" />
            </div>
            <p className="relative text-center text-xs text-muted-foreground bg-card px-3 mx-auto w-fit">
              или
            </p>
          </div>

          <div className="w-full flex justify-center pb-1">
            <GoogleLoginButton onAuth={finish} text="signup_with" width={320} />
          </div>
        </div>

        {signup && (
          <p className="text-xs text-muted-foreground text-center mt-5">
            <Link to="/" className="underline hover:text-foreground">
              На главную
            </Link>
          </p>
        )}
      </div>
    </div>
  );
}
