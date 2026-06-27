import { Sparkles, X } from 'lucide-react';
import { formatPriceKzt } from '../utils/pricing';
import { haptic } from '../api';

export default function PriceListView({ open, onClose, plans, meta, profile, reason = 'limit' }) {
  if (!open) return null;

  const checkout = meta?.startifyCheckoutUrl;
  const enforced = profile?.subscription?.enforced;
  const dailyLimit = meta?.aiSearchDailyLimit ?? 3;
  const isLimitReason = reason === 'limit';

  const handleClose = () => {
    haptic('light');
    onClose?.();
  };

  return (
    <div
      className="fixed inset-0 z-50 flex flex-col"
      style={{
        background: 'var(--lumo-bg)',
        color: 'var(--lumo-text)',
        paddingTop: 'env(safe-area-inset-top)',
        paddingBottom: 'env(safe-area-inset-bottom)',
      }}
    >
      <div className="max-w-lg mx-auto w-full flex flex-col flex-1 px-4 py-4">
        <div className="flex items-start justify-between gap-3 mb-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Sparkles size={18} style={{ color: 'var(--lumo-accent)' }} />
              <h1 className="text-[20px] font-bold leading-tight">Тарифы Lumo</h1>
            </div>
            {isLimitReason ? (
              <p className="text-[13px] leading-relaxed" style={{ color: 'var(--lumo-text-muted)' }}>
                {dailyLimit} AI-запроса на сегодня закончились. Выбери тариф — безлимитный AI-поиск и
                сохранение профиля.
              </p>
            ) : (
              <p className="text-[13px] leading-relaxed" style={{ color: 'var(--lumo-text-muted)' }}>
                Безлимитный AI-поиск · каталог · уведомления в боте
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={handleClose}
            className="w-9 h-9 shrink-0 rounded-xl flex items-center justify-center"
            style={{ color: 'var(--lumo-text-muted)', background: 'var(--lumo-surface-muted)' }}
            aria-label="Закрыть"
          >
            <X size={18} />
          </button>
        </div>

        <div
          className="lumo-card overflow-hidden mb-4"
          style={{ borderColor: 'var(--lumo-border)' }}
        >
          <div
            className="grid grid-cols-[1fr_auto_auto] gap-2 px-3 py-2.5 text-[11px] font-semibold uppercase tracking-wide"
            style={{
              color: 'var(--lumo-text-muted)',
              background: 'var(--lumo-surface-muted)',
              borderBottom: '1px solid var(--lumo-border)',
            }}
          >
            <span>Тариф</span>
            <span className="text-right">Стоимость</span>
            <span className="text-right min-w-[72px]">Выгода</span>
          </div>

          <div className="divide-y" style={{ borderColor: 'var(--lumo-border)' }}>
            {(plans || []).map((plan) => (
              <div
                key={plan.id}
                className="grid grid-cols-[1fr_auto_auto] gap-2 items-center px-3 py-3"
                style={{ borderColor: 'var(--lumo-border)' }}
              >
                <div>
                  <div className="text-[14px] font-semibold leading-snug">
                    {plan.id === 'plan_6m' && (
                      <span
                        className="text-[10px] font-bold uppercase mr-1.5 px-1.5 py-0.5 rounded-md"
                        style={{ background: 'var(--lumo-accent)', color: '#fff' }}
                      >
                        Старт
                      </span>
                    )}
                    {plan.label}
                  </div>
                  {plan.description && (
                    <div className="text-[11px] mt-0.5" style={{ color: 'var(--lumo-text-muted)' }}>
                      {plan.description}
                    </div>
                  )}
                </div>
                <div className="text-[14px] font-bold text-right whitespace-nowrap">
                  {formatPriceKzt(plan.priceKzt)}
                </div>
                <div
                  className="text-[11px] text-right min-w-[72px] leading-snug"
                  style={{ color: plan.benefit ? 'var(--lumo-link)' : 'var(--lumo-text-muted)' }}
                >
                  {plan.benefit || '—'}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-auto space-y-3">
          {checkout && enforced ? (
            <a
              href={checkout}
              className="block w-full text-center py-3.5 rounded-2xl text-[15px] font-bold text-white lumo-send-btn"
              onClick={() => haptic('medium')}
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

          <button
            type="button"
            onClick={handleClose}
            className="w-full py-3 rounded-2xl text-[14px] font-semibold"
            style={{
              background: 'var(--lumo-surface-muted)',
              color: 'var(--lumo-text)',
            }}
          >
            {isLimitReason ? 'Продолжить с каталогом' : 'Закрыть'}
          </button>

          {isLimitReason && (
            <p className="text-[11px] text-center pb-1" style={{ color: 'var(--lumo-text-muted)' }}>
              Короткий поиск (&lt; {meta?.interestMinLength ?? 25} символов) всё ещё доступен · лимит
              обновится завтра
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
