import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Bell, ChevronDown, Globe, Zap } from 'lucide-react';
import LumoLogo, { LumoMark } from './components/LumoLogo.jsx';
import { TestimonialsSection } from './components/TestimonialsSection';
import { LUMO_PRICING_PLANS, Pricing } from '@/components/ui/pricing';

const BOT_URL = 'https://t.me/LumoAI1bot';

const FEATURES = [
  {
    icon: Zap,
    iconClass: 'gradient-btn',
    title: 'Ответ за 10 секунд',
    text: 'Напиши «Ищу гранты по ИИ для первокурсников» и получи подборку моментально.',
  },
  {
    icon: Globe,
    iconClass: 'bg-sky-600',
    title: 'Все каналы в одном',
    text: 'Telegram, VK, сайты универов и фондов — всё мониторится 24/7. Добавляй свои каналы.',
  },
  {
    icon: Bell,
    iconClass: 'bg-blue-700',
    title: 'Умные алерты',
    text: 'Lumo напомнит о дедлайне подачи заявки и подсветит возможности по твоему профилю.',
  },
];

const CONTESTS = [
  {
    category: 'IT & ENGINEERING',
    title: 'Олимпиада НТО',
    deadline: '15.03.2026',
    prize: '100 000 ₽',
  },
  {
    category: 'STARTUP',
    title: 'Skolkovo Student Grant',
    deadline: '01.04.2026',
    prize: '500 000 ₽',
  },
  {
    category: 'АЛГОРИТМЫ',
    title: 'Турнир по спортивному программированию',
    deadline: '20.03.2026',
    prize: '50 000 ₽',
  },
  {
    category: 'НАУКА',
    title: 'Российская научная олимпиада',
    deadline: '10.04.2026',
    prize: 'Стипендия',
  },
  {
    category: 'ДИЗАЙН',
    title: 'Art Masters Challenge',
    deadline: '25.03.2026',
    prize: '75 000 ₽',
  },
  {
    category: 'БИЗНЕС',
    title: 'Startup Weekend Moscow',
    deadline: '05.04.2026',
    prize: '300 000 ₽',
  },
  {
    category: 'IT & ENGINEERING',
    title: 'Yandex Cup',
    deadline: '18.03.2026',
    prize: '200 000 ₽',
  },
  {
    category: 'СТАЖИРОВКА',
    title: 'VK Tech Internship',
    deadline: '30.03.2026',
    prize: '80 000 ₽/мес',
  },
];

const FAQ = [
  {
    q: 'Как быстро Lumo находит информацию?',
    a: 'Lumo ищет по базе из 1000+ конкурсов и каналов за 10 секунд. Просто напиши запрос — как в ChatGPT, только про возможности.',
  },
  {
    q: 'Могу ли я добавить свои каналы для мониторинга?',
    a: 'Да. Добавь до 5 своих Telegram-каналов — Lumo будет мониторить их вместе с основной базой и присылать новые возможности.',
  },
  {
    q: 'Это платно?',
    a: 'Старт бесплатный. Базовый поиск, подборки и алерты доступны без оплаты. Расширенные функции — по подписке.',
  },
  {
    q: 'Только для айтишников?',
    a: 'Нет. Lumo находит гранты, олимпиады, стажировки и конкурсы для любых направлений — от науки и дизайна до бизнеса и спорта.',
  },
];

const TOPICS = [
  'хакатоны',
  'гранты',
  'стажировки',
  'олимпиады',
  'конкурсы',
  'стипендии',
  'акселераторы',
  'форумы',
];

const FLOATING_MARKS = [
  { top: '22%', left: '10%', size: 28, rot: '-8deg', delay: '0s', opacity: 0.2 },
  { top: '58%', left: '7%', size: 36, rot: '6deg', delay: '-2s', opacity: 0.15 },
  { top: '30%', right: '11%', size: 32, rot: '10deg', delay: '-1s', opacity: 0.18 },
  { top: '62%', right: '8%', size: 24, rot: '-5deg', delay: '-3s', opacity: 0.12 },
];

function Navbar({ scrolled }) {
  return (
    <header
      className={`fixed top-0 inset-x-0 z-50 transition-all duration-300 ${
        scrolled ? 'bg-[#07080c]/85 backdrop-blur-xl border-b border-white/5' : 'bg-transparent'
      }`}
    >
      <div className="max-w-6xl mx-auto px-5 h-16 flex items-center justify-between">
        <LumoLogo theme="dark" />

        <nav className="hidden md:flex items-center gap-8 text-sm text-zinc-400">
          <a href="#features" className="hover:text-white transition-colors">
            Возможности
          </a>
          <a href="#contests" className="hover:text-white transition-colors">
            База конкурсов
          </a>
          <a href="#pricing" className="hover:text-white transition-colors">
            Тарифы
          </a>
        </nav>

        <Link
          to="/app?signup=1"
          className="inline-flex items-center px-5 py-2 rounded-full bg-white text-black text-sm font-semibold hover:bg-zinc-100 transition-colors"
        >
          Попробовать
        </Link>
      </div>
    </header>
  );
}

function HeroSection() {
  return (
    <section className="relative min-h-screen flex items-center justify-center pt-16 pb-24 px-5 overflow-hidden">
      <div className="absolute inset-0 hero-glow pointer-events-none" aria-hidden />

      {FLOATING_MARKS.map(({ top, left, right, size, rot, delay, opacity }) => (
        <div
          key={`${top}-${left ?? right}`}
          className="absolute floating-mark pointer-events-none select-none text-white"
          style={{
            top,
            left,
            right,
            '--rot': rot,
            '--opacity': opacity,
            animationDelay: delay,
          }}
          aria-hidden
        >
          <LumoMark size={size} className="opacity-[var(--opacity)]" />
        </div>
      ))}

      <div className="relative max-w-3xl mx-auto text-center">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 mb-8 rounded-full border border-sky-500/30 bg-sky-500/10 text-sky-300 text-sm">
          <span className="w-1.5 h-1.5 rounded-full bg-sky-400" />
          150+ студентов уже используют Lumo
        </div>

        <h1 className="text-[clamp(2.25rem,5.5vw,4rem)] font-bold leading-[1.1] tracking-tight mb-6">
          <span className="text-white">Все возможности —</span>
          <br />
          <span className="gradient-heading">в одном запросе</span>
        </h1>

        <p className="text-lg text-zinc-400 max-w-xl mx-auto mb-10 leading-relaxed">
          Просто напиши что ищёшь — Lumo найдёт за 10 секунд. Гранты, стажировки, конкурсы и
          хакатоны со всего интернета.
        </p>

        <div className="flex flex-wrap items-center justify-center gap-4">
          <Link
            to="/app?signup=1"
            className="inline-flex items-center gap-2 px-8 py-3.5 rounded-full bg-white text-black font-semibold text-base hover:bg-zinc-100 transition-all shadow-[0_0_40px_rgba(56,189,248,0.15)]"
          >
            Попробовать бесплатно
            <ArrowRight size={18} />
          </Link>
          <a
            href="#features"
            className="inline-flex items-center px-8 py-3.5 rounded-full border border-zinc-700 bg-zinc-900/80 text-white font-semibold text-base hover:bg-zinc-800 transition-colors"
          >
            Как это работает
          </a>
        </div>
      </div>
    </section>
  );
}

function FeaturesSection() {
  return (
    <section id="features" className="px-5 py-24 md:py-32">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold text-white mb-4 tracking-tight">
            Как работает твой персональный скаут
          </h2>
          <p className="text-zinc-400 text-lg max-w-2xl mx-auto">
            Больше не нужно скроллить десятки каналов и бояться пропустить дедлайн.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-5">
          {FEATURES.map(({ icon: Icon, iconClass, title, text }) => (
            <div
              key={title}
              className="p-7 rounded-2xl border border-zinc-800 bg-zinc-900/40 hover:border-sky-500/20 transition-colors"
            >
              <div
                className={`w-10 h-10 mb-5 rounded-xl ${iconClass} flex items-center justify-center`}
              >
                <Icon size={20} className="text-white" strokeWidth={2} />
              </div>
              <h3 className="text-lg font-semibold text-white mb-3">{title}</h3>
              <p className="text-zinc-400 text-sm leading-relaxed">{text}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function SocialProofSection() {
  const items = [...TOPICS, ...TOPICS];

  return (
    <section className="px-5 py-24 md:py-32 border-t border-zinc-900">
      <div className="max-w-4xl mx-auto text-center">
        <h2 className="text-3xl md:text-4xl font-bold text-white mb-4 tracking-tight">
          150+ студентов уже в Lumo
        </h2>
        <p className="text-zinc-400 text-lg mb-12">
          Школьники и студенты, которые больше не пропускают возможности.
        </p>

        <div className="overflow-hidden relative">
          <div className="absolute left-0 top-0 bottom-0 w-16 bg-gradient-to-r from-[#07080c] to-transparent z-10 pointer-events-none" />
          <div className="absolute right-0 top-0 bottom-0 w-16 bg-gradient-to-l from-[#07080c] to-transparent z-10 pointer-events-none" />
          <div className="marquee-track flex w-max gap-4 items-center">
            {items.map((topic, i) => (
              <span
                key={`${topic}-${i}`}
                className="shrink-0 px-5 py-2 rounded-full border border-zinc-800 bg-zinc-900/50 text-sm text-zinc-500"
              >
                {topic}
              </span>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function PricingSection() {
  const plans = LUMO_PRICING_PLANS.map((plan) => ({ ...plan, href: '/app?signup=1' }));

  return (
    <section id="pricing" className="border-t border-zinc-900">
      <Pricing
        variant="dark"
        plans={plans}
        title="Тарифы Lumo"
        description={'Начни бесплатно с 3 запросами.\nПереходи на платный план, когда нужно больше.'}
      />
    </section>
  );
}

function ContestCard({ category, title, deadline, prize }) {
  return (
    <div className="p-5 rounded-xl border border-zinc-800 bg-zinc-900/60">
      <p className="text-[11px] font-semibold uppercase tracking-wider text-sky-400 mb-3">
        {category}
      </p>
      <h3 className="text-base font-semibold text-white mb-4 leading-snug">{title}</h3>
      <div className="space-y-1.5 text-sm">
        <p>
          <span className="text-zinc-500">Дедлайн: </span>
          <span className="text-zinc-300">{deadline}</span>
        </p>
        <p>
          <span className="text-zinc-500">Приз: </span>
          <span className="text-zinc-300">{prize}</span>
        </p>
      </div>
    </div>
  );
}

function ContestsSection() {
  return (
    <section id="contests" className="px-5 py-24 md:py-32 relative">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-14">
          <h2 className="text-3xl md:text-4xl font-bold text-white mb-4 tracking-tight">
            Скрытые возможности
          </h2>
          <p className="text-zinc-400 text-lg">
            Сотни конкурсов проходят мимо, пока ты скроллишь ленту.
          </p>
        </div>

        <div className="relative">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 contests-fade">
            {CONTESTS.map((c) => (
              <ContestCard key={c.title} {...c} />
            ))}
          </div>

          <div className="absolute inset-x-0 bottom-0 h-2/3 flex flex-col items-center justify-end pb-8 bg-gradient-to-t from-[#07080c] via-[#07080c]/80 to-transparent pointer-events-none">
            <p className="text-xl font-bold text-white mb-5 pointer-events-auto">
              И ещё 1000+ актуальных конкурсов
            </p>
            <Link
              to="/app?signup=1"
              className="pointer-events-auto inline-flex items-center gap-2 px-8 py-3.5 rounded-full gradient-btn text-white font-semibold transition-all shadow-[0_0_30px_rgba(56,189,248,0.25)] hover:shadow-[0_0_40px_rgba(56,189,248,0.35)]"
            >
              Найди конкурсы для себя
              <ArrowRight size={18} />
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}

function FaqItem({ q, a, open, onToggle }) {
  return (
    <div className="border-b border-zinc-800">
      <button
        type="button"
        onClick={onToggle}
        className="w-full flex items-center justify-between gap-4 py-6 text-left group"
      >
        <span className="text-base md:text-lg text-white font-medium group-hover:text-zinc-200 transition-colors">
          {q}
        </span>
        <ChevronDown
          size={20}
          className={`text-zinc-500 shrink-0 transition-transform duration-300 ${open ? 'rotate-180' : ''}`}
        />
      </button>
      <div className={`faq-answer ${open ? 'open' : ''}`}>
        <div>
          <p className="pb-6 text-zinc-400 text-sm leading-relaxed">{a}</p>
        </div>
      </div>
    </div>
  );
}

function FaqSection() {
  const [openIndex, setOpenIndex] = useState(null);

  return (
    <section id="faq" className="px-5 py-24 md:py-32">
      <div className="max-w-2xl mx-auto">
        <h2 className="text-3xl md:text-4xl font-bold text-white text-center mb-12 tracking-tight">
          Частые вопросы
        </h2>
        <div>
          {FAQ.map((item, i) => (
            <FaqItem
              key={item.q}
              {...item}
              open={openIndex === i}
              onToggle={() => setOpenIndex(openIndex === i ? null : i)}
            />
          ))}
        </div>
      </div>
    </section>
  );
}

function FinalCtaSection() {
  return (
    <section className="relative px-5 py-28 md:py-36 overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-b from-sky-950/30 via-[#07080c] to-[#07080c] pointer-events-none" />
      <div className="absolute inset-0 cta-glow pointer-events-none" />

      <div className="relative max-w-2xl mx-auto text-center">
        <h2 className="text-3xl md:text-5xl font-bold text-white mb-5 tracking-tight leading-tight">
          Хватит упускать шансы
        </h2>
        <p className="text-zinc-400 text-lg mb-10 leading-relaxed">
          Присоединяйся к 150+ студентам, которые уже находят лучшие гранты и конкурсы первыми.
        </p>
        <Link
          to="/app?signup=1"
          className="inline-flex items-center px-10 py-4 rounded-full bg-white text-black font-semibold text-lg hover:bg-zinc-100 transition-all shadow-[0_0_50px_rgba(56,189,248,0.2)]"
        >
          Попробовать Lumo
        </Link>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="px-5 py-12 border-t border-zinc-900">
      <div className="max-w-6xl mx-auto text-center">
        <div className="flex justify-center mb-4">
          <LumoLogo theme="dark" />
        </div>
        <p className="text-zinc-500 text-sm mb-8 max-w-md mx-auto leading-relaxed">
          Твой ИИ-скаут для грантов и конкурсов. Всегда на связи.
        </p>
        <div className="flex flex-wrap items-center justify-center gap-6 text-sm text-zinc-500">
          <a href="#" className="hover:text-zinc-300 transition-colors">
            Пользовательское соглашение
          </a>
          <a href="#" className="hover:text-zinc-300 transition-colors">
            Политика конфиденциальности
          </a>
          <a href={BOT_URL} target="_blank" rel="noreferrer" className="hover:text-zinc-300 transition-colors">
            Контакты
          </a>
        </div>
      </div>
    </footer>
  );
}

export default function Landing() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <div className="min-h-screen bg-[#07080c] text-white overflow-x-hidden">
      <Navbar scrolled={scrolled} />
      <HeroSection />
      <FeaturesSection />
      <SocialProofSection />
      <TestimonialsSection />
      <PricingSection />
      <ContestsSection />
      <FaqSection />
      <FinalCtaSection />
      <Footer />
    </div>
  );
}
