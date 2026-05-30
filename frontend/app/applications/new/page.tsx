"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { UserCV } from "@/lib/types";

function getCvName(cv: UserCV | null): string {
  return cv?.full_name || cv?.cv_id || "No CV selected";
}

export default function NewApplicationPage() {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [description, setDescription] = useState("");
  const [jobUrl, setJobUrl] = useState("");
  const [cvs, setCvs] = useState<UserCV[]>([]);
  const [selectedCv, setSelectedCv] = useState<UserCV | null>(null);
  const [isCvModalOpen, setIsCvModalOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .getCVs()
      .then((items) => {
        if (cancelled) return;
        setCvs(items);
        setSelectedCv(items[0] ?? null);
      })
      .catch(() => {
        if (!cancelled) setCvs([]);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const canSubmit = useMemo(
    () => title.trim() && companyName.trim() && description.trim(),
    [companyName, description, title]
  );

  const clearError = () => {
    if (error) setError(null);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!canSubmit || loading) return;

    setLoading(true);
    setError(null);
    try {
      const job = await api.createJob({
        title: title.trim(),
        company_name: companyName.trim(),
        description: description.trim(),
        url: jobUrl.trim() || undefined,
      });
      router.push(`/applications/${job.job_id || job.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create application");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-[#fcf7f5] px-6 py-8">
      <div className="mx-auto flex w-full max-w-3xl flex-col gap-5">
        <button
          type="button"
          onClick={() => router.push("/dashboard")}
          className="w-fit text-base font-medium text-[#f97316] hover:underline"
        >
          ← Back
        </button>

        <section className="rounded-[8px] border border-[#cbd5e1] bg-white p-6 shadow-sm">
          <h1 className="text-2xl font-bold text-[#1e2229]">New Application</h1>

          <form onSubmit={handleSubmit} className="mt-5 flex flex-col gap-4">
            {error && (
              <div role="alert" className="rounded-[4px] border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                {error}
              </div>
            )}

            <div className="flex flex-col gap-1">
              <label htmlFor="legacy-new-app-title" className="text-sm font-medium text-[#1e2229]">
                Job Title <span aria-hidden="true">*</span>
              </label>
              <input
                id="legacy-new-app-title"
                type="text"
                required
                disabled={loading}
                value={title}
                onChange={(event) => {
                  clearError();
                  setTitle(event.target.value);
                }}
                className="rounded-[4px] border border-[#cbd5e1] px-3 py-2.5 text-sm text-[#1e2229] outline-none focus:border-[#f97316] disabled:opacity-60"
              />
            </div>

            <div className="flex flex-col gap-1">
              <label htmlFor="legacy-new-app-company" className="text-sm font-medium text-[#1e2229]">
                Company Name <span aria-hidden="true">*</span>
              </label>
              <input
                id="legacy-new-app-company"
                type="text"
                required
                disabled={loading}
                value={companyName}
                onChange={(event) => {
                  clearError();
                  setCompanyName(event.target.value);
                }}
                className="rounded-[4px] border border-[#cbd5e1] px-3 py-2.5 text-sm text-[#1e2229] outline-none focus:border-[#f97316] disabled:opacity-60"
              />
            </div>

            <div className="flex flex-col gap-1">
              <label htmlFor="legacy-new-app-description" className="text-sm font-medium text-[#1e2229]">
                Job Description <span aria-hidden="true">*</span>
              </label>
              <textarea
                id="legacy-new-app-description"
                required
                rows={7}
                disabled={loading}
                value={description}
                onChange={(event) => {
                  clearError();
                  setDescription(event.target.value);
                }}
                className="resize-y rounded-[4px] border border-[#cbd5e1] px-3 py-2.5 text-sm text-[#1e2229] outline-none focus:border-[#f97316] disabled:opacity-60"
              />
            </div>

            <div className="flex flex-col gap-1">
              <label htmlFor="legacy-new-app-url" className="text-sm font-medium text-[#1e2229]">
                Job URL
              </label>
              <input
                id="legacy-new-app-url"
                type="url"
                disabled={loading}
                value={jobUrl}
                onChange={(event) => {
                  clearError();
                  setJobUrl(event.target.value);
                }}
                className="rounded-[4px] border border-[#cbd5e1] px-3 py-2.5 text-sm text-[#1e2229] outline-none focus:border-[#f97316] disabled:opacity-60"
              />
            </div>

            <section className="rounded-[8px] border border-[#cbd5e1] bg-[#f8fafc] p-4">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <h2 className="text-base font-bold text-[#1e2229]">Base CV</h2>
                  <p className="mt-1 text-sm text-[#6b7280]">{getCvName(selectedCv)}</p>
                </div>
                <button
                  type="button"
                  disabled={loading}
                  onClick={() => setIsCvModalOpen(true)}
                  className="rounded-[8px] border border-[#cbd5e1] bg-[#f0f2f5] px-4 py-2 text-sm font-medium text-[#1e2229] disabled:opacity-60"
                >
                  Change
                </button>
              </div>
            </section>

            <div className="mt-2 flex justify-end gap-3">
              <button
                type="button"
                disabled={loading}
                onClick={() => router.push("/dashboard")}
                className="rounded-[8px] border border-[#cbd5e1] bg-[#f0f2f5] px-5 py-2 text-sm font-medium text-[#1e2229] disabled:opacity-60"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={!canSubmit || loading}
                className="rounded-[8px] bg-[#f97316] px-5 py-2 text-sm font-bold text-white disabled:opacity-60"
              >
                {loading ? "Creating..." : "Create Application"}
              </button>
            </div>
          </form>
        </section>
      </div>

      {isCvModalOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Choose Base CV"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
        >
          <div className="w-full max-w-lg rounded-[8px] border border-[#cbd5e1] bg-white p-6 shadow-lg">
            <h2 className="text-xl font-bold text-[#1e2229]">Choose Base CV</h2>
            <div className="mt-4 flex flex-col gap-2">
              {cvs.length === 0 ? (
                <p className="text-sm text-[#6b7280]">No CVs available</p>
              ) : (
                cvs.map((cv) => (
                  <button
                    key={cv.cv_id ?? cv.full_name}
                    type="button"
                    onClick={() => {
                      setSelectedCv(cv);
                      setIsCvModalOpen(false);
                    }}
                    className="rounded-[6px] border border-[#cbd5e1] px-3 py-2 text-left text-sm text-[#1e2229] hover:bg-[#f8fafc]"
                  >
                    {getCvName(cv)}
                  </button>
                ))
              )}
            </div>
            <div className="mt-5 flex justify-end">
              <button
                type="button"
                onClick={() => setIsCvModalOpen(false)}
                className="rounded-[8px] border border-[#cbd5e1] bg-[#f0f2f5] px-5 py-2 text-sm font-medium text-[#1e2229]"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
