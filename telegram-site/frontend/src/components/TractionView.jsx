import { useCallback, useEffect, useState } from 'react';
import {
  ArrowUpRight,
  Eye,
  ExternalLink,
  MousePointerClick,
  PlusCircle,
  RefreshCw,
  Send,
  UserPlus,
} from 'lucide-react';
import { apiFetch, haptic } from '../api';
import { typeLabel, typeStyle } from '../utils/categories';

function MetricTile({ icon: Icon, value, label, sub, accent = 'var(--lumo-admin-accent)' }) {
  return (
    <div className="lumo-card p-4">
      <div
        className="w-9 h-9 rounded-xl flex items-center justify-center mb-3"
        style={{ background: 'var(--lumo-admin-soft)' }}
      >
        <Icon size={16} style={{ color: accent }} />
      </div>
      <div className="text-[26px] font-bold leading-none mb-1">{value}</div>
      <div className="text-[12px]" style={{ color: 'var(--lumo-text-muted)' }}>
        {label}
      </div>
      {sub && (
        <div className="text-[11px] mt-1 font-semibold" style={{ color: accent }}>
          {sub}
        </div>
      )}
    </div>
  );
}

function SourceBar({ label, bot, app, color }) {
  const total = bot + app;
  if (!total) return null;
  const botPct = Math.round((bot / total) * 100);
  return (
    <div className="mb-3">
      <div className="flex justify-between text-[12px] mb-1.5">
        <span style={{ color: 'var(--lumo-text-muted)' }}>{label}</span>
        <span className="font-semibold">
          {total}{' '}
          <span className="font-normal opacity-60">· бот {botPct}%</span>
        </span>
      </div>
      <div className="lumo-progress-track h-2 flex overflow-hidden">
        <div className="h-full" style={{ width: `${botPct}%`, background: color }} />
        <div
          className="h-full flex-1"
          style={{ background: 'color-mix(in srgb, var(--lumo-accent) 70%, transparent)' }}
        />
      </div>
    </div>
  );
}

function submissionStatus(status) {
  if (status === 'approved') return { text: 'Опубликовано', color: '#22c55e' };
  if (status === 'rejected') return { text: 'Отклонено', color: '#ef4444' };
  return { text: 'На проверке', color: '#fbbf24' };
}

function formatWhen(iso) {
  if (!iso) return '';
  const dt = new Date(iso);
  const now = new Date();
  const diffDays = Math.floor((now - dt) / (1000 * 60 * 60 * 24));
  if (diffDays <= 0) return 'сегодня';
  if (diffDays === 1) return 'вчера';
  return `${diffDays} дн назад`;
}
function actionLabel(action) {
  if (action === 'apply') return { text: 'Заявка', color: '#22c55e' };
  if (action === 'telegram') return { text: 'Telegram', color: '#3b82f6' };
  return { text: 'Просмотр', color: 'var(--lumo-admin-accent)' };
}

export default function TractionView() {
  const [days, setDays] = useState(30);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await apiFetch(`/admin/traction?days=${days}`));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading && !data) {
    return (
      <p className="text-center py-16 text-[13px]" style={{ color: 'var(--lumo-text-muted)' }}>
        Загрузка трекшна…
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

  const s = data?.summary || {};
  const src = data?.sources || { bot: {}, miniApp: {} };
  const subStats = data?.userSubmissions || { total: 0, pending: 0, approved: 0, rejected: 0 };

  return (
    <div className="space-y-5 pb-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-[18px] font-bold">Трекшн каталога</h2>
          <p className="text-[12px]" style={{ color: 'var(--lumo-text-muted)' }}>
            Клики из бота и Mini App
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            haptic('light');
            load();
          }}
          className="w-9 h-9 rounded-xl flex items-center justify-center"
          style={{ color: 'var(--lumo-text-muted)' }}
        >
          <RefreshCw size={16} />
        </button>
      </div>

      <div className="flex gap-2">
        {[7, 30, 0].map((d) => (
          <button
            key={d}
            type="button"
            onClick={() => setDays(d)}
            className={`px-3 py-1.5 rounded-full text-[12px] font-semibold transition ${
              days === d ? 'text-white' : ''
            }`}
            style={
              days === d
                ? { background: 'var(--lumo-admin-accent)' }
                : { background: 'var(--lumo-surface-muted)', color: 'var(--lumo-text-muted)' }
            }
          >
            {d === 0 ? 'Всё' : `${d}д`}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-3">
        <MetricTile icon={Eye} value={s.views ?? 0} label="Просмотры" sub={`CTR заявок ${s.ctrApply ?? 0}%`} />
        <MetricTile
          icon={Send}
          value={s.applyClicks ?? 0}
          label="Подать заявку"
          sub={`${s.ctrApply ?? 0}% от просмотров`}
          accent="#22c55e"
        />
        <MetricTile
          icon={ExternalLink}
          value={s.telegramClicks ?? 0}
          label="Переход в Telegram"
          sub={`${s.ctrTelegram ?? 0}% от просмотров`}
          accent="#3b82f6"
        />
        <MetricTile
          icon={MousePointerClick}
          value={s.uniqueUsers ?? 0}
          label="Уникальных юзеров"
          sub={`${s.totalClicks ?? 0} кликов всего`}
        />
      </div>

      <section className="lumo-card p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-[14px] font-bold">Посты от пользователей</h3>
          <PlusCircle size={16} style={{ color: 'var(--lumo-admin-accent)' }} />
        </div>
        <div className="grid grid-cols-2 gap-2 mb-4">
          <div className="rounded-xl p-3" style={{ background: 'var(--lumo-surface-muted)' }}>
            <div className="text-[22px] font-bold">{subStats.total ?? 0}</div>
            <div className="text-[11px]" style={{ color: 'var(--lumo-text-muted)' }}>
              заявок всего
            </div>
          </div>
          <div className="rounded-xl p-3" style={{ background: 'rgba(34,197,94,0.1)' }}>
            <div className="text-[22px] font-bold" style={{ color: '#22c55e' }}>
              {subStats.approved ?? 0}
            </div>
            <div className="text-[11px]" style={{ color: 'var(--lumo-text-muted)' }}>
              опубликовано
            </div>
          </div>
          <div className="rounded-xl p-3" style={{ background: 'rgba(251,191,36,0.1)' }}>
            <div className="text-[22px] font-bold" style={{ color: '#fbbf24' }}>
              {subStats.pending ?? 0}
            </div>
            <div className="text-[11px]" style={{ color: 'var(--lumo-text-muted)' }}>
              на модерации
            </div>
          </div>
          <div className="rounded-xl p-3" style={{ background: 'rgba(239,68,68,0.08)' }}>
            <div className="text-[22px] font-bold" style={{ color: '#ef4444' }}>
              {subStats.rejected ?? 0}
            </div>
            <div className="text-[11px]" style={{ color: 'var(--lumo-text-muted)' }}>
              отклонено
            </div>
          </div>
        </div>

        {(data?.topContributors || []).length > 0 && (
          <>
            <p className="text-[12px] font-semibold mb-2 flex items-center gap-1.5">
              <UserPlus size={14} />
              Кто добавлял
            </p>
            <ul className="space-y-2 mb-4">
              {data.topContributors.map((row) => (
                <li key={row.user} className="flex items-center justify-between text-[12px]">
                  <span className="font-semibold truncate">{row.user}</span>
                  <span style={{ color: 'var(--lumo-text-muted)' }}>
                    {row.submissions} заявок · {row.approved} в каталоге
                  </span>
                </li>
              ))}
            </ul>
          </>
        )}

        {(data?.recentSubmissions || []).length === 0 ? (
          <p className="text-[13px]" style={{ color: 'var(--lumo-text-muted)' }}>
            Пока никто не добавлял через «Добавить» в каталоге
          </p>
        ) : (
          <ul className="space-y-3">
            {(data.recentSubmissions || []).map((row) => {
              const st = submissionStatus(row.status);
              return (
                <li key={row.id} className="border-b pb-3 last:border-0 last:pb-0" style={{ borderColor: 'var(--lumo-border)' }}>
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <p className="text-[13px] font-semibold leading-snug line-clamp-2 flex-1">{row.title}</p>
                    <span
                      className="text-[10px] font-bold px-2 py-0.5 rounded-full shrink-0"
                      style={{ background: `${st.color}22`, color: st.color }}
                    >
                      {st.text}
                    </span>
                  </div>
                  <p className="text-[11px] mb-1" style={{ color: 'var(--lumo-text-muted)' }}>
                    {row.user} · {row.sourceMode === 'channel' ? 'из канала' : 'вручную'}
                    {row.type ? ` · ${row.type}` : ''} · {formatWhen(row.createdAt)}
                  </p>
                  {row.link && (
                    <p className="text-[11px] truncate" style={{ color: 'var(--lumo-link)' }}>
                      {row.link}
                    </p>
                  )}
                  {row.catalogId && (
                    <p className="text-[11px] mt-0.5 font-medium" style={{ color: '#22c55e' }}>
                      В каталоге #{row.catalogId}
                    </p>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <section className="lumo-card p-4">
        <h3 className="text-[14px] font-bold mb-4">Откуда клики</h3>
        <SourceBar
          label="Подать заявку"
          bot={src.bot?.apply ?? 0}
          app={src.miniApp?.apply ?? 0}
          color="#22c55e"
        />
        <SourceBar
          label="Telegram / пост"
          bot={src.bot?.telegram ?? 0}
          app={src.miniApp?.telegram ?? 0}
          color="#3b82f6"
        />
        <p className="text-[11px] mt-2" style={{ color: 'var(--lumo-text-muted)' }}>
          Слева — бот · справа — Mini App
        </p>
      </section>

      <section className="lumo-card p-4">
        <h3 className="text-[14px] font-bold mb-3">Топ возможностей</h3>
        {(data?.topItems || []).length === 0 ? (
          <p className="text-[13px]" style={{ color: 'var(--lumo-text-muted)' }}>
            Пока нет кликов — открой карточки в каталоге или нажми кнопки в боте
          </p>
        ) : (
          <ul className="space-y-4">
            {(data.topItems || []).map((item, idx) => {
              const tag = typeStyle(item.type);
              const max = Math.max(...data.topItems.map((x) => x.totalClicks), 1);
              return (
                <li key={item.catalogId}>
                  <div className="flex items-start gap-2 mb-1.5">
                    <span
                      className="text-[11px] font-bold w-5 shrink-0 pt-0.5"
                      style={{ color: 'var(--lumo-text-muted)' }}
                    >
                      {idx + 1}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-[13px] font-semibold leading-snug line-clamp-2">{item.title}</p>
                      <div className="flex flex-wrap gap-2 mt-1 text-[11px]" style={{ color: 'var(--lumo-text-muted)' }}>
                        <span
                          className="px-2 py-0.5 rounded-full font-semibold"
                          style={{ background: tag.bg, color: tag.text }}
                        >
                          {typeLabel(item.type)}
                        </span>
                        <span>{item.uniqueUsers} чел.</span>
                        <span>{item.views} просм.</span>
                        <span style={{ color: '#22c55e' }}>{item.applyClicks} заявок</span>
                        <span style={{ color: '#3b82f6' }}>{item.telegramClicks} TG</span>
                      </div>
                    </div>
                  </div>
                  <div className="lumo-progress-track h-1.5 ml-7">
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${Math.round((item.totalClicks / max) * 100)}%`,
                        background: 'linear-gradient(90deg, var(--lumo-admin-accent), #6366f1)',
                      }}
                    />
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <section className="lumo-card p-4">
        <h3 className="text-[14px] font-bold mb-3">Последние действия</h3>
        <ul className="space-y-2.5">
          {(data?.recent || []).map((row, idx) => {
            const act = actionLabel(row.action);
            return (
              <li key={`${row.at}-${idx}`} className="flex items-start gap-2 text-[12px]">
                <span
                  className="shrink-0 text-[10px] font-bold px-2 py-0.5 rounded-full mt-0.5"
                  style={{ background: `${act.color}22`, color: act.color }}
                >
                  {act.text}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="font-medium truncate">{row.title}</p>
                  <p style={{ color: 'var(--lumo-text-muted)' }}>
                    {row.user} · {row.source === 'bot' ? 'бот' : 'Mini App'}
                  </p>
                </div>
                <ArrowUpRight size={14} className="shrink-0 opacity-40 mt-1" />
              </li>
            );
          })}
        </ul>
      </section>
    </div>
  );
}
