import { LANDING_LOCALES } from '@/i18n/landingLocales';
import { useLandingLanguage } from '@/i18n/LandingLanguageContext';

export default function LandingLanguageSwitcher() {
  const { locale, setLocale } = useLandingLanguage();

  return (
    <div
      className="inline-flex items-center rounded-full border border-zinc-700 bg-zinc-900/80 p-0.5 text-xs font-semibold"
      role="group"
      aria-label="Language"
    >
      {LANDING_LOCALES.map(({ id, label }) => {
        const active = locale === id;
        return (
          <button
            key={id}
            type="button"
            onClick={() => setLocale(id)}
            className={`px-2.5 py-1 rounded-full transition-colors ${
              active ? 'bg-white text-black' : 'text-zinc-400 hover:text-white'
            }`}
            aria-pressed={active}
          >
            {label}
          </button>
        );
      })}
    </div>
  );
}
