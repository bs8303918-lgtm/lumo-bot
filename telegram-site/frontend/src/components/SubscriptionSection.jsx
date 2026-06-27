import { Sparkles } from 'lucide-react';
import { formatPriceKzt, resolvePlans } from '../utils/pricing';
import { haptic } from '../api';

export default function SubscriptionSection({ meta, profile, plans, onOpenPriceList }) {
  if (!meta?.subscriptionPreviewEnabled) return null;

  const sub = profile?.subscription;
  const checkout = meta?.startifyCheckoutUrl;
  const enforced = sub?.enforced;
  const visiblePlans = resolvePlans(plans).slice(0, 3);

  return (
    <section className="lumo-card p-4">
      <div className="flex items-center justify-between gap-2 mb-3">
        <div className="flex items-center gap-2">
          <Sparkles size={16} style={{ color: 'var(--lumo-accent)' }} />
          <h2 className="text-[15px] font-bold">Подписка Lumo</h2>
        </div>
        {onOpenPriceList && (
          <button
            type="button"
            onClick={() => {
              haptic('light');
              onOpenPriceList('manual');
            }}
            className="text-[11px] font-semibold underline shrink-0"
            style={{ color: 'var(--lumo-link)' }}
          >
            Price
          </button>
        )}
      </div>

      <p className="text-[13px] mb-3" style={{ color: 'var(--lumo-text-muted)' }}>
        {enforced
          ? 'Оплата через AI Startify · Kaspi'
          : `Сейчас бесплатно: ${meta?.aiSearchDailyLimit ?? 3} AI-запроса в день. Тарифы — для безлимитного доступа.`}
      </p>

      {sub && (
        <div
          className="rounded-xl px-3 py-2 mb-3 text-[12px]"
          style={{ background: 'var(--lumo-surface-muted)' }}
        >
          Текущий план: <strong>{sub.planLabel || sub.plan}</strong>
          {sub.expiresAt && (
            <span style={{ color: 'var(--lumo-text-muted)' }}>
              {' '}
              · до {new Date(sub.expiresAt).toLocaleDateString('ru-RU')}
            </span>
          )}
        </div>
      )}

      <div className="space-y-2">
        {(visiblePlans || []).map((plan) => (
          <div
            key={plan.id}
            className="flex items-center justify-between gap-3 rounded-xl px-3 py-2.5"
            style={{ background: 'var(--lumo-surface-muted)' }}
          >
            <div>
              <div className="text-[13px] font-semibold">{plan.label}</div>
              <div className="text-[11px]" style={{ color: 'var(--lumo-text-muted)' }}>
                {plan.benefit || plan.description}
              </div>
            </div>
            <div className="text-right shrink-0">
              <div className="text-[13px] font-bold">{formatPriceKzt(plan.priceKzt)}</div>
              {checkout && !enforced && (
                <span className="text-[10px]" style={{ color: 'var(--lumo-text-muted)' }}>
                  скоро
                </span>
              )}
              {checkout && enforced && (
                <a
                  href={checkout}
                  className="text-[11px] font-semibold underline"
                  style={{ color: 'var(--lumo-link)' }}
                >
                  Оплатить
                </a>
              )}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
