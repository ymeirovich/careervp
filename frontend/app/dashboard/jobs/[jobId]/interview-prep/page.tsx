"use client";

import { useState, useEffect, use } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { Topbar } from "@/components/dashboard/Topbar";
import type { PrepQuestion, JobDetail } from "@/lib/types";

// ─── Types ────────────────────────────────────────────────────────────────────

type PrepResult = NonNullable<
  Awaited<ReturnType<typeof api.getInterviewPrep>>["result"]
>;

// ─── Helpers ──────────────────────────────────────────────────────────────────

const CARD = "rounded-[8px] border border-[#cbd5e1] bg-white p-6 flex flex-col gap-4";
const TITLE = "text-base font-bold text-[#1e2229]";

function questionTypeBadge(type: string) {
  const map: Record<string, { bg: string; text: string; label: string }> = {
    behavioral:  { bg: "#eff6ff", text: "#3b82f6", label: "Behavioral" },
    technical:   { bg: "#f5f3ff", text: "#8b5cf6", label: "Technical" },
    situational: { bg: "#fffbeb", text: "#f59e0b", label: "Situational" },
    gap_focused: { bg: "#fff7ed", text: "#f97316", label: "Gap-Focused" },
  };
  const c = map[type.toLowerCase()] ?? { bg: "#f0f2f5", text: "#6b7280", label: type };
  return (
    <span
      className="px-2 py-0.5 text-xs font-medium rounded-[4px]"
      style={{ background: c.bg, color: c.text }}
    >
      {c.label}
    </span>
  );
}

// ─── Question Card ─────────────────────────────────────────────────────────────

function QuestionCard({ q, index }: { q: PrepQuestion; index: number }) {
  const [expanded, setExpanded] = useState(false);
  const sa = q.suggested_answer;
  const starKeys = ["situation", "task", "action", "result"] as const;
  const hasStar = sa && starKeys.some((k) => sa[k]);

  return (
    <div className="flex flex-col rounded-[8px] border border-[#e2e8f0] overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-start justify-between gap-3 px-4 py-3 text-left hover:bg-[#f9fafb] transition-colors"
      >
        <div className="flex items-start gap-2 min-w-0">
          <span className="shrink-0 text-sm font-medium text-[#6b7280]">
            {index + 1}.
          </span>
          <span className="text-sm font-medium text-[#1e2229] leading-snug">
            {q.text}
          </span>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {questionTypeBadge(q.question_type)}
          <span className="text-xs text-[#9ca3af]">{expanded ? "▲" : "▼"}</span>
        </div>
      </button>

      {/* Body */}
      {expanded && (
        <div className="border-t border-[#e2e8f0] px-4 py-4 flex flex-col gap-3 bg-[#fafafa]">
          {hasStar && (
            <div className="flex flex-col gap-2">
              <p className="text-xs font-semibold text-[#6b7280] uppercase tracking-wide">
                Suggested STAR Answer
              </p>
              {starKeys.map((key) => {
                const val = sa?.[key as keyof typeof sa];
                if (!val) return null;
                return (
                  <div key={key} className="flex gap-2 text-sm">
                    <span className="shrink-0 font-semibold text-[#f97316] w-20 capitalize">
                      {key}:
                    </span>
                    <span className="text-[#1e2229] leading-relaxed">{val as string}</span>
                  </div>
                );
              })}
            </div>
          )}
          {!hasStar && (
            <p className="text-xs text-[#9ca3af] italic">No suggested answer provided.</p>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function InterviewPrepPage({
  params,
}: {
  params: Promise<{ jobId: string }>;
}) {
  const { jobId } = use(params);
  const router = useRouter();

  const [prep, setPrep] = useState<PrepResult | null>(null);
  const [job, setJob] = useState<JobDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [checkedItems, setCheckedItems] = useState<Record<number, boolean>>({});

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

      const artifactId = hub?.artifacts.interview_prep?.artifact_id;
      const artifactStatus = hub?.artifacts.interview_prep?.status;

      if (!artifactId || artifactStatus !== "completed") {
        router.replace(`/dashboard/jobs/${jobId}`);
        return;
      }

      try {
        const data = await api.getInterviewPrep(artifactId);
        if (!data.result) {
          router.replace(`/dashboard/jobs/${jobId}`);
          return;
        }
        setPrep(data.result);
      } catch (err) {
        setError("Failed to load interview prep.");
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    init();
  }, [jobId, router]);

  const breadcrumb = [
    { label: "Dashboard", href: "/dashboard" },
    {
      label: job?.title ?? "Application",
      href: `/dashboard/jobs/${jobId}`,
    },
  ];

  if (loading) {
    return (
      <>
        <Topbar title="Interview Prep" breadcrumb={breadcrumb} />
        <main className="flex flex-col gap-6 p-6">
          <div className="text-sm text-[#6b7280]">Loading…</div>
        </main>
      </>
    );
  }

  if (error) {
    return (
      <>
        <Topbar title="Interview Prep" breadcrumb={breadcrumb} />
        <main className="flex flex-col gap-6 p-6">
          <div className="rounded-[8px] bg-[#fef2f2] border border-[#ef4444] px-4 py-3 text-sm text-[#ef4444]">
            {error}
          </div>
        </main>
      </>
    );
  }

  const questions = prep?.questions ?? [];
  const questionsToAsk = prep?.questions_to_ask ?? [];
  const checklist = prep?.pre_interview_checklist ?? [];
  const salaryGuidance = prep?.salary_guidance;

  return (
    <>
      <Topbar title="Interview Prep" breadcrumb={breadcrumb} />
      <main className="flex flex-col gap-6 p-6">
        {/* Page Header */}
        <div className="flex items-start justify-between gap-4">
          <div className="flex flex-col gap-1">
            <h1 className="text-xl font-bold text-[#1e2229]">Interview Prep</h1>
            {job && (
              <p className="text-sm text-[#6b7280]">
                {job.title} · {job.company_name}
              </p>
            )}
            <p className="text-sm text-[#6b7280]">
              {questions.length} question{questions.length !== 1 ? "s" : ""}
            </p>
          </div>
          <button
            onClick={() => router.push(`/dashboard/jobs/${jobId}`)}
            className="shrink-0 rounded-[8px] border border-[#cbd5e1] px-3 py-2 text-sm text-[#1e2229] hover:bg-[rgba(217,217,217,0.3)]"
          >
            ← Back to Hub
          </button>
        </div>

        {/* Interview Questions */}
        {questions.length > 0 && (
          <div className={CARD}>
            <h2 className={TITLE}>Interview Questions</h2>
            <div className="flex flex-col gap-2">
              {questions.map((q, i) => (
                <QuestionCard key={q.id ?? i} q={q} index={i} />
              ))}
            </div>
          </div>
        )}

        {/* Questions to Ask Interviewer */}
        {questionsToAsk.length > 0 && (
          <div className={CARD}>
            <h2 className={TITLE}>Questions to Ask the Interviewer</h2>
            <div className="flex flex-col gap-4">
              {questionsToAsk.map((item, i) => (
                <div key={i} className="flex flex-col gap-1">
                  <p className="text-sm font-medium text-[#1e2229]">
                    {item.question}
                  </p>
                  {item.purpose && (
                    <p className="text-xs text-[#6b7280] italic">{item.purpose}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Pre-Interview Checklist */}
        {checklist.length > 0 && (
          <div className={CARD}>
            <h2 className={TITLE}>Pre-Interview Checklist</h2>
            <div className="flex flex-col gap-2">
              {checklist.map((item, i) => (
                <label
                  key={i}
                  className="flex items-start gap-2 cursor-pointer group"
                >
                  <input
                    type="checkbox"
                    checked={checkedItems[i] ?? false}
                    onChange={() =>
                      setCheckedItems((prev) => ({ ...prev, [i]: !prev[i] }))
                    }
                    className="mt-0.5 accent-[#f97316]"
                  />
                  <span
                    className={`text-sm transition-colors ${
                      checkedItems[i]
                        ? "line-through text-[#9ca3af]"
                        : "text-[#1e2229]"
                    }`}
                  >
                    {item}
                  </span>
                </label>
              ))}
            </div>
          </div>
        )}

        {/* Salary Guidance */}
        {salaryGuidance && (
          <div className={CARD}>
            <h2 className={TITLE}>Salary Guidance</h2>
            <p className="text-sm text-[#1e2229] leading-relaxed">{salaryGuidance}</p>
          </div>
        )}

        {/* Empty state */}
        {questions.length === 0 &&
          questionsToAsk.length === 0 &&
          checklist.length === 0 && (
            <div className="rounded-[8px] border border-[#cbd5e1] bg-white px-6 py-12 text-center text-sm text-[#6b7280]">
              No interview prep content available.
            </div>
          )}
      </main>
    </>
  );
}
