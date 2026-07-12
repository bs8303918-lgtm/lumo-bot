import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

import {
  LANDING_COPY,
  detectLandingLocale,
  type LandingCopy,
  type LandingLocale,
} from './landingLocales';

const STORAGE_KEY = 'lumo-landing-locale';

type LandingLanguageContextValue = {
  locale: LandingLocale;
  setLocale: (locale: LandingLocale) => void;
  t: LandingCopy;
};

const LandingLanguageContext = createContext<LandingLanguageContextValue | null>(null);

export function LandingLanguageProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<LandingLocale>(() => detectLandingLocale());

  const setLocale = useCallback((next: LandingLocale) => {
    setLocaleState(next);
    localStorage.setItem(STORAGE_KEY, next);
  }, []);

  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  const value = useMemo(
    () => ({
      locale,
      setLocale,
      t: LANDING_COPY[locale],
    }),
    [locale, setLocale],
  );

  return (
    <LandingLanguageContext.Provider value={value}>{children}</LandingLanguageContext.Provider>
  );
}

export function useLandingLanguage() {
  const ctx = useContext(LandingLanguageContext);
  if (!ctx) {
    throw new Error('useLandingLanguage must be used within LandingLanguageProvider');
  }
  return ctx;
}
