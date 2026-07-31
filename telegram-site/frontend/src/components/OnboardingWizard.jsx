import { useEffect, useState } from 'react';
import { ArrowRight, PartyPopper } from 'lucide-react';
import { apiFetch, haptic } from '../api';
import OpportunityCard from './OpportunityCard';

const ONBOARDING_KEY = 'lumo-onboarding-done';

export function isOnboardingDone() {
  return localStorage.getItem(ONBOARDING_KEY) === '1';
}

function markOnboardingDone() {
  localStorage.setItem(ONBOARDING_KEY, '1');
}

const GRADE_OPTIONS = ['9 класс', '10 класс', '11 класс', '1 курс', '2 курс', '3 курс', '4 курс', 'Выпускник'];
const SUBJECT_OPTIONS = ['Математика', 'Физика', 'Информатика', 'Биология', 'Химия', 'Экономика', 'Английский язык', 'История', 'Дизайн', 'Робототехника'];
const ENGLISH_LEVEL_OPTIONS = [
  { id: 'none', label: 'Не оцениваю' },
  { id: 'a2', label: 'A2 — элементарный' },
  { id: 'b1', label: 'B1 — средний' },
  { id: 'b2', label: 'B2 — выше среднего' },
  { id: 'c1', label: 'C1 — продвинутый' },
  { id: 'c2', label: 'C2 — свободный' },
];
const REGION_OPTIONS = ['Алматы', 'Астана', 'Шымкент', 'Караганда', 'Актобе'];
const INTEREST_OPTIONS = [
  { id: 'it', label: 'IT / робототехника' },
  { id: 'business', label: 'Бизнес / экономика' },
  { id: 'science', label: 'Наука' },
  { id: 'languages', label: 'Языки' },
  { id: 'creative', label: 'Творчество' },
];
const GOAL_OPTIONS = [
  { id: 'грант', label: 'Гранты' },
  { id: 'хакатон', label: 'Хакатоны' },
  { id: 'стажировка', label: 'Стажировки' },
  { id: 'олимпиада', label: 'Олимпиады' },
];

const STEPS = ['grade', 'subjects', 'english', 'interests', 'region', 'goal', 'matches'];

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

export default function OnboardingWizard({ onFinish, onSkip, onOpenItem }) {
  const [stepIndex, setStepIndex] = useState(0);
  const [grade, setGrade] = useState('');
  const [subjects, setSubjects] = useState([]);
  const [englishLevel, setEnglishLevel] = useState('');
  const [interests, setInterests] = useState([]);
  const [region, setRegion] = useState('');
  const [goals, setGoals] = useState([]);
  const [loadingMatches, setLoadingMatches] = useState(false);
  const [matchError, setMatchError] = useState('');
  const [items, setItems] = useState([]);

  const step = STEPS[stepIndex];
  const goTo = (i) => setStepIndex(Math.max(0, Math.min(STEPS.length - 1, i)));

  const toggleFrom = (setFn) => (id) =>
    setFn((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  const toggleSubject = toggleFrom(setSubjects);
  const toggleInterest = toggleFrom(setInterests);
  const toggleGoal = toggleFrom(setGoals);

  const finish = async () => {
    setLoadingMatches(true);
    setMatchError('');

    apiFetch('/users/profile', {
      method: 'PUT',
      body: JSON.stringify({ grade, region, englishLevel, subjects }),
    }).catch(() => {});

    const interestLabels = INTEREST_OPTIONS.filter((o) => interests.includes(o.id)).map((o) => o.label);
    const goalLabels = GOAL_OPTIONS.filter((o) => goals.includes(o.id)).map((o) => o.label);
    const query = [
      grade && `Учусь: ${grade}`,
      subjects.length && `Предметы: ${subjects.join(', ')}`,
      interestLabels.length && `Интересы: ${interestLabels.join(', ')}`,
      region && `Город: ${region}`,
      goalLabels.length && `Ищу: ${goalLabels.join(', ')}`,
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
      goTo(STEPS.length - 1);
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
            <div className="flex flex-wrap justify-center gap-2 mb-8">
              {GRADE_OPTIONS.map((g) => (
                <Chip key={g} active={grade === g} onClick={() => setGrade(g)}>
                  {g}
                </Chip>
              ))}
            </div>
            <ContinueButton onClick={() => goTo(1)} disabled={!grade}>
              Продолжить
            </ContinueButton>
          </div>
        )}

        {step === 'subjects' && (
          <div>
            <h1 className="text-[24px] font-bold mb-2 text-center">Какие предметы сильные?</h1>
            <p className="text-[13px] text-center mb-6" style={{ color: 'var(--lumo-text-muted)' }}>
              Поможет находить профильные олимпиады и стипендии
            </p>
            <div className="flex flex-wrap justify-center gap-2 mb-8">
              {SUBJECT_OPTIONS.map((s) => (
                <Chip key={s} active={subjects.includes(s)} onClick={() => toggleSubject(s)}>
                  {s}
                </Chip>
              ))}
            </div>
            <ContinueButton onClick={() => goTo(2)}>Продолжить</ContinueButton>
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
            <ContinueButton onClick={() => goTo(3)}>Продолжить</ContinueButton>
          </div>
        )}

        {step === 'interests' && (
          <div>
            <h1 className="text-[24px] font-bold mb-2 text-center">Что тебе интересно?</h1>
            <p className="text-[13px] text-center mb-6" style={{ color: 'var(--lumo-text-muted)' }}>
              Можно выбрать несколько
            </p>
            <div className="flex flex-wrap justify-center gap-2 mb-8">
              {INTEREST_OPTIONS.map((o) => (
                <Chip key={o.id} active={interests.includes(o.id)} onClick={() => toggleInterest(o.id)}>
                  {o.label}
                </Chip>
              ))}
            </div>
            <ContinueButton onClick={() => goTo(4)} disabled={interests.length === 0}>
              Продолжить
            </ContinueButton>
          </div>
        )}

        {step === 'region' && (
          <div>
            <h1 className="text-[24px] font-bold mb-2 text-center">Из какого ты города?</h1>
            <p className="text-[13px] text-center mb-6" style={{ color: 'var(--lumo-text-muted)' }}>
              Покажем возможности рядом с тобой
            </p>
            <div className="flex flex-wrap justify-center gap-2 mb-8">
              {REGION_OPTIONS.map((r) => (
                <Chip key={r} active={region === r} onClick={() => setRegion(r)}>
                  {r}
                </Chip>
              ))}
            </div>
            <ContinueButton onClick={() => goTo(5)} disabled={!region}>
              Продолжить
            </ContinueButton>
          </div>
        )}

        {step === 'goal' && (
          <div>
            <h1 className="text-[24px] font-bold mb-2 text-center">Что ищешь в первую очередь?</h1>
            <p className="text-[13px] text-center mb-6" style={{ color: 'var(--lumo-text-muted)' }}>
              Можно выбрать несколько
            </p>
            <div className="flex flex-wrap justify-center gap-2 mb-4">
              {GOAL_OPTIONS.map((o) => (
                <Chip key={o.id} active={goals.includes(o.id)} onClick={() => toggleGoal(o.id)}>
                  {o.label}
                </Chip>
              ))}
            </div>
            {matchError && <p className="text-[12px] text-center text-red-400 mb-4">{matchError}</p>}
            <ContinueButton onClick={finish} disabled={goals.length === 0 || loadingMatches}>
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

            <ContinueButton onClick={done}>Перейти в Lumo</ContinueButton>
          </div>
        )}
      </div>
    </div>
  );
}
