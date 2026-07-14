import { useState } from 'react';
import { X } from 'lucide-react';
import { haptic } from '../api';
import { resolvePlans } from '../utils/pricing';
import PlanCards, { PricingFooter, PricingHeader } from './PlanCards';

/** Полноэкранный оверлей при исчерпании лимита (дублирует вкладку «Тарифы») */
export default function PriceListView({ open, onClose, plans, meta, profile, reason = 'limit' }) {
  const resolved = resolvePlans(plans);
  const [selectedPlan, setSelectedPlan] = useState(
    resolved.find((p) => p.featured || p.id === 'plan_6m') || null,
  );

  if (!open) return null;

  const isLimitReason = reason === 'limit';
  const needsSubscription = reason === 'subscription';

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
      <div className="max-w-lg mx-auto w-full flex flex-col flex-1 px-4 py-4 pb-36">
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

        <PricingHeader limitNotice={isLimitReason} needsSubscription={needsSubscription} meta={meta} />
        <PlanCards plans={resolved} selectedId={selectedPlan?.id} onSelect={setSelectedPlan} />
        <div
          className="fixed bottom-0 left-0 right-0 z-20 px-4 pt-3 pb-4 border-t"
          style={{
            background: 'var(--lumo-bg)',
            borderColor: 'var(--lumo-border)',
            paddingBottom: 'max(1rem, env(safe-area-inset-bottom))',
            boxShadow: '0 -8px 24px rgba(0,0,0,0.12)',
          }}
        >
          <PricingFooter
            meta={meta}
            profile={profile}
            limitNotice={isLimitReason}
            needsSubscription={needsSubscription}
            onClose={handleClose}
            selectedPlan={selectedPlan}
          />
        </div>
      </div>
    </div>
  );
}
