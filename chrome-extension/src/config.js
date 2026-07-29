export const API_BASE = 'https://lumo-bot-production-9903.up.railway.app';
export const API = `${API_BASE}/api`;
// Fallback if /lumo/meta hasn't loaded yet — the bot's default username in config.py.
export const DEFAULT_BOT_USERNAME = 'LumoAI1bot';

export const CHECK_ALARM_NAME = 'lumo-catalog-check';
export const CHECK_INTERVAL_MINUTES = 30;
export const NEW_CHECK_LIMIT = 30;

export const CATEGORY_DISPLAY = {
  грант: ['💰', 'Гранты'],
  стипендия: ['🎓', 'Стипендии'],
  хакатон: ['💻', 'Хакатоны'],
  стажировка: ['🏢', 'Стажировки'],
  конкурс: ['🏆', 'Конкурсы'],
  олимпиада: ['🥇', 'Олимпиады'],
  эссе: ['✍️', 'Эссе'],
  кейс: ['📋', 'Кейс-чемпионаты'],
  летняя_школа: ['☀️', 'Летние школы'],
  курс: ['📚', 'Курсы'],
  мероприятие: ['📅', 'Мероприятия'],
  зритель: ['👀', 'Зрителю'],
  другое: ['📌', 'Другое'],
};

export const FILTER_TYPES = [
  'грант',
  'стипендия',
  'хакатон',
  'стажировка',
  'конкурс',
  'олимпиада',
  'кейс',
  'летняя_школа',
];
