import { useEffect, useState } from 'react';
import { Plus, Trash2, Users } from 'lucide-react';
import { apiFetch, getTelegram, haptic, openBotCommand } from '../api';
import BugReportModal from './BugReportModal';
import SubscriptionSection from './SubscriptionSection';
import { typeLabel } from '../utils/categories';

const GRADE_OPTIONS = ['9 класс', '10 класс', '11 класс', '1 курс', '2 курс', '3 курс', '4 курс', 'Выпускник'];
const SUBJECT_OPTIONS = ['Математика', 'Физика', 'Информатика', 'Биология', 'Химия', 'Экономика', 'Английский язык', 'История', 'Дизайн', 'Робототехника'];
const ENGLISH_LEVEL_OPTIONS = [
  { id: 'none', label: 'Не оцениваю' },
  { id: 'a2', label: 'A2' },
  { id: 'b1', label: 'B1' },
  { id: 'b2', label: 'B2' },
  { id: 'c1', label: 'C1' },
  { id: 'c2', label: 'C2' },
];
const REGION_OPTIONS = ['Алматы', 'Астана', 'Шымкент', 'Караганда', 'Актобе'];

function StudentProfileSection() {
  const [profile, setProfile] = useState(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    apiFetch('/users/profile')
      .then(setProfile)
      .catch(() => setProfile({ grade: '', region: '', englishLevel: '', subjects: [], visibleInCommunity: false }));
  }, []);

  if (!profile) return null;

  const patch = (fields) => setProfile((p) => ({ ...p, ...fields }));
  const toggleSubject = (s) =>
    patch({ subjects: profile.subjects.includes(s) ? profile.subjects.filter((x) => x !== s) : [...profile.subjects, s] });

  const save = async () => {
    haptic('medium');
    try {
      await apiFetch('/users/profile', {
        method: 'PUT',
        body: JSON.stringify({
          grade: profile.grade,
          region: profile.region,
          englishLevel: profile.englishLevel,
          subjects: profile.subjects,
          visibleInCommunity: profile.visibleInCommunity,
        }),
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 1500);
    } catch {
      /* best effort */
    }
  };

  const ChipGroup = ({ options, value, onToggle, multi = false }) => (
    <div className="flex flex-wrap gap-2">
      {options.map((opt) => {
        const id = typeof opt === 'string' ? opt : opt.id;
        const label = typeof opt === 'string' ? opt : opt.label;
        const active = multi ? value.includes(id) : value === id;
        return (
          <button
            key={id}
            type="button"
            onClick={() => {
              haptic('light');
              onToggle(id);
            }}
            className={`px-3 py-2 rounded-xl text-[12px] font-semibold ${active ? 'lumo-filter-active' : 'lumo-filter-inactive'}`}
          >
            {label}
          </button>
        );
      })}
    </div>
  );

  return (
    <section className="lumo-card p-4">
      <p className="text-[11px] font-bold uppercase tracking-widest mb-3" style={{ color: 'var(--lumo-text-muted)' }}>
        Профиль ученика
      </p>

      <div className="space-y-4">
        <div>
          <p className="text-[12px] font-medium mb-2" style={{ color: 'var(--lumo-text-muted)' }}>
            Класс / курс
          </p>
          <ChipGroup options={GRADE_OPTIONS} value={profile.grade} onToggle={(v) => patch({ grade: v })} />
        </div>

        <div>
          <p className="text-[12px] font-medium mb-2" style={{ color: 'var(--lumo-text-muted)' }}>
            Предметы
          </p>
          <ChipGroup options={SUBJECT_OPTIONS} value={profile.subjects} onToggle={toggleSubject} multi />
        </div>

        <div>
          <p className="text-[12px] font-medium mb-2" style={{ color: 'var(--lumo-text-muted)' }}>
            Английский
          </p>
          <ChipGroup options={ENGLISH_LEVEL_OPTIONS} value={profile.englishLevel} onToggle={(v) => patch({ englishLevel: v })} />
        </div>

        <div>
          <p className="text-[12px] font-medium mb-2" style={{ color: 'var(--lumo-text-muted)' }}>
            Город
          </p>
          <ChipGroup options={REGION_OPTIONS} value={profile.region} onToggle={(v) => patch({ region: v })} />
        </div>

        <div className="flex items-start justify-between gap-3 pt-1">
          <div className="flex-1">
            <p className="text-[13px] font-semibold mb-0.5">«Кто ещё подаётся»</p>
            <p className="text-[11px]" style={{ color: 'var(--lumo-text-muted)' }}>
              Показывать другим счётчик, что ты тоже смотришь конкурс (без имени)
            </p>
          </div>
          <button
            type="button"
            onClick={() => patch({ visibleInCommunity: !profile.visibleInCommunity })}
            className="shrink-0 w-11 h-6 rounded-full relative"
            style={{ background: profile.visibleInCommunity ? 'var(--lumo-accent)' : 'var(--lumo-surface-muted)' }}
          >
            <span
              className="absolute top-0.5 w-5 h-5 rounded-full bg-white transition-transform"
              style={{ transform: profile.visibleInCommunity ? 'translateX(20px)' : 'translateX(2px)' }}
            />
          </button>
        </div>

        <button type="button" onClick={save} className="w-full py-3 rounded-xl font-bold text-[13px] text-white lumo-btn-primary">
          {saved ? 'Сохранено ✓' : 'Сохранить'}
        </button>
      </div>
    </section>
  );
}

const COMMANDS = [
  { cmd: 'set_interest', label: 'Изменить профиль и интересы' },
  { cmd: 'add_channel', label: 'Добавить канал' },
  { cmd: 'my_channels', label: 'Мои каналы' },
  { cmd: 'status', label: 'Статус последнего скана' },
  { cmd: 'bug', label: 'Сообщить о баге или идее' },
];

function channelInitial(title) {
  const ch = (title || '?').trim();
  return ch[0]?.toUpperCase() || '?';
}

export default function ProfileView({ meta, profile, plans = [], onProfileRefresh, onOpenPriceList }) {
  const [channels, setChannels] = useState([]);
  const [bugOpen, setBugOpen] = useState(false);
  const [removingId, setRemovingId] = useState(null);
  const inTelegram = Boolean(getTelegram()?.initData);
  const bot = meta?.botUsername || 'LumoAI1bot';
  const maxChannels = meta?.maxUserChannels ?? 5;
  const remaining = Math.max(0, maxChannels - channels.length);
  const progress = Math.min(100, (channels.length / maxChannels) * 100);

  useEffect(() => {
    apiFetch('/users/channels').then(setChannels).catch(() => setChannels([]));
  }, [profile]);

  const [devId, setDevId] = useState(localStorage.getItem('lumo-dev-telegram-id') || '');

  const removeChannel = async (ch) => {
    if (removingId) return;
    const ok = window.confirm(`Удалить @${ch.identifier} из мониторинга?`);
    if (!ok) return;
    setRemovingId(ch.id);
    haptic('medium');
    try {
      await apiFetch(`/users/channels/${ch.id}`, { method: 'DELETE' });
      setChannels((prev) => prev.filter((item) => item.id !== ch.id));
      onProfileRefresh?.();
    } catch (err) {
      window.alert(err.message || 'Не удалось удалить канал');
    } finally {
      setRemovingId(null);
    }
  };

  const saveDevId = () => {
    localStorage.setItem('lumo-dev-telegram-id', devId.trim());
    onProfileRefresh?.();
  };

  const runCommand = (cmd) => {
    if (cmd === 'bug') {
      setBugOpen(true);
      return;
    }
    openBotCommand(bot, cmd);
  };

  return (
    <div className="pb-8 space-y-4">
      <header className="mb-1">
        <h1 className="text-[22px] font-bold mb-2">Профиль</h1>
        <p className="text-[13px]" style={{ color: 'var(--lumo-text-muted)' }}>
          Всё то же самое, что команды бота — здесь или в чате
        </p>
        {profile?.telegramId && (
          <p className="text-[11px] mt-2" style={{ color: 'var(--lumo-text-muted)' }}>
            ID: {profile.telegramId}
            {profile.isAdmin ? ' · Admin ✅' : ''}
          </p>
        )}
      </header>

      <SubscriptionSection
        meta={meta}
        profile={profile}
        plans={plans}
        onOpenPriceList={onOpenPriceList}
      />

      <StudentProfileSection />

      <section className="lumo-card p-4">
        <p className="text-[11px] font-bold uppercase tracking-widest mb-3" style={{ color: 'var(--lumo-text-muted)' }}>
          Мой запрос
        </p>
        {profile?.interestQuery ? (
          <p className="text-[14px] leading-relaxed">{profile.interestQuery}</p>
        ) : (
          <p className="text-[14px]" style={{ color: 'var(--lumo-text-muted)' }}>
            Не задан — напиши во вкладке AI-поиск
          </p>
        )}
        {profile?.categories?.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-4">
            {profile.categories.map((type) => (
              <span
                key={type}
                className="text-[12px] px-3 py-1.5 rounded-full font-medium"
                style={{ background: 'var(--lumo-profile-chip-bg)', color: 'var(--lumo-profile-chip-text)' }}
              >
                {typeLabel(type)}
              </span>
            ))}
          </div>
        )}
      </section>

      {meta?.communityTelegramUrl && (
        <section className="lumo-card p-4">
          <div className="flex items-start gap-3">
            <div
              className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
              style={{ background: 'var(--lumo-profile-chip-bg)' }}
            >
              <Users size={18} style={{ color: 'var(--lumo-accent)' }} />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-[15px] font-bold mb-1">
                {meta.communityTelegramHandle || 'Сообщество Lumo'}
              </p>
              <p className="text-[13px] leading-relaxed mb-3" style={{ color: 'var(--lumo-text-muted)' }}>
                Чат пользователей бота: возможности, хакатоны, стартапы и вопросы по Lumo.
              </p>
              <a
                href={meta.communityTelegramUrl}
                target="_blank"
                rel="noreferrer"
                onClick={() => haptic('light')}
                className="inline-flex items-center justify-center px-4 py-2.5 rounded-xl text-[13px] font-bold text-white"
                style={{ background: 'var(--lumo-accent)' }}
              >
                Вступить в сообщество
              </a>
            </div>
          </div>
        </section>
      )}

      <section className="lumo-card p-4">
        <p className="text-[11px] font-bold uppercase tracking-widest mb-3" style={{ color: 'var(--lumo-text-muted)' }}>
          Каналы ({channels.length} / {maxChannels})
        </p>

        {channels.length === 0 ? (
          <p className="text-[13px] mb-4" style={{ color: 'var(--lumo-text-muted)' }}>
            Пока нет — добавь через бота
          </p>
        ) : (
          <ul className="space-y-3 mb-4">
            {channels.map((ch) => (
              <li key={ch.id} className="flex items-center gap-3">
                <div
                  className="w-9 h-9 rounded-full flex items-center justify-center text-white text-sm font-bold shrink-0"
                  style={{ background: 'linear-gradient(135deg, var(--lumo-accent-light), var(--lumo-accent))' }}
                >
                  {channelInitial(ch.title)}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-[14px] font-semibold truncate">{ch.title}</p>
                  <p className="text-[12px] truncate" style={{ color: 'var(--lumo-text-muted)' }}>
                    @{ch.identifier}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => removeChannel(ch)}
                  disabled={removingId === ch.id}
                  className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0 disabled:opacity-40"
                  style={{ background: 'rgba(239,68,68,0.12)', color: '#ef4444' }}
                  aria-label="Удалить канал"
                >
                  <Trash2 size={16} />
                </button>
              </li>
            ))}
          </ul>
        )}

        <div className="lumo-progress-track h-1.5 mb-2">
          <div className="lumo-progress-fill h-full" style={{ width: `${progress}%` }} />
        </div>
        <p className="text-[12px] mb-4" style={{ color: 'var(--lumo-text-muted)' }}>
          {remaining > 0
            ? `Можно добавить ещё ${remaining} ${remaining === 1 ? 'канал' : remaining < 5 ? 'канала' : 'каналов'}`
            : 'Достигнут лимит каналов'}
          {channels.length > 0 && ' · 🗑 — удалить из мониторинга'}
        </p>

        <button
          type="button"
          onClick={() => openBotCommand(bot, 'add_channel')}
          className="flex items-center gap-1.5 text-[13px] font-semibold"
          style={{ color: 'var(--lumo-link)' }}
        >
          <Plus size={16} />
          Добавить канал в боте
        </button>
      </section>

      <section className="lumo-card p-4">
        <p className="text-[11px] font-bold uppercase tracking-widest mb-3" style={{ color: 'var(--lumo-text-muted)' }}>
          Команды бота
        </p>
        <div>
          {COMMANDS.map(({ cmd, label }, idx) => (
            <button
              key={cmd}
              type="button"
              onClick={() => runCommand(cmd)}
              className="w-full flex items-center justify-between py-3 text-[14px] text-left"
              style={{
                borderBottom: idx < COMMANDS.length - 1 ? '1px solid var(--lumo-border)' : undefined,
              }}
            >
              <span>{label}</span>
              <span className="text-[13px] font-mono shrink-0 ml-3" style={{ color: 'var(--lumo-link)' }}>
                /{cmd}
              </span>
            </button>
          ))}
        </div>
      </section>

      {!inTelegram && (
        <section className="lumo-card p-4 border-dashed">
          <p className="text-[12px] mb-3" style={{ color: 'var(--lumo-text-muted)' }}>
            Превью в браузере — укажи Telegram ID (нужен API_ALLOW_DEV_AUTH=true)
          </p>
          <div className="flex gap-2">
            <input
              type="number"
              value={devId}
              onChange={(e) => setDevId(e.target.value)}
              placeholder="Telegram ID"
              className="flex-1 rounded-xl px-3 py-2.5 text-[14px] border"
              style={{ borderColor: 'var(--lumo-border)', background: 'var(--lumo-surface-muted)' }}
            />
            <button type="button" onClick={saveDevId} className="px-4 py-2.5 rounded-xl text-[14px] font-bold lumo-btn-primary">
              OK
            </button>
          </div>
        </section>
      )}

      <BugReportModal
        open={bugOpen}
        onClose={() => setBugOpen(false)}
        supportContact={meta?.supportContact}
      />
    </div>
  );
}
