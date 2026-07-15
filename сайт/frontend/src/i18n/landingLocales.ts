export type LandingLocale = 'ru' | 'en';

export const LANDING_LOCALES: { id: LandingLocale; label: string }[] = [
  { id: 'ru', label: 'RU' },
  { id: 'en', label: 'EN' },
];

export type LandingPricingPlan = {
  name: string;
  price: number;
  period: string;
  features: string[];
  description: string;
  buttonText: string;
  href: string;
  isPopular: boolean;
};

export type LandingCopy = {
  nav: { features: string; contests: string; consultation: string; try: string };
  hero: {
    badge: string;
    titleLine1: string;
    titleLine2: string;
    subtitle: string;
    ctaPrimary: string;
    ctaSecondary: string;
  };
  features: {
    title: string;
    subtitle: string;
    items: { title: string; text: string }[];
  };
  social: { title: string; subtitle: string; topics: string[] };
  testimonials: { badge: string; title: string; subtitle: string };
  consultation: {
    title: string;
    titleAccent: string;
    subtitle: string;
    namePlaceholder: string;
    contactPlaceholder: string;
    interestPlaceholder: string;
    interests: { id: string; label: string }[];
    button: string;
    success: string;
    contactHint: string;
    telegram: string;
    contactError: string;
    submitError: string;
  };
  contests: {
    title: string;
    subtitle: string;
    deadline: string;
    prize: string;
    more: string;
    cta: string;
    items: { category: string; title: string; deadline: string; prize: string }[];
  };
  faq: { title: string; items: { q: string; a: string }[] };
  footer: { tagline: string; terms: string; privacy: string; contacts: string };
};

const LANDING_PRICING_RU = [
  {
    name: 'Бесплатно',
    price: 0,
    period: 'навсегда',
    features: [
      '3 AI-запроса',
      'Базовая подборка конкурсов',
      'Доступ к каталогу возможностей',
      'Обновления базы',
    ],
    description: 'Попробуй Lumo без карты',
    buttonText: 'Начать бесплатно',
    href: '/app?signup=1',
    isPopular: false,
  },
  {
    name: 'Старт',
    price: 4990,
    period: '3 месяца',
    features: [
      'Безлимитные AI-запросы',
      'Умные алерты о дедлайнах',
      '5 своих каналов для мониторинга',
      'Приоритетная подборка',
      'Профиль интересов',
    ],
    description: 'Для активного поиска возможностей',
    buttonText: 'Выбрать Старт',
    href: '/app?signup=1',
    isPopular: true,
  },
  {
    name: 'Про',
    price: 7990,
    period: '6 месяцев',
    features: [
      'Всё из тарифа Старт',
      'Расширенный профиль',
      'Ранний доступ к новым фичам',
      'Приоритетная поддержка',
    ],
    description: 'Максимум от Lumo на полгода',
    buttonText: 'Выбрать Про',
    href: '/app?signup=1',
    isPopular: false,
  },
] satisfies LandingPricingPlan[];

const LANDING_PRICING_EN = [
  {
    name: 'Free',
    price: 0,
    period: 'forever',
    features: [
      '3 AI searches per day',
      'Basic opportunity picks',
      'Catalog access',
      'Database updates',
    ],
    description: 'Try Lumo — no card required',
    buttonText: 'Start for free',
    href: '/app?signup=1',
    isPopular: false,
  },
  {
    name: 'Start',
    price: 4990,
    period: '3 months',
    features: [
      'Unlimited AI searches',
      'Smart deadline alerts',
      '5 custom channels to monitor',
      'Priority matching',
      'Interest profile',
    ],
    description: 'For active opportunity hunting',
    buttonText: 'Choose Start',
    href: '/app?signup=1',
    isPopular: true,
  },
  {
    name: 'Pro',
    price: 7990,
    period: '6 months',
    features: [
      'Everything in Start',
      'Extended profile',
      'Early access to new features',
      'Priority support',
    ],
    description: 'Get the most from Lumo for six months',
    buttonText: 'Choose Pro',
    href: '/app?signup=1',
    isPopular: false,
  },
] satisfies LandingPricingPlan[];

export const LANDING_COPY: Record<LandingLocale, LandingCopy> = {
  ru: {
    nav: {
      features: 'Возможности',
      contests: 'База конкурсов',
      consultation: 'Консультация',
      try: 'Попробовать',
    },
    hero: {
      badge: '250+ студентов уже используют Lumo',
      titleLine1: 'Все возможности —',
      titleLine2: 'в одном запросе',
      subtitle:
        'Просто напиши что ищёшь — Lumo найдёт за 10 секунд. Гранты, стажировки, конкурсы и хакатоны со всего интернета.',
      ctaPrimary: 'Попробовать бесплатно',
      ctaSecondary: 'Как это работает',
    },
    features: {
      title: 'Как работает твой персональный скаут',
      subtitle: 'Больше не нужно скроллить десятки каналов и бояться пропустить дедлайн.',
      items: [
        {
          title: 'Ответ за 10 секунд',
          text: 'Напиши «Ищу гранты по ИИ для первокурсников» и получи подборку моментально.',
        },
        {
          title: 'Все каналы в одном',
          text: 'Telegram, VK, сайты универов и фондов — всё мониторится 24/7. Добавляй свои каналы.',
        },
        {
          title: 'Умные алерты',
          text: 'Lumo напомнит о дедлайне подачи заявки и подсветит возможности по твоему профилю.',
        },
      ],
    },
    social: {
      title: '250+ студентов уже в Lumo',
      subtitle: 'Школьники и студенты, которые больше не пропускают возможности.',
      topics: [
        'хакатоны',
        'гранты',
        'стажировки',
        'олимпиады',
        'конкурсы',
        'стипендии',
        'акселераторы',
        'форумы',
      ],
    },
    testimonials: {
      badge: 'Отзывы',
      title: 'Что говорят пользователи',
      subtitle: 'Реальные сообщения из Lumo chat.',
    },
    consultation: {
      title: 'Не обязан искать вручную —',
      titleAccent: 'разберём твой профиль',
      subtitle:
        'Запишись на бесплатную консультацию. Покажем, какие гранты, хакатоны и стажировки подходят именно тебе — и как не пропускать дедлайны.',
      namePlaceholder: 'Ваше имя',
      contactPlaceholder: 'Telegram или телефон',
      interestPlaceholder: 'Что ищешь?',
      interests: [
        { id: 'grants', label: 'Гранты и стипендии' },
        { id: 'hackathons', label: 'Хакатоны' },
        { id: 'internships', label: 'Стажировки' },
        { id: 'admission', label: 'Поступление за рубеж' },
        { id: 'other', label: 'Другое' },
      ],
      button: 'Записаться на консультацию',
      success: 'Заявка принята! Напишем в Telegram в ближайшее время.',
      contactHint: 'или напиши в Telegram',
      telegram: '@LumoAI1bot',
      contactError: 'Укажи Telegram или телефон',
      submitError: 'Не удалось отправить заявку',
    },
    contests: {
      title: 'Скрытые возможности',
      subtitle: 'Сотни конкурсов проходят мимо, пока ты скроллишь ленту.',
      deadline: 'Дедлайн:',
      prize: 'Приз:',
      more: 'И ещё 1000+ актуальных конкурсов',
      cta: 'Найди конкурсы для себя',
      items: [
        { category: 'IT & ENGINEERING', title: 'Олимпиада НТО', deadline: '15.03.2026', prize: '100 000 ₽' },
        { category: 'STARTUP', title: 'Skolkovo Student Grant', deadline: '01.04.2026', prize: '500 000 ₽' },
        { category: 'АЛГОРИТМЫ', title: 'Турнир по спортивному программированию', deadline: '20.03.2026', prize: '50 000 ₽' },
        { category: 'НАУКА', title: 'Российская научная олимпиада', deadline: '10.04.2026', prize: 'Стипендия' },
        { category: 'ДИЗАЙН', title: 'Art Masters Challenge', deadline: '25.03.2026', prize: '75 000 ₽' },
        { category: 'БИЗНЕС', title: 'Startup Weekend Moscow', deadline: '05.04.2026', prize: '300 000 ₽' },
        { category: 'IT & ENGINEERING', title: 'Yandex Cup', deadline: '18.03.2026', prize: '200 000 ₽' },
        { category: 'СТАЖИРОВКА', title: 'VK Tech Internship', deadline: '30.03.2026', prize: '80 000 ₽/мес' },
      ],
    },
    faq: {
      title: 'Частые вопросы',
      items: [
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
          a: 'Консультация и старт в боте — бесплатно. Поможем настроить профиль и покажем, как искать возможности через Lumo.',
        },
        {
          q: 'Только для айтишников?',
          a: 'Нет. Lumo находит гранты, олимпиады, стажировки и конкурсы для любых направлений — от науки и дизайна до бизнеса и спорта.',
        },
      ],
    },
    footer: {
      tagline: 'Твой ИИ-скаут для грантов и конкурсов. Всегда на связи.',
      terms: 'Пользовательское соглашение',
      privacy: 'Политика конфиденциальности',
      contacts: 'Контакты',
    },
  },
  en: {
    nav: {
      features: 'Features',
      contests: 'Opportunities',
      consultation: 'Consultation',
      try: 'Try Lumo',
    },
    hero: {
      badge: '250+ students already use Lumo',
      titleLine1: 'Every opportunity —',
      titleLine2: 'one prompt away',
      subtitle:
        'Just type what you need — Lumo finds it in 10 seconds. Grants, internships, contests, and hackathons from across the web.',
      ctaPrimary: 'Try for free',
      ctaSecondary: 'How it works',
    },
    features: {
      title: 'Your personal opportunity scout',
      subtitle: 'No more scrolling dozens of channels or missing deadlines.',
      items: [
        {
          title: 'Answers in 10 seconds',
          text: 'Type “AI grants for freshmen” and get a tailored shortlist instantly.',
        },
        {
          title: 'All channels in one place',
          text: 'Telegram, VK, university sites, and foundations — monitored 24/7. Add your own channels.',
        },
        {
          title: 'Smart alerts',
          text: 'Lumo reminds you before deadlines and highlights matches for your profile.',
        },
      ],
    },
    social: {
      title: '250+ students already in Lumo',
      subtitle: 'School and university students who no longer miss opportunities.',
      topics: [
        'hackathons',
        'grants',
        'internships',
        'olympiads',
        'contests',
        'scholarships',
        'accelerators',
        'forums',
      ],
    },
    testimonials: {
      badge: 'Testimonials',
      title: 'What users say',
      subtitle: 'Real messages from the Lumo community.',
    },
    consultation: {
      title: "You don't have to search alone —",
      titleAccent: "let's map your profile",
      subtitle:
        'Book a free consultation. We will show which grants, hackathons, and internships fit you — and how not to miss deadlines.',
      namePlaceholder: 'Your name',
      contactPlaceholder: 'Telegram or phone',
      interestPlaceholder: 'What are you looking for?',
      interests: [
        { id: 'grants', label: 'Grants & scholarships' },
        { id: 'hackathons', label: 'Hackathons' },
        { id: 'internships', label: 'Internships' },
        { id: 'admission', label: 'Study abroad' },
        { id: 'other', label: 'Other' },
      ],
      button: 'Book a consultation',
      success: 'Request received! We will message you on Telegram soon.',
      contactHint: 'or message us on Telegram',
      telegram: '@LumoAI1bot',
      contactError: 'Add Telegram or phone',
      submitError: 'Could not submit the request',
    },
    contests: {
      title: 'Hidden opportunities',
      subtitle: 'Hundreds of programs pass by while you scroll your feed.',
      deadline: 'Deadline:',
      prize: 'Prize:',
      more: 'And 1000+ more active opportunities',
      cta: 'Find programs for you',
      items: [
        { category: 'IT & ENGINEERING', title: 'NTO Olympiad', deadline: '15.03.2026', prize: '100,000 ₽' },
        { category: 'STARTUP', title: 'Skolkovo Student Grant', deadline: '01.04.2026', prize: '500,000 ₽' },
        { category: 'ALGORITHMS', title: 'Sports Programming Tournament', deadline: '20.03.2026', prize: '50,000 ₽' },
        { category: 'SCIENCE', title: 'Russian Science Olympiad', deadline: '10.04.2026', prize: 'Scholarship' },
        { category: 'DESIGN', title: 'Art Masters Challenge', deadline: '25.03.2026', prize: '75,000 ₽' },
        { category: 'BUSINESS', title: 'Startup Weekend Moscow', deadline: '05.04.2026', prize: '300,000 ₽' },
        { category: 'IT & ENGINEERING', title: 'Yandex Cup', deadline: '18.03.2026', prize: '200,000 ₽' },
        { category: 'INTERNSHIP', title: 'VK Tech Internship', deadline: '30.03.2026', prize: '80,000 ₽/mo' },
      ],
    },
    faq: {
      title: 'FAQ',
      items: [
        {
          q: 'How fast does Lumo find opportunities?',
          a: 'Lumo searches 1000+ programs and channels in about 10 seconds. Type a prompt — like ChatGPT, but for real opportunities.',
        },
        {
          q: 'Can I add my own channels to monitor?',
          a: 'Yes. Add up to 5 Telegram channels — Lumo will watch them along with the main database and send new matches.',
        },
        {
          q: 'Is it paid?',
          a: 'The consultation and getting started in the bot are free. We will help you set up your profile and show how to search with Lumo.',
        },
        {
          q: 'Is it only for IT students?',
          a: 'No. Lumo covers grants, olympiads, internships, and contests across science, design, business, sports, and more.',
        },
      ],
    },
    footer: {
      tagline: 'Your AI scout for grants and contests. Always on.',
      terms: 'Terms of use',
      privacy: 'Privacy policy',
      contacts: 'Contact',
    },
  },
};

export function resolveLandingLocale(raw: string | null | undefined): LandingLocale {
  return raw === 'en' ? 'en' : 'ru';
}

export function detectLandingLocale(): LandingLocale {
  if (typeof window === 'undefined') return 'ru';
  const stored = localStorage.getItem('lumo-landing-locale');
  if (stored) return resolveLandingLocale(stored);
  const browser = navigator.language?.toLowerCase() ?? '';
  return browser.startsWith('en') ? 'en' : 'ru';
}
