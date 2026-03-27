"use client";

import { useState, useEffect, use, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { Topbar } from "@/components/dashboard/Topbar";
import type { CVTailoredStatusResponse, JobDetail } from "@/lib/types";

// ─── Inner component (needs Suspense boundary for useSearchParams) ─────────────

function CVTailoredContent({ jobId }: { jobId: string }) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const artifactId = searchParams.get("id");

  const [data, setData] = useState<CVTailoredStatusResponse | null>(null);
  const [job, setJob] = useState<JobDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const init = async () => {
      if (!artifactId) {
        router.replace(`/dashboard/jobs/${jobId}`);
        return;
      }
      setLoading(true);
      const [cvResult, jobResult] = await Promise.allSettled([
        api.getCVTailored(artifactId),
        api.getJob(jobId),
      ]);

      const cvData =
        cvResult.status === "fulfilled" ? cvResult.value : null;
      const jobData =
        jobResult.status === "fulfilled" ? jobResult.value : null;

      setJob(jobData);

      if (!cvData || cvData.status !== "completed") {
        router.replace(`/dashboard/jobs/${jobId}`);
        return;
      }
      setData(cvData);
      setLoading(false);
    };
    init();
  }, [jobId, artifactId, router]);

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
        <Topbar title="Tailored CV" breadcrumb={breadcrumb} />
        <main className="p-6">
          <div className="text-sm text-[#6b7280]">Loading…</div>
        </main>
      </>
    );
  }

  const result = data?.result;
  const tailoredCvText = result?.tailored_cv ?? "";
  const atsScore = result?.ats_score;
  const suggestions = result?.suggestions ?? [];
  const keywordMatches = result?.keyword_matches;

  const handleCopy = async () => {
    if (!tailoredCvText) return;
    await navigator.clipboard.writeText(tailoredCvText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <>
      <Topbar title="Tailored CV" breadcrumb={breadcrumb} />
      <main className="flex flex-col gap-6 p-6 max-w-3xl">

        {/* ATS Score & Keyword Matches */}
        {(atsScore !== undefined || keywordMatches) && (
          <div className="rounded-[8px] border border-[#cbd5e1] bg-white p-6 flex items-start gap-8">
            {atsScore !== undefined && (
              <div className="flex flex-col items-center gap-1 shrink-0">
                <span
                  className="inline-flex items-center justify-center w-14 h-14 rounded-full text-white font-bold text-xl"
                  style={{
                    background:
                      atsScore >= 8
                        ? "#16b44b"
                        : atsScore >= 6
                          ? "#f59e0b"
                          : "#ef4444",
                  }}
                >
                  {Math.round(atsScore * 10)}
                </span>
                <span className="text-xs text-[#6b7280]">ATS Score</span>
              </div>
            )}
            {keywordMatches && (
              <div className="flex flex-col gap-2 flex-1 min-w-0">
                {keywordMatches.matched.length > 0 && (
                  <div>
                    <span className="text-xs font-semibold text-[#16b44b]">
                      Matched:{" "}
                    </span>
                    <span className="text-xs text-[#6b7280]">
                      {keywordMatches.matched.join(", ")}
                    </span>
                  </div>
                )}
                {keywordMatches.missing.length > 0 && (
                  <div>
                    <span className="text-xs font-semibold text-[#ef4444]">
                      Missing:{" "}
                    </span>
                    <span className="text-xs text-[#6b7280]">
                      {keywordMatches.missing.join(", ")}
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Tailored CV Text */}
        {tailoredCvText && (
          <div className="rounded-[8px] border border-[#cbd5e1] bg-white p-6 flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-bold text-[#1e2229]">
                Tailored CV
              </h2>
              <button
                onClick={handleCopy}
                className="text-xs font-medium text-[#6b7280] hover:text-[#1e2229] transition-colors"
              >
                {copied ? "Copied ✓" : "Copy to clipboard"}
              </button>
            </div>
            <pre className="text-sm text-[#1e2229] leading-relaxed whitespace-pre-wrap font-sans">
              {tailoredCvText}
            </pre>
          </div>
        )}

        {/* Suggestions */}
        {suggestions.length > 0 && (
          <div className="rounded-[8px] border border-[#cbd5e1] bg-white p-6 flex flex-col gap-3">
            <h2 className="text-base font-bold text-[#1e2229]">Suggestions</h2>
            <ul className="flex flex-col gap-2">
              {suggestions.map((s, i) => (
                <li key={i} className="flex gap-2 text-sm text-[#6b7280]">
                  <span className="text-[#f97316] shrink-0 mt-0.5">•</span>
                  <span>{s}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </main>
    </>
  );
}

// ─── Page (with Suspense wrapper for useSearchParams) ─────────────────────────

export default function CVTailoredPage({
  params,
}: {
  params: Promise<{ jobId: string }>;
}) {
  const { jobId } = use(params);

  return (
    <Suspense fallback={null}>
      <CVTailoredContent jobId={jobId} />
    </Suspense>
  );
}
