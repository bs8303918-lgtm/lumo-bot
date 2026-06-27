import { useCallback, useEffect, useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  ClipboardList,
  LogOut,
  RefreshCw,
  Satellite,
  TrendingDown,
  TrendingUp,
  Users,
  XCircle,
} from 'lucide-react';
import { apiFetch, getTelegram, haptic } from '../api';
import TractionView from './TractionView';
import InterestPromptsView from './InterestPromptsView';

function AdminSubNav({ section, onChange }) {
  const tabs = [
    { id: 'traction', label: '📊 Трекшн' },
    { id: 'prompts', label: '💬 Промпты' },
    { id: 'stats', label: '👥 Статистика' },
  ];
  return (
    <div
      className="flex gap-2 mb-5 overflow-x-auto scrollbar-none -mx-1 px-1 pb-1"
      style={{ borderBottom: '1px solid var(--lumo-border)' }}
    >
      {tabs.map(({ id, label }) => {
        const active = section === id;
        return (
          <button
            key={id}
            type="button"
            onClick={() => {
              haptic('light');
              onChange(id);
            }}
            className="shrink-0 px-4 py-2.5 rounded-xl text-[13px] font-bold transition"
            style={
              active
                ? { background: 'var(--lumo-admin-soft)', color: 'var(--lumo-admin-accent)' }
                : { color: 'var(--lumo-text-muted)' }
            }
          >
            {label}
          </button>
        );
      })}
    </div>
  );
}

function Sparkline({ data }) {
  const values = data?.length ? data : [0];
  const max = Math.max(...values, 1);
  const width = 280;
  const height = 48;
  const step = width / Math.max(values.length - 1, 1);
  const points = values
    .map((v, i) => `${i * step},${height - (v / max) * (height - 6) - 3}`)
    .join(' ');
  const area = `M0,${height} L${points.split(' ').join(' L')} L${width},${height} Z`;

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-12" preserveAspectRatio="none">
      <defs>
        <linearGradient id="ai-chart-fill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--lumo-admin-accent)" stopOpacity="0.35" />
          <stop offset="100%" stopColor="var(--lumo-admin-accent)" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill="url(#ai-chart-fill)" />
      <polyline
        fill="none"
        stroke="var(--lumo-admin-accent)"
        strokeWidth="2"
        strokeLinejoin="round"
        strokeLinecap="round"
        points={points}
      />
    </svg>
  );
}

function MetricCard({ icon: Icon, value, label, delta, deltaLabel, tone = 'default' }) {
  const positive = delta >= 0;
  const toneColors = {
    default: 'var(--lumo-text)',
    green: '#22c55e',
    orange: '#f97316',
  };

  return (
    <div className="lumo-card p-4">
      <div className="flex items-start justify-between mb-3">
        <div
          className="w-9 h-9 rounded-xl flex items-center justify-center"
          style={{ background: 'var(--lumo-admin-soft)' }}
        >
          <Icon size={16} style={{ color: 'var(--lumo-admin-accent)' }} />
        </div>
        {delta !== null && delta !== undefined && (
          <div
            className="flex items-center gap-0.5 text-[11px] font-semibold"
            style={{ color: positive ? '#22c55e' : '#ef4444' }}
          >
            {positive ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
            {positive ? '+' : ''}
            {delta} {deltaLabel}
          </div>
        )}
      </div>
      <div className="text-[28px] font-bold leading-none mb-1" style={{ color: toneColors[tone] || toneColors.default }}>
        {value}
      </div>
      <div className="text-[12px]" style={{ color: 'var(--lumo-text-muted)' }}>
        {label}
      </div>
    </div>
  );
}

function StatusDot({ status }) {
  const colors = { today: '#22c55e', recent: '#f97316', inactive: '#64748b' };
  return (
    <span
      className="w-2 h-2 rounded-full shrink-0"
      style={{ background: colors[status] || colors.inactive }}
    />
  );
}

function formatLastActive(iso) {
  if (!iso) return 'давно';
  const dt = new Date(iso);
  const now = new Date();
  const diffDays = Math.floor((now - dt) / (1000 * 60 * 60 * 24));
  if (diffDays <= 0) return 'Сегодня';
  if (diffDays === 1) return 'Вчера';
  return `${diffDays} дн назад`;
}

function ScanIcon({ status }) {
  if (status === 'ok') return <CheckCircle2 size={14} className="text-green-500 shrink-0" />;
  if (status === 'warn') return <AlertTriangle size={14} className="text-orange-400 shrink-0" />;
  return <XCircle size={14} className="text-red-400 shrink-0" />;
}

function userRef(user) {
  if (user.username) return `@${user.username}`;
  if (user.telegramId != null) return `id${user.telegramId}`;
  return '?';
}

function initial(name) {
  const ch = String(name ?? '?').replace('@', '').trim();
  return ch[0]?.toUpperCase() || '?';
}

function SubmissionRow({ item, onDone }) {
  const [busy, setBusy] = useState(false);

  const act = async (action) => {
    if (busy) return;
    haptic('medium');
    setBusy(true);
    try {
      await apiFetch(`/admin/submissions/${item.id}/${action}`, { method: 'POST', body: '{}' });
      onDone();
    } catch (err) {
      alert(err.message || 'Ошибка');
    } finally {
      setBusy(false);
    }
  };

  const who = item.username ? `@${item.username}` : item.telegramId ? `id${item.telegramId}` : '?';
  const title = item.title || item.link || 'Без названия';

  return (
    <li className="border-b pb-4 last:border-0 last:pb-0" style={{ borderColor: 'var(--lumo-border)' }}>
      <div className="flex items-center justify-between gap-2 mb-1">
        <span className="text-[13px] font-semibold truncate">{title}</span>
        <span
          className="text-[10px] font-bold px-2 py-0.5 rounded-full shrink-0"
          style={{ background: 'rgba(251, 191, 36, 0.15)', color: '#fbbf24' }}
        >
          {item.sourceMode === 'channel' ? 'Канал' : 'Вручную'}
        </span>
      </div>
      <p className="text-[12px] mb-1" style={{ color: 'var(--lumo-text-muted)' }}>
        {who}
        {item.type ? ` · ${item.type}` : ''}
        {item.location ? ` · ${item.location}` : ''}
      </p>
      {item.description && (
        <p className="text-[13px] mb-2 line-clamp-2" style={{ color: 'var(--lumo-text-muted)' }}>
          {item.description}
        </p>
      )}
      {item.link && (
        <p className="text-[12px] mb-2 truncate" style={{ color: 'var(--lumo-link)' }}>
          {item.link}
        </p>
      )}
      <div className="flex gap-2">
        <button
          type="button"
          disabled={busy}
          onClick={() => act('approve')}
          className="flex-1 py-2 rounded-xl text-[12px] font-bold text-white disabled:opacity-40"
          style={{ background: '#22c55e' }}
        >
          Одобрить
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => act('reject')}
          className="flex-1 py-2 rounded-xl text-[12px] font-bold disabled:opacity-40"
          style={{ background: 'rgba(239,68,68,0.12)', color: '#ef4444' }}
        >
          Отклонить
        </button>
      </div>
    </li>
  );
}

export default function AdminView({ onExit }) {
  const [section, setSection] = useState('traction');
  return (
    <div>
      <AdminSubNav section={section} onChange={setSection} />
      {section === 'traction' && <TractionView />}
      {section === 'prompts' && <InterestPromptsView />}
      {section === 'stats' && <AdminStatsView onExit={onExit} />}
    </div>
  );
}

function AdminStatsView({ onExit }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await apiFetch('/admin/tracking'));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const closeApp = () => {
    haptic('light');
    if (onExit) onExit();
    else getTelegram()?.close?.();
  };

  if (loading && !data) {
    return (
      <p className="text-center py-16 text-[13px]" style={{ color: 'var(--lumo-text-muted)' }}>
        Загрузка трекинга…
      </p>
    );
  }

  if (error) {
    return (
      <div className="text-center py-16">
        <p className="text-red-400 text-[13px] mb-3">{error}</p>
        <button type="button" onClick={load} className="text-[13px] font-semibold" style={{ color: 'var(--lumo-admin-accent)' }}>
          Повторить
        </button>
      </div>
    );
  }

  if (!data?.metrics) {
    return (
      <div className="text-center py-16">
        <p className="text-[13px] mb-3" style={{ color: 'var(--lumo-text-muted)' }}>
          Нет данных трекинга
        </p>
        <button type="button" onClick={load} className="text-[13px] font-semibold" style={{ color: 'var(--lumo-admin-accent)' }}>
          Обновить
        </button>
      </div>
    );
  }

  const m = data.metrics;

  return (
    <div className="pb-8 space-y-5">
      <header className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-[22px] font-bold mb-1">Статистика</h1>
          <p className="text-[12px]" style={{ color: 'var(--lumo-text-muted)' }}>
            Обновлено {data.updatedAgo || 'недавно'}
          </p>
        </div>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => {
              haptic('light');
              load();
            }}
            className="w-9 h-9 rounded-xl flex items-center justify-center"
            style={{ color: 'var(--lumo-text-muted)' }}
            aria-label="Обновить"
          >
            <RefreshCw size={16} />
          </button>
          <button
            type="button"
            onClick={closeApp}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-[12px] font-semibold"
            style={{ background: 'rgba(239,68,68,0.12)', color: '#ef4444' }}
          >
            <LogOut size={14} />
            Выйти
          </button>
        </div>
      </header>

      <div className="grid grid-cols-2 gap-3">
        <MetricCard
          icon={Users}
          value={m.users.total}
          label="Пользователей"
          delta={m.users.deltaWeek}
          deltaLabel="за неделю"
        />
        <MetricCard
          icon={CheckCircle2}
          value={m.active.total}
          label="Активных"
          delta={m.active.deltaWeek}
          deltaLabel="за неделю"
          tone="green"
        />
        <MetricCard
          icon={Satellite}
          value={m.channels.total}
          label="Каналов в индексе"
          delta={m.channels.deltaWeek}
          deltaLabel="новых"
        />
        <MetricCard
          icon={ClipboardList}
          value={m.postsToday.total}
          label="Постов за сутки"
          delta={m.postsToday.deltaYesterday}
          deltaLabel="вчера"
          tone="orange"
        />
      </div>

      <section className="lumo-card p-4">
        <div className="flex items-start justify-between gap-3 mb-2">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-widest mb-1" style={{ color: 'var(--lumo-text-muted)' }}>
              AI-запросов сегодня
            </p>
            <div className="text-[32px] font-bold leading-none">{data.aiToday.total}</div>
          </div>
          <div className="text-right text-[12px]" style={{ color: 'var(--lumo-text-muted)' }}>
            avg <span className="font-bold" style={{ color: 'var(--lumo-text)' }}>{data.aiToday.avgPerUser}</span>
            <br />
            / пользователь
          </div>
        </div>
        <Sparkline data={data.aiToday.chart} />
      </section>

      <section className="lumo-card p-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-[15px] font-bold">Последние пользователи</h2>
          <span
            className="text-[11px] font-bold px-2.5 py-1 rounded-full"
            style={{ background: 'var(--lumo-admin-soft)', color: 'var(--lumo-admin-accent)' }}
          >
            {m.users.total} всего
          </span>
        </div>
        <ul className="space-y-3">
          {(data.recentUsers || []).map((user, idx) => (
            <li key={user.telegramId ?? `user-${idx}`} className="flex items-center gap-3">
              <div
                className="w-9 h-9 rounded-full flex items-center justify-center text-white text-sm font-bold shrink-0"
                style={{ background: 'linear-gradient(135deg, var(--lumo-admin-accent), #6366f1)' }}
              >
                {initial(user.username || user.telegramId)}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-[14px] font-semibold truncate">{userRef(user)}</p>
                <p className="text-[12px]" style={{ color: 'var(--lumo-text-muted)' }}>
                  {user.channelCount} канала · {user.requestCount} запросов · {formatLastActive(user.lastActiveAt)}
                </p>
              </div>
              <StatusDot status={user.status} />
            </li>
          ))}
        </ul>
      </section>

      <section className="lumo-card p-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-[15px] font-bold">Топ каналов по добавлениям</h2>
          <span
            className="text-[11px] font-bold px-2.5 py-1 rounded-full"
            style={{ background: 'var(--lumo-admin-soft)', color: 'var(--lumo-admin-accent)' }}
          >
            {m.channels.total} активных
          </span>
        </div>
        <ul className="space-y-3">
          {(data.topChannels || []).map((ch) => (
            <li key={ch.identifier}>
              <div className="flex items-center justify-between gap-2 mb-1.5">
                <span className="text-[14px] font-semibold truncate">@{ch.identifier}</span>
                <span className="text-[12px] shrink-0" style={{ color: 'var(--lumo-text-muted)' }}>
                  {ch.userCount} польз.
                </span>
              </div>
              <div className="lumo-progress-track h-1.5">
                <div
                  className="h-full rounded-full"
                  style={{ width: `${ch.percent}%`, background: 'var(--lumo-admin-accent)' }}
                />
              </div>
            </li>
          ))}
        </ul>
      </section>

      <section className="lumo-card p-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-[15px] font-bold">Лог сканирований</h2>
          <span
            className="text-[11px] font-bold px-2.5 py-1 rounded-full"
            style={{ background: 'var(--lumo-admin-soft)', color: 'var(--lumo-admin-accent)' }}
          >
            {data.monitorSchedule}
          </span>
        </div>
        <ul className="space-y-2.5">
          {(data.scanLog.length ? data.scanLog : [{ time: '—', status: 'warn', message: 'Лог появится после первого скана' }]).map(
            (row, idx) => (
              <li key={`${row.time}-${idx}`} className="flex items-start gap-2 text-[13px]">
                <span className="shrink-0 font-mono text-[12px] w-10" style={{ color: 'var(--lumo-text-muted)' }}>
                  {row.time}
                </span>
                <ScanIcon status={row.status} />
                <span className="leading-snug">{row.message}</span>
              </li>
            ),
          )}
        </ul>
      </section>

      <section className="lumo-card p-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-[15px] font-bold">Заявки на модерацию</h2>
          {data.pendingSubmissions > 0 && (
            <span
              className="text-[11px] font-bold px-2.5 py-1 rounded-full"
              style={{ background: 'rgba(251, 191, 36, 0.15)', color: '#fbbf24' }}
            >
              {data.pendingSubmissions} новых
            </span>
          )}
        </div>
        {(data.submissions || []).length === 0 ? (
          <p className="text-[13px]" style={{ color: 'var(--lumo-text-muted)' }}>
            Пока нет — пользователи могут добавить через Каталог → Добавить
          </p>
        ) : (
          <ul className="space-y-4">
            {(data.submissions || []).map((item) => (
              <SubmissionRow key={item.id} item={item} onDone={load} />
            ))}
          </ul>
        )}
      </section>

      <section className="lumo-card p-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-[15px] font-bold">Баги и идеи</h2>
          {data.unreadFeedback > 0 && (
            <span
              className="text-[11px] font-bold px-2.5 py-1 rounded-full"
              style={{ background: 'var(--lumo-admin-soft)', color: 'var(--lumo-admin-accent)' }}
            >
              {data.unreadFeedback} новых
            </span>
          )}
        </div>
        {data.feedback.length === 0 ? (
          <p className="text-[13px]" style={{ color: 'var(--lumo-text-muted)' }}>
            Пока нет — пользователи могут отправить через Профиль → /bug
          </p>
        ) : (
          <ul className="space-y-3">
            {data.feedback.map((item) => (
              <li key={item.id} className="border-b pb-3 last:border-0 last:pb-0" style={{ borderColor: 'var(--lumo-border)' }}>
                <div className="flex items-center justify-between gap-2 mb-1">
                  <span className="text-[13px] font-semibold">
                    {item.username ? `@${item.username}` : 'Аноним'}
                  </span>
                  <span className="text-[11px]" style={{ color: 'var(--lumo-text-muted)' }}>
                    {formatLastActive(item.createdAt)}
                  </span>
                </div>
                <div className="flex items-start gap-2">
                  <span
                    className="text-[10px] font-bold px-2 py-0.5 rounded-full shrink-0"
                    style={{
                      background: item.kind === 'bug' ? 'rgba(239,68,68,0.15)' : 'rgba(59,130,246,0.15)',
                      color: item.kind === 'bug' ? '#ef4444' : '#3b82f6',
                    }}
                  >
                    {item.kind === 'bug' ? 'Баг' : 'Идея'}
                  </span>
                  <p className="text-[13px] leading-relaxed" style={{ color: 'var(--lumo-text-muted)' }}>
                    {item.message}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
