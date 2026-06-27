import PlanCards, { PricingFooter, PricingHeader } from './PlanCards';
import { resolvePlans } from '../utils/pricing';

export default function PricingView({ meta, profile, plans, limitNotice = false, onDismissLimit }) {
  const resolved = resolvePlans(plans);
  const dailyLimit = meta?.aiSearchDailyLimit ?? 3;

  return (
    <div className="pb-8">
      <PricingHeader limitNotice={limitNotice} dailyLimit={dailyLimit} />
      <PlanCards plans={resolved} />
      <PricingFooter
        meta={meta}
        profile={profile}
        limitNotice={limitNotice}
        onClose={limitNotice ? onDismissLimit : null}
      />
    </div>
  );
}
