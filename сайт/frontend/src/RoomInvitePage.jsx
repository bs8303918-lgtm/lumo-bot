import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Loader2, Users } from 'lucide-react';
import { apiFetch, isAuthenticated, setActiveRoom, syncSession } from './api.js';
import AuthModal from './components/AuthModal.jsx';
import LumoLogo from './components/LumoLogo.jsx';

export default function RoomInvitePage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const roomId = Number(searchParams.get('room'));
  const token = searchParams.get('token') || '';

  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [accepting, setAccepting] = useState(false);
  const [error, setError] = useState(null);
  const [authed, setAuthed] = useState(isAuthenticated());
  const [authModal, setAuthModal] = useState(false);

  useEffect(() => {
    if (!roomId || !token) {
      setError('Некорректная ссылка приглашения');
      setLoading(false);
      return;
    }

    apiFetch(`/rooms/preview?room=${roomId}&token=${encodeURIComponent(token)}`, { auth: false })
      .then(setPreview)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [roomId, token]);

  const acceptInvite = async () => {
    if (!authed) {
      setAuthModal(true);
      return;
    }
    setAccepting(true);
    setError(null);
    try {
      const data = await apiFetch('/rooms/accept', {
        method: 'POST',
        body: JSON.stringify({ roomId, token }),
      });
      setActiveRoom(data.studentId, data.studentName);
      navigate(`/app?view=workspace&room=${data.studentId}`, { replace: true });
    } catch (err) {
      if (err.needsAuth) setAuthModal(true);
      else setError(err.message);
    } finally {
      setAccepting(false);
    }
  };

  const handleAuthed = async () => {
    const ok = await syncSession();
    setAuthed(ok);
    if (ok) {
      setAuthModal(false);
      acceptInvite();
    }
  };

  return (
    <div className="min-h-dvh flex flex-col items-center justify-center px-4 py-12 bg-neutral-50">
      <div className="mb-8">
        <LumoLogo size="md" theme="light" />
      </div>

      <div className="w-full max-w-md rounded-2xl border border-neutral-200 bg-white p-6 shadow-sm space-y-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-violet-100 flex items-center justify-center text-violet-700">
            <Users size={20} />
          </div>
          <div>
            <h1 className="text-lg font-bold text-neutral-900">Приглашение ментора</h1>
            <p className="text-sm text-neutral-500">Комната совместной работы Lumo</p>
          </div>
        </div>

        {loading && (
          <p className="text-sm text-neutral-400 flex items-center gap-2 py-6 justify-center">
            <Loader2 size={16} className="animate-spin" /> Проверяем ссылку…
          </p>
        )}

        {error && !loading && (
          <p className="text-sm text-rose-600 bg-rose-50 border border-rose-100 rounded-xl px-4 py-3">{error}</p>
        )}

        {preview && !loading && (
          <div className="space-y-4">
            <p className="text-sm text-neutral-700">
              Студент <strong>{preview.studentName}</strong> приглашает тебя помочь с подбором конкурсов и грантов.
            </p>

            {!preview.subscriptionActive && (
              <p className="text-sm text-amber-800 bg-amber-50 border border-amber-100 rounded-xl px-4 py-3">
                Подписка студента неактивна — войти в комнату пока нельзя.
              </p>
            )}

            {preview.alreadyHasMentor && (
              <p className="text-sm text-amber-800 bg-amber-50 border border-amber-100 rounded-xl px-4 py-3">
                У студента уже подключён другой ментор. Попроси студента отозвать доступ и отправить новую ссылку.
              </p>
            )}

            <button
              type="button"
              onClick={acceptInvite}
              disabled={
                accepting || !preview.subscriptionActive || preview.alreadyHasMentor
              }
              className="w-full inline-flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-violet-600 text-white text-sm font-semibold disabled:opacity-60"
            >
              {accepting ? <Loader2 size={16} className="animate-spin" /> : null}
              {authed ? 'Войти в комнату студента' : 'Войти и принять приглашение'}
            </button>

            {!authed && (
              <p className="text-xs text-center text-neutral-400">
                Нет аккаунта? При регистрации тебе автоматически назначится роль ментора.
              </p>
            )}
          </div>
        )}
      </div>

      <AuthModal
        open={authModal}
        onClose={() => setAuthModal(false)}
        onAuthed={handleAuthed}
        signup={!authed}
      />
    </div>
  );
}
