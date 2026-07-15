import { useCallback, useEffect, useState } from 'react';
import {
  Check,
  ClipboardCopy,
  ExternalLink,
  Loader2,
  Mail,
  Shield,
  UserX,
} from 'lucide-react';
import { apiFetch } from '../api.js';

const STATUS_BADGE = {
  todo: 'bg-amber-50 text-amber-800 border-amber-200',
  in_progress: 'bg-sky-50 text-sky-800 border-sky-200',
  submitted: 'bg-emerald-50 text-emerald-800 border-emerald-200',
};

function buildInviteUrl(invitePath) {
  const origin = typeof window !== 'undefined' ? window.location.origin : '';
  return `${origin}${invitePath}`;
}

export default function SharedRoomStudentPanel({ authed, profile, onNeedsAuth, onOpenItem }) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [room, setRoom] = useState(null);
  const [proposals, setProposals] = useState([]);
  const [proposalStats, setProposalStats] = useState({ todo: 0, in_progress: 0, submitted: 0 });
  const [mentorEmail, setMentorEmail] = useState('');
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);
  const [copied, setCopied] = useState(false);
  const [updatingId, setUpdatingId] = useState(null);

  const loadData = useCallback(async () => {
    if (!authed) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const [roomData, proposalsData] = await Promise.all([
        apiFetch('/rooms/my'),
        apiFetch('/rooms/my/proposals').catch(() => ({ items: [], stats: {} })),
      ]);
      setRoom(roomData);
      setMentorEmail(roomData.pendingMentorEmail || roomData.mentorEmail || '');
      setProposals(proposalsData.items ?? []);
      setProposalStats(proposalsData.stats ?? { todo: 0, in_progress: 0, submitted: 0 });
    } catch (err) {
      if (err.needsAuth) onNeedsAuth();
      else setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [authed, onNeedsAuth]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const invite = async () => {
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const data = await apiFetch('/rooms/invite', {
        method: 'POST',
        body: JSON.stringify({ mentorEmail: mentorEmail.trim() || null }),
      });
      setRoom(data);
      setMessage(data.message || 'Ссылка готова');
    } catch (err) {
      if (err.needsAuth) onNeedsAuth();
      else setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const revoke = async () => {
    if (!window.confirm('Отозвать доступ ментора? Ему нужно будет перейти по новой ссылке.')) return;
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const data = await apiFetch('/rooms/mentor', { method: 'DELETE' });
      await loadData();
      setMessage(data.message || 'Доступ отозван');
    } catch (err) {
      if (err.needsAuth) onNeedsAuth();
      else setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const copyLink = async () => {
    if (!room?.invitePath) return;
    const url = buildInviteUrl(room.invitePath);
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setError('Не удалось скопировать — выдели ссылку вручную');
    }
  };

  const updateStatus = async (appId, status) => {
    setUpdatingId(appId);
    setError(null);
    try {
      const data = await apiFetch(`/rooms/my/proposals/${appId}`, {
        method: 'PATCH',
        body: JSON.stringify({ status }),
      });
      setProposals((prev) =>
        prev.map((item) => (item.id === appId ? data.application : item)),
      );
      setProposalStats((prev) => {
        const old = proposals.find((p) => p.id === appId);
        const next = { ...prev };
        if (old?.status && next[old.status] > 0) next[old.status] -= 1;
        next[status] = (next[status] || 0) + 1;
        return next;
      });
    } catch (err) {
      if (err.needsAuth) onNeedsAuth();
      else setError(err.message);
    } finally {
      setUpdatingId(null);
    }
  };

  if (!authed) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center px-4 text-center">
        <h1 className="text-xl font-semibold mb-2">Совместный доступ</h1>
        <p className="text-muted-foreground mb-6 max-w-md text-sm">
          Войди, чтобы пригласить ментора в свою комнату Lumo
        </p>
        <button
          type="button"
          onClick={onNeedsAuth}
          className="px-5 py-2.5 rounded-full bg-foreground text-background text-sm font-semibold"
        >
          Войти
        </button>
      </div>
    );
  }

  const subActive = room?.hasActiveSubscription ?? profile?.subscription?.isActive;
  const hasMentor = Boolean(room?.mentorId);

  return (
    <div className="flex-1 overflow-y-auto px-4 md:px-8 py-6 md:py-8">
      <div className="max-w-6xl mx-auto space-y-6">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-neutral-400 mb-1">Shared Space</p>
          <h1 className="text-2xl font-bold text-neutral-900">Мой ментор</h1>
          <p className="text-sm text-neutral-500 mt-1">
            Ментор предлагает программы — ты видишь статус подачи в таблице ниже
          </p>
        </div>

        {!subActive && (
          <p className="text-sm text-amber-800 bg-amber-50 border border-amber-100 rounded-xl px-4 py-3">
            Нужна активная подписка, чтобы открыть совместный доступ ментору.
          </p>
        )}

        {error && (
          <p className="text-sm text-rose-600 bg-rose-50 border border-rose-100 rounded-xl px-4 py-3">{error}</p>
        )}
        {message && (
          <p className="text-sm text-emerald-700 bg-emerald-50 border border-emerald-100 rounded-xl px-4 py-3">
            {message}
          </p>
        )}

        {loading ? (
          <p className="text-center text-neutral-400 py-12 flex items-center justify-center gap-2">
            <Loader2 size={18} className="animate-spin" /> Загрузка…
          </p>
        ) : (
          <>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-1 rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm space-y-4">
                <h2 className="text-sm font-semibold text-neutral-900">Приглашение</h2>
                {hasMentor ? (
                  <div className="flex items-start gap-3 p-3 rounded-xl bg-violet-50 border border-violet-100">
                    <Shield size={20} className="text-violet-600 shrink-0 mt-0.5" />
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-violet-900">Ментор подключён</p>
                      <p className="text-sm text-violet-700 truncate">{room.mentorName || room.mentorEmail}</p>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-neutral-500">Ментор ещё не принял приглашение</p>
                )}

                <label className="block space-y-1.5">
                  <span className="text-sm font-medium text-neutral-700">Email ментора</span>
                  <div className="relative">
                    <Mail size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400" />
                    <input
                      type="email"
                      value={mentorEmail}
                      onChange={(e) => setMentorEmail(e.target.value)}
                      placeholder="mentor@agency.kz"
                      disabled={!subActive || saving}
                      className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-neutral-200 text-sm disabled:bg-neutral-50"
                    />
                  </div>
                </label>

                <button
                  type="button"
                  onClick={invite}
                  disabled={!subActive || saving}
                  className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-neutral-900 text-white text-sm font-semibold disabled:opacity-60"
                >
                  {saving ? <Loader2 size={16} className="animate-spin" /> : null}
                  {hasMentor ? 'Обновить приглашение' : 'Пригласить ментора'}
                </button>

                {room?.invitePath && (
                  <div className="space-y-2 pt-2 border-t border-neutral-100">
                    <p className="text-xs text-neutral-500">Ссылка-приглашение</p>
                    <div className="flex gap-2">
                      <input
                        readOnly
                        value={buildInviteUrl(room.invitePath)}
                        className="flex-1 min-w-0 px-3 py-2 rounded-lg border border-neutral-200 text-xs bg-neutral-50 truncate"
                      />
                      <button
                        type="button"
                        onClick={copyLink}
                        className="shrink-0 inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-neutral-200 text-xs font-medium hover:bg-neutral-50"
                      >
                        <ClipboardCopy size={14} />
                        {copied ? 'OK' : 'Копировать'}
                      </button>
                    </div>
                  </div>
                )}

                {hasMentor && (
                  <button
                    type="button"
                    onClick={revoke}
                    disabled={saving}
                    className="inline-flex items-center gap-2 text-sm text-rose-600 hover:text-rose-700 font-medium"
                  >
                    <UserX size={16} />
                    Отозвать доступ
                  </button>
                )}
              </div>

              <div className="lg:col-span-2 rounded-2xl border border-neutral-200 bg-white shadow-sm overflow-hidden">
                <div className="px-5 py-4 border-b border-neutral-100 flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h2 className="text-sm font-semibold text-neutral-900">Предложения ментора</h2>
                    <p className="text-xs text-neutral-500 mt-0.5">
                      {hasMentor
                        ? 'Отмечай статус — ментор увидит это в своей CRM-доске'
                        : 'Таблица появится после подключения ментора'}
                    </p>
                  </div>
                  {hasMentor && (
                    <div className="flex gap-2 text-xs">
                      <span className="px-2.5 py-1 rounded-full bg-amber-50 text-amber-800 border border-amber-200">
                        Нужно: {proposalStats.todo ?? 0}
                      </span>
                      <span className="px-2.5 py-1 rounded-full bg-sky-50 text-sky-800 border border-sky-200">
                        В процессе: {proposalStats.in_progress ?? 0}
                      </span>
                      <span className="px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200">
                        Подано: {proposalStats.submitted ?? 0}
                      </span>
                    </div>
                  )}
                </div>

                {!hasMentor ? (
                  <p className="text-sm text-neutral-400 text-center py-16 px-4">
                    Пригласи ментора — он добавит конкурсы, а ты увидишь их здесь
                  </p>
                ) : proposals.length === 0 ? (
                  <p className="text-sm text-neutral-400 text-center py-16 px-4">
                    Ментор ещё не предложил программы. Скоро появятся в этой таблице.
                  </p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="bg-neutral-50 text-left text-xs text-neutral-500 uppercase tracking-wide">
                          <th className="px-4 py-3 font-semibold">Программа</th>
                          <th className="px-4 py-3 font-semibold hidden sm:table-cell">Дедлайн</th>
                          <th className="px-4 py-3 font-semibold">Статус</th>
                          <th className="px-4 py-3 font-semibold text-right">Действия</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-neutral-100">
                        {proposals.map((row) => {
                          const opp = row.opportunity || {};
                          const badge = STATUS_BADGE[row.status] || STATUS_BADGE.todo;
                          const applyUrl = opp.applicationUrl || opp.messageLink || opp.channelUrl;
                          return (
                            <tr key={row.id} className="hover:bg-neutral-50/80">
                              <td className="px-4 py-3">
                                <button
                                  type="button"
                                  onClick={() => onOpenItem?.(opp)}
                                  className="text-left font-medium text-neutral-900 hover:text-violet-700 line-clamp-2"
                                >
                                  {opp.emoji ? `${opp.emoji} ` : ''}
                                  {opp.title || 'Без названия'}
                                </button>
                                <p className="text-xs text-neutral-400 mt-0.5">{opp.label || opp.type}</p>
                                {row.notes && (
                                  <p className="text-xs text-neutral-500 mt-1 italic">«{row.notes}»</p>
                                )}
                              </td>
                              <td className="px-4 py-3 hidden sm:table-cell whitespace-nowrap">
                                <span className={opp.deadlineUrgent ? 'text-rose-600 font-medium' : 'text-neutral-600'}>
                                  {opp.deadlineLabel || '—'}
                                </span>
                              </td>
                              <td className="px-4 py-3">
                                <span className={`inline-flex px-2.5 py-1 rounded-full text-xs font-semibold border ${badge}`}>
                                  {row.statusLabel}
                                </span>
                              </td>
                              <td className="px-4 py-3">
                                <div className="flex flex-wrap justify-end gap-1.5">
                                  {row.status !== 'in_progress' && row.status !== 'submitted' && (
                                    <button
                                      type="button"
                                      disabled={updatingId === row.id}
                                      onClick={() => updateStatus(row.id, 'in_progress')}
                                      className="px-2.5 py-1 rounded-lg border border-sky-200 text-sky-700 text-xs font-medium hover:bg-sky-50 disabled:opacity-50"
                                    >
                                      В процессе
                                    </button>
                                  )}
                                  {row.status !== 'submitted' && (
                                    <button
                                      type="button"
                                      disabled={updatingId === row.id}
                                      onClick={() => updateStatus(row.id, 'submitted')}
                                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg border border-emerald-200 text-emerald-700 text-xs font-medium hover:bg-emerald-50 disabled:opacity-50"
                                    >
                                      {updatingId === row.id ? (
                                        <Loader2 size={12} className="animate-spin" />
                                      ) : (
                                        <Check size={12} />
                                      )}
                                      Подал
                                    </button>
                                  )}
                                  {applyUrl && (
                                    <a
                                      href={applyUrl}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg border border-neutral-200 text-neutral-700 text-xs font-medium hover:bg-neutral-50"
                                    >
                                      <ExternalLink size={12} />
                                      Ссылка
                                    </a>
                                  )}
                                </div>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
