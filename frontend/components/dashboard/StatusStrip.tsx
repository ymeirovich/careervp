import { cn } from "@/lib/utils";
import type { Usage, SubscriptionResponse } from "@/lib/types";

const ASSET_STATUS_DOT =
  "https://www.figma.com/api/mcp/asset/62714d3b-6e61-40cf-917d-9ad5f45735ac";

function getPlanLabel(
  usage: Usage | null,
  sub: SubscriptionResponse | null
): string {
  if (usage?.trial?.active) return "Free Trial";
  if (sub?.subscription?.plan_type === "monthly") return "Monthly";
  if (sub?.subscription?.plan_type === "annual") return "Annual";
  return "—";
}

function isAccountActive(
  usage: Usage | null,
  sub: SubscriptionResponse | null
): boolean {
  return !!(usage?.trial?.active || sub?.has_active_subscription);
}

interface StatusStripProps {
  usage: Usage | null;
  subscription: SubscriptionResponse | null;
}

export function StatusStrip({ usage, subscription }: StatusStripProps) {
  const cardBase =
    "flex items-center justify-center rounded-[4px] border border-[#cbd5e1] bg-[rgba(245,245,245,0.61)] px-4 py-3";

  const plan = getPlanLabel(usage, subscription);
  const total = usage
    ? usage.applications.used + usage.applications.remaining
    : null;
  const creditsText = usage
    ? `${usage.applications.remaining} / ${total}`
    : "—";
  const active = isAccountActive(usage, subscription);

  return (
    <div className="flex items-center gap-8 rounded-[8px] border border-[#cbd5e1] bg-white px-[26px] py-[11px] w-full">
      <div className={cardBase}>
        <div className="flex items-center gap-1.5 text-sm font-bold text-[#1e2229] whitespace-nowrap">
          <span>Plan:</span>
          <span>{plan}</span>
        </div>
      </div>

      <div className={cardBase}>
        <div className="flex items-center gap-1.5 text-sm font-bold text-[#1e2229] whitespace-nowrap">
          <span>Credits Remaining:</span>
          <span>{creditsText}</span>
        </div>
      </div>

      <div className={cn(cardBase, "ml-auto flex-row gap-2")}>
        <div className="flex items-center gap-1.5 text-sm font-bold whitespace-nowrap">
          <span className="text-[#1e2229]">Status:</span>
          <span className={active ? "text-[#16b44b]" : "text-[#6b7280]"}>
            {active ? "Active" : usage ? "Expired" : "—"}
          </span>
        </div>
        {active && (
          <img
            src={ASSET_STATUS_DOT}
            alt="active"
            className="h-4 w-4 object-contain shrink-0"
          />
        )}
      </div>
    </div>
  );
}
