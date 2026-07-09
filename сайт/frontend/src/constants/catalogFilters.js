export const CATALOG_SORT_OPTIONS = [
  { id: 'newest', label: 'Сначала новые' },
  { id: 'deadline', label: 'По дедлайну' },
];

export const CATALOG_PRIZE_OPTIONS = [
  { id: 'any', label: 'Все' },
  { id: 'yes', label: 'С денежным призом' },
  { id: 'no', label: 'Без денежного приза' },
];

export const DEFAULT_CATALOG_FILTERS = {
  types: [],
  sort: 'newest',
  cashPrize: 'any',
};

export const CATALOG_TYPE_LABELS = {
  грант: 'Грант',
  стипендия: 'Стипендия',
  хакатон: 'Хакатон',
  стажировка: 'Стажировка',
  конкурс: 'Конкурс',
  олимпиада: 'Олимпиада',
  эссе: 'Конкурс эссе',
  кейс: 'Кейс-чемпионат',
  летняя_школа: 'Летняя школа',
  курс: 'Курс',
  мероприятие: 'Мероприятие',
  зритель: 'Зрителю',
};

export function buildCatalogQuery({ query, types, sort, cashPrize, pageSize, offset }) {
  const params = new URLSearchParams();
  if (query?.trim()) params.set('q', query.trim());
  if (types?.length) params.set('types', types.join(','));
  if (sort) params.set('sort', sort);
  if (cashPrize && cashPrize !== 'any') params.set('cash_prize', cashPrize);
  params.set('page_size', String(pageSize ?? 24));
  if (offset) params.set('offset', String(offset));
  return params.toString();
}
