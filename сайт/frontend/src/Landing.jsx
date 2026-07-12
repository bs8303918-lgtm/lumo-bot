import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Bell, ChevronDown, Globe, Zap } from 'lucide-react';
import LumoLogo, { LumoMark } from './components/LumoLogo.jsx';
import LandingLanguageSwitcher from './components/LandingLanguageSwitcher';
import { TestimonialsSection } from './components/TestimonialsSection';
import { Pricing } from '@/components/ui/pricing';
import { LandingLanguageProvider, useLandingLanguage } from '@/i18n/LandingLanguageContext';

const BOT_URL = 'https://t.me/LumoAI1bot';

const FEATURE_ICONS = [Zap, Globe, Bell];
const FEATURE_ICON_CLASSES = ['gradient-btn', 'bg-sky-600', 'bg-blue-700'];

const FLOATING_MARKS = [
  { top: '22%', left: '10%', size: 28, rot: '-8deg', delay: '0s', opacity: 0.2 },
  { top: '58%', left: '7%', size: 36, rot: '6deg', delay: '-2s', opacity: 0.15 },
  { top: '30%', right: '11%', size: 32, rot: '10deg', delay: '-1s', opacity: 0.18 },
  { top: '62%', right: '8%', size: 24, rot: '-5deg', delay: '-3s', opacity: 0.12 },
];

function Navbar({ scrolled }) {
  const { t } = useLandingLanguage();

  return (
    <header
      className={`fixed top-0 inset-x-0 z-50 transition-all duration-300 ${
        scrolled ? 'bg-[#07080c]/85 backdrop-blur-xl border-b border-white/5' : 'bg-transparent'
      }`}
    >
      <div className="max-w-6xl mx-auto px-5 h-16 flex items-center justify-between gap-3">
        <LumoLogo theme="dark" />

        <nav className="hidden md:flex items-center gap-8 text-sm text-zinc-400">
          <a href="#features" className="hover:text-white transition-colors">
            {t.nav.features}
          </a>
          <a href="#contests" className="hover:text-white transition-colors">
            {t.nav.contests}
          </a>
          <a href="#pricing" className="hover:text-white transition-colors">
            {t.nav.pricing}
          </a>
        </nav>

        <div className="flex items-center gap-2 sm:gap-3">
          <LandingLanguageSwitcher />
          <Link
            to="/app?signup=1"
            className="inline-flex items-center px-4 sm:px-5 py-2 rounded-full bg-white text-black text-sm font-semibold hover:bg-zinc-100 transition-colors"
          >
            {t.nav.try}
          </Link>
        </div>
      </div>
    </header>
  );
}

function HeroSection() {
  const { t } = useLandingLanguage();

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
          {t.hero.badge}
        </div>

        <h1 className="text-[clamp(2.25rem,5.5vw,4rem)] font-bold leading-[1.1] tracking-tight mb-6">
          <span className="text-white">{t.hero.titleLine1}</span>
          <br />
          <span className="gradient-heading">{t.hero.titleLine2}</span>
        </h1>

        <p className="text-lg text-zinc-400 max-w-xl mx-auto mb-10 leading-relaxed">{t.hero.subtitle}</p>

        <div className="flex flex-wrap items-center justify-center gap-4">
          <Link
            to="/app?signup=1"
            className="inline-flex items-center gap-2 px-8 py-3.5 rounded-full bg-white text-black font-semibold text-base hover:bg-zinc-100 transition-all shadow-[0_0_40px_rgba(56,189,248,0.15)]"
          >
            {t.hero.ctaPrimary}
            <ArrowRight size={18} />
          </Link>
          <a
            href="#features"
            className="inline-flex items-center px-8 py-3.5 rounded-full border border-zinc-700 bg-zinc-900/80 text-white font-semibold text-base hover:bg-zinc-800 transition-colors"
          >
            {t.hero.ctaSecondary}
          </a>
        </div>
      </div>
    </section>
  );
}

function FeaturesSection() {
  const { t } = useLandingLanguage();

  return (
    <section id="features" className="px-5 py-24 md:py-32">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold text-white mb-4 tracking-tight">{t.features.title}</h2>
          <p className="text-zinc-400 text-lg max-w-2xl mx-auto">{t.features.subtitle}</p>
        </div>

        <div className="grid md:grid-cols-3 gap-5">
          {t.features.items.map(({ title, text }, index) => {
            const Icon = FEATURE_ICONS[index];
            const iconClass = FEATURE_ICON_CLASSES[index];
            return (
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
            );
          })}
        </div>
      </div>
    </section>
  );
}

function SocialProofSection() {
  const { t } = useLandingLanguage();
  const items = [...t.social.topics, ...t.social.topics];

  return (
    <section className="px-5 py-24 md:py-32 border-t border-zinc-900">
      <div className="max-w-4xl mx-auto text-center">
        <h2 className="text-3xl md:text-4xl font-bold text-white mb-4 tracking-tight">{t.social.title}</h2>
        <p className="text-zinc-400 text-lg mb-12">{t.social.subtitle}</p>

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
  const { t } = useLandingLanguage();

  return (
    <section id="pricing" className="border-t border-zinc-900">
      <Pricing
        variant="dark"
        plans={t.pricing.plans.map((plan) => ({ ...plan }))}
        title={t.pricing.title}
        description={t.pricing.description}
      />
    </section>
  );
}

function ContestCard({ category, title, deadline, prize, labels }) {
  return (
    <div className="p-5 rounded-xl border border-zinc-800 bg-zinc-900/60">
      <p className="text-[11px] font-semibold uppercase tracking-wider text-sky-400 mb-3">{category}</p>
      <h3 className="text-base font-semibold text-white mb-4 leading-snug">{title}</h3>
      <div className="space-y-1.5 text-sm">
        <p>
          <span className="text-zinc-500">{labels.deadline} </span>
          <span className="text-zinc-300">{deadline}</span>
        </p>
        <p>
          <span className="text-zinc-500">{labels.prize} </span>
          <span className="text-zinc-300">{prize}</span>
        </p>
      </div>
    </div>
  );
}

function ContestsSection() {
  const { t } = useLandingLanguage();

  return (
    <section id="contests" className="px-5 py-24 md:py-32 relative">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-14">
          <h2 className="text-3xl md:text-4xl font-bold text-white mb-4 tracking-tight">{t.contests.title}</h2>
          <p className="text-zinc-400 text-lg">{t.contests.subtitle}</p>
        </div>

        <div className="relative">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 contests-fade">
            {t.contests.items.map((c) => (
              <ContestCard
                key={c.title}
                {...c}
                labels={{ deadline: t.contests.deadline, prize: t.contests.prize }}
              />
            ))}
          </div>

          <div className="absolute inset-x-0 bottom-0 h-2/3 flex flex-col items-center justify-end pb-8 bg-gradient-to-t from-[#07080c] via-[#07080c]/80 to-transparent pointer-events-none">
            <p className="text-xl font-bold text-white mb-5 pointer-events-auto">{t.contests.more}</p>
            <Link
              to="/app?signup=1"
              className="pointer-events-auto inline-flex items-center gap-2 px-8 py-3.5 rounded-full gradient-btn text-white font-semibold transition-all shadow-[0_0_30px_rgba(56,189,248,0.25)] hover:shadow-[0_0_40px_rgba(56,189,248,0.35)]"
            >
              {t.contests.cta}
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
  const { t } = useLandingLanguage();

  return (
    <section id="faq" className="px-5 py-24 md:py-32">
      <div className="max-w-2xl mx-auto">
        <h2 className="text-3xl md:text-4xl font-bold text-white text-center mb-12 tracking-tight">
          {t.faq.title}
        </h2>
        <div>
          {t.faq.items.map((item, i) => (
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
  const { t } = useLandingLanguage();

  return (
    <section className="relative px-5 py-28 md:py-36 overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-b from-sky-950/30 via-[#07080c] to-[#07080c] pointer-events-none" />
      <div className="absolute inset-0 cta-glow pointer-events-none" />

      <div className="relative max-w-2xl mx-auto text-center">
        <h2 className="text-3xl md:text-5xl font-bold text-white mb-5 tracking-tight leading-tight">
          {t.finalCta.title}
        </h2>
        <p className="text-zinc-400 text-lg mb-10 leading-relaxed">{t.finalCta.subtitle}</p>
        <Link
          to="/app?signup=1"
          className="inline-flex items-center px-10 py-4 rounded-full bg-white text-black font-semibold text-lg hover:bg-zinc-100 transition-all shadow-[0_0_50px_rgba(56,189,248,0.2)]"
        >
          {t.finalCta.button}
        </Link>
      </div>
    </section>
  );
}

function Footer() {
  const { t } = useLandingLanguage();

  return (
    <footer className="px-5 py-12 border-t border-zinc-900">
      <div className="max-w-6xl mx-auto text-center">
        <div className="flex justify-center mb-4">
          <LumoLogo theme="dark" />
        </div>
        <p className="text-zinc-500 text-sm mb-8 max-w-md mx-auto leading-relaxed">{t.footer.tagline}</p>
        <div className="flex flex-wrap items-center justify-center gap-6 text-sm text-zinc-500">
          <a href="#" className="hover:text-zinc-300 transition-colors">
            {t.footer.terms}
          </a>
          <a href="#" className="hover:text-zinc-300 transition-colors">
            {t.footer.privacy}
          </a>
          <a href={BOT_URL} target="_blank" rel="noreferrer" className="hover:text-zinc-300 transition-colors">
            {t.footer.contacts}
          </a>
        </div>
      </div>
    </footer>
  );
}

function LandingPage() {
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

export default function Landing() {
  return (
    <LandingLanguageProvider>
      <LandingPage />
    </LandingLanguageProvider>
  );
}
