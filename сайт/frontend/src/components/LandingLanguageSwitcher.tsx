import { LANDING_LOCALES } from '@/i18n/landingLocales';
import { useLandingLanguage } from '@/i18n/LandingLanguageContext';

export default function LandingLanguageSwitcher() {
  const { locale, setLocale } = useLandingLanguage();

  return (
    <div
      className="inline-flex items-center rounded-full border border-neutral-200 bg-neutral-50 p-0.5 text-xs font-semibold text-neutral-500"
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
              active ? 'bg-white text-neutral-900 shadow-sm' : 'hover:text-neutral-900'
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
