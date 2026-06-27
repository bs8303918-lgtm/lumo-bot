export function formatPriceKzt(kzt) {
  if (!kzt) return 'Бесплатно';
  return `${kzt.toLocaleString('ru-RU')} ₸`;
}

/** Запасной прайс — если Railway ещё без /lumo/subscription-plans */
export const FALLBACK_PLANS = [
  {
    id: 'plan_1m',
    label: '1 месяц',
    priceKzt: 990,
    description: 'Без лимита AI-поиска',
    benefit: null,
  },
  {
    id: 'plan_3m',
    label: '3 месяца',
    priceKzt: 4990,
    description: 'Без лимита AI-поиска',
    benefit: null,
  },
  {
    id: 'plan_6m',
    label: '6 месяцев',
    priceKzt: 7990,
    description: 'Тариф «Старт»',
    benefit: 'Экономия 1 990 ₸',
    featured: true,
  },
  {
    id: 'plan_12m',
    label: '12 месяцев',
    priceKzt: 11880,
    description: 'Лучшая цена за год',
    benefit: '990 ₸/мес',
  },
  {
    id: 'unlimited',
    label: 'Безлимит',
    priceKzt: 49000,
    description: 'Разовая покупка навсегда',
    benefit: 'Навсегда',
  },
];

export function resolvePlans(plans) {
  if (Array.isArray(plans) && plans.length > 0) return plans;
  return FALLBACK_PLANS;
}
