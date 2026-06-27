import { X } from 'lucide-react';
import { haptic } from '../api';
import { resolvePlans } from '../utils/pricing';
import PlanCards, { PricingFooter, PricingHeader } from './PlanCards';

/** Полноэкранный оверлей при исчерпании лимита (дублирует вкладку «Тарифы») */
export default function PriceListView({ open, onClose, plans, meta, profile, reason = 'limit' }) {
  if (!open) return null;

  const resolved = resolvePlans(plans);
  const isLimitReason = reason === 'limit';
  const dailyLimit = meta?.aiSearchDailyLimit ?? 3;

  const handleClose = () => {
    haptic('light');
    onClose?.();
  };

  return (
    <div
      className="fixed inset-0 z-50 flex flex-col overflow-y-auto"
      style={{
        background: 'var(--lumo-bg)',
        color: 'var(--lumo-text)',
        paddingTop: 'env(safe-area-inset-top)',
        paddingBottom: 'env(safe-area-inset-bottom)',
      }}
    >
      <div className="max-w-lg mx-auto w-full flex flex-col flex-1 px-4 py-4">
        <div className="flex justify-end mb-1">
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

        <PricingHeader limitNotice={isLimitReason} dailyLimit={dailyLimit} />
        <PlanCards plans={resolved} />
        <PricingFooter
          meta={meta}
          profile={profile}
          limitNotice={isLimitReason}
          onClose={handleClose}
        />
      </div>
    </div>
  );
}
