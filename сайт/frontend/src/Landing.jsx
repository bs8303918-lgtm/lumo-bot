import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Bell, ChevronDown, Globe, Zap } from 'lucide-react';
import LumoLogo from './components/LumoLogo.jsx';
import LandingLanguageSwitcher from './components/LandingLanguageSwitcher';
import { TestimonialsSection } from './components/TestimonialsSection';
import { Pricing } from '@/components/ui/pricing';
import { LandingLanguageProvider, useLandingLanguage } from '@/i18n/LandingLanguageContext';

const BOT_URL = 'https://t.me/LumoAI1bot';

const FEATURE_ICONS = [Zap, Globe, Bell];

function Navbar({ scrolled }) {
  const { t } = useLandingLanguage();

  return (
    <div className="fixed top-0 inset-x-0 z-50 px-4 sm:px-6 pt-4">
      <header
        className={`max-w-5xl mx-auto h-14 px-4 sm:px-6 flex items-center justify-between gap-3 rounded-2xl border transition-all duration-300 ${
          scrolled
            ? 'bg-white/95 backdrop-blur-xl border-neutral-200 shadow-lg shadow-black/[0.06]'
            : 'bg-white/90 backdrop-blur-md border-neutral-200/80 shadow-md shadow-black/[0.04]'
        }`}
      >
        <LumoLogo theme="light" />

        <nav className="hidden md:flex items-center gap-8 text-sm text-neutral-500">
          <a href="#features" className="hover:text-neutral-900 transition-colors">
            {t.nav.features}
          </a>
          <a href="#contests" className="hover:text-neutral-900 transition-colors">
            {t.nav.contests}
          </a>
          <a href="#pricing" className="hover:text-neutral-900 transition-colors">
            {t.nav.pricing}
          </a>
        </nav>

        <div className="flex items-center gap-2 sm:gap-3">
          <LandingLanguageSwitcher />
          <Link
            to="/app"
            className="hidden sm:inline text-sm text-neutral-600 hover:text-neutral-900 transition-colors"
          >
            Log in
          </Link>
          <Link
            to="/app?signup=1"
            className="inline-flex items-center px-4 sm:px-5 py-2 rounded-full bg-neutral-900 text-white text-sm font-semibold hover:bg-neutral-800 transition-colors"
          >
            {t.nav.try}
          </Link>
        </div>
      </header>
    </div>
  );
}

function HeroSection() {
  const { t } = useLandingLanguage();

  return (
    <section className="relative min-h-[92vh] flex items-center justify-center pt-28 pb-24 px-5">
      <div className="absolute inset-0 landing-hero-glow pointer-events-none" aria-hidden />

      <div className="relative max-w-3xl mx-auto text-center">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 mb-8 rounded-full border border-neutral-200 bg-neutral-50 text-neutral-600 text-sm">
          <span className="w-1.5 h-1.5 rounded-full bg-neutral-900" />
          {t.hero.badge}
        </div>

        <h1 className="text-[clamp(2.5rem,6vw,4.25rem)] font-bold leading-[1.08] tracking-tight mb-6 text-neutral-900">
          {t.hero.titleLine1}
          <br />
          <span className="text-neutral-900">{t.hero.titleLine2}</span>
        </h1>

        <p className="text-lg text-neutral-500 max-w-xl mx-auto mb-10 leading-relaxed">{t.hero.subtitle}</p>

        <div className="flex flex-wrap items-center justify-center gap-3">
          <Link
            to="/app?signup=1"
            className="inline-flex items-center gap-2 px-8 py-3.5 rounded-full border border-neutral-200 bg-white text-neutral-900 font-semibold text-base hover:bg-neutral-50 transition-colors shadow-sm"
          >
            {t.hero.ctaPrimary}
          </Link>
          <Link
            to="/app?signup=1"
            className="inline-flex items-center gap-2 px-8 py-3.5 rounded-full bg-neutral-900 text-white font-semibold text-base hover:bg-neutral-800 transition-colors"
          >
            {t.nav.try}
            <ArrowRight size={18} />
          </Link>
        </div>
      </div>
    </section>
  );
}

function FeaturesSection() {
  const { t } = useLandingLanguage();

  return (
    <section id="features" className="px-5 py-24 md:py-32 bg-neutral-50/60">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold text-neutral-900 mb-4 tracking-tight">{t.features.title}</h2>
          <p className="text-neutral-500 text-lg max-w-2xl mx-auto">{t.features.subtitle}</p>
        </div>

        <div className="grid md:grid-cols-3 gap-5">
          {t.features.items.map(({ title, text }, index) => {
            const Icon = FEATURE_ICONS[index];
            return (
              <div
                key={title}
                className="p-7 rounded-2xl border border-neutral-200 bg-white hover:border-neutral-300 hover:shadow-md hover:shadow-black/[0.04] transition-all"
              >
                <div className="w-10 h-10 mb-5 rounded-xl bg-neutral-900 flex items-center justify-center">
                  <Icon size={20} className="text-white" strokeWidth={2} />
                </div>
                <h3 className="text-lg font-semibold text-neutral-900 mb-3">{title}</h3>
                <p className="text-neutral-500 text-sm leading-relaxed">{text}</p>
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
    <section className="px-5 py-24 md:py-32 border-t border-neutral-200">
      <div className="max-w-4xl mx-auto text-center">
        <h2 className="text-3xl md:text-4xl font-bold text-neutral-900 mb-4 tracking-tight">{t.social.title}</h2>
        <p className="text-neutral-500 text-lg mb-12">{t.social.subtitle}</p>

        <div className="overflow-hidden relative">
          <div className="absolute left-0 top-0 bottom-0 w-16 bg-gradient-to-r from-white to-transparent z-10 pointer-events-none" />
          <div className="absolute right-0 top-0 bottom-0 w-16 bg-gradient-to-l from-white to-transparent z-10 pointer-events-none" />
          <div className="marquee-track flex w-max gap-4 items-center">
            {items.map((topic, i) => (
              <span
                key={`${topic}-${i}`}
                className="shrink-0 px-5 py-2 rounded-full border border-neutral-200 bg-neutral-50 text-sm text-neutral-600"
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
    <section id="pricing" className="border-t border-neutral-200 bg-white">
      <Pricing
        variant="light"
        plans={t.pricing.plans.map((plan) => ({ ...plan }))}
        title={t.pricing.title}
        description={t.pricing.description}
      />
    </section>
  );
}

function ContestCard({ category, title, deadline, prize, labels }) {
  return (
    <div className="p-5 rounded-xl border border-neutral-200 bg-white shadow-sm">
      <p className="text-[11px] font-semibold uppercase tracking-wider text-neutral-500 mb-3">{category}</p>
      <h3 className="text-base font-semibold text-neutral-900 mb-4 leading-snug">{title}</h3>
      <div className="space-y-1.5 text-sm">
        <p>
          <span className="text-neutral-400">{labels.deadline} </span>
          <span className="text-neutral-700">{deadline}</span>
        </p>
        <p>
          <span className="text-neutral-400">{labels.prize} </span>
          <span className="text-neutral-700">{prize}</span>
        </p>
      </div>
    </div>
  );
}

function ContestsSection() {
  const { t } = useLandingLanguage();

  return (
    <section id="contests" className="px-5 py-24 md:py-32 relative bg-neutral-50/40">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-14">
          <h2 className="text-3xl md:text-4xl font-bold text-neutral-900 mb-4 tracking-tight">{t.contests.title}</h2>
          <p className="text-neutral-500 text-lg">{t.contests.subtitle}</p>
        </div>

        <div className="relative">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 contests-fade-light">
            {t.contests.items.map((c) => (
              <ContestCard
                key={c.title}
                {...c}
                labels={{ deadline: t.contests.deadline, prize: t.contests.prize }}
              />
            ))}
          </div>

          <div className="absolute inset-x-0 bottom-0 h-2/3 flex flex-col items-center justify-end pb-8 bg-gradient-to-t from-neutral-50 via-neutral-50/90 to-transparent pointer-events-none">
            <p className="text-xl font-bold text-neutral-900 mb-5 pointer-events-auto">{t.contests.more}</p>
            <Link
              to="/app?signup=1"
              className="pointer-events-auto inline-flex items-center gap-2 px-8 py-3.5 rounded-full bg-neutral-900 text-white font-semibold transition-all hover:bg-neutral-800 shadow-lg shadow-black/10"
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
    <div className="border-b border-neutral-200">
      <button
        type="button"
        onClick={onToggle}
        className="w-full flex items-center justify-between gap-4 py-6 text-left group"
      >
        <span className="text-base md:text-lg text-neutral-900 font-medium group-hover:text-neutral-700 transition-colors">
          {q}
        </span>
        <ChevronDown
          size={20}
          className={`text-neutral-400 shrink-0 transition-transform duration-300 ${open ? 'rotate-180' : ''}`}
        />
      </button>
      <div className={`faq-answer ${open ? 'open' : ''}`}>
        <div>
          <p className="pb-6 text-neutral-500 text-sm leading-relaxed">{a}</p>
        </div>
      </div>
    </div>
  );
}

function FaqSection() {
  const [openIndex, setOpenIndex] = useState(null);
  const { t } = useLandingLanguage();

  return (
    <section id="faq" className="px-5 py-24 md:py-32 bg-white">
      <div className="max-w-2xl mx-auto">
        <h2 className="text-3xl md:text-4xl font-bold text-neutral-900 text-center mb-12 tracking-tight">
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
    <section className="relative px-5 py-28 md:py-36 overflow-hidden bg-neutral-50 border-t border-neutral-200">
      <div className="relative max-w-2xl mx-auto text-center">
        <h2 className="text-3xl md:text-5xl font-bold text-neutral-900 mb-5 tracking-tight leading-tight">
          {t.finalCta.title}
        </h2>
        <p className="text-neutral-500 text-lg mb-10 leading-relaxed">{t.finalCta.subtitle}</p>
        <Link
          to="/app?signup=1"
          className="inline-flex items-center px-10 py-4 rounded-full bg-neutral-900 text-white font-semibold text-lg hover:bg-neutral-800 transition-all shadow-lg shadow-black/10"
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
    <footer className="px-5 py-12 border-t border-neutral-200 bg-white">
      <div className="max-w-6xl mx-auto text-center">
        <div className="flex justify-center mb-4">
          <LumoLogo theme="light" />
        </div>
        <p className="text-neutral-500 text-sm mb-8 max-w-md mx-auto leading-relaxed">{t.footer.tagline}</p>
        <div className="flex flex-wrap items-center justify-center gap-6 text-sm text-neutral-500">
          <a href="#" className="hover:text-neutral-900 transition-colors">
            {t.footer.terms}
          </a>
          <a href="#" className="hover:text-neutral-900 transition-colors">
            {t.footer.privacy}
          </a>
          <a href={BOT_URL} target="_blank" rel="noreferrer" className="hover:text-neutral-900 transition-colors">
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
    <div className="min-h-screen bg-white text-neutral-900 overflow-x-hidden">
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
