import { useState } from 'react';
import { Copy, Sparkles } from 'lucide-react';
import { formatPriceKzt, KASPI_PAYMENT_PHONE } from '../utils/pricing';
import { getTelegram, haptic } from '../api';

export default function PlanCards({ plans, compact = false, selectedId, onSelect }) {
  return (
    <div className={compact ? 'space-y-2' : 'space-y-3'}>
      {plans.map((plan) => {
        const featured = plan.featured || plan.id === 'plan_6m';
        const selected = selectedId === plan.id;
        return (
          <button
            key={plan.id}
            type="button"
            onClick={() => {
              haptic('light');
              onSelect?.(plan);
            }}
            className="lumo-card relative overflow-hidden w-full text-left transition active:scale-[0.99]"
            style={
              selected
                ? {
                    borderColor: 'var(--lumo-accent)',
                    boxShadow: '0 0 0 2px color-mix(in srgb, var(--lumo-accent) 45%, transparent)',
                  }
                : featured
                  ? {
                      borderColor: 'var(--lumo-accent)',
                      boxShadow: '0 0 0 1px color-mix(in srgb, var(--lumo-accent) 35%, transparent)',
                    }
                  : undefined
            }
          >
            {featured && (
              <div
                className="absolute top-0 right-0 text-[10px] font-bold uppercase px-2.5 py-1 rounded-bl-xl"
                style={{ background: 'var(--lumo-accent)', color: '#fff' }}
              >
                Старт
              </div>
            )}
            <div className={compact ? 'p-3' : 'p-4'}>
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <h3 className={`font-bold leading-snug ${compact ? 'text-[14px]' : 'text-[16px]'}`}>
                    {plan.label}
                  </h3>
                  {plan.description && (
                    <p
                      className={`mt-1 ${compact ? 'text-[11px]' : 'text-[12px]'}`}
                      style={{ color: 'var(--lumo-text-muted)' }}
                    >
                      {plan.description}
                    </p>
                  )}
                  {plan.benefit && (
                    <p
                      className={`mt-1.5 font-semibold ${compact ? 'text-[11px]' : 'text-[12px]'}`}
                      style={{ color: 'var(--lumo-link)' }}
                    >
                      {plan.benefit}
                    </p>
                  )}
                  {selected && (
                    <p
                      className="mt-2 text-[11px] font-semibold"
                      style={{ color: 'var(--lumo-link)' }}
                    >
                      ↓ Kaspi для оплаты внизу экрана
                    </p>
                  )}
                </div>
                <div className="text-right shrink-0 pt-0.5">
                  <div className={`font-bold ${compact ? 'text-[16px]' : 'text-[20px]'}`}>
                    {formatPriceKzt(plan.priceKzt)}
                  </div>
                  {plan.id === 'plan_12m' && (
                    <div className="text-[10px] mt-0.5" style={{ color: 'var(--lumo-text-muted)' }}>
                      ≈ 990 ₸/мес
                    </div>
                  )}
                </div>
              </div>
            </div>
          </button>
        );
      })}
    </div>
  );
}

function KaspiPaymentBlock({ phone, selectedPlan, supportContact }) {
  const [copied, setCopied] = useState(false);
  const displayPhone = phone || KASPI_PAYMENT_PHONE;

  const copyPhone = async () => {
    haptic('light');
    try {
      await navigator.clipboard.writeText(displayPhone);
      setCopied(true);
      getTelegram()?.HapticFeedback?.notificationOccurred('success');
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* ignore */
    }
  };

  const support = (supportContact || '@taton4i').replace('@', '');

  return (
    <div
      className="rounded-2xl px-4 py-4 space-y-3"
      style={{ background: 'var(--lumo-surface-muted)' }}
    >
      <p className="text-[13px] font-semibold text-center">Оплата через Kaspi</p>
      {selectedPlan ? (
        <p className="text-[12px] text-center" style={{ color: 'var(--lumo-text-muted)' }}>
          Тариф: <strong>{selectedPlan.label}</strong> · переведи{' '}
          <strong>{formatPriceKzt(selectedPlan.priceKzt)}</strong>
        </p>
      ) : (
        <p className="text-[12px] text-center" style={{ color: 'var(--lumo-text-muted)' }}>
          Выбери тариф выше и переведи сумму на номер Kaspi
        </p>
      )}
      <button
        type="button"
        onClick={copyPhone}
        className="w-full flex items-center justify-center gap-2 py-3.5 rounded-xl text-[16px] font-bold text-white lumo-send-btn"
      >
        <Copy size={16} />
        {displayPhone}
      </button>
      <p className="text-[11px] text-center" style={{ color: 'var(--lumo-text-muted)' }}>
        {copied ? 'Номер скопирован — открой Kaspi и переведи' : 'Нажми, чтобы скопировать номер'}
      </p>
      <p className="text-[11px] text-center" style={{ color: 'var(--lumo-text-muted)' }}>
        После оплаты напиши @{support} — активируем доступ
      </p>
    </div>
  );
}

export function PricingFooter({ meta, profile, onClose, limitNotice = false, selectedPlan }) {
  const checkout = meta?.startifyCheckoutUrl;
  const enforced = profile?.subscription?.enforced;
  const kaspiPhone = meta?.kaspiPaymentPhone || KASPI_PAYMENT_PHONE;
  const useStartify = Boolean(checkout && enforced);

  return (
    <div className="space-y-3 mt-4">
      {useStartify ? (
        <a
          href={checkout}
          className="block w-full text-center py-3.5 rounded-2xl text-[15px] font-bold text-white lumo-send-btn"
        >
          Оплатить через Kaspi
        </a>
      ) : (
        <KaspiPaymentBlock
          phone={kaspiPhone}
          selectedPlan={selectedPlan}
          supportContact={meta?.supportContact}
        />
      )}

      {onClose && (
        <button
          type="button"
          onClick={onClose}
          className="w-full py-3 rounded-2xl text-[14px] font-semibold"
          style={{ background: 'var(--lumo-surface-muted)', color: 'var(--lumo-text)' }}
        >
          {limitNotice ? 'Продолжить с каталогом' : 'Закрыть'}
        </button>
      )}

      {limitNotice && (
        <p className="text-[11px] text-center" style={{ color: 'var(--lumo-text-muted)' }}>
          Короткий поиск (&lt; {meta?.interestMinLength ?? 25} символов) всё ещё доступен · лимит
          обновится завтра
        </p>
      )}
    </div>
  );
}

export function PricingHeader({ limitNotice, dailyLimit = 3 }) {
  return (
    <header className="mb-5">
      <div className="flex items-center gap-2 mb-2">
        <Sparkles size={18} style={{ color: 'var(--lumo-accent)' }} />
        <h1 className="text-[22px] font-bold leading-tight">Тарифы</h1>
      </div>
      {limitNotice ? (
        <p className="text-[13px] leading-relaxed" style={{ color: '#f87171' }}>
          {dailyLimit} AI-запроса на сегодня закончились. Выбери тариф — безлимитный AI-поиск и
          сохранение профиля.
        </p>
      ) : (
        <p className="text-[13px] leading-relaxed" style={{ color: 'var(--lumo-text-muted)' }}>
          Безлимитный AI-поиск · каталог · уведомления в боте. Сейчас бесплатно —{' '}
          {dailyLimit} AI-запроса в день.
        </p>
      )}
    </header>
  );
}
