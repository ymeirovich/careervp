'use client';

import React, { useState, useEffect, Suspense } from 'react';
import { useSearchParams, useRouter, useParams } from 'next/navigation';
import { api } from '../../../../api/methods';
import { ErrorBoundary } from '../../../../components/ErrorBoundary/ErrorBoundary';
import { ExportDropdown } from '../../../../components/ExportDropdown/ExportDropdown';
import { Spinner } from '../../../../components/ui/Spinner';
import type {
  VPRStatusResponse,
  VPRFullData,
  VPRFullStrength,
  VPRFullConcern,
  VPRCoreResponsibility,
  VPRRelevantExperience,
  VPRObjection,
  JobDetail,
} from '../../../../lib/types';

// ─── Helpers ──────────────────────────────────────────────────────────────────

const CARD = 'rounded-md border border-border-default bg-card p-6 flex flex-col gap-4';
const TITLE = 'text-base font-bold text-text-primary';
const LABEL = 'text-xs font-semibold uppercase tracking-wide text-text-muted';
const BODY = 'text-sm text-text-primary leading-relaxed';
const MUTED = 'text-sm text-text-muted leading-relaxed';

function FitScoreBadge({ score }: { score: number }) {
  const color = score >= 80 ? 'bg-state-active' : score >= 60 ? 'bg-state-warning' : 'bg-state-error';
  return (
    <span
      data-testid="vpr-fit-score"
      className={`inline-flex items-center justify-center w-16 h-16 rounded-full text-white font-bold text-xl shrink-0 ${color}`}
    >
      {score}
    </span>
  );
}

function SeverityBadge({ severity }: { severity: string }) {
  const map: Record<string, string> = {
    high: 'bg-state-error/10 text-state-error',
    medium: 'bg-state-warning/10 text-state-warning',
    low: 'bg-state-active/10 text-state-active',
  };
  const cls = map[severity.toLowerCase()] ?? 'bg-surface-subtle text-text-muted';
  return (
    <span className={`inline-flex px-2 py-0.5 rounded text-xs font-semibold ${cls}`}>
      {severity}
    </span>
  );
}

function ApproachBadge({ approach }: { approach: string }) {
  const labels: Record<string, { label: string; className: string }> = {
    aggressive_apply: { label: 'Apply Aggressively', className: 'bg-state-active text-white' },
    apply_with_customization: { label: 'Apply with Customization', className: 'bg-state-warning text-white' },
    apply_cautiously: { label: 'Apply Cautiously', className: 'bg-orange-500 text-white' },
    do_not_apply: { label: 'Do Not Apply', className: 'bg-state-error text-white' },
  };
  const { label, className } = labels[approach] ?? { label: approach, className: 'bg-surface-subtle text-text-muted' };
  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-semibold ${className}`}>
      {label}
    </span>
  );
}

function AlignmentBar({ score }: { score: number }) {
  const colorClass = score >= 85 ? 'bg-state-active' : score >= 70 ? 'bg-state-warning' : 'bg-orange-500';
  const textClass = score >= 85 ? 'text-state-active' : score >= 70 ? 'text-state-warning' : 'text-orange-500';
  return (
    <div className="flex items-center gap-2 shrink-0">
      <div className="w-20 h-1.5 bg-border-default rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${colorClass}`} style={{ width: `${score}%` }} />
      </div>
      <span className={`text-xs font-semibold ${textClass}`}>{score}</span>
    </div>
  );
}

function ExecSummarySection({ data }: { data: VPRFullData['executiveSummary'] }) {
  return (
    <div className={CARD} data-testid="vpr-exec-summary">
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
        <div className="flex flex-col gap-3">
          <p className={LABEL}>Top Strengths</p>
          <div className="flex flex-col gap-3">
            {data.topThreeStrengths.map((s: VPRFullStrength, i: number) => (
              <div key={i} className="flex flex-col gap-1 border-l-2 border-state-active pl-3">
                <p className="text-sm font-semibold text-text-primary">{s.strength}</p>
                <p className={MUTED}>{s.evidence}</p>
                <p className="text-xs text-state-active">{s.relevanceToRole}</p>
              </div>
            ))}
          </div>
        </div>
        <div className="flex flex-col gap-3">
          <p className={LABEL}>Concerns</p>
          <div className="flex flex-col gap-3">
            {data.topThreeConcerns.map((c: VPRFullConcern, i: number) => (
              <div key={i} className="flex flex-col gap-1 border-l-2 border-state-warning pl-3">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-semibold text-text-primary flex-1">{c.concern}</p>
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

function AppStrategySection({ data }: { data: VPRFullData['applicationStrategy'] }) {
  return (
    <div className={CARD}>
      <h2 className={TITLE}>Application Strategy</h2>
      <div className="flex flex-col gap-1">
        <p className={LABEL}>Messaging Approach</p>
        <p className={BODY}>{data.messagingApproach}</p>
      </div>
      <div className="flex flex-col gap-1">
        <p className={LABEL}>CV Opening Line</p>
        <div className="rounded-md bg-surface-subtle border border-border-default p-3">
          <p className={BODY}>{data.cvLeadDifferentiator}</p>
        </div>
      </div>
      <div className="flex flex-col gap-2">
        <p className={LABEL}>ATS Keywords</p>
        <div className="flex flex-wrap gap-1.5">
          {data.atsKeywords.primary.map((kw: string) => (
            <span key={kw} className="px-2 py-0.5 rounded-full text-xs font-medium bg-state-info/10 text-state-info border border-state-info/30">
              {kw}
            </span>
          ))}
        </div>
        <div className="flex flex-wrap gap-1.5">
          {data.atsKeywords.secondary.map((kw: string) => (
            <span key={kw} className="px-2 py-0.5 rounded-full text-xs font-medium bg-surface-subtle text-text-muted">
              {kw}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

function RoleAlignmentSection({ data }: { data: VPRFullData['roleAlignment'] }) {
  return (
    <div className={CARD}>
      <h2 className={TITLE}>Role Alignment</h2>
      <div className="flex flex-col gap-3">
        {data.coreResponsibilities.map((r: VPRCoreResponsibility, i: number) => (
          <div key={i} className="flex flex-col gap-1.5 border-b border-border-subtle pb-3 last:border-0 last:pb-0">
            <div className="flex items-start justify-between gap-3">
              <p className="text-sm font-semibold text-text-primary flex-1">{r.responsibility}</p>
              <AlignmentBar score={r.alignmentScore} />
            </div>
            <ul className="flex flex-col gap-0.5 pl-3">
              {r.candidateEvidence.map((e: string, j: number) => (
                <li key={j} className="flex items-start gap-1.5 text-sm text-text-muted">
                  <span className="mt-1.5 shrink-0 w-1 h-1 rounded-full bg-primary-action" />
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

function ExperienceSection({ data }: { data: VPRFullData['experienceMapping'] }) {
  return (
    <div className={CARD}>
      <h2 className={TITLE}>Experience Mapping</h2>
      <div className="flex flex-col gap-4">
        {data.relevantExperiences.map((exp: VPRRelevantExperience, i: number) => (
          <div key={i} className="flex flex-col gap-2 border-b border-border-subtle pb-4 last:border-0 last:pb-0">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-bold text-text-primary">{exp.role}</p>
                <p className={MUTED}>{exp.organization} · {exp.duration}</p>
              </div>
              <AlignmentBar score={exp.relevanceScore} />
            </div>
            <p className="text-xs text-state-info">{exp.relevanceToTargetRole}</p>
            <div className="flex flex-col gap-1">
              {exp.keyAchievements.map((a, j) => (
                <div key={j} className="flex items-start gap-2 text-sm">
                  <span className="mt-1 shrink-0 w-1.5 h-1.5 rounded-full bg-primary-action" />
                  <span className="text-text-primary">{a.achievement}</span>
                  <span className="text-text-muted shrink-0">— {a.metric}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ObjectionsSection({ data }: { data: VPRFullData['concernsAndMitigations'] }) {
  return (
    <div className={CARD}>
      <h2 className={TITLE}>Objections & Responses</h2>
      <div className="flex flex-col gap-4">
        {data.likelyObjections.map((o: VPRObjection, i: number) => (
          <div key={i} className="flex flex-col gap-2 border-b border-border-subtle pb-4 last:border-0 last:pb-0">
            <div className="flex items-start justify-between gap-3">
              <p className="text-sm font-semibold text-text-primary flex-1">{o.objection}</p>
              <span className="text-xs text-text-muted shrink-0 capitalize">{o.likelihood}</span>
            </div>
            <div className="rounded-md bg-state-active/5 border border-state-active/30 p-3">
              <p className="text-xs font-semibold text-state-active mb-1 uppercase tracking-wide">Response Script</p>
              <p className={BODY}>{o.mitigation.messaging}</p>
            </div>
            <p className="text-xs text-text-muted">Address in: {o.whereToAddress.join(', ')}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function GapsSection({ data }: { data: VPRFullData['evidenceGaps'] }) {
  if (!data.priorityGapsToAddress?.length) return null;
  return (
    <div className={CARD}>
      <h2 className={TITLE}>Priority Action Items</h2>
      <div className="flex flex-col gap-3">
        {data.priorityGapsToAddress.map((g, i) => (
          <div key={i} className="flex gap-3">
            <span className="shrink-0 w-6 h-6 rounded-full bg-primary-action text-white text-xs font-bold flex items-center justify-center mt-0.5">
              {g.priority}
            </span>
            <div className="flex flex-col gap-1">
              <p className="text-sm font-semibold text-text-primary">{g.gap}</p>
              <p className={MUTED}>{g.actionItem}</p>
              <span className="text-xs text-text-muted capitalize">{g.deadline.replace(/_/g, ' ')}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function SkillsSection({ data }: { data: VPRFullData['skillsAnalysis'] }) {
  return (
    <div className={CARD}>
      <h2 className={TITLE}>Skills Analysis</h2>
      <div className="flex flex-col gap-2">
        {data.technicalSkills.map((s, i) => (
          <div key={i} className="flex items-start justify-between gap-3 border-b border-border-subtle pb-2 last:border-0 last:pb-0">
            <div className="flex flex-col gap-0.5 flex-1 min-w-0">
              <p className="text-sm font-semibold text-text-primary">{s.skill}</p>
              <p className={MUTED}>{s.evidence}</p>
            </div>
            <div className="shrink-0 flex flex-col items-end gap-0.5">
              <span className="text-xs font-semibold text-text-primary capitalize">{s.candidateLevel}</span>
              <span className="text-xs text-text-muted">req: {s.requiredLevel}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Inner component (needs Suspense for useSearchParams) ─────────────────────

function VPRContent({ jobId }: { jobId: string }) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const queryId = searchParams.get('id');

  const [vpr, setVpr] = useState<VPRStatusResponse | null>(null);
  const [fullVpr, setFullVpr] = useState<VPRFullData | null>(null);
  const [job, setJob] = useState<JobDetail | null>(null);
  const [artifactId, setArtifactId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const init = async () => {
      setLoading(true);
      const [hubResult, jobResult] = await Promise.allSettled([
        api.getApplication(jobId),
        api.getJob(jobId),
      ]);

      const hub = hubResult.status === 'fulfilled' ? hubResult.value : null;
      const jobData = jobResult.status === 'fulfilled' ? jobResult.value : null;
      setJob(jobData);

      const resolvedArtifactId = hub?.artifacts.vpr?.artifact_id ?? queryId;
      const artifactStatus = hub?.artifacts.vpr?.status;

      if (!resolvedArtifactId || (artifactStatus && artifactStatus !== 'completed' && !queryId)) {
        router.replace(`/applications/${jobId}`);
        return;
      }

      setArtifactId(resolvedArtifactId);

      try {
        const vprData = await api.getVPR(resolvedArtifactId);
        setVpr(vprData);

        const downloadUrl = vprData?.result?.download_url;
        if (downloadUrl) {
          const resp = await fetch(downloadUrl);
          if (resp.ok) {
            const data: VPRFullData = await resp.json();
            setFullVpr(data);
          }
        }
      } catch (err) {
        setError('Failed to load Value Proposition Report.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    void init();
  }, [jobId, queryId, router]);

  const backButton = (
    <button
      onClick={() => router.push(`/applications/${jobId}`)}
      className="shrink-0 rounded-md border border-border-default px-3 py-2 text-sm text-text-primary hover:bg-surface-subtle"
    >
      ← Back to Hub
    </button>
  );

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner size="lg" aria-label="Loading Value Proposition Report…" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col gap-6">
        <div className="flex items-start justify-between gap-4">
          <h1 className="text-xl font-bold text-text-primary">Value Proposition Report</h1>
          {backButton}
        </div>
        <div className="rounded-md bg-state-error/10 border border-state-error px-4 py-3 text-sm text-state-error">
          {error}
        </div>
      </div>
    );
  }

  const jobTitle = job?.title ?? 'Application';
  const jobCompany = job?.company_name ?? '';

  return (
    <div className="flex flex-col gap-6" data-testid="vpr-page">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="flex flex-col gap-0.5">
          <h1 className="text-xl font-bold text-text-primary">Value Proposition Report</h1>
          {fullVpr && (
            <p className="text-sm text-text-muted">
              {fullVpr.metadata.candidateName} · {fullVpr.metadata.targetRole} at {fullVpr.metadata.targetCompany}
            </p>
          )}
          {!fullVpr && jobTitle && (
            <p className="text-sm text-text-muted">{jobTitle}{jobCompany ? ` at ${jobCompany}` : ''}</p>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {artifactId && (
            <ExportDropdown jobId={jobId} moduleType="vpr" artifactId={artifactId} />
          )}
          {backButton}
        </div>
      </div>

      {fullVpr ? (
        <>
          <ExecSummarySection data={fullVpr.executiveSummary} />
          <AppStrategySection data={fullVpr.applicationStrategy} />
          <RoleAlignmentSection data={fullVpr.roleAlignment} />
          <ExperienceSection data={fullVpr.experienceMapping} />
          <ObjectionsSection data={fullVpr.concernsAndMitigations} />
          <GapsSection data={fullVpr.evidenceGaps} />
          <SkillsSection data={fullVpr.skillsAnalysis} />
        </>
      ) : (
        <>
          {(vpr?.result?.uvp ?? vpr?.result?.strategic_narrative) && (
            <div className={CARD}>
              <h2 className={TITLE}>Summary</h2>
              <p className={BODY}>{vpr?.result?.uvp ?? vpr?.result?.strategic_narrative}</p>
            </div>
          )}
          {(vpr?.result?.differentiators ?? []).length > 0 && (
            <div className={CARD}>
              <h2 className={TITLE}>Key Differentiators</h2>
              <ul className="flex flex-col gap-2 pl-1">
                {(vpr?.result?.differentiators ?? []).map((d, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-text-primary">
                    <span className="mt-1 shrink-0 w-1.5 h-1.5 rounded-full bg-primary-action" />
                    {d.text}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {!vpr?.result?.uvp && !vpr?.result?.strategic_narrative && (
            <div className="rounded-md border border-border-default bg-card px-6 py-12 text-center text-sm text-text-muted">
              No VPR content available.
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default function VPRPage({ params: _params }: { params: Promise<{ id: string }> }) {
  const { id: jobId } = useParams<{ id: string }>();
  return (
    <ErrorBoundary cloudwatchKey="vpr-page">
      <Suspense fallback={<div className="flex justify-center py-12"><Spinner size="lg" aria-label="Loading…" /></div>}>
        <VPRContent jobId={jobId} />
      </Suspense>
    </ErrorBoundary>
  );
}
