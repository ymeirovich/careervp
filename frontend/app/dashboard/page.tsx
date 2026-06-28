"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useDashboard } from "@/app/dashboard/dashboard-context";
import { Topbar } from "@/components/dashboard/Topbar";
import { StatusStrip } from "@/components/dashboard/StatusStrip";
import { cn } from "@/lib/utils";
import type { Job } from "@/lib/types";

// ─── Table config ─────────────────────────────────────────────────────────────
const TABLE_COLUMNS = [
  { key: "title", label: "Job Title", className: "flex-1 min-w-0" },
  { key: "company", label: "Company", className: "w-[160px] shrink-0" },
  { key: "status", label: "Status", className: "w-[120px] shrink-0" },
  { key: "updated", label: "Updated", className: "w-[140px] shrink-0" },
  { key: "action", label: "Action", className: "w-[140px] shrink-0" },
] as const;

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

// ─── Jobs Card ────────────────────────────────────────────────────────────────
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
            "hover:opacity-90 active:opacity-80"
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
            No applications yet. Click &quot;+ New Application&quot; to get
            started.
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
                    : "text-[#6b7280]"
                )}
              >
                {job.status}
              </span>
              <span className="w-[140px] shrink-0">
                {formatDate(job.created_at)}
              </span>
              <span className="w-[140px] shrink-0">
                <a
                  href={`/dashboard/jobs/${job.job_id}`}
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
  const router = useRouter();
  const { usage, subscription } = useDashboard();

  const [jobs, setJobs] = useState<Job[]>([]);
  const [dataLoading, setDataLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      setDataLoading(true);
      try {
        const jobsData = await api.getJobs();
        setJobs(jobsData);
      } catch (err) {
        console.error("Jobs fetch error:", err);
      } finally {
        setDataLoading(false);
      }
    };
    load();
  }, []);

  return (
    <>
      <Topbar title="Dashboard" />
      <main className="flex flex-col gap-6 p-6">
        <StatusStrip usage={usage} subscription={subscription} />
        <JobsCard
          jobs={jobs}
          loading={dataLoading}
          onNewApplication={() => router.push("/applications/new")}
        />
      </main>
    </>
  );
}
