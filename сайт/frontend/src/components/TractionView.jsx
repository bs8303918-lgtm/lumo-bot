import { useCallback, useEffect, useState } from 'react';

import {

  ArrowUpRight,

  Eye,

  ExternalLink,

  MousePointerClick,

  PlusCircle,

  RefreshCw,

  Send,

} from 'lucide-react';

import { apiFetch } from '../api.js';



function MetricTile({ icon: Icon, value, label, sub, accentClass = 'text-sky-500' }) {

  return (

    <div className="rounded-2xl border border-border bg-card p-4">

      <div className="w-9 h-9 rounded-xl bg-muted flex items-center justify-center mb-3">

        <Icon size={16} className={accentClass} />

      </div>

      <div className="text-2xl font-bold leading-none mb-1">{value}</div>

      <div className="text-xs text-muted-foreground">{label}</div>

      {sub && <div className={`text-[11px] mt-1 font-semibold ${accentClass}`}>{sub}</div>}

    </div>

  );

}



function SourceBar({ label, bot, app, colorClass }) {

  const total = bot + app;

  if (!total) return null;

  const botPct = Math.round((bot / total) * 100);

  return (

    <div className="mb-3">

      <div className="flex justify-between text-xs mb-1.5">

        <span className="text-muted-foreground">{label}</span>

        <span className="font-semibold">

          {total} <span className="font-normal opacity-60">· бот {botPct}%</span>

        </span>

      </div>

      <div className="h-2 rounded-full bg-muted overflow-hidden flex">

        <div className={`h-full ${colorClass}`} style={{ width: `${botPct}%` }} />

        <div className="h-full flex-1 bg-sky-500/40" />

      </div>

    </div>

  );

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

    return <p className="text-center py-16 text-sm text-muted-foreground">Загрузка трекшна…</p>;

  }



  if (error) {

    return (

      <div className="text-center py-16">

        <p className="text-red-500 text-sm mb-3">{error}</p>

        <button type="button" onClick={load} className="text-sm font-semibold text-primary">

          Повторить

        </button>

      </div>

    );

  }



  const s = data?.summary || {};

  const src = data?.sources || { bot: {}, miniApp: {} };

  const subStats = data?.userSubmissions || { total: 0, pending: 0, approved: 0, rejected: 0 };

  const recent = data?.recentActivity || [];



  return (

    <div className="flex-1 overflow-y-auto px-4 md:px-8 py-8">

      <div className="max-w-4xl mx-auto space-y-6">

        <div className="flex items-center justify-between gap-3">

          <div>

            <h1 className="text-2xl font-bold">Трекшн</h1>

            <p className="text-sm text-muted-foreground">Клики из бота и веб-приложения</p>

          </div>

          <button

            type="button"

            onClick={load}

            className="w-9 h-9 rounded-xl border border-border flex items-center justify-center text-muted-foreground hover:bg-muted"

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

              className={`px-3 py-1.5 rounded-full text-xs font-semibold transition ${

                days === d ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'

              }`}

            >

              {d === 0 ? 'Всё' : `${d}д`}

            </button>

          ))}

        </div>



        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">

          <MetricTile icon={Eye} value={s.views ?? 0} label="Просмотры" sub={`CTR ${s.ctrApply ?? 0}%`} />

          <MetricTile

            icon={Send}

            value={s.applyClicks ?? 0}

            label="Заявки"

            sub={`${s.ctrApply ?? 0}%`}

            accentClass="text-green-500"

          />

          <MetricTile

            icon={ExternalLink}

            value={s.telegramClicks ?? 0}

            label="Telegram"

            sub={`${s.ctrTelegram ?? 0}%`}

            accentClass="text-blue-500"

          />

          <MetricTile

            icon={MousePointerClick}

            value={s.uniqueUsers ?? 0}

            label="Юзеры"

            sub={`${s.totalClicks ?? 0} кликов`}

          />

        </div>



        <section className="rounded-2xl border border-border bg-card p-5">

          <div className="flex items-center justify-between mb-4">

            <h2 className="font-semibold">Посты от пользователей</h2>

            <PlusCircle size={16} className="text-primary" />

          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-center text-sm">

            <div className="rounded-xl bg-muted p-3">

              <div className="text-xl font-bold">{subStats.total}</div>

              <div className="text-muted-foreground text-xs">Всего</div>

            </div>

            <div className="rounded-xl bg-muted p-3">

              <div className="text-xl font-bold text-amber-500">{subStats.pending}</div>

              <div className="text-muted-foreground text-xs">На проверке</div>

            </div>

            <div className="rounded-xl bg-muted p-3">

              <div className="text-xl font-bold text-green-500">{subStats.approved}</div>

              <div className="text-muted-foreground text-xs">Опубликовано</div>

            </div>

            <div className="rounded-xl bg-muted p-3">

              <div className="text-xl font-bold text-red-500">{subStats.rejected}</div>

              <div className="text-muted-foreground text-xs">Отклонено</div>

            </div>

          </div>

        </section>



        <section className="rounded-2xl border border-border bg-card p-5">

          <h2 className="font-semibold mb-4">Источники кликов</h2>

          <SourceBar label="Просмотры" bot={src.bot?.views ?? 0} app={src.miniApp?.views ?? 0} colorClass="bg-zinc-500" />

          <SourceBar

            label="Заявки"

            bot={src.bot?.applyClicks ?? 0}

            app={src.miniApp?.applyClicks ?? 0}

            colorClass="bg-green-500"

          />

          <SourceBar

            label="Telegram"

            bot={src.bot?.telegramClicks ?? 0}

            app={src.miniApp?.telegramClicks ?? 0}

            colorClass="bg-blue-500"

          />

        </section>



        {recent.length > 0 && (

          <section className="rounded-2xl border border-border bg-card p-5">

            <h2 className="font-semibold mb-4">Последняя активность</h2>

            <div className="space-y-2">

              {recent.slice(0, 12).map((row, i) => (

                <div key={i} className="flex items-center justify-between text-sm py-2 border-b border-border last:border-0">

                  <span className="text-muted-foreground truncate flex-1">{row.title || row.action}</span>

                  <span className="text-xs text-muted-foreground shrink-0 ml-2 flex items-center gap-1">

                    {row.action}

                    <ArrowUpRight size={12} />

                  </span>

                </div>

              ))}

            </div>

          </section>

        )}

      </div>

    </div>

  );

}

