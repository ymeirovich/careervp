"use client";

import { useState, useEffect, use } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { Topbar } from "@/components/dashboard/Topbar";
import { Badge } from "@/components/ui/Badge";
import type { VPRStatusResponse, VPRDifferentiator, JobDetail } from "@/lib/types";

// ─── Helpers ──────────────────────────────────────────────────────────────────

const CARD = "rounded-[8px] border border-[#cbd5e1] bg-white p-6 flex flex-col gap-4";
const TITLE = "text-base font-bold text-[#1e2229]";

function ScoreBadge({ score }: { score: number }) {
  const pct = Math.round(score * 10);
  const color =
    pct >= 80 ? "#16b44b" : pct >= 60 ? "#f59e0b" : "#ef4444";
  return (
    <span
      className="inline-flex items-center justify-center w-12 h-12 rounded-full text-white font-bold text-lg"
      style={{ background: color }}
    >
      {pct}
    </span>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function VPRPage({
  params,
}: {
  params: Promise<{ jobId: string }>;
}) {
  const { jobId } = use(params);
  const router = useRouter();

  const [vpr, setVpr] = useState<VPRStatusResponse | null>(null);
  const [job, setJob] = useState<JobDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const init = async () => {
      setLoading(true);
      const [hubResult, jobResult] = await Promise.allSettled([
        api.getApplication(jobId),
        api.getJob(jobId),
      ]);

      const hub = hubResult.status === "fulfilled" ? hubResult.value : null;
      const jobData = jobResult.status === "fulfilled" ? jobResult.value : null;
      setJob(jobData);

      const artifactId = hub?.artifacts.vpr?.artifact_id;
      const artifactStatus = hub?.artifacts.vpr?.status;

      if (!artifactId || artifactStatus !== "completed") {
        router.replace(`/dashboard/jobs/${jobId}`);
        return;
      }

      try {
        const vprData = await api.getVPR(artifactId);
        setVpr(vprData);
      } catch (err) {
        setError("Failed to load Value Proposition Report.");
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    init();
  }, [jobId, router]);

  // ── Derived ──────────────────────────────────────────────────────────────────

  const displayJob = job;
  const result = vpr?.result;
  const summary = result?.uvp || result?.strategic_narrative || "";
  const differentiators: VPRDifferentiator[] = result?.differentiators ?? [];
  const fitScore = result?.company_job_fit_score;
  const meta = result?.meta_evaluation;

  const breadcrumb = [
    { label: "Dashboard", href: "/dashboard" },
    {
      label: displayJob?.title ?? "Application",
      href: `/dashboard/jobs/${jobId}`,
    },
  ];

  // ── Render ───────────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <>
        <Topbar title="Value Proposition Report" breadcrumb={breadcrumb} />
        <main className="flex flex-col gap-6 p-6">
          <div className="text-sm text-[#6b7280]">Loading…</div>
        </main>
      </>
    );
  }

  if (error) {
    return (
      <>
        <Topbar title="Value Proposition Report" breadcrumb={breadcrumb} />
        <main className="flex flex-col gap-6 p-6">
          <div className="rounded-[8px] bg-[#fef2f2] border border-[#ef4444] px-4 py-3 text-sm text-[#ef4444]">
            {error}
          </div>
        </main>
      </>
    );
  }

  return (
    <>
      <Topbar title="Value Proposition Report" breadcrumb={breadcrumb} />
      <main className="flex flex-col gap-8 p-6">
        {/* Page Header */}
        <div className="flex items-start justify-between gap-4">
          <div className="flex flex-col gap-1">
            <h1 className="text-xl font-bold text-[#1e2229]">
              Value Proposition Report
            </h1>
            {displayJob && (
              <p className="text-sm text-[#6b7280]">
                {displayJob.title} · {displayJob.company_name}
              </p>
            )}
          </div>
          <button
            onClick={() =>
              router.push(`/dashboard/jobs/${jobId}`)
            }
            className="shrink-0 rounded-[8px] border border-[#cbd5e1] px-3 py-2 text-sm text-[#1e2229] hover:bg-[rgba(217,217,217,0.3)]"
          >
            ← Back to Hub
          </button>
        </div>

        {/* Executive Summary */}
        {summary && (
          <div className={CARD}>
            <h2 className={TITLE}>Executive Summary</h2>
            <p className="text-sm text-[#1e2229] leading-relaxed">{summary}</p>
          </div>
        )}

        {/* Key Differentiators */}
        {differentiators.length > 0 && (
          <div className={CARD}>
            <h2 className={TITLE}>Key Differentiators</h2>
            <ul className="flex flex-col gap-2 pl-1">
              {differentiators.map((d, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-[#1e2229]">
                  <span className="mt-1 shrink-0 w-1.5 h-1.5 rounded-full bg-[#f97316]" />
                  <span className="leading-relaxed">{d.text}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Fit Score */}
        {(fitScore !== undefined || meta) && (
          <div className={CARD}>
            <h2 className={TITLE}>Assessment</h2>
            <div className="flex flex-wrap gap-6 items-center">
              {fitScore !== undefined && (
                <div className="flex flex-col items-center gap-1">
                  <ScoreBadge score={fitScore} />
                  <span className="text-xs text-[#6b7280]">Fit Score / 100</span>
                </div>
              )}
              {meta && (
                <>
                  <div className="flex flex-col gap-1">
                    <div className="flex items-center gap-2">
                      <Badge variant="amber" size="sm">
                        Persuasion {Math.round(meta.persuasion_score * 10)}%
                      </Badge>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant="blue" size="sm">
                        Completeness {Math.round(meta.completeness_score * 10)}%
                      </Badge>
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        )}

        {/* Empty state */}
        {!summary && differentiators.length === 0 && (
          <div className="rounded-[8px] border border-[#cbd5e1] bg-white px-6 py-12 text-center text-sm text-[#6b7280]">
            No VPR content available.
          </div>
        )}
      </main>
    </>
  );
}
