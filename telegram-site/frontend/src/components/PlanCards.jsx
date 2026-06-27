import { Sparkles } from 'lucide-react';
import { formatPriceKzt } from '../utils/pricing';

export default function PlanCards({ plans, compact = false }) {
  return (
    <div className={compact ? 'space-y-2' : 'space-y-3'}>
      {plans.map((plan) => {
        const featured = plan.featured || plan.id === 'plan_6m';
        return (
          <div
            key={plan.id}
            className="lumo-card relative overflow-hidden"
            style={
              featured
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
          </div>
        );
      })}
    </div>
  );
}

export function PricingFooter({ meta, profile, onClose, limitNotice = false }) {
  const checkout = meta?.startifyCheckoutUrl;
  const enforced = profile?.subscription?.enforced;

  return (
    <div className="space-y-3 mt-4">
      {checkout && enforced ? (
        <a
          href={checkout}
          className="block w-full text-center py-3.5 rounded-2xl text-[15px] font-bold text-white lumo-send-btn"
        >
          Оплатить через Kaspi
        </a>
      ) : (
        <div
          className="rounded-2xl px-4 py-3 text-[13px] text-center"
          style={{ background: 'var(--lumo-surface-muted)', color: 'var(--lumo-text-muted)' }}
        >
          Оплата скоро через AI Startify · Kaspi
        </div>
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
