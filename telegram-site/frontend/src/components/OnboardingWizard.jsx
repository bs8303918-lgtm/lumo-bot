import { useEffect, useState } from 'react';
import { ArrowRight, PartyPopper, Sparkles } from 'lucide-react';
import { apiFetch, haptic, openExternalLink } from '../api';
import OpportunityCard from './OpportunityCard';

const LANDING_URL = 'https://lumo-site-mu.vercel.app/';

const ONBOARDING_KEY = 'lumo-onboarding-done';

export function isOnboardingDone() {
  return localStorage.getItem(ONBOARDING_KEY) === '1';
}

function markOnboardingDone() {
  localStorage.setItem(ONBOARDING_KEY, '1');
}

const OTHER = 'Другое';

const GRADE_OPTIONS = ['9 класс', '10 класс', '11 класс', '1 курс', '2 курс', '3 курс', '4 курс', 'Выпускник', OTHER];
const SUBJECT_OPTIONS = ['Математика', 'Физика', 'Информатика', 'Биология', 'Химия', 'Экономика', 'Английский язык', 'История', 'Дизайн', 'Робототехника'];
const ENGLISH_LEVEL_OPTIONS = [
  { id: 'none', label: 'Не оцениваю' },
  { id: 'a2', label: 'A2 — элементарный' },
  { id: 'b1', label: 'B1 — средний' },
  { id: 'b2', label: 'B2 — выше среднего' },
  { id: 'c1', label: 'C1 — продвинутый' },
  { id: 'c2', label: 'C2 — свободный' },
];
const REGION_OPTIONS = ['Алматы', 'Астана', 'Шымкент', 'Караганда', 'Актобе', OTHER];

// Полный список сфер — тот же словарь, который распознаёт бэкенд (services/interest_domains.py),
// чтобы выбор реально попадал в категории, а не терялся.
const DOMAIN_OPTIONS = [
  { id: 'it', label: '💻 IT' },
  { id: 'робототехника', label: '🤖 Робототехника' },
  { id: 'инженерия', label: '⚙️ Инженерия' },
  { id: 'кибербезопасность', label: '🔐 Кибербезопасность' },
  { id: 'математика', label: '📐 Математика' },
  { id: 'физика', label: '⚛️ Физика' },
  { id: 'информатика', label: '🖥 Информатика' },
  { id: 'stem', label: '🔭 STEM' },
  { id: 'биология', label: '🔬 Биология' },
  { id: 'биотех', label: '🧬 Биотех' },
  { id: 'нейронаука', label: '🧬 Нейронаука' },
  { id: 'медицина', label: '🏥 Медицина' },
  { id: 'химия', label: '⚗️ Химия' },
  { id: 'астрофизика', label: '🌌 Астрофизика' },
  { id: 'экология', label: '🌿 Экология' },
  { id: 'сельское хозяйство', label: '🌾 Агро' },
  { id: 'стартапы', label: '🚀 Стартапы' },
  { id: 'бизнес', label: '💼 Бизнес' },
  { id: 'экономика', label: '📊 Экономика' },
  { id: 'финансы', label: '💹 Финансы' },
  { id: 'право', label: '⚖️ Право' },
  { id: 'политология', label: '🏛 Политология' },
  { id: 'дизайн', label: '🎨 Дизайн' },
  { id: 'искусство', label: '🎭 Искусство' },
  { id: 'архитектура', label: '🏗 Архитектура' },
  { id: 'музыка', label: '🎵 Музыка' },
  { id: 'кино', label: '🎥 Кино' },
  { id: 'медиа', label: '🎬 Медиа' },
  { id: 'журналистика', label: '📰 Журналистика' },
  { id: 'лингвистика', label: '🗣 Лингвистика' },
  { id: 'психология', label: '🧠 Психология' },
  { id: 'социология', label: '👥 Социология' },
  { id: 'философия', label: '📚 Философия' },
  { id: 'география', label: '🗺 География' },
  { id: 'edtech', label: '📱 EdTech' },
  { id: 'medtech', label: '🩺 MedTech' },
  { id: 'спорт', label: '🏅 Спорт' },
  { id: 'денежные призы', label: '💵 Денежные призы' },
];

// Полный список типов возможностей — тот же, что в каталоге (db/repositories/opportunity_catalog.py).
const TYPE_OPTIONS = [
  { id: 'грант', label: '💰 Гранты' },
  { id: 'стипендия', label: '🎓 Стипендии' },
  { id: 'хакатон', label: '💻 Хакатоны' },
  { id: 'стажировка', label: '🏢 Стажировки' },
  { id: 'конкурс', label: '🏆 Конкурсы' },
  { id: 'олимпиада', label: '🥇 Олимпиады' },
  { id: 'эссе', label: '✍️ Конкурсы эссе' },
  { id: 'кейс', label: '📋 Кейс-чемпионаты' },
  { id: 'летняя_школа', label: '☀️ Летние школы' },
  { id: 'курс', label: '📚 Курсы' },
  { id: 'мероприятие', label: '📅 Мероприятия' },
];

const FORMAT_OPTIONS = [
  { id: 'any', label: 'Без разницы' },
  { id: 'online', label: 'Онлайн' },
  { id: 'offline', label: 'Офлайн' },
];
const TEAM_OPTIONS = [
  { id: 'any', label: 'Без разницы' },
  { id: 'team', label: 'В команде' },
  { id: 'solo', label: 'Соло' },
];

const STEPS = [
  'grade',
  'subjects',
  'domains',
  'types',
  'english',
  'format',
  'team',
  'region',
  'about',
  'matches',
  'regFirstName',
  'regLastName',
  'regEmail',
  'regPassword',
  'regDone',
];

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function ProgressBar({ step }) {
  const pct = ((step + 1) / STEPS.length) * 100;
  return (
    <div className="fixed top-0 inset-x-0 h-1 z-[90]" style={{ background: 'var(--lumo-surface-muted)' }}>
      <div
        className="h-full transition-all duration-400"
        style={{ width: `${pct}%`, background: 'linear-gradient(90deg, var(--lumo-accent-light), var(--lumo-accent))' }}
      />
    </div>
  );
}

function Chip({ active, onClick, children }) {
  return (
    <button
      type="button"
      onClick={() => {
        haptic('light');
        onClick();
      }}
      className={`px-3.5 py-2.5 rounded-xl text-[13px] font-semibold transition-colors ${active ? 'lumo-filter-active' : 'lumo-filter-inactive'}`}
    >
      {children}
    </button>
  );
}

function CustomTextInput({ value, onChange, placeholder }) {
  return (
    <input
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className="lumo-form-input mb-8"
    />
  );
}

function ContinueButton({ onClick, disabled, children }) {
  return (
    <button
      type="button"
      onClick={() => {
        haptic('medium');
        onClick();
      }}
      disabled={disabled}
      className="w-full inline-flex items-center justify-center gap-2 py-3.5 rounded-xl font-bold text-white disabled:opacity-40 lumo-btn-primary"
    >
      {children}
      <ArrowRight size={17} />
    </button>
  );
}

function useLivePreview(params, enabled) {
  const key = JSON.stringify(params);
  const [items, setItems] = useState([]);

  useEffect(() => {
    if (!enabled) {
      setItems([]);
      return undefined;
    }
    let cancelled = false;
    const timer = setTimeout(async () => {
      try {
        const search = new URLSearchParams({ sort: 'relevance', limit: '2', ...JSON.parse(key) });
        const data = await apiFetch(`/lumo/opportunities?${search.toString()}`);
        if (!cancelled) setItems((data.items ?? []).slice(0, 2));
      } catch {
        if (!cancelled) setItems([]);
      }
    }, 450);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, enabled]);

  return items;
}

function LivePreviewList({ items }) {
  if (!items.length) return null;
  return (
    <div className="mb-4 space-y-1.5">
      <p className="text-[11px] font-semibold uppercase tracking-wide flex items-center gap-1" style={{ color: 'var(--lumo-accent)' }}>
        <Sparkles size={12} /> Уже нашли похожее
      </p>
      {items.map((it) => (
        <div
          key={it.id}
          className="flex items-center gap-2 px-3 py-2.5 rounded-xl text-[13px]"
          style={{ background: 'var(--lumo-surface-muted)' }}
        >
          <span>{it.emoji || '✨'}</span>
          <span className="font-semibold truncate">{it.title}</span>
        </div>
      ))}
    </div>
  );
}

export default function OnboardingWizard({ onFinish, onSkip, onOpenItem }) {
  const [stepIndex, setStepIndex] = useState(0);
  const [grade, setGrade] = useState('');
  const [customGrade, setCustomGrade] = useState('');
  const [subjects, setSubjects] = useState([]);
  const [customSubjects, setCustomSubjects] = useState('');
  const [domains, setDomains] = useState([]);
  const [customDomains, setCustomDomains] = useState('');
  const [types, setTypes] = useState([]);
  const [customTypes, setCustomTypes] = useState('');
  const [englishLevel, setEnglishLevel] = useState('');
  const [format, setFormat] = useState('any');
  const [team, setTeam] = useState('any');
  const [region, setRegion] = useState('');
  const [customRegion, setCustomRegion] = useState('');
  const [about, setAbout] = useState('');
  const [loadingMatches, setLoadingMatches] = useState(false);
  const [matchError, setMatchError] = useState('');
  const [items, setItems] = useState([]);
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regSubmitting, setRegSubmitting] = useState(false);
  const [regError, setRegError] = useState('');

  const step = STEPS[stepIndex];
  const goTo = (i) => setStepIndex(Math.max(0, Math.min(STEPS.length - 1, i)));

  const toggleFrom = (setFn) => (id) =>
    setFn((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  const toggleSubject = toggleFrom(setSubjects);
  const toggleDomain = toggleFrom(setDomains);
  const toggleType = toggleFrom(setTypes);

  const typesPreview = useLivePreview({ types: types.join(',') }, step === 'types' && types.length > 0);
  const lastDomainLabel = domains.length
    ? (DOMAIN_OPTIONS.find((o) => o.id === domains[domains.length - 1])?.label || '').replace(/^\S+\s/, '')
    : '';
  const domainsPreview = useLivePreview({ q: lastDomainLabel }, step === 'domains' && Boolean(lastDomainLabel));

  const finalGrade = grade === OTHER ? customGrade.trim() : grade;
  const finalRegion = region === OTHER ? customRegion.trim() : region;

  const finish = async () => {
    setLoadingMatches(true);
    setMatchError('');

    const subjectList = [...subjects, ...customSubjects.split(',').map((s) => s.trim()).filter(Boolean)];

    apiFetch('/users/profile', {
      method: 'PUT',
      body: JSON.stringify({ grade: finalGrade, region: finalRegion, englishLevel, subjects: subjectList }),
    }).catch(() => {});

    const domainLabels = [
      ...DOMAIN_OPTIONS.filter((o) => domains.includes(o.id)).map((o) => o.label.replace(/^\S+\s/, '')),
      ...customDomains.split(',').map((s) => s.trim()).filter(Boolean),
    ];
    const typeLabels = [
      ...TYPE_OPTIONS.filter((o) => types.includes(o.id)).map((o) => o.label.replace(/^\S+\s/, '')),
      ...customTypes.split(',').map((s) => s.trim()).filter(Boolean),
    ];
    const formatText = format === 'online' ? 'Формат: онлайн' : format === 'offline' ? 'Формат: офлайн' : '';
    const teamText = team === 'team' ? 'Ищу команду' : team === 'solo' ? 'Готов подавать соло' : '';

    const query = [
      finalGrade && `Учусь: ${finalGrade}`,
      subjectList.length && `Предметы: ${subjectList.join(', ')}`,
      domainLabels.length && `Интересы: ${domainLabels.join(', ')}`,
      typeLabels.length && `Ищу: ${typeLabels.join(', ')}`,
      finalRegion && `Город: ${finalRegion}`,
      formatText,
      teamText,
      about.trim(),
    ]
      .filter(Boolean)
      .join('. ');

    try {
      const data = await apiFetch('/lumo/match', {
        method: 'POST',
        body: JSON.stringify({ query: query || 'подбери подходящие конкурсы для школьника', saveInterest: true }),
      });
      setItems(data.items ?? []);
    } catch (err) {
      setMatchError(err.message || 'Не получилось подобрать совпадения — открой каталог.');
      setItems([]);
    } finally {
      setLoadingMatches(false);
      haptic('success');
      goTo(STEPS.indexOf('matches'));
    }
  };

  const submitRegistration = async () => {
    setRegSubmitting(true);
    setRegError('');
    try {
      await apiFetch('/auth/set-password', {
        method: 'POST',
        body: JSON.stringify({
          firstName: firstName.trim(),
          lastName: lastName.trim(),
          email: regEmail.trim().toLowerCase(),
          password: regPassword,
        }),
      });
      haptic('success');
      goTo(stepIndex + 1);
    } catch (err) {
      setRegError(err.message || 'Не получилось сохранить — попробуй другой email');
    } finally {
      setRegSubmitting(false);
    }
  };

  useEffect(() => {
    if (step === 'matches') haptic('success');
  }, [step]);

  const skip = () => {
    markOnboardingDone();
    onSkip?.();
  };

  const done = () => {
    markOnboardingDone();
    onFinish?.();
  };

  return (
    <div className="fixed inset-0 z-[80] overflow-y-auto" style={{ background: 'var(--lumo-bg)' }}>
      <ProgressBar step={stepIndex} />
      <button
        type="button"
        onClick={skip}
        className="fixed top-4 right-4 z-[90] text-[13px] font-semibold"
        style={{ color: 'var(--lumo-text-muted)' }}
      >
        Пропустить
      </button>

      <div className="min-h-full flex flex-col justify-center px-5 py-16 max-w-lg mx-auto">
        {step === 'grade' && (
          <div>
            <h1 className="text-[24px] font-bold mb-2 text-center">В каком ты классе?</h1>
            <p className="text-[13px] text-center mb-6" style={{ color: 'var(--lumo-text-muted)' }}>
              30 секунд — и увидишь подборку под себя
            </p>
            <div className="flex flex-wrap justify-center gap-2 mb-4">
              {GRADE_OPTIONS.map((g) => (
                <Chip key={g} active={grade === g} onClick={() => setGrade(g)}>
                  {g}
                </Chip>
              ))}
            </div>
            {grade === OTHER && (
              <CustomTextInput value={customGrade} onChange={setCustomGrade} placeholder="Свой вариант" />
            )}
            <ContinueButton
              onClick={() => goTo(1)}
              disabled={!grade || (grade === OTHER && !customGrade.trim())}
            >
              Продолжить
            </ContinueButton>
            <button
              type="button"
              onClick={() => openExternalLink(LANDING_URL)}
              className="w-full text-center text-[12px] font-semibold mt-5 underline"
              style={{ color: 'var(--lumo-text-muted)' }}
            >
              Наш сайт: lumo-site-mu.vercel.app
            </button>
          </div>
        )}

        {step === 'subjects' && (
          <div>
            <h1 className="text-[24px] font-bold mb-2 text-center">Какие предметы сильные?</h1>
            <p className="text-[13px] text-center mb-6" style={{ color: 'var(--lumo-text-muted)' }}>
              Поможет находить профильные олимпиады и стипендии
            </p>
            <div className="flex flex-wrap justify-center gap-2 mb-4">
              {SUBJECT_OPTIONS.map((s) => (
                <Chip key={s} active={subjects.includes(s)} onClick={() => toggleSubject(s)}>
                  {s}
                </Chip>
              ))}
            </div>
            <CustomTextInput
              value={customSubjects}
              onChange={setCustomSubjects}
              placeholder="Своего предмета нет в списке? Впиши через запятую"
            />
            <ContinueButton onClick={() => goTo(2)}>Продолжить</ContinueButton>
          </div>
        )}

        {step === 'domains' && (
          <div>
            <h1 className="text-[24px] font-bold mb-2 text-center">Что тебе интересно?</h1>
            <p className="text-[13px] text-center mb-6" style={{ color: 'var(--lumo-text-muted)' }}>
              Вся наша карта сфер — выбери сколько угодно
            </p>
            <div className="flex flex-wrap justify-center gap-2 mb-4 max-h-[42vh] overflow-y-auto py-1">
              {DOMAIN_OPTIONS.map((o) => (
                <Chip key={o.id} active={domains.includes(o.id)} onClick={() => toggleDomain(o.id)}>
                  {o.label}
                </Chip>
              ))}
            </div>
            <CustomTextInput
              value={customDomains}
              onChange={setCustomDomains}
              placeholder="Не нашёл свою сферу? Впиши через запятую"
            />
            <LivePreviewList items={domainsPreview} />
            <ContinueButton onClick={() => goTo(3)} disabled={domains.length === 0 && !customDomains.trim()}>
              Продолжить
            </ContinueButton>
          </div>
        )}

        {step === 'types' && (
          <div>
            <h1 className="text-[24px] font-bold mb-2 text-center">Что именно ищешь?</h1>
            <p className="text-[13px] text-center mb-6" style={{ color: 'var(--lumo-text-muted)' }}>
              Все категории конкурсов — можно выбрать несколько
            </p>
            <div className="flex flex-wrap justify-center gap-2 mb-4 max-h-[42vh] overflow-y-auto py-1">
              {TYPE_OPTIONS.map((o) => (
                <Chip key={o.id} active={types.includes(o.id)} onClick={() => toggleType(o.id)}>
                  {o.label}
                </Chip>
              ))}
            </div>
            <CustomTextInput
              value={customTypes}
              onChange={setCustomTypes}
              placeholder="Что-то ещё? Впиши свой вариант"
            />
            <LivePreviewList items={typesPreview} />
            <ContinueButton onClick={() => goTo(4)} disabled={types.length === 0 && !customTypes.trim()}>
              Продолжить
            </ContinueButton>
          </div>
        )}

        {step === 'english' && (
          <div>
            <h1 className="text-[24px] font-bold mb-2 text-center">Уровень английского?</h1>
            <p className="text-[13px] text-center mb-6" style={{ color: 'var(--lumo-text-muted)' }}>
              Не будем предлагать программы не по уровню
            </p>
            <div className="flex flex-wrap justify-center gap-2 mb-8">
              {ENGLISH_LEVEL_OPTIONS.map((o) => (
                <Chip key={o.id} active={englishLevel === o.id} onClick={() => setEnglishLevel(o.id)}>
                  {o.label}
                </Chip>
              ))}
            </div>
            <ContinueButton onClick={() => goTo(5)}>Продолжить</ContinueButton>
          </div>
        )}

        {step === 'format' && (
          <div>
            <h1 className="text-[24px] font-bold mb-2 text-center">Какой формат удобнее?</h1>
            <p className="text-[13px] text-center mb-6" style={{ color: 'var(--lumo-text-muted)' }}>
              Онлайн или готов ехать очно
            </p>
            <div className="flex flex-wrap justify-center gap-2 mb-8">
              {FORMAT_OPTIONS.map((o) => (
                <Chip key={o.id} active={format === o.id} onClick={() => setFormat(o.id)}>
                  {o.label}
                </Chip>
              ))}
            </div>
            <ContinueButton onClick={() => goTo(6)}>Продолжить</ContinueButton>
          </div>
        )}

        {step === 'team' && (
          <div>
            <h1 className="text-[24px] font-bold mb-2 text-center">Команда или соло?</h1>
            <p className="text-[13px] text-center mb-6" style={{ color: 'var(--lumo-text-muted)' }}>
              Некоторые конкурсы требуют команду — не будем их зря подсовывать
            </p>
            <div className="flex flex-wrap justify-center gap-2 mb-8">
              {TEAM_OPTIONS.map((o) => (
                <Chip key={o.id} active={team === o.id} onClick={() => setTeam(o.id)}>
                  {o.label}
                </Chip>
              ))}
            </div>
            <ContinueButton onClick={() => goTo(7)}>Продолжить</ContinueButton>
          </div>
        )}

        {step === 'region' && (
          <div>
            <h1 className="text-[24px] font-bold mb-2 text-center">Из какого ты города?</h1>
            <p className="text-[13px] text-center mb-6" style={{ color: 'var(--lumo-text-muted)' }}>
              Покажем возможности рядом с тобой
            </p>
            <div className="flex flex-wrap justify-center gap-2 mb-4">
              {REGION_OPTIONS.map((r) => (
                <Chip key={r} active={region === r} onClick={() => setRegion(r)}>
                  {r}
                </Chip>
              ))}
            </div>
            {region === OTHER && (
              <CustomTextInput value={customRegion} onChange={setCustomRegion} placeholder="Впиши свой город" />
            )}
            <ContinueButton
              onClick={() => goTo(8)}
              disabled={!region || (region === OTHER && !customRegion.trim())}
            >
              Продолжить
            </ContinueButton>
          </div>
        )}

        {step === 'about' && (
          <div>
            <h1 className="text-[24px] font-bold mb-2 text-center">Расскажи о себе</h1>
            <p className="text-[13px] text-center mb-6" style={{ color: 'var(--lumo-text-muted)' }}>
              Проекты, достижения, чего хочешь добиться — что угодно, что поможет AI подобрать точнее. Необязательно.
            </p>
            <textarea
              value={about}
              onChange={(e) => setAbout(e.target.value)}
              rows={4}
              placeholder="Например: занимаюсь Python 2 года, делал школьный проект по эко-стартапам, хочу поступить в вуз за рубежом"
              className="lumo-form-input resize-none mb-4"
            />
            {matchError && <p className="text-[12px] text-center text-red-400 mb-4">{matchError}</p>}
            <ContinueButton onClick={finish} disabled={loadingMatches}>
              {loadingMatches ? 'Lumo подбирает…' : 'Найти мою подборку'}
            </ContinueButton>
          </div>
        )}

        {step === 'matches' && (
          <div>
            <div className="text-center mb-6">
              <div
                className="w-14 h-14 rounded-2xl flex items-center justify-center mx-auto mb-4"
                style={{ background: 'linear-gradient(135deg, var(--lumo-accent-light), var(--lumo-accent))' }}
              >
                <PartyPopper size={26} className="text-white" />
              </div>
              <h1 className="text-[24px] font-bold mb-2">Профиль готов</h1>
              <p className="text-[13px]" style={{ color: 'var(--lumo-text-muted)' }}>
                {items.length > 0
                  ? `Вот ${items.length} совпадени${items.length === 1 ? 'е' : 'я'} по твоему профилю. Остальное — в каталоге.`
                  : 'Открой каталог — там полная база конкурсов и грантов.'}
              </p>
            </div>

            {items.length > 0 && (
              <div className="space-y-3 mb-6">
                {items.slice(0, 5).map((item) => (
                  <OpportunityCard key={item.id} item={item} onOpen={onOpenItem || (() => {})} />
                ))}
              </div>
            )}

            <ContinueButton onClick={() => goTo(stepIndex + 1)}>Продолжить</ContinueButton>
          </div>
        )}

        {step === 'regFirstName' && (
          <div>
            <h1 className="text-[24px] font-bold mb-2 text-center">Как тебя зовут?</h1>
            <p className="text-[13px] text-center mb-6" style={{ color: 'var(--lumo-text-muted)' }}>
              Заодно сможешь заходить в Lumo с сайта, не только из Telegram
            </p>
            <input
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              placeholder="Имя"
              className="lumo-form-input mb-8"
            />
            <ContinueButton onClick={() => goTo(stepIndex + 1)} disabled={!firstName.trim()}>
              Продолжить
            </ContinueButton>
          </div>
        )}

        {step === 'regLastName' && (
          <div>
            <h1 className="text-[24px] font-bold mb-2 text-center">А фамилия?</h1>
            <p className="text-[13px] text-center mb-6" style={{ color: 'var(--lumo-text-muted)' }}>
              Необязательно
            </p>
            <input
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
              placeholder="Фамилия"
              className="lumo-form-input mb-8"
            />
            <ContinueButton onClick={() => goTo(stepIndex + 1)}>Продолжить</ContinueButton>
          </div>
        )}

        {step === 'regEmail' && (
          <div>
            <h1 className="text-[24px] font-bold mb-2 text-center">Email для входа на сайт</h1>
            <p className="text-[13px] text-center mb-6" style={{ color: 'var(--lumo-text-muted)' }}>
              На lumo-site-mu.vercel.app сможешь заходить тем же аккаунтом
            </p>
            <input
              type="email"
              value={regEmail}
              onChange={(e) => setRegEmail(e.target.value)}
              placeholder="you@example.com"
              className="lumo-form-input mb-8"
            />
            <ContinueButton onClick={() => goTo(stepIndex + 1)} disabled={!EMAIL_PATTERN.test(regEmail.trim())}>
              Продолжить
            </ContinueButton>
          </div>
        )}

        {step === 'regPassword' && (
          <div>
            <h1 className="text-[24px] font-bold mb-2 text-center">Придумай пароль</h1>
            <p className="text-[13px] text-center mb-6" style={{ color: 'var(--lumo-text-muted)' }}>
              Минимум 8 символов
            </p>
            <input
              type="password"
              value={regPassword}
              onChange={(e) => setRegPassword(e.target.value)}
              placeholder="Пароль"
              className="lumo-form-input mb-4"
            />
            {regError && <p className="text-[12px] text-center text-red-400 mb-4">{regError}</p>}
            <ContinueButton onClick={submitRegistration} disabled={regPassword.length < 8 || regSubmitting}>
              {regSubmitting ? 'Сохраняю…' : 'Создать пароль'}
            </ContinueButton>
          </div>
        )}

        {step === 'regDone' && (
          <div>
            <div className="text-center mb-6">
              <div
                className="w-14 h-14 rounded-2xl flex items-center justify-center mx-auto mb-4"
                style={{ background: 'linear-gradient(135deg, var(--lumo-accent-light), var(--lumo-accent))' }}
              >
                <PartyPopper size={26} className="text-white" />
              </div>
              <h1 className="text-[24px] font-bold mb-2">Готово!</h1>
              <p className="text-[13px]" style={{ color: 'var(--lumo-text-muted)' }}>
                Теперь можешь заходить в Lumo и с сайта — тем же email и паролем.
              </p>
            </div>
            <ContinueButton onClick={done}>Перейти в Lumo</ContinueButton>
          </div>
        )}
      </div>
    </div>
  );
}
