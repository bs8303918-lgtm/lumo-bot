export function formatPriceKzt(kzt) {
  if (!kzt) return 'Бесплатно';
  return `${kzt.toLocaleString('ru-RU')} ₸`;
}
