import { Sparkles } from 'lucide-react';
import { haptic } from '../api';

export default function AiPaywall({ meta, onOpenPriceList }) {
  const contact = meta?.supportContact || '@taton4i';

  return (
    <div className="pb-8">
      <div className="lumo-card p-6 text-center">
        <div className="flex justify-center mb-3">
          <Sparkles size={28} style={{ color: 'var(--lumo-accent)' }} />
        </div>
        <h1 className="text-[20px] font-bold mb-2">AI-поиск недоступен</h1>
        <p className="text-[14px] leading-relaxed mb-4" style={{ color: 'var(--lumo-text-muted)' }}>
          Каталог с фильтрами открыт бесплатно. Для AI-поиска оформи подписку или trial.
        </p>
        <div
          className="rounded-2xl px-4 py-3 mb-4 text-[13px] text-left"
          style={{ background: 'var(--lumo-surface-muted)' }}
        >
          <p className="font-semibold mb-1">🎁 7 дней бесплатно</p>
          <p style={{ color: 'var(--lumo-text-muted)' }}>
            Напиши <strong>{contact}</strong> — подключим trial и менторскую поддержку на подачу.
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            haptic('medium');
            onOpenPriceList?.('subscription');
          }}
          className="w-full py-3.5 rounded-2xl text-[15px] font-bold text-white lumo-send-btn mb-2"
        >
          Подключить 7 дней бесплатно
        </button>
        <p className="text-[12px]" style={{ color: 'var(--lumo-text-muted)' }}>
          Или выбери тариф во вкладке <strong>Price</strong>
        </p>
      </div>
    </div>
  );
}
