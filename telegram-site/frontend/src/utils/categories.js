export const TYPE_STYLES = {
  грант: { bg: 'var(--lumo-tag-grant-bg)', text: 'var(--lumo-tag-grant-text)', label: 'Грант' },
  стипендия: { bg: 'var(--lumo-tag-scholar-bg)', text: 'var(--lumo-tag-scholar-text)', label: 'Стипендия' },
  хакатон: { bg: 'var(--lumo-tag-hack-bg)', text: 'var(--lumo-tag-hack-text)', label: 'Хакатон' },
  стажировка: { bg: 'var(--lumo-tag-intern-bg)', text: 'var(--lumo-tag-intern-text)', label: 'Стажировка' },
  конкурс: { bg: 'var(--lumo-tag-contest-bg)', text: 'var(--lumo-tag-contest-text)', label: 'Конкурс' },
  мероприятие: { bg: 'var(--lumo-tag-event-bg)', text: 'var(--lumo-tag-event-text)', label: 'Мероприятие' },
  зритель: { bg: 'var(--lumo-tag-audience-bg)', text: 'var(--lumo-tag-audience-text)', label: 'Зрителю' },
  другое: { bg: 'var(--lumo-tag-default-bg)', text: 'var(--lumo-tag-default-text)', label: 'Другое' },
};

export function typeStyle(type) {
  return TYPE_STYLES[type] || TYPE_STYLES.другое;
}

export function tagStyle(tag) {
  if (tag && typeof tag === 'object') {
    const base = TYPE_STYLES[tag.type];
    if (base) return { ...base, label: tag.label || base.label };
    return {
      bg: 'var(--lumo-tag-default-bg)',
      text: 'var(--lumo-tag-default-text)',
      label: tag.label || tag.type,
    };
  }
  return typeStyle(tag);
}

export function itemTags(item) {
  if (item?.tags?.length) return item.tags;
  return [{ type: item.type, label: item.label }];
}

export function typeLabel(type) {
  return TYPE_STYLES[type]?.label || type;
}
