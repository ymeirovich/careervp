"use client";

import Link from "next/link";
import { useDashboard } from "@/app/dashboard/dashboard-context";

interface TopbarProps {
  title: string;
  breadcrumb?: { label: string; href: string }[];
}

export function Topbar({ title, breadcrumb }: TopbarProps) {
  const { userName, usage } = useDashboard();

  const total = usage
    ? usage.applications.used + usage.applications.remaining
    : null;
  const creditsText = usage
    ? `${usage.applications.remaining} / ${total}`
    : "—";

  return (
    <div className="flex h-20 shrink-0 items-center justify-between border-b border-[#cbd5e1] bg-white px-6">
      {/* Left: optional breadcrumb + title */}
      <div className="flex flex-col justify-center gap-0.5">
        {breadcrumb && breadcrumb.length > 0 && (
          <div className="flex items-center gap-1 text-xs text-[#6b7280]">
            {breadcrumb.map((crumb, i) => (
              <span key={crumb.href} className="flex items-center gap-1">
                {i > 0 && <span>›</span>}
                {i < breadcrumb.length - 1 ? (
                  <Link href={crumb.href} className="hover:underline">
                    {crumb.label}
                  </Link>
                ) : (
                  <span>{crumb.label}</span>
                )}
              </span>
            ))}
          </div>
        )}
        <span className="text-2xl font-semibold text-[#1e2229] whitespace-nowrap leading-none">
          {title}
        </span>
      </div>

      {/* Right: credits + user chip */}
      <div className="flex items-center gap-3">
        <span className="text-base font-normal text-[#1e2229] whitespace-nowrap">
          Credits: {creditsText}
        </span>

        <div className="flex items-center gap-2.5 rounded-[8px] border border-[#6b7280] bg-[#f0f2f5] px-3 py-1.5">
          <span className="text-base font-normal text-[#1e2229] whitespace-nowrap leading-none">
            {userName || "…"}
          </span>
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="h-[14px] w-[14px] object-contain"
            style={{ transform: "scaleY(-1)" }}
          >
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </div>
      </div>
    </div>
  );
}
