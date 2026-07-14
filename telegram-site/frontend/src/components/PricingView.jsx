import { useCallback, useRef, useState } from 'react';
import PlanCards, { PricingFooter, PricingHeader } from './PlanCards';
import { resolvePlans } from '../utils/pricing';

export default function PricingView({
  meta,
  profile,
  plans,
  limitNotice = false,
  needsSubscription = false,
  standalone = false,
  onDismissLimit,
}) {
  const resolved = resolvePlans(plans);
  const [selectedPlan, setSelectedPlan] = useState(resolved.find((p) => p.featured || p.id === 'plan_6m') || null);
  const kaspiRef = useRef(null);

  const handleSelectPlan = useCallback((plan) => {
    setSelectedPlan(plan);
    requestAnimationFrame(() => {
      kaspiRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    });
  }, []);

  return (
    <div className="pb-36">
      <PricingHeader
        limitNotice={limitNotice}
        needsSubscription={needsSubscription}
        standalone={standalone}
        meta={meta}
      />
      <PlanCards plans={resolved} selectedId={selectedPlan?.id} onSelect={handleSelectPlan} />
      <div
        ref={kaspiRef}
        className="fixed bottom-0 left-0 right-0 z-20 px-4 pt-3 pb-4 border-t"
        style={{
          background: 'var(--lumo-bg)',
          borderColor: 'var(--lumo-border)',
          paddingBottom: 'max(1rem, env(safe-area-inset-bottom))',
          boxShadow: '0 -8px 24px rgba(0,0,0,0.12)',
        }}
      >
        <div className="max-w-lg mx-auto">
          <PricingFooter
            meta={meta}
            profile={profile}
            limitNotice={limitNotice}
            needsSubscription={needsSubscription}
            standalone={standalone}
            onClose={standalone || limitNotice || needsSubscription ? onDismissLimit : null}
            selectedPlan={selectedPlan}
          />
        </div>
      </div>
    </div>
  );
}
