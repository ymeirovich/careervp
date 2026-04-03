"use client";

import { useState, useEffect, use, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { Topbar } from "@/components/dashboard/Topbar";
import { Badge } from "@/components/ui/Badge";
import type {
  VPRStatusResponse,
  VPRFullData,
  VPRFullStrength,
  VPRFullConcern,
  VPRCoreResponsibility,
  VPRRelevantExperience,
  VPRObjection,
  JobDetail,
} from "@/lib/types";

// ─── Helpers ──────────────────────────────────────────────────────────────────

const CARD = "rounded-[8px] border border-[#cbd5e1] bg-white p-6 flex flex-col gap-4";
const TITLE = "text-base font-bold text-[#1e2229]";
const LABEL = "text-xs font-semibold uppercase tracking-wide text-[#6b7280]";
const BODY = "text-sm text-[#1e2229] leading-relaxed";
const MUTED = "text-sm text-[#6b7280] leading-relaxed";

function FitScoreBadge({ score }: { score: number }) {
  const color = score >= 80 ? "#16b44b" : score >= 60 ? "#f59e0b" : "#ef4444";
  return (
    <span
      className="inline-flex items-center justify-center w-16 h-16 rounded-full text-white font-bold text-xl shrink-0"
      style={{ background: color }}
    >
      {score}
    </span>
  );
}

function SeverityBadge({ severity }: { severity: string }) {
  const map: Record<string, string> = {
    high: "bg-[#fee2e2] text-[#ef4444]",
    medium: "bg-[#fef3c7] text-[#d97706]",
    low: "bg-[#f0fdf4] text-[#16a34a]",
  };
  const cls = map[severity.toLowerCase()] ?? "bg-[#f1f5f9] text-[#64748b]";
  return (
    <span className={`inline-flex px-2 py-0.5 rounded text-xs font-semibold ${cls}`}>
      {severity}
    </span>
  );
}

function ApproachBadge({ approach }: { approach: string }) {
  const labels: Record<string, { label: string; color: string }> = {
    aggressive_apply: { label: "Apply Aggressively", color: "#16b44b" },
    apply_with_customization: { label: "Apply with Customization", color: "#f59e0b" },
    apply_cautiously: { label: "Apply Cautiously", color: "#f97316" },
    do_not_apply: { label: "Do Not Apply", color: "#ef4444" },
  };
  const { label, color } = labels[approach] ?? { label: approach, color: "#64748b" };
  return (
    <span
      className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-semibold text-white"
      style={{ background: color }}
    >
      {label}
    </span>
  );
}

function AlignmentBar({ score }: { score: number }) {
  const color = score >= 85 ? "#16b44b" : score >= 70 ? "#f59e0b" : "#f97316";
  return (
    <div className="flex items-center gap-2 shrink-0">
      <div className="w-20 h-1.5 bg-[#e2e8f0] rounded-full overflow-hidden">
        <div className="h-full rounded-full" style={{ width: `${score}%`, background: color }} />
      </div>
      <span className="text-xs font-semibold" style={{ color }}>{score}</span>
    </div>
  );
}

// ─── Section: Executive Summary ───────────────────────────────────────────────

function ExecSummarySection({ data }: { data: VPRFullData["executiveSummary"] }) {
  return (
    <div className={CARD}>
      <div className="flex items-start gap-4">
        <FitScoreBadge score={data.overallFitScore} />
        <div className="flex flex-col gap-2 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h2 className={TITLE}>Executive Summary</h2>
            <ApproachBadge approach={data.recommendedApproach} />
          </div>
          <p className={BODY}>{data.fitRationale}</p>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-4 pt-2">
        {/* Strengths */}
        <div className="flex flex-col gap-3">
          <p className={LABEL}>Top Strengths</p>
          <div className="flex flex-col gap-3">
            {data.topThreeStrengths.map((s: VPRFullStrength, i: number) => (
              <div key={i} className="flex flex-col gap-1 border-l-2 border-[#16b44b] pl-3">
                <p className="text-sm font-semibold text-[#1e2229]">{s.strength}</p>
                <p className={MUTED}>{s.evidence}</p>
                <p className="text-xs text-[#16b44b]">{s.relevanceToRole}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Concerns */}
        <div className="flex flex-col gap-3">
          <p className={LABEL}>Concerns</p>
          <div className="flex flex-col gap-3">
            {data.topThreeConcerns.map((c: VPRFullConcern, i: number) => (
              <div key={i} className="flex flex-col gap-1 border-l-2 border-[#f59e0b] pl-3">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-semibold text-[#1e2229] flex-1">{c.concern}</p>
                  <SeverityBadge severity={c.severity} />
                </div>
                <p className={MUTED}>{c.mitigation}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Section: Application Strategy ───────────────────────────────────────────

function AppStrategySection({ data }: { data: VPRFullData["applicationStrategy"] }) {
  return (
    <div className={CARD}>
      <h2 className={TITLE}>Application Strategy</h2>

      <div className="flex flex-col gap-1">
        <p className={LABEL}>Messaging Approach</p>
        <p className={BODY}>{data.messagingApproach}</p>
      </div>

      <div className="flex flex-col gap-1">
        <p className={LABEL}>CV Opening Line</p>
        <div className="rounded-[6px] bg-[#f8fafc] border border-[#e2e8f0] p-3">
          <p className={BODY}>{data.cvLeadDifferentiator}</p>
        </div>
      </div>

      <div className="flex flex-col gap-2">
        <p className={LABEL}>ATS Keywords</p>
        <div className="flex flex-col gap-2">
          <div className="flex flex-wrap gap-1.5">
            {data.atsKeywords.primary.map((kw: string) => (
              <span key={kw} className="px-2 py-0.5 rounded-full text-xs font-medium bg-[#eff6ff] text-[#2563eb] border border-[#bfdbfe]">
                {kw}
              </span>
            ))}
          </div>
          <div className="flex flex-wrap gap-1.5">
            {data.atsKeywords.secondary.map((kw: string) => (
              <span key={kw} className="px-2 py-0.5 rounded-full text-xs font-medium bg-[#f1f5f9] text-[#64748b]">
                {kw}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Section: Role Alignment ──────────────────────────────────────────────────

function RoleAlignmentSection({ data }: { data: VPRFullData["roleAlignment"] }) {
  return (
    <div className={CARD}>
      <h2 className={TITLE}>Role Alignment</h2>
      <div className="flex flex-col gap-3">
        {data.coreResponsibilities.map((r: VPRCoreResponsibility, i: number) => (
          <div key={i} className="flex flex-col gap-1.5 border-b border-[#f1f5f9] pb-3 last:border-0 last:pb-0">
            <div className="flex items-start justify-between gap-3">
              <p className="text-sm font-semibold text-[#1e2229] flex-1">{r.responsibility}</p>
              <AlignmentBar score={r.alignmentScore} />
            </div>
            <ul className="flex flex-col gap-0.5 pl-3">
              {r.candidateEvidence.map((e: string, j: number) => (
                <li key={j} className="flex items-start gap-1.5 text-sm text-[#6b7280]">
                  <span className="mt-1.5 shrink-0 w-1 h-1 rounded-full bg-[#f97316]" />
                  {e}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Section: Experience Mapping ──────────────────────────────────────────────

function ExperienceSection({ data }: { data: VPRFullData["experienceMapping"] }) {
  return (
    <div className={CARD}>
      <h2 className={TITLE}>Experience Mapping</h2>
      <div className="flex flex-col gap-4">
        {data.relevantExperiences.map((exp: VPRRelevantExperience, i: number) => (
          <div key={i} className="flex flex-col gap-2 border-b border-[#f1f5f9] pb-4 last:border-0 last:pb-0">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-bold text-[#1e2229]">{exp.role}</p>
                <p className={MUTED}>{exp.organization} · {exp.duration}</p>
              </div>
              <AlignmentBar score={exp.relevanceScore} />
            </div>
            <p className="text-xs text-[#2563eb]">{exp.relevanceToTargetRole}</p>
            <div className="flex flex-col gap-1">
              {exp.keyAchievements.map((a, j) => (
                <div key={j} className="flex items-start gap-2 text-sm">
                  <span className="mt-1 shrink-0 w-1.5 h-1.5 rounded-full bg-[#f97316]" />
                  <span className="text-[#1e2229]">{a.achievement}</span>
                  <span className="text-[#6b7280] shrink-0">— {a.metric}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Section: Objections & Mitigations ───────────────────────────────────────

function ObjectionsSection({ data }: { data: VPRFullData["concernsAndMitigations"] }) {
  return (
    <div className={CARD}>
      <h2 className={TITLE}>Objections & Responses</h2>
      <div className="flex flex-col gap-4">
        {data.likelyObjections.map((o: VPRObjection, i: number) => (
          <div key={i} className="flex flex-col gap-2 border-b border-[#f1f5f9] pb-4 last:border-0 last:pb-0">
            <div className="flex items-start justify-between gap-3">
              <p className="text-sm font-semibold text-[#1e2229] flex-1">{o.objection}</p>
              <span className="text-xs text-[#6b7280] shrink-0 capitalize">{o.likelihood}</span>
            </div>
            <div className="rounded-[6px] bg-[#f0fdf4] border border-[#bbf7d0] p-3">
              <p className="text-xs font-semibold text-[#16a34a] mb-1 uppercase tracking-wide">
                Response Script
              </p>
              <p className={BODY}>{o.mitigation.messaging}</p>
            </div>
            <p className="text-xs text-[#6b7280]">
              Address in: {o.whereToAddress.join(", ")}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Section: Priority Gaps ───────────────────────────────────────────────────

function GapsSection({ data }: { data: VPRFullData["evidenceGaps"] }) {
  if (!data.priorityGapsToAddress?.length) return null;
  return (
    <div className={CARD}>
      <h2 className={TITLE}>Priority Action Items</h2>
      <div className="flex flex-col gap-3">
        {data.priorityGapsToAddress.map((g, i) => (
          <div key={i} className="flex gap-3">
            <span className="shrink-0 w-6 h-6 rounded-full bg-[#f97316] text-white text-xs font-bold flex items-center justify-center mt-0.5">
              {g.priority}
            </span>
            <div className="flex flex-col gap-1">
              <p className="text-sm font-semibold text-[#1e2229]">{g.gap}</p>
              <p className={MUTED}>{g.actionItem}</p>
              <span className="text-xs text-[#6b7280] capitalize">{g.deadline.replace(/_/g, " ")}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Section: Skills ──────────────────────────────────────────────────────────

function SkillsSection({ data }: { data: VPRFullData["skillsAnalysis"] }) {
  return (
    <div className={CARD}>
      <h2 className={TITLE}>Skills Analysis</h2>
      <div className="flex flex-col gap-2">
        {data.technicalSkills.map((s, i) => (
          <div key={i} className="flex items-start justify-between gap-3 border-b border-[#f1f5f9] pb-2 last:border-0 last:pb-0">
            <div className="flex flex-col gap-0.5 flex-1 min-w-0">
              <p className="text-sm font-semibold text-[#1e2229]">{s.skill}</p>
              <p className={MUTED}>{s.evidence}</p>
            </div>
            <div className="shrink-0 flex flex-col items-end gap-0.5">
              <span className="text-xs font-semibold text-[#1e2229] capitalize">{s.candidateLevel}</span>
              <span className="text-xs text-[#6b7280]">req: {s.requiredLevel}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Full VPR render ──────────────────────────────────────────────────────────

function FullVPRView({
  fullVpr,
  job,
  jobId,
}: {
  fullVpr: VPRFullData;
  job: JobDetail | null;
  jobId: string;
}) {
  const router = useRouter();
  const { metadata, executiveSummary, applicationStrategy, roleAlignment, experienceMapping,
    concernsAndMitigations, evidenceGaps, skillsAnalysis } = fullVpr;

  const breadcrumb = [
    { label: "Dashboard", href: "/dashboard" },
    { label: job?.title ?? "Application", href: `/dashboard/jobs/${jobId}` },
  ];

  return (
    <>
      <Topbar title="Value Proposition Report" breadcrumb={breadcrumb} />
      <main className="flex flex-col gap-6 p-6">
        {/* Page header */}
        <div className="flex items-start justify-between gap-4">
          <div className="flex flex-col gap-0.5">
            <h1 className="text-xl font-bold text-[#1e2229]">Value Proposition Report</h1>
            <p className="text-sm text-[#6b7280]">
              {metadata.candidateName} · {metadata.targetRole} at {metadata.targetCompany}
            </p>
          </div>
          <button
            onClick={() => router.push(`/dashboard/jobs/${jobId}`)}
            className="shrink-0 rounded-[8px] border border-[#cbd5e1] px-3 py-2 text-sm text-[#1e2229] hover:bg-[rgba(217,217,217,0.3)]"
          >
            ← Back to Hub
          </button>
        </div>

        <ExecSummarySection data={executiveSummary} />
        <AppStrategySection data={applicationStrategy} />
        <RoleAlignmentSection data={roleAlignment} />
        <ExperienceSection data={experienceMapping} />
        <ObjectionsSection data={concernsAndMitigations} />
        <GapsSection data={evidenceGaps} />
        <SkillsSection data={skillsAnalysis} />
      </main>
    </>
  );
}

// ─── Inner component ──────────────────────────────────────────────────────────

function VPRContent({ jobId }: { jobId: string }) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const queryId = searchParams.get("id");

  const [vpr, setVpr] = useState<VPRStatusResponse | null>(null);
  const [fullVpr, setFullVpr] = useState<VPRFullData | null>(null);
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

      const artifactId = hub?.artifacts.vpr?.artifact_id ?? queryId;
      const artifactStatus = hub?.artifacts.vpr?.status;

      if (!artifactId || (artifactStatus && artifactStatus !== "completed" && !queryId)) {
        router.replace(`/dashboard/jobs/${jobId}`);
        return;
      }

      try {
        const vprData = await api.getVPR(artifactId);
        setVpr(vprData);

        // Fetch full VPR JSON from S3
        const downloadUrl = vprData?.result?.download_url;
        if (downloadUrl) {
          const resp = await fetch(downloadUrl);
          if (resp.ok) {
            const data: VPRFullData = await resp.json();
            setFullVpr(data);
          }
        }
      } catch (err) {
        setError("Failed to load Value Proposition Report.");
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    init();
  }, [jobId, queryId, router]);

  const breadcrumb = [
    { label: "Dashboard", href: "/dashboard" },
    { label: job?.title ?? "Application", href: `/dashboard/jobs/${jobId}` },
  ];

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

  // Full rich VPR from S3
  if (fullVpr) {
    return <FullVPRView fullVpr={fullVpr} job={job} jobId={jobId} />;
  }

  // Fallback: basic summary from status endpoint
  const result = vpr?.result;
  const summary = result?.uvp || result?.strategic_narrative || "";
  const differentiators = result?.differentiators ?? [];

  return (
    <>
      <Topbar title="Value Proposition Report" breadcrumb={breadcrumb} />
      <main className="flex flex-col gap-8 p-6">
        <div className="flex items-start justify-between gap-4">
          <h1 className="text-xl font-bold text-[#1e2229]">Value Proposition Report</h1>
          <button
            onClick={() => router.push(`/dashboard/jobs/${jobId}`)}
            className="shrink-0 rounded-[8px] border border-[#cbd5e1] px-3 py-2 text-sm text-[#1e2229] hover:bg-[rgba(217,217,217,0.3)]"
          >
            ← Back to Hub
          </button>
        </div>

        {summary && (
          <div className={CARD}>
            <h2 className={TITLE}>Summary</h2>
            <p className={BODY}>{summary}</p>
          </div>
        )}

        {differentiators.length > 0 && (
          <div className={CARD}>
            <h2 className={TITLE}>Key Differentiators</h2>
            <ul className="flex flex-col gap-2 pl-1">
              {differentiators.map((d, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-[#1e2229]">
                  <span className="mt-1 shrink-0 w-1.5 h-1.5 rounded-full bg-[#f97316]" />
                  {d.text}
                </li>
              ))}
            </ul>
          </div>
        )}

        {!summary && differentiators.length === 0 && (
          <div className="rounded-[8px] border border-[#cbd5e1] bg-white px-6 py-12 text-center text-sm text-[#6b7280]">
            No VPR content available.
          </div>
        )}
      </main>
    </>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function VPRPage({
  params,
}: {
  params: Promise<{ jobId: string }>;
}) {
  const { jobId } = use(params);
  return (
    <Suspense fallback={null}>
      <VPRContent jobId={jobId} />
    </Suspense>
  );
}
