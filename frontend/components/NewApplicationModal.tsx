"use client";

import { useState, type FormEvent } from "react";
import { api } from "@/lib/api";
import type { Job } from "@/lib/types";

interface Props {
  onClose: () => void;
  onCreated: (job: Job) => void;
}

export function NewApplicationModal({ onClose, onCreated }: Props) {
  const [title, setTitle] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [description, setDescription] = useState("");
  const [jobUrl, setJobUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const job = await api.createJob({
        title,
        company_name: companyName,
        description,
        url: jobUrl || undefined,
      });
      onCreated(job);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create application");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/30"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="w-full max-w-[600px] rounded-[8px] border border-[#cbd5e1] bg-white p-8 shadow-lg mx-4">
        <h2 className="mb-6 text-right text-xl font-bold text-[#1e2229]">
          New Job Application
        </h2>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {/* Job Title */}
          <div className="flex flex-col gap-1">
            <label className="text-sm font-medium text-[#6b7280]">
              Job Title
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Enter job title"
              required
              className="rounded-[4px] border border-[#cbd5e1] px-3 py-2.5 text-sm text-[#1e2229] outline-none focus:border-[#f97316] transition-colors"
            />
          </div>

          {/* Company */}
          <div className="flex flex-col gap-1">
            <label className="text-sm font-medium text-[#6b7280]">
              Company
            </label>
            <input
              type="text"
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              placeholder="Enter company name"
              required
              className="rounded-[4px] border border-[#cbd5e1] px-3 py-2.5 text-sm text-[#1e2229] outline-none focus:border-[#f97316] transition-colors"
            />
          </div>

          {/* Job URL */}
          <div className="flex flex-col gap-1">
            <label className="text-sm font-medium text-[#6b7280]">
              Job URL
            </label>
            <input
              type="url"
              value={jobUrl}
              onChange={(e) => setJobUrl(e.target.value)}
              placeholder="Enter Job URL"
              className="rounded-[4px] border border-[#cbd5e1] px-3 py-2.5 text-sm text-[#1e2229] outline-none focus:border-[#f97316] transition-colors"
            />
          </div>

          {/* Description */}
          <div className="flex flex-col gap-1">
            <label className="text-sm font-medium text-[#6b7280]">
              Job Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Paste the job description here"
              required
              rows={4}
              className="rounded-[4px] border border-[#cbd5e1] px-3 py-2.5 text-sm text-[#1e2229] outline-none focus:border-[#f97316] transition-colors resize-none"
            />
          </div>

          {error && (
            <p className="rounded-[4px] bg-red-50 px-3 py-2 text-sm text-red-600">
              {error}
            </p>
          )}

          {/* Actions */}
          <div className="mt-2 flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="rounded-[8px] border border-[#cbd5e1] bg-[#f0f2f5] px-5 py-2 text-sm font-medium text-[#1e2229] transition-opacity hover:opacity-80"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="rounded-[8px] bg-[#f97316] px-5 py-2 text-sm font-bold text-white transition-opacity hover:opacity-90 disabled:opacity-60"
            >
              {loading ? "Creating…" : "Create Application"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
