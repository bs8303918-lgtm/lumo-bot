import { useState } from 'react';
import PlanCards, { PricingFooter, PricingHeader } from './PlanCards';
import { resolvePlans } from '../utils/pricing';

export default function PricingView({ meta, profile, plans, limitNotice = false, onDismissLimit }) {
  const resolved = resolvePlans(plans);
  const dailyLimit = meta?.aiSearchDailyLimit ?? 3;
  const [selectedPlan, setSelectedPlan] = useState(resolved.find((p) => p.featured || p.id === 'plan_6m') || null);

  return (
    <div className="pb-8">
      <PricingHeader limitNotice={limitNotice} dailyLimit={dailyLimit} />
      <PlanCards plans={resolved} selectedId={selectedPlan?.id} onSelect={setSelectedPlan} />
      <PricingFooter
        meta={meta}
        profile={profile}
        limitNotice={limitNotice}
        onClose={limitNotice ? onDismissLimit : null}
        selectedPlan={selectedPlan}
      />
    </div>
  );
}
