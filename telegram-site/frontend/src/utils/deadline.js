export function formatDeadlineMeta(deadline) {
  const text = (deadline || '').trim();
  if (!text || text === 'не указан' || text === '—') {
    return { label: 'Без дедлайна', urgent: false, icon: 'calendar' };
  }

  const lower = text.toLowerCase();
  if (lower.includes('ongoing') || lower.includes('открыт')) {
    return { label: text, urgent: false, icon: 'calendar' };
  }

  const daysLeftMatch = text.match(/(\d+)\s*дн/i);
  if (daysLeftMatch) {
    const days = Number(daysLeftMatch[1]);
    if (days <= 7) {
      return { label: `Осталось ${days} ${pluralDays(days)}`, urgent: true, icon: 'clock' };
    }
  }

  const dateMatch = text.match(/^(\d{1,2})[./](\d{1,2})(?:[./](\d{2,4}))?$/);
  if (dateMatch) {
    const day = Number(dateMatch[1]);
    const month = Number(dateMatch[2]) - 1;
    const year = dateMatch[3] ? Number(dateMatch[3].length === 2 ? `20${dateMatch[3]}` : dateMatch[3]) : new Date().getFullYear();
    const target = new Date(year, month, day);
    const now = new Date();
    now.setHours(0, 0, 0, 0);
    const diffDays = Math.ceil((target - now) / (1000 * 60 * 60 * 24));
    if (diffDays >= 0 && diffDays <= 7) {
      return { label: `Осталось ${diffDays} ${pluralDays(diffDays)}`, urgent: true, icon: 'clock' };
    }
    const months = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'];
    return { label: `${day} ${months[month]}`, urgent: false, icon: 'calendar' };
  }

  if (lower.includes('остал')) {
    return { label: text, urgent: true, icon: 'clock' };
  }

  return { label: text, urgent: false, icon: 'calendar' };
}

function pluralDays(n) {
  if (n % 10 === 1 && n % 100 !== 11) return 'день';
  if (n % 10 >= 2 && n % 10 <= 4 && (n % 100 < 10 || n % 100 >= 20)) return 'дня';
  return 'дней';
}

export function sourceHandle(item) {
  const link = item.messageLink || '';
  const match = link.match(/t\.me\/([^/?#]+)/i);
  if (match) return `@${match[1]}`;
  const name = (item.sourceChannelName || '').trim();
  if (name.startsWith('@')) return name;
  if (name) return `@${name.replace(/\s+/g, '_').toLowerCase().slice(0, 24)}`;
  return '';
}
