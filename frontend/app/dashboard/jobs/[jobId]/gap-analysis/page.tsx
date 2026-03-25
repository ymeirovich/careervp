"use client";

import { useState, useEffect, use } from "react";
import { api } from "@/lib/api";
import { Topbar } from "@/components/dashboard/Topbar";
import { Badge } from "@/components/ui/Badge";
import { cn } from "@/lib/utils";
import type { UserCV, JobDetail, GapResponse } from "@/lib/types";

// ─── Types ────────────────────────────────────────────────────────────────────

type FormMode = "view" | "edit" | "saving";

type LocalResponse = {
  answer: string;
  destination: "CV_IMPACT" | "INTERVIEW_MVP_ONLY" | "";
};

// Backend may return id/text (API model) or question_id/question (stored format)
type RawQuestion = {
  id?: string;
  question_id?: string;
  text?: string;
  question?: string;
  impact?: string;
  probability?: string;
  tags?: string[];
};

function getQId(q: RawQuestion): string {
  return q.question_id ?? q.id ?? "";
}

function getQText(q: RawQuestion): string {
  return q.question ?? q.text ?? "";
}

function impactVariant(
  v?: string
): "green" | "amber" | "gray" {
  if (v === "HIGH") return "green";
  if (v === "MEDIUM" || v === "MED") return "amber";
  return "gray";
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function GapAnalysisPage({
  params,
}: {
  params: Promise<{ jobId: string }>;
}) {
  const { jobId } = use(params);

  const [questions, setQuestions] = useState<RawQuestion[]>([]);
  const [responses, setResponses] = useState<Record<string, LocalResponse>>({});
  const [savedResponses, setSavedResponses] = useState<Record<string, LocalResponse>>({});
  const [mode, setMode] = useState<FormMode>("view");
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedToast, setSavedToast] = useState(false);
  const [cv, setCv] = useState<UserCV | null>(null);
  const [job, setJob] = useState<JobDetail | null>(null);

  useEffect(() => {
    const init = async () => {
      setLoading(true);
      const [questionsResult, hubResult, cvResult, jobResult] =
        await Promise.allSettled([
          api.getGapQuestions(jobId),
          api.getApplication(jobId),
          api.getCV(),
          api.getJob(jobId),
        ]);

      const qs =
        questionsResult.status === "fulfilled"
          ? (questionsResult.value as RawQuestion[])
          : [];
      const hub =
        hubResult.status === "fulfilled" ? hubResult.value : null;
      const cvData =
        cvResult.status === "fulfilled" ? cvResult.value : null;
      const jobData =
        jobResult.status === "fulfilled" ? jobResult.value : null;

      setCv(cvData);
      setJob(jobData);
      setQuestions(qs);

      // Pre-populate responses from hub gap_analysis.responses
      const existingMap: Record<string, LocalResponse> = {};
      for (const r of hub?.gap_analysis.responses ?? []) {
        const entry = r as Record<string, unknown>;
        existingMap[r.question_id] = {
          answer: String(entry.response ?? entry.answer ?? ""),
          destination:
            (entry.destination as "CV_IMPACT" | "INTERVIEW_MVP_ONLY") ?? "",
        };
      }
      setResponses(existingMap);
      setSavedResponses(existingMap);

      // Default to EDIT if questions exist but no responses yet
      if (qs.length > 0 && Object.keys(existingMap).length === 0) {
        setMode("edit");
      }

      setLoading(false);
    };
    init();
  }, [jobId]);

  // ── Handlers ────────────────────────────────────────────────────────────────

  const handleGenerate = async () => {
    if (!cv?.cv_id) return;
    setGenerating(true);
    setError(null);
    try {
      const result = await api.generateGapQuestions({
        job_id: jobId,
        cv_id: cv.cv_id,
      });
      const qs = (result.questions ?? []) as RawQuestion[];
      setQuestions(qs);
      setResponses({});
      setSavedResponses({});
      setMode("edit");
    } catch (err) {
      setError("Failed to generate questions. Please try again.");
      console.error(err);
    } finally {
      setGenerating(false);
    }
  };

  const handleEdit = () => {
    setResponses({ ...savedResponses });
    setMode("edit");
    setError(null);
  };

  const handleCancel = () => {
    setResponses({ ...savedResponses });
    setMode("view");
    setError(null);
  };

  const handleSave = async () => {
    setMode("saving");
    setError(null);
    try {
      const payload: GapResponse[] = questions
        .flatMap((q) => {
          const qid = getQId(q);
          const r = responses[qid];
          if (!r?.answer.trim()) return [];
          return [
            {
              question_id: qid,
              question: getQText(q),
              answer: r.answer.trim(),
              destination:
                (r.destination as "CV_IMPACT" | "INTERVIEW_MVP_ONLY") ||
                "CV_IMPACT",
            },
          ];
        });

      await api.saveGapResponses(jobId, payload);
      setSavedResponses({ ...responses });
      setMode("view");
      setSavedToast(true);
      setTimeout(() => setSavedToast(false), 3000);
    } catch (err) {
      setError("Failed to save. Please try again.");
      console.error(err);
      setMode("edit");
    }
  };

  const setResponse = (qid: string, patch: Partial<LocalResponse>) => {
    setResponses((prev) => ({
      ...prev,
      [qid]: { ...{ answer: "", destination: "" }, ...prev[qid], ...patch },
    }));
  };

  // ── Derived ──────────────────────────────────────────────────────────────────

  const answeredCount = questions.filter((q) =>
    responses[getQId(q)]?.answer.trim()
  ).length;

  const isEdit = mode === "edit" || mode === "saving";
  const isSaving = mode === "saving";

  const breadcrumb = [
    { label: "Dashboard", href: "/dashboard" },
    {
      label: job?.title ?? "Application",
      href: `/dashboard/jobs/${jobId}`,
    },
  ];

  // ── Render ───────────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <>
        <Topbar title="Gap Analysis" breadcrumb={breadcrumb} />
        <main className="flex flex-col gap-6 p-6">
          <div className="text-sm text-[#6b7280]">Loading…</div>
        </main>
      </>
    );
  }

  return (
    <>
      <Topbar title="Gap Analysis" breadcrumb={breadcrumb} />
      <main className="flex flex-col gap-6 p-6">
        {/* Page Header */}
        <div className="flex items-start justify-between gap-4">
          <div className="flex flex-col gap-1">
            <h1 className="text-xl font-bold text-[#1e2229]">Gap Analysis</h1>
            <p className="text-sm text-[#6b7280]">
              Answer questions to identify gaps between your CV and this role
            </p>
          </div>
          {questions.length === 0 && (
            <button
              onClick={handleGenerate}
              disabled={generating || !cv?.cv_id}
              className="shrink-0 rounded-[8px] bg-[#f97316] px-3 py-2 text-sm font-bold text-white hover:opacity-90 active:opacity-80 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {generating ? "Generating…" : "Generate Questions"}
            </button>
          )}
        </div>

        {/* Toast */}
        {savedToast && (
          <div className="rounded-[8px] bg-[#dcfce7] border border-[#16b44b] px-4 py-3 text-sm font-medium text-[#16b44b]">
            Saved successfully
          </div>
        )}

        {/* Error banner */}
        {error && (
          <div className="rounded-[8px] bg-[#fef2f2] border border-[#ef4444] px-4 py-3 text-sm text-[#ef4444]">
            {error}
          </div>
        )}

        {/* Empty state */}
        {questions.length === 0 && !generating && (
          <div className="rounded-[8px] border border-[#cbd5e1] bg-white px-6 py-12 text-center text-sm text-[#6b7280]">
            No questions generated yet. Click &ldquo;Generate Questions&rdquo; to
            start.
          </div>
        )}

        {/* Questions form */}
        {questions.length > 0 && (
          <div className="flex flex-col rounded-[8px] border border-[#cbd5e1] bg-white overflow-hidden">
            {/* Sticky button bar */}
            <div className="sticky top-0 z-10 flex items-center justify-between bg-white border-b border-[#cbd5e1] px-6 py-3">
              <span className="text-sm text-[#6b7280]">
                {answeredCount} of {questions.length} answered
              </span>
              <div className="flex gap-2">
                {isEdit ? (
                  <>
                    <button
                      onClick={handleCancel}
                      disabled={isSaving}
                      className="px-4 py-2 text-sm border border-[#cbd5e1] rounded-[8px] text-[#1e2229] hover:bg-[rgba(217,217,217,0.3)] disabled:opacity-50"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleSave}
                      disabled={isSaving}
                      className="px-4 py-2 text-sm bg-[#f97316] text-white rounded-[8px] hover:opacity-90 disabled:opacity-50"
                    >
                      {isSaving ? "Saving…" : "Save"}
                    </button>
                  </>
                ) : (
                  <button
                    onClick={handleEdit}
                    className="px-4 py-2 text-sm bg-[#f97316] text-white rounded-[8px] hover:opacity-90"
                  >
                    Edit
                  </button>
                )}
              </div>
            </div>

            {/* Question list */}
            <div className="flex flex-col gap-4 p-6">
              {questions.map((q, i) => {
                const qid = getQId(q);
                const qtext = getQText(q);
                const r = responses[qid] ?? { answer: "", destination: "" };
                const impact = q.impact;
                const probability = q.probability;

                return (
                  <div
                    key={qid || i}
                    className="flex flex-col gap-3 rounded-[8px] border border-[#e2e8f0] p-4"
                  >
                    {/* Question header */}
                    <div className="flex items-start gap-2 flex-wrap">
                      <span className="text-sm font-medium text-[#1e2229] flex-1 min-w-0">
                        {i + 1}. {qtext}
                      </span>
                      <div className="flex gap-1 shrink-0">
                        {impact && (
                          <Badge variant={impactVariant(impact)} size="sm">
                            Impact: {impact}
                          </Badge>
                        )}
                        {probability && (
                          <Badge variant={impactVariant(probability)} size="sm">
                            Prob: {probability}
                          </Badge>
                        )}
                      </div>
                    </div>

                    {/* Destination */}
                    {isEdit ? (
                      <div className="flex gap-4 pl-4">
                        <label className="flex items-center gap-1.5 text-sm text-[#1e2229] cursor-pointer">
                          <input
                            type="radio"
                            name={`dest-${qid || i}`}
                            value="CV_IMPACT"
                            checked={r.destination === "CV_IMPACT"}
                            onChange={() =>
                              setResponse(qid, { destination: "CV_IMPACT" })
                            }
                            className="accent-[#f97316]"
                          />
                          Include in CV
                        </label>
                        <label className="flex items-center gap-1.5 text-sm text-[#1e2229] cursor-pointer">
                          <input
                            type="radio"
                            name={`dest-${qid || i}`}
                            value="INTERVIEW_MVP_ONLY"
                            checked={r.destination === "INTERVIEW_MVP_ONLY"}
                            onChange={() =>
                              setResponse(qid, {
                                destination: "INTERVIEW_MVP_ONLY",
                              })
                            }
                            className="accent-[#f97316]"
                          />
                          Interview Only
                        </label>
                      </div>
                    ) : r.destination ? (
                      <div className="pl-4">
                        <Badge
                          variant={
                            r.destination === "CV_IMPACT" ? "blue" : "gray"
                          }
                          size="sm"
                        >
                          {r.destination === "CV_IMPACT"
                            ? "Include in CV"
                            : "Interview Only"}
                        </Badge>
                      </div>
                    ) : null}

                    {/* Answer */}
                    {isEdit ? (
                      <textarea
                        rows={4}
                        value={r.answer}
                        onChange={(e) =>
                          setResponse(qid, { answer: e.target.value })
                        }
                        placeholder="Your answer…"
                        className="w-full rounded-[4px] border border-[#cbd5e1] px-3 py-2 text-sm text-[#1e2229] placeholder:text-[#9ca3af] focus:outline-none focus:border-[#f97316] focus:ring-1 focus:ring-[#f97316] resize-none"
                      />
                    ) : (
                      <p
                        className={cn(
                          "pl-4 text-sm leading-relaxed",
                          r.answer
                            ? "text-[#1e2229]"
                            : "text-[#9ca3af] italic"
                        )}
                      >
                        {r.answer || "No answer yet"}
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </main>
    </>
  );
}
