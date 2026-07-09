import { useState } from 'react';
import { webLogin, webRegister } from '../api.js';

export default function EmailAuthForm({ mode = 'register', onSuccess, onError, onSuggestLogin }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (loading) return;

    const trimmedEmail = email.trim().toLowerCase();
    if (!trimmedEmail.includes('@')) {
      onError?.('Введи корректный email');
      return;
    }
    if (mode === 'register' && password.length < 8) {
      onError?.('Пароль — минимум 8 символов');
      return;
    }

    setLoading(true);
    onError?.('');
    try {
      if (mode === 'register') {
        await webRegister({ email: trimmedEmail, password, name: name.trim() || undefined });
      } else {
        await webLogin({ email: trimmedEmail, password });
      }
      onSuccess?.();
    } catch (err) {
      const msg = err.message || 'Не удалось войти';
      onError?.(msg);
      if (mode === 'register' && (msg.includes('уже есть') || msg.includes('409'))) {
        onSuggestLogin?.();
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={submit} className="space-y-3">
      {mode === 'register' && (
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Имя"
          autoComplete="name"
          className="w-full px-4 py-3 rounded-xl border border-border bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-foreground/30"
        />
      )}
      <input
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="Email"
        required
        autoComplete="email"
        className="w-full px-4 py-3 rounded-xl border border-border bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-foreground/30"
      />
      <input
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder={mode === 'register' ? 'Пароль (мин. 8 символов)' : 'Пароль'}
        required
        minLength={mode === 'register' ? 8 : 1}
        autoComplete={mode === 'register' ? 'new-password' : 'current-password'}
        className="w-full px-4 py-3 rounded-xl border border-border bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-foreground/30"
      />
      <button
        type="submit"
        disabled={loading}
        className="w-full py-3 rounded-xl bg-foreground text-background font-semibold hover:opacity-90 transition-opacity disabled:opacity-50"
      >
        {loading ? 'Создаём аккаунт…' : mode === 'register' ? 'Создать аккаунт Lumo' : 'Войти'}
      </button>
    </form>
  );
}
