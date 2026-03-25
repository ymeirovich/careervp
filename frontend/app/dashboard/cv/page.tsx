"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { Topbar } from "@/components/dashboard/Topbar";
import { Badge } from "@/components/ui/Badge";
import type { UserCV } from "@/lib/types";

const CARD = "rounded-[8px] border border-[#cbd5e1] bg-white p-6 flex flex-col gap-4";

function ContactChip({ label, value }: { label: string; value?: string }) {
  if (!value) return null;
  return (
    <span className="inline-flex items-center gap-1 px-2 py-1 text-xs rounded-[4px] bg-[#f1f5f9] text-[#1e2229]">
      <span className="text-[#6b7280]">{label}:</span>
      <span>{value}</span>
    </span>
  );
}

export default function CVCenterPage() {
  const [cv, setCv] = useState<UserCV | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getCV().then((data) => {
      setCv(data);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return (
      <>
        <Topbar title="CV Center" breadcrumb={[{ label: "Dashboard", href: "/dashboard" }]} />
        <main className="flex flex-col gap-6 p-6">
          <div className="text-sm text-[#6b7280]">Loading…</div>
        </main>
      </>
    );
  }

  return (
    <>
      <Topbar title="CV Center" breadcrumb={[{ label: "Dashboard", href: "/dashboard" }]} />
      <main className="flex flex-col gap-6 p-6">
        {/* Header */}
        <div className="flex items-center justify-between gap-4">
          <h1 className="text-xl font-bold text-[#1e2229]">My CV</h1>
          {cv ? (
            <Link
              href="/dashboard/cv/edit"
              className="rounded-[8px] bg-[#f97316] px-3 py-2 text-sm font-bold text-white hover:opacity-90"
            >
              Edit CV
            </Link>
          ) : (
            <Link
              href="/dashboard/cv/new"
              className="rounded-[8px] bg-[#f97316] px-3 py-2 text-sm font-bold text-white hover:opacity-90"
            >
              + Upload CV
            </Link>
          )}
        </div>

        {/* Empty state */}
        {!cv && (
          <div className={`${CARD} items-center py-12`}>
            <p className="text-sm text-[#6b7280]">No CV uploaded yet.</p>
            <Link
              href="/dashboard/cv/new"
              className="rounded-[8px] bg-[#f97316] px-4 py-2 text-sm font-bold text-white hover:opacity-90"
            >
              + Upload CV
            </Link>
          </div>
        )}

        {/* CV Summary Card */}
        {cv && (
          <div className={CARD}>
            {/* Header row */}
            <div className="flex items-start justify-between gap-4 flex-wrap">
              <div className="flex flex-col gap-1">
                <span className="text-2xl font-bold text-[#1e2229]">{cv.full_name}</span>
                {cv.updated_at && (
                  <span className="text-xs text-[#6b7280]">
                    Last updated {new Date(cv.updated_at).toLocaleDateString()}
                  </span>
                )}
              </div>
              <Badge variant={cv.language === "he" ? "amber" : "blue"} size="md">
                {cv.language === "he" ? "HE" : "EN"}
              </Badge>
            </div>

            {/* Contact info chips */}
            {cv.contact_info && (
              <div className="flex flex-wrap gap-2">
                <ContactChip label="Email" value={cv.contact_info.email} />
                <ContactChip label="Phone" value={cv.contact_info.phone} />
                <ContactChip label="Location" value={cv.contact_info.location} />
                {cv.contact_info.linkedin && (
                  <ContactChip label="LinkedIn" value={cv.contact_info.linkedin} />
                )}
              </div>
            )}

            {/* Skills preview */}
            {cv.skills.length > 0 && (
              <div className="flex flex-col gap-2">
                <span className="text-xs font-semibold text-[#6b7280] uppercase tracking-wide">
                  Skills
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {cv.skills.slice(0, 10).map((s) => (
                    <span
                      key={s}
                      className="px-2 py-0.5 text-xs rounded-[4px] bg-[#f0f2f5] text-[#1e2229]"
                    >
                      {s}
                    </span>
                  ))}
                  {cv.skills.length > 10 && (
                    <span className="px-2 py-0.5 text-xs text-[#6b7280]">
                      …and {cv.skills.length - 10} more
                    </span>
                  )}
                </div>
              </div>
            )}

            {/* Experience count */}
            {cv.experience.length > 0 && (
              <span className="text-sm text-[#6b7280]">
                {cv.experience.length} position{cv.experience.length !== 1 ? "s" : ""}
              </span>
            )}

            {/* CTA */}
            <div className="pt-2 border-t border-[#f1f5f9]">
              <Link
                href="/dashboard/cv/edit"
                className="text-sm font-medium text-[#f97316] hover:underline"
              >
                View / Edit Full CV →
              </Link>
            </div>
          </div>
        )}
      </main>
    </>
  );
}
