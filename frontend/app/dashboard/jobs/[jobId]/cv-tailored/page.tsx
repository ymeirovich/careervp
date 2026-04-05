"use client";

import { useState, useEffect, use, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { Topbar } from "@/components/dashboard/Topbar";
import type {
  CVTailoredStatusResponse,
  CVSections,
  JobDetail,
} from "@/lib/types";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatDateRange(
  start: string,
  end?: string | null,
  isCurrent?: boolean
): string {
  const endLabel = isCurrent || !end || end === "Present" ? "Present" : end;
  return start ? `${start} – ${endLabel}` : endLabel ?? "";
}

function buildCopyText(cv: CVSections): string {
  const c = cv.contact;
  const contactLine = [c.email, c.phone, c.linkedin, c.location]
    .filter(Boolean)
    .join(" | ");

  const lines: string[] = [c.name, contactLine, ""];

  lines.push("PROFESSIONAL SUMMARY", cv.summary, "");

  if (cv.skills.technical.length > 0) {
    lines.push("CORE COMPETENCIES", cv.skills.technical.join(" | "), "");
  }

  if (cv.experience.length > 0) {
    lines.push("PROFESSIONAL EXPERIENCE");
    for (const exp of cv.experience) {
      lines.push(
        `${exp.title} | ${exp.company} | ${formatDateRange(exp.start_date, exp.end_date, exp.is_current)}`
      );
      for (const b of exp.bullets) {
        lines.push(`  • ${b.text}`);
      }
      lines.push("");
    }
  }

  if (cv.education.length > 0) {
    lines.push("EDUCATION");
    for (const edu of cv.education) {
      const grad = edu.graduation_date ? ` | ${edu.graduation_date}` : "";
      lines.push(`${edu.degree} in ${edu.field} | ${edu.institution}${grad}`);
    }
    lines.push("");
  }

  if (cv.certifications.length > 0) {
    lines.push("CERTIFICATIONS");
    for (const cert of cv.certifications) {
      const date = cert.date ? ` | ${cert.date}` : "";
      lines.push(`  • ${cert.name} | ${cert.issuer}${date}`);
    }
    lines.push("");
  }

  if (cv.languages && cv.languages.length > 0) {
    lines.push("LANGUAGES", cv.languages.join(", "), "");
  }

  return lines.join("\n").trim();
}

// ─── CV Document Renderer ─────────────────────────────────────────────────────

function CVDocument({ cv }: { cv: CVSections }) {
  const c = cv.contact;
  const contactParts = [c.email, c.phone, c.linkedin, c.location].filter(
    Boolean
  );

  return (
    <div className="flex flex-col gap-6 font-sans">
      {/* Header */}
      <div className="text-center border-b border-[#cbd5e1] pb-4">
        <h1 className="text-xl font-bold text-[#1e2229] tracking-wide uppercase">
          {c.name}
        </h1>
        {contactParts.length > 0 && (
          <p className="text-sm text-[#4b5563] mt-1">
            {contactParts.join(" | ")}
          </p>
        )}
      </div>

      {/* Professional Summary */}
      <section>
        <h2 className="text-sm font-bold text-[#1e2229] uppercase tracking-wider border-b border-[#1e2229] pb-1 mb-2">
          Professional Summary
        </h2>
        <p className="text-sm text-[#374151] leading-relaxed">{cv.summary}</p>
      </section>

      {/* Core Competencies */}
      {cv.skills.technical.length > 0 && (
        <section>
          <h2 className="text-sm font-bold text-[#1e2229] uppercase tracking-wider border-b border-[#1e2229] pb-1 mb-2">
            Core Competencies
          </h2>
          <p className="text-sm text-[#374151]">
            {cv.skills.technical.join(" | ")}
          </p>
        </section>
      )}

      {/* Professional Experience */}
      {cv.experience.length > 0 && (
        <section>
          <h2 className="text-sm font-bold text-[#1e2229] uppercase tracking-wider border-b border-[#1e2229] pb-1 mb-3">
            Professional Experience
          </h2>
          <div className="flex flex-col gap-4">
            {cv.experience.map((exp, i) => (
              <div key={i}>
                <div className="flex items-start justify-between gap-2">
                  <span className="text-sm font-semibold text-[#1e2229]">
                    {exp.title} | {exp.company}
                  </span>
                  <span className="text-xs text-[#6b7280] shrink-0">
                    {formatDateRange(
                      exp.start_date,
                      exp.end_date,
                      exp.is_current
                    )}
                  </span>
                </div>
                {exp.location && (
                  <p className="text-xs text-[#6b7280] mb-1">{exp.location}</p>
                )}
                <ul className="mt-1 flex flex-col gap-1">
                  {exp.bullets.map((b, j) => (
                    <li key={j} className="flex gap-2 text-sm text-[#374151]">
                      <span className="shrink-0 mt-0.5">•</span>
                      <span className="leading-relaxed">{b.text}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Education */}
      {cv.education.length > 0 && (
        <section>
          <h2 className="text-sm font-bold text-[#1e2229] uppercase tracking-wider border-b border-[#1e2229] pb-1 mb-2">
            Education
          </h2>
          <div className="flex flex-col gap-1">
            {cv.education.map((edu, i) => (
              <div key={i} className="flex items-start justify-between gap-2">
                <span className="text-sm text-[#374151]">
                  <span className="font-medium">{edu.degree}</span> in{" "}
                  {edu.field} | {edu.institution}
                  {edu.gpa && (
                    <span className="text-[#6b7280]"> | GPA: {edu.gpa}</span>
                  )}
                </span>
                {edu.graduation_date && (
                  <span className="text-xs text-[#6b7280] shrink-0">
                    {edu.graduation_date}
                  </span>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Certifications */}
      {cv.certifications.length > 0 && (
        <section>
          <h2 className="text-sm font-bold text-[#1e2229] uppercase tracking-wider border-b border-[#1e2229] pb-1 mb-2">
            Certifications
          </h2>
          <ul className="flex flex-col gap-1">
            {cv.certifications.map((cert, i) => (
              <li key={i} className="flex gap-2 text-sm text-[#374151]">
                <span className="shrink-0 mt-0.5">•</span>
                <span>
                  {cert.name}
                  {cert.issuer && (
                    <span className="text-[#6b7280]"> | {cert.issuer}</span>
                  )}
                  {cert.date && (
                    <span className="text-[#6b7280]"> | {cert.date}</span>
                  )}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Languages */}
      {cv.languages && cv.languages.length > 0 && (
        <section>
          <h2 className="text-sm font-bold text-[#1e2229] uppercase tracking-wider border-b border-[#1e2229] pb-1 mb-2">
            Languages
          </h2>
          <p className="text-sm text-[#374151]">{cv.languages.join(", ")}</p>
        </section>
      )}
    </div>
  );
}

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
  const cvSections = result?.cv_sections;

  // ATS score: now 0-100 integer; grade comes from ats_grade field
  const atsScore = result?.ats_score;
  const atsGrade = result?.ats_grade;
  const keywordsMatched =
    result?.keywords_matched ??
    result?.keyword_matches?.matched ??
    [];
  const keywordsMissing =
    result?.keywords_missing ??
    result?.keyword_matches?.missing ??
    [];

  const suggestions = result?.suggestions ?? [];

  const atsColor =
    atsGrade === "green"
      ? "#16b44b"
      : atsGrade === "yellow"
        ? "#f59e0b"
        : "#ef4444";

  const handleCopy = async () => {
    const text = cvSections
      ? buildCopyText(cvSections)
      : (result?.tailored_cv ?? "");
    if (!text) return;
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <>
      <Topbar title="Tailored CV" breadcrumb={breadcrumb} />
      <main className="flex flex-col gap-6 p-6 max-w-3xl">

        {/* ATS Score & Keywords */}
        {atsScore !== undefined && (
          <div className="rounded-[8px] border border-[#cbd5e1] bg-white p-6 flex items-start gap-8">
            <div className="flex flex-col items-center gap-1 shrink-0">
              <span
                className="inline-flex items-center justify-center w-14 h-14 rounded-full text-white font-bold text-xl"
                style={{ background: atsColor }}
              >
                {atsScore}
              </span>
              <span className="text-xs text-[#6b7280]">ATS Score</span>
            </div>
            <div className="flex flex-col gap-2 flex-1 min-w-0">
              {keywordsMatched.length > 0 && (
                <div>
                  <span className="text-xs font-semibold text-[#16b44b]">
                    Matched:{" "}
                  </span>
                  <span className="text-xs text-[#6b7280]">
                    {keywordsMatched.join(", ")}
                  </span>
                </div>
              )}
              {keywordsMissing.length > 0 && (
                <div>
                  <span className="text-xs font-semibold text-[#ef4444]">
                    Missing:{" "}
                  </span>
                  <span className="text-xs text-[#6b7280]">
                    {keywordsMissing.join(", ")}
                  </span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* CV Document */}
        {cvSections ? (
          <div className="rounded-[8px] border border-[#cbd5e1] bg-white p-8 flex flex-col gap-2">
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-base font-bold text-[#1e2229]">Tailored CV</h2>
              <button
                onClick={handleCopy}
                className="text-xs font-medium text-[#6b7280] hover:text-[#1e2229] transition-colors"
              >
                {copied ? "Copied ✓" : "Copy to clipboard"}
              </button>
            </div>
            <CVDocument cv={cvSections} />
          </div>
        ) : result?.tailored_cv ? (
          /* Fallback: older artifacts without cv_sections */
          <div className="rounded-[8px] border border-[#cbd5e1] bg-white p-6 flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-bold text-[#1e2229]">Tailored CV</h2>
              <button
                onClick={handleCopy}
                className="text-xs font-medium text-[#6b7280] hover:text-[#1e2229] transition-colors"
              >
                {copied ? "Copied ✓" : "Copy to clipboard"}
              </button>
            </div>
            <pre className="text-sm text-[#1e2229] leading-relaxed whitespace-pre-wrap font-sans">
              {result.tailored_cv}
            </pre>
          </div>
        ) : null}

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
