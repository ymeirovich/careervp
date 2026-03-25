"use client";

import { useState, useEffect, use } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { Topbar } from "@/components/dashboard/Topbar";
import type { JobDetail } from "@/lib/types";

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function CoverLetterPage({
  params,
}: {
  params: Promise<{ jobId: string }>;
}) {
  const { jobId } = use(params);
  const router = useRouter();

  const [fullText, setFullText] = useState<string | null>(null);
  const [job, setJob] = useState<JobDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

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

      const artifactId = hub?.artifacts.cover_letter?.artifact_id;
      const artifactStatus = hub?.artifacts.cover_letter?.status;

      if (!artifactId || artifactStatus !== "completed") {
        router.replace(`/dashboard/jobs/${jobId}`);
        return;
      }

      try {
        const data = await api.getCoverLetter(artifactId);
        const text = data.result?.cover_letter ?? null;
        setFullText(text);
        if (!text) {
          // No content — back to hub
          router.replace(`/dashboard/jobs/${jobId}`);
        }
      } catch (err) {
        setError("Failed to load cover letter.");
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    init();
  }, [jobId, router]);

  const handleCopy = async () => {
    if (!fullText) return;
    try {
      await navigator.clipboard.writeText(fullText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // clipboard not available
    }
  };

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
        <Topbar title="Cover Letter" breadcrumb={breadcrumb} />
        <main className="flex flex-col gap-6 p-6">
          <div className="text-sm text-[#6b7280]">Loading…</div>
        </main>
      </>
    );
  }

  if (error) {
    return (
      <>
        <Topbar title="Cover Letter" breadcrumb={breadcrumb} />
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
      <Topbar title="Cover Letter" breadcrumb={breadcrumb} />
      <main className="flex flex-col gap-6 p-6">
        {/* Page Header */}
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex flex-col gap-1">
            <h1 className="text-xl font-bold text-[#1e2229]">Cover Letter</h1>
            {job && (
              <p className="text-sm text-[#6b7280]">
                {job.title} · {job.company_name}
              </p>
            )}
          </div>
          <div className="flex gap-2 shrink-0">
            <button
              onClick={handleCopy}
              className="rounded-[8px] bg-[#f97316] px-3 py-2 text-sm font-bold text-white hover:opacity-90 active:opacity-80"
            >
              {copied ? "Copied!" : "Copy to Clipboard"}
            </button>
            <button
              onClick={() => router.push(`/dashboard/jobs/${jobId}`)}
              className="rounded-[8px] border border-[#cbd5e1] px-3 py-2 text-sm text-[#1e2229] hover:bg-[rgba(217,217,217,0.3)]"
            >
              ← Back to Hub
            </button>
          </div>
        </div>

        {/* Copied toast */}
        {copied && (
          <div className="rounded-[8px] bg-[#dcfce7] border border-[#16b44b] px-4 py-3 text-sm font-medium text-[#16b44b]">
            Copied to clipboard
          </div>
        )}

        {/* Cover Letter text */}
        {fullText && (
          <div className="rounded-[8px] border border-[#cbd5e1] bg-white p-6 flex flex-col gap-4">
            <h2 className="text-base font-bold text-[#1e2229]">Cover Letter</h2>
            <p className="text-sm text-[#1e2229] leading-relaxed whitespace-pre-wrap font-[inherit]">
              {fullText}
            </p>
          </div>
        )}
      </main>
    </>
  );
}
