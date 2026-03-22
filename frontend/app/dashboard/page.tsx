"use client";

/**
 * CareerVP — Dashboard (live data)
 * Figma: OAncxa2CNTZFvQ3gGrI79O · node 66:262 "Desktop / Dashboard Full"
 *
 * Design tokens (Figma-exact):
 *   Page bg:        #fcf7f5
 *   App shell bg:   #fafafa
 *   Card / sidebar: white
 *   Border:         #cbd5e1
 *   Text primary:   #1e2229
 *   Text muted:     #6b7280
 *   Active green:   #16b44b
 *   Brand orange:   #f97316
 *   Active nav bg:  rgba(217,217,217,0.61)
 *   Status strip:   rgba(245,245,245,0.61)
 */

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { useAuth } from "@/app/auth-context";
import { NewApplicationModal } from "@/components/NewApplicationModal";
import type { Job, Usage, SubscriptionResponse } from "@/lib/types";

// ─── Figma asset URLs ────────────────────────────────────────────────────────
const ASSET_CVP_LOGO =
  "https://www.figma.com/api/mcp/asset/661cfe6f-1041-4faa-8666-3d001bb92746";
const ASSET_STATUS_DOT =
  "https://www.figma.com/api/mcp/asset/62714d3b-6e61-40cf-917d-9ad5f45735ac";
const ASSET_DROPDOWN_ARROW =
  "https://www.figma.com/api/mcp/asset/29ba343a-ed50-4f60-ab33-814b014f47b8";

// ─── Nav ─────────────────────────────────────────────────────────────────────
const NAV_ITEMS = [
  { label: "CareerVP", isSection: true },
  { label: "Dashboard", active: true, href: "/dashboard" },
  { label: "Applications", href: "#" },
  { label: "CV Center", href: "#" },
  { label: "Billing", href: "#" },
  { label: "Settings", href: "#" },
] as const;

const TABLE_COLUMNS = [
  { key: "title", label: "Job Title", className: "flex-1 min-w-0" },
  { key: "company", label: "Company", className: "w-[160px] shrink-0" },
  { key: "status", label: "Status", className: "w-[120px] shrink-0" },
  { key: "updated", label: "Updated", className: "w-[140px] shrink-0" },
  { key: "action", label: "Action", className: "w-[140px] shrink-0" },
] as const;

// ─── Helpers ─────────────────────────────────────────────────────────────────
function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}

function getPlanLabel(usage: Usage | null, sub: SubscriptionResponse | null): string {
  if (usage?.trial?.active) return "Free Trial";
  if (sub?.subscription?.plan_type === "monthly") return "Monthly";
  if (sub?.subscription?.plan_type === "annual") return "Annual";
  return "—";
}

function isAccountActive(usage: Usage | null, sub: SubscriptionResponse | null): boolean {
  return !!(usage?.trial?.active || sub?.has_active_subscription);
}

// ─── Sidebar ─────────────────────────────────────────────────────────────────
function Sidebar() {
  return (
    <aside
      className="flex w-60 shrink-0 flex-col bg-white border-r border-[#cbd5e1]"
      style={{ height: "900px" }}
    >
      <div className="flex items-center gap-2.5 px-[26px] py-5">
        <img
          src={ASSET_CVP_LOGO}
          alt="CareerVP"
          className="h-[30px] w-[30px] rounded-[4px] object-cover shrink-0"
        />
        <span className="text-lg font-bold text-[#1e2229] leading-none whitespace-nowrap">
          CareerVP
        </span>
      </div>

      <div className="border-b border-[#cbd5e1] mx-0" />

      <nav className="flex flex-col pt-[18px] px-[10px]">
        {NAV_ITEMS.map((item) => {
          if (item.isSection) {
            return (
              <span
                key={item.label}
                className="px-[13px] py-[8px] text-sm font-bold text-[#1e2229] whitespace-nowrap"
              >
                {item.label}
              </span>
            );
          }
          return (
            <a
              key={item.label}
              href={"href" in item ? item.href : "#"}
              className={cn(
                "px-[13px] py-[8px] text-sm font-bold text-[#1e2229] whitespace-nowrap rounded-sm transition-colors",
                "active" in item && item.active
                  ? "bg-[rgba(217,217,217,0.61)]"
                  : "hover:bg-[rgba(217,217,217,0.3)]",
              )}
            >
              {item.label}
            </a>
          );
        })}
      </nav>
    </aside>
  );
}

// ─── Topbar ──────────────────────────────────────────────────────────────────
function Topbar({ userName, usage }: { userName: string; usage: Usage | null }) {
  const total = usage
    ? usage.applications.used + usage.applications.remaining
    : null;
  const creditsText = usage ? `${usage.applications.remaining} / ${total}` : "—";

  return (
    <div className="flex h-20 shrink-0 items-center justify-between border-b border-[#cbd5e1] bg-white px-6">
      <span className="text-2xl font-semibold text-[#1e2229] whitespace-nowrap leading-none">
        Dashboard
      </span>

      <div className="flex items-center gap-3">
        <span className="text-base font-normal text-[#1e2229] whitespace-nowrap">
          Credits: {creditsText}
        </span>

        <div className="flex items-center gap-2.5 rounded-[8px] border border-[#6b7280] bg-[#f0f2f5] px-3 py-1.5">
          <span className="text-base font-normal text-[#1e2229] whitespace-nowrap leading-none">
            {userName || "…"}
          </span>
          <img
            src={ASSET_DROPDOWN_ARROW}
            alt=""
            aria-hidden
            className="h-[14px] w-[14px] object-contain"
            style={{ transform: "scaleY(-1)" }}
          />
        </div>
      </div>
    </div>
  );
}

// ─── Status Strip ─────────────────────────────────────────────────────────────
function StatusStrip({
  usage,
  subscription,
}: {
  usage: Usage | null;
  subscription: SubscriptionResponse | null;
}) {
  const cardBase =
    "flex items-center justify-center rounded-[4px] border border-[#cbd5e1] bg-[rgba(245,245,245,0.61)] px-4 py-3";

  const plan = getPlanLabel(usage, subscription);
  const total = usage ? usage.applications.used + usage.applications.remaining : null;
  const creditsText = usage ? `${usage.applications.remaining} / ${total}` : "—";
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

// ─── Jobs Card ───────────────────────────────────────────────────────────────
function JobsCard({
  jobs,
  loading,
  onNewApplication,
}: {
  jobs: Job[];
  loading: boolean;
  onNewApplication: () => void;
}) {
  return (
    <div className="flex flex-col gap-2.5 rounded-[8px] border border-[#cbd5e1] bg-white p-2.5 w-full">
      <div className="flex items-center justify-between overflow-hidden p-4">
        <span className="flex-1 min-w-0 text-[18px] font-bold text-[#1e2229] leading-normal">
          My Jobs
        </span>
        <button
          onClick={onNewApplication}
          className={cn(
            "flex shrink-0 items-center rounded-[8px] bg-[#f97316] px-3 py-2 transition-opacity",
            "hover:opacity-90 active:opacity-80",
          )}
        >
          <span className="text-sm font-bold text-white whitespace-nowrap leading-normal">
            + New Application
          </span>
        </button>
      </div>

      <div className="flex flex-col p-2.5 w-full overflow-hidden">
        <div className="flex items-start gap-4 border-b border-[#e2e8f0] bg-[#cbd5e1] px-4 py-3 text-sm font-medium text-[#6b7280]">
          {TABLE_COLUMNS.map((col) => (
            <span key={col.key} className={col.className}>
              {col.label}
            </span>
          ))}
        </div>

        {loading ? (
          <div className="px-4 py-6 text-sm text-[#6b7280]">Loading…</div>
        ) : jobs.length === 0 ? (
          <div className="px-4 py-6 text-sm text-[#6b7280]">
            No applications yet. Click &quot;+ New Application&quot; to get started.
          </div>
        ) : (
          jobs.map((job, i) => (
            <div
              key={job.id ?? job.job_id ?? i}
              className="flex items-start gap-4 border border-[#e2e8f0] px-4 py-3 text-sm font-medium text-[#1e2229] hover:bg-[rgba(245,245,245,0.5)] transition-colors"
            >
              <span className="flex-1 min-w-0">{job.title}</span>
              <span className="w-[160px] shrink-0">{job.company_name}</span>
              <span
                className={cn(
                  "w-[120px] shrink-0 capitalize",
                  job.status?.toLowerCase() === "active"
                    ? "text-[#16b44b]"
                    : "text-[#6b7280]",
                )}
              >
                {job.status}
              </span>
              <span className="w-[140px] shrink-0">
                {formatDate(job.created_at)}
              </span>
              <span className="w-[140px] shrink-0">
                <a
                  href="#"
                  className="text-[#1e2229] hover:underline transition-colors"
                >
                  View Application
                </a>
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────
export default function DashboardPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();

  const [jobs, setJobs] = useState<Job[]>([]);
  const [usage, setUsage] = useState<Usage | null>(null);
  const [subscription, setSubscription] = useState<SubscriptionResponse | null>(null);
  const [dataLoading, setDataLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login");
    }
  }, [authLoading, user, router]);

  useEffect(() => {
    if (!user) return;

    const load = async () => {
      setDataLoading(true);
      try {
        const [jobsData, usageData, subData] = await Promise.all([
          api.getJobs(),
          api.getUsage(),
          api.getSubscription(),
        ]);
        setJobs(jobsData);
        setUsage(usageData);
        setSubscription(subData);
      } catch (err) {
        console.error("Dashboard fetch error:", err);
      } finally {
        setDataLoading(false);
      }
    };

    load();
  }, [user]);

  const handleJobCreated = (newJob: Job) => {
    setJobs((prev) => [newJob, ...prev]);
    setShowModal(false);
  };

  // Use the `name` field from the API; fall back to the part before @ in email
  const userName = user?.name ?? user?.email?.split("@")[0] ?? "User";

  if (authLoading) {
    return (
      <div
        className="flex min-h-screen items-center justify-center"
        style={{ backgroundColor: "#fcf7f5" }}
      >
        <span className="text-sm text-[#6b7280]">Loading…</span>
      </div>
    );
  }

  return (
    <div className="min-h-screen w-full" style={{ backgroundColor: "#fcf7f5" }}>
      <div
        className="mx-auto flex border border-[#cbd5e1] bg-[#fafafa]"
        style={{
          marginLeft: "100px",
          marginTop: "62px",
          width: "1239px",
          minHeight: "900px",
        }}
      >
        <Sidebar />

        <div className="flex flex-1 flex-col min-w-0">
          <Topbar userName={userName} usage={usage} />

          <main className="flex flex-col gap-6 p-6">
            <StatusStrip usage={usage} subscription={subscription} />
            <JobsCard
              jobs={jobs}
              loading={dataLoading}
              onNewApplication={() => setShowModal(true)}
            />
          </main>
        </div>
      </div>

      {showModal && (
        <NewApplicationModal
          onClose={() => setShowModal(false)}
          onCreated={handleJobCreated}
        />
      )}
    </div>
  );
}
