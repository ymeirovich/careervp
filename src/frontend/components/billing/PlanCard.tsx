import React from 'react';

export interface PlanCardProps {
  planKey: string;
  displayName: string;
  pricePerMonth: number;
  billingPeriodLabel: string;
  isCurrentPlan: boolean;
  isRecommended: boolean;
  onChoosePlan: (planKey: string) => void;
}

function buildPriceAriaLabel(pricePerMonth: number, billingPeriodLabel: string): string {
  const normalizedBilling = billingPeriodLabel
    .trim()
    .replace(/\$/g, '')
    .replace(/^Billed\s+/i, 'billed ')
    .replace(/\s+/g, ' ');

  return `${pricePerMonth} dollars per month, ${normalizedBilling}`;
}

export function PlanCard({
  planKey,
  displayName,
  pricePerMonth,
  billingPeriodLabel,
  isCurrentPlan,
  isRecommended,
  onChoosePlan,
}: PlanCardProps) {
  const borderClasses = isRecommended
    ? 'border-2 border-primary-action'
    : 'border border-border-default';

  const hoverClasses = isCurrentPlan ? '' : 'hover:bg-surface-selected';

  const buttonText = isCurrentPlan ? 'Current Plan' : 'Choose Plan';
  const buttonClasses = isCurrentPlan
    ? 'bg-surface-subtle text-text-muted cursor-not-allowed'
    : 'bg-primary-action text-white hover:opacity-90';

  const handleChoosePlan = () => {
    if (isCurrentPlan) return;
    onChoosePlan(planKey);
  };

  return (
    <div
      data-testid={`plan-card-${planKey}`}
      className={`
        bg-card rounded-xl p-5 transition-colors
        ${borderClasses}
        ${hoverClasses}
      `.trim()}
    >
      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <h3 className="text-text-primary text-lg font-bold">{displayName}</h3>
          <div
            className="flex items-baseline gap-1 text-text-primary"
            aria-label={buildPriceAriaLabel(pricePerMonth, billingPeriodLabel)}
          >
            <span className="text-4xl font-extrabold">${pricePerMonth}</span>
            <span className="text-sm font-semibold text-text-muted">/mo</span>
          </div>
          <p className="text-text-muted text-sm">{billingPeriodLabel}</p>
        </div>

        <button
          type="button"
          aria-disabled={isCurrentPlan || undefined}
          onClick={handleChoosePlan}
          className={`
            w-full inline-flex items-center justify-center rounded-xl px-4 py-2 text-base font-bold transition-colors
            focus:outline-none focus:ring-2 focus:ring-primary-action focus:ring-offset-2
            ${buttonClasses}
          `.trim()}
        >
          {buttonText}
        </button>
      </div>
    </div>
  );
}

