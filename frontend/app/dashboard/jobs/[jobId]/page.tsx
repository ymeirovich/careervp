"use client";

import { useState, useEffect, useCallback, use } from "react";
import { api } from "@/lib/api";
import { Topbar } from "@/components/dashboard/Topbar";
import { ResourceCard } from "@/components/dashboard/ResourceCard";
import { Badge } from "@/components/ui/Badge";
import { cn } from "@/lib/utils";
import type {
  ApplicationHubData,
  UserCV,
  CompanyResearchResult,
  JobDetail,
} from "@/lib/types";

// ─── Page ─────────────────────────────────────────────────────────────────────
export default function ApplicationHubPage({
  params,
}: {
  params: Promise<{ jobId: string }>;
}) {
  const { jobId } = use(params);

  const [hub, setHub] = useState<ApplicationHubData | null>(null);
  const [job, setJob] = useState<JobDetail | null>(null);
  const [cv, setCv] = useState<UserCV | null>(null);
  const [research, setResearch] = useState<CompanyResearchResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(false);

  // Polling task IDs
  const [vprTaskId, setVprTaskId] = useState<string | null>(null);
  const [clTaskId, setClTaskId] = useState<string | null>(null);
  const [ipTaskId, setIpTaskId] = useState<string | null>(null);
  const [cvTaskId, setCvTaskId] = useState<string | null>(null);

  // Completed artifact IDs (session-local, because backend may not update artifact_statuses)
  const [cvTailoredId, setCvTailoredId] = useState<string | null>(null);
  const [vprLocalId, setVprLocalId] = useState<string | null>(null);
  const [clLocalId, setClLocalId] = useState<string | null>(null);
  const [ipLocalId, setIpLocalId] = useState<string | null>(null);

  // Action in-flight
  const [generatingVpr, setGeneratingVpr] = useState(false);
  const [generatingCl, setGeneratingCl] = useState(false);
  const [generatingIp, setGeneratingIp] = useState(false);
  const [generatingResearch, setGeneratingResearch] = useState(false);
  const [generatingCv, setGeneratingCv] = useState(false);

  const refreshHub = useCallback(async () => {
    const data = await api.getApplication(jobId);
    setHub(data);
    return data;
  }, [jobId]);

  // Initial load
  useEffect(() => {
    const init = async () => {
      setLoading(true);
      const [hubResult, cvResult, jobResult, researchResult] =
        await Promise.allSettled([
          api.getApplication(jobId),
          api.getCV(),
          api.getJob(jobId),
          api.getCompanyResearch(jobId),
        ]);

      const hubData =
        hubResult.status === "fulfilled" ? hubResult.value : null;
      const cvData = cvResult.status === "fulfilled" ? cvResult.value : null;
      const jobData =
        jobResult.status === "fulfilled" ? jobResult.value : null;
      const researchData =
        researchResult.status === "fulfilled" ? researchResult.value : null;

      setHub(hubData);
      setCv(cvData);
      setJob(jobData);
      setResearch(researchData);

      // Resume in-progress polls
      if (
        hubData?.artifacts.vpr?.status === "processing" &&
        hubData.artifacts.vpr.artifact_id
      ) {
        setVprTaskId(hubData.artifacts.vpr.artifact_id);
      }
      if (
        hubData?.artifacts.cover_letter?.status === "processing" &&
        hubData.artifacts.cover_letter.artifact_id
      ) {
        setClTaskId(hubData.artifacts.cover_letter.artifact_id);
      }
      if (
        hubData?.artifacts.interview_prep?.status === "processing" &&
        hubData.artifacts.interview_prep.artifact_id
      ) {
        setIpTaskId(hubData.artifacts.interview_prep.artifact_id);
      }
      if (
        hubData?.artifacts.cv_tailored?.status === "processing" &&
        hubData.artifacts.cv_tailored.artifact_id
      ) {
        setCvTaskId(hubData.artifacts.cv_tailored.artifact_id);
      }

      setLoading(false);
    };
    init();
  }, [jobId]);

  // VPR polling
  useEffect(() => {
    if (!vprTaskId) return;
    const interval = setInterval(async () => {
      try {
        const result = await api.pollVPRStatus(vprTaskId);
        if (result.status === "completed" || result.status === "failed") {
          clearInterval(interval);
          if (result.status === "completed") {
            setVprLocalId(vprTaskId);
          }
          setVprTaskId(null);
          refreshHub();
        }
      } catch {
        // ignore transient poll errors
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [vprTaskId, refreshHub]);

  // Cover Letter polling
  useEffect(() => {
    if (!clTaskId) return;
    const interval = setInterval(async () => {
      try {
        const result = await api.pollCoverLetterStatus(clTaskId);
        if (result.status === "completed" || result.status === "failed") {
          clearInterval(interval);
          if (result.status === "completed") {
            setClLocalId(clTaskId);
          }
          setClTaskId(null);
          refreshHub();
        }
      } catch {
        // ignore transient poll errors
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [clTaskId, refreshHub]);

  // Interview Prep polling
  useEffect(() => {
    if (!ipTaskId) return;
    const interval = setInterval(async () => {
      try {
        const result = await api.pollInterviewPrepStatus(ipTaskId);
        if (result.status === "completed" || result.status === "failed") {
          clearInterval(interval);
          if (result.status === "completed") {
            setIpLocalId(ipTaskId);
          }
          setIpTaskId(null);
          refreshHub();
        }
      } catch {
        // ignore transient poll errors
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [ipTaskId, refreshHub]);

  // CV Tailored polling
  useEffect(() => {
    if (!cvTaskId) return;
    const interval = setInterval(async () => {
      try {
        const result = await api.pollCVTailored(cvTaskId);
        if (result.status === "completed" || result.status === "failed") {
          clearInterval(interval);
          if (result.status === "completed") {
            setCvTailoredId(cvTaskId);
          }
          setCvTaskId(null);
          refreshHub();
        }
      } catch {
        // ignore transient poll errors
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [cvTaskId, refreshHub]);

  // ── Generate handlers ────────────────────────────────────────────────────────

  const handleGenerateVpr = async () => {
    if (!cv?.cv_id) return;
    const gapResponseIds =
      hub?.gap_analysis.responses.map((r) => r.question_id) ?? [];
    setGeneratingVpr(true);
    try {
      const task = await api.generateVPR({
        job_id: jobId,
        cv_id: cv.cv_id,
        gap_response_ids: gapResponseIds,
      });
      setVprTaskId(task.request_id);
      setHub((prev) =>
        prev
          ? {
              ...prev,
              artifacts: {
                ...prev.artifacts,
                vpr: { status: "processing", artifact_id: null },
              },
            }
          : prev
      );
    } catch (err) {
      console.error("Generate VPR error:", err);
    } finally {
      setGeneratingVpr(false);
    }
  };

  const handleGenerateCoverLetter = async () => {
    if (!cv?.cv_id || !hub || !research?.id) return;
    const vprId = hub.artifacts.vpr?.artifact_id ?? vprLocalId;
    if (!vprId) return;
    const gapResponseIds = hub.gap_analysis.responses.map((r) => r.question_id);
    setGeneratingCl(true);
    try {
      const task = await api.generateCoverLetter({
        job_id: jobId,
        cv_id: cv.cv_id,
        vpr_id: vprId,
        company_research_id: research.id,
        gap_response_ids: gapResponseIds,
      });
      setClTaskId(task.request_id);
      setHub((prev) =>
        prev
          ? {
              ...prev,
              artifacts: {
                ...prev.artifacts,
                cover_letter: { status: "processing", artifact_id: null },
              },
            }
          : prev
      );
    } catch (err) {
      console.error("Generate Cover Letter error:", err);
    } finally {
      setGeneratingCl(false);
    }
  };

  const handleGenerateInterviewPrep = async () => {
    if (!hub) return;
    const vprId = hub.artifacts.vpr?.artifact_id ?? vprLocalId;
    if (!vprId) return;
    const gapResponseIds = hub.gap_analysis.responses.map((r) => r.question_id);
    setGeneratingIp(true);
    try {
      const task = await api.generateInterviewPrep({
        vpr_id: vprId,
        gap_response_ids: gapResponseIds,
        job_id: jobId,
      });
      setIpTaskId(task.request_id);
      setHub((prev) =>
        prev
          ? {
              ...prev,
              artifacts: {
                ...prev.artifacts,
                interview_prep: { status: "processing", artifact_id: null },
              },
            }
          : prev
      );
    } catch (err) {
      console.error("Generate Interview Prep error:", err);
    } finally {
      setGeneratingIp(false);
    }
  };

  const handleGenerateResearch = async () => {
    const companyName = hub?.job.company_name ?? job?.company_name;
    if (!companyName) return;
    setGeneratingResearch(true);
    try {
      await api.fetchCompanyResearch({
        job_id: jobId,
        company_name: companyName,
      });
      const researchData = await api.getCompanyResearch(jobId);
      setResearch(researchData);
    } catch (err) {
      console.error("Company research error:", err);
    } finally {
      setGeneratingResearch(false);
    }
  };

  const handleGenerateCV = async () => {
    if (!cv?.cv_id) return;
    const vprId = hub?.artifacts.vpr?.artifact_id ?? undefined;
    setGeneratingCv(true);
    try {
      const task = await api.generateCV({
        job_id: jobId,
        cv_id: cv.cv_id,
        vpr_id: vprId,
      });
      setCvTaskId(task.request_id);
      setHub((prev) =>
        prev
          ? {
              ...prev,
              artifacts: {
                ...prev.artifacts,
                cv_tailored: { status: "processing", artifact_id: null },
              },
            }
          : prev
      );
    } catch (err) {
      console.error("Generate CV error:", err);
    } finally {
      setGeneratingCv(false);
    }
  };

  // ── Derived state ────────────────────────────────────────────────────────────

  const displayJob = hub?.job ?? job;
  const vprArtifact = hub?.artifacts.vpr;
  const clArtifact = hub?.artifacts.cover_letter;
  const ipArtifact = hub?.artifacts.interview_prep;
  const cvTailoredArtifact = hub?.artifacts.cv_tailored;

  const vprStatus = vprArtifact?.status ?? "not_started";
  const clStatus = clArtifact?.status ?? "not_started";
  const ipStatus = ipArtifact?.status ?? "not_started";

  // Session-local artifact IDs: hub won't update artifact_statuses until app reload
  // so we track the IDs locally when polling completes.
  const vprArtifactId = vprArtifact?.artifact_id ?? vprLocalId;
  const clArtifactId = clArtifact?.artifact_id ?? clLocalId;
  const ipArtifactId = ipArtifact?.artifact_id ?? ipLocalId;

  const vprReady = vprStatus === "completed" || !!vprLocalId;
  const clReady = clStatus === "completed" || !!clLocalId;
  const ipReady = ipStatus === "completed" || !!ipLocalId;

  const gapQuestions = hub?.gap_analysis.questions ?? [];
  const gapResponses = hub?.gap_analysis.responses ?? [];

  // Application state is the authoritative signal for gap completion.
  // gap_questions are stored in a separate table and may not appear in the hub
  // record, so we also accept "responses exist" as a completion signal.
  const appState = hub?.application?.state ?? "";
  const gapSubmittedByState = ["gap_responses_submitted", "artifacts_generating", "artifacts_completed"].includes(appState);
  const gapComplete =
    gapSubmittedByState ||
    (gapResponses.length > 0 &&
      (gapQuestions.length === 0 || gapResponses.length >= gapQuestions.length));
  const gapInProgress =
    !gapComplete && gapQuestions.length > 0 && gapResponses.length > 0;

  const cvSelected = !!cv?.cv_id;
  const vprProcessing = vprStatus === "processing" || !!vprTaskId;
  const clProcessing = clStatus === "processing" || !!clTaskId;
  const ipProcessing = ipStatus === "processing" || !!ipTaskId;
  const cvProcessing =
    cvTailoredArtifact?.status === "processing" || !!cvTaskId;

  // Tailored CV artifact ID: prefer hub's artifact_id, fall back to session-local
  const cvTailoredArtifactId =
    cvTailoredArtifact?.artifact_id ?? cvTailoredId;
  const cvTailoredReady =
    cvTailoredArtifact?.status === "completed" || !!cvTailoredId;

  // ── Render ───────────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <>
        <Topbar
          title="Loading…"
          breadcrumb={[{ label: "Dashboard", href: "/dashboard" }]}
        />
        <main className="flex flex-col gap-6 p-6">
          <div className="text-sm text-[#6b7280]">Loading application…</div>
        </main>
      </>
    );
  }

  if (!displayJob) {
    return (
      <>
        <Topbar
          title="Application"
          breadcrumb={[{ label: "Dashboard", href: "/dashboard" }]}
        />
        <main className="flex flex-col gap-6 p-6">
          <div className="text-sm text-[#6b7280]">Job not found.</div>
        </main>
      </>
    );
  }

  const jobStatusVariant =
    displayJob.status?.toLowerCase() === "active" ? "green" : "gray";

  return (
    <>
      <Topbar
        title={displayJob.title}
        breadcrumb={[{ label: "Dashboard", href: "/dashboard" }]}
      />
      <main className="flex flex-col gap-6 p-6">
        {/* Job Header */}
        <div className="rounded-[8px] border border-[#cbd5e1] bg-white p-6 flex flex-col gap-3">
          <div className="flex items-start justify-between gap-4">
            <div className="flex flex-col gap-1 min-w-0">
              <span className="text-2xl font-bold text-[#1e2229] leading-tight">
                {displayJob.title}
              </span>
              <span className="text-lg text-[#6b7280]">
                {displayJob.company_name}
              </span>
            </div>
            <Badge variant={jobStatusVariant} size="md">
              <span className="capitalize">{displayJob.status}</span>
            </Badge>
          </div>

          {displayJob.url && (
            <a
              href={displayJob.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-[#f97316] hover:underline w-fit"
            >
              View Job Posting ↗
            </a>
          )}

          {displayJob.description && (
            <div>
              <p
                className={cn(
                  "text-sm text-[#6b7280] leading-relaxed",
                  !expanded && "line-clamp-3"
                )}
              >
                {displayJob.description}
              </p>
              <button
                onClick={() => setExpanded(!expanded)}
                className="text-xs text-[#f97316] hover:underline mt-1"
              >
                {expanded ? "Show less" : "Show more"}
              </button>
            </div>
          )}
        </div>

        {/* Resource Grid — follows the application workflow top to bottom */}
        <div className="grid grid-cols-2 gap-4">

          {/* ① Company Research */}
          <ResourceCard
            title="Company Research"
            description={
              research
                ? research.company_name ?? displayJob.company_name
                : "Generate company intelligence"
            }
            status={research ? "ready" : "not_started"}
            statusLabel={research ? "Ready" : undefined}
            preview={research?.mission ?? undefined}
            primaryAction={{
              label: research ? "Regenerate" : "Generate",
              onClick: handleGenerateResearch,
              loading: generatingResearch,
            }}
          />

          {/* ② Base CV */}
          <ResourceCard
            title="Base CV"
            description={
              cv
                ? `${cv.full_name} · ${cv.language === "he" ? "Hebrew" : "English"}`
                : "No CV uploaded"
            }
            status={cv ? "ready" : "not_started"}
            primaryAction={{
              label: cv ? "Change CV" : "Upload CV",
              href: "/dashboard/cv",
            }}
          />

          {/* ③ Gap Analysis */}
          <ResourceCard
            title="Gap Analysis"
            description={
              !cvSelected
                ? "Select a CV first"
                : gapComplete
                  ? `${gapResponses.length} questions answered ✓`
                  : gapInProgress
                    ? `${gapResponses.length} of ${gapQuestions.length} questions answered`
                    : "Identify qualification gaps"
            }
            status={
              gapComplete ? "ready" : gapInProgress ? "partial" : "not_started"
            }
            primaryAction={{
              label: gapComplete
                ? "Edit Responses"
                : gapInProgress
                  ? "Continue Answering"
                  : "Start Gap Analysis",
              href: cvSelected
                ? `/dashboard/jobs/${jobId}/gap-analysis`
                : undefined,
              disabled: !cvSelected,
            }}
            dependency={!cvSelected ? "Select a CV first" : undefined}
          />

          {/* ④ Tailored CV */}
          <ResourceCard
            title="Tailored CV"
            description={
              cvTailoredReady
                ? "Your tailored CV is ready"
                : cvProcessing
                  ? "Tailoring your CV…"
                  : "Generate a CV tailored for this role"
            }
            status={
              cvTailoredReady
                ? "ready"
                : cvProcessing
                  ? "processing"
                  : "not_started"
            }
            statusLabel={cvTailoredReady ? "Ready" : undefined}
            primaryAction={{
              label: cvProcessing
                ? "Generating…"
                : cvTailoredReady
                  ? "Regenerate"
                  : "Generate CV",
              onClick: handleGenerateCV,
              loading: generatingCv || cvProcessing,
              disabled: !cvSelected || !gapComplete || cvProcessing,
            }}
            secondaryAction={
              cvTailoredArtifactId
                ? {
                    label: "Edit",
                    href: `/dashboard/jobs/${jobId}/cv-tailored?id=${cvTailoredArtifactId}`,
                  }
                : undefined
            }
            dependency={
              !cvSelected
                ? "Select a CV first"
                : !gapComplete
                  ? "Complete Gap Analysis first"
                  : undefined
            }
          />

          {/* ⑤ VPR */}
          <ResourceCard
            title="Value Proposition Report"
            description={
              vprReady
                ? "Your positioning brief is ready"
                : vprProcessing
                  ? "Generating your positioning brief…"
                  : "Generate your positioning brief"
            }
            status={
              vprReady ? "ready" : vprProcessing ? "processing" : "not_started"
            }
            statusLabel={vprReady ? "Ready" : undefined}
            primaryAction={{
              label: vprProcessing
                ? "Generating…"
                : vprReady
                  ? "Regenerate"
                  : "Generate VPR",
              onClick: handleGenerateVpr,
              loading: generatingVpr || vprProcessing,
              disabled: !cvSelected || !gapComplete || vprProcessing,
            }}
            secondaryAction={
              vprArtifactId
                ? {
                    label: "Edit",
                    href: `/dashboard/jobs/${jobId}/vpr?id=${vprArtifactId}`,
                  }
                : undefined
            }
            dependency={
              !cvSelected
                ? "Select a CV first"
                : !gapComplete
                  ? "Complete Gap Analysis first"
                  : undefined
            }
          />

          {/* ⑥ Cover Letter */}
          <ResourceCard
            title="Cover Letter"
            description={
              clReady
                ? "Your cover letter is ready"
                : clProcessing
                  ? "Generating your letter…"
                  : "Draft your application letter"
            }
            status={
              clReady
                ? "ready"
                : clProcessing
                  ? "processing"
                  : "not_started"
            }
            statusLabel={clReady ? "Ready" : undefined}
            primaryAction={{
              label: clProcessing
                ? "Generating…"
                : clReady
                  ? "Regenerate"
                  : "Generate Cover Letter",
              onClick: handleGenerateCoverLetter,
              loading: generatingCl || clProcessing,
              disabled: !vprReady || clProcessing,
            }}
            secondaryAction={
              clArtifactId
                ? {
                    label: "Edit",
                    href: `/dashboard/jobs/${jobId}/cover-letter?id=${clArtifactId}`,
                  }
                : undefined
            }
            dependency={!vprReady ? "Generate VPR first" : undefined}
          />

          {/* ⑦ Interview Prep */}
          <ResourceCard
            title="Interview Prep"
            description={
              ipReady
                ? "Your interview prep is ready"
                : ipProcessing
                  ? "Generating interview questions…"
                  : "Prepare for your interview"
            }
            status={
              ipReady
                ? "ready"
                : ipProcessing
                  ? "processing"
                  : "not_started"
            }
            statusLabel={ipReady ? "Ready" : undefined}
            primaryAction={{
              label: ipProcessing
                ? "Generating…"
                : ipReady
                  ? "Regenerate"
                  : "Generate Prep",
              onClick: handleGenerateInterviewPrep,
              loading: generatingIp || ipProcessing,
              disabled: !vprReady || ipProcessing,
            }}
            secondaryAction={
              ipArtifactId
                ? {
                    label: "Edit",
                    href: `/dashboard/jobs/${jobId}/interview-prep?id=${ipArtifactId}`,
                  }
                : undefined
            }
            dependency={!vprReady ? "Generate VPR first" : undefined}
          />
        </div>
      </main>
    </>
  );
}
