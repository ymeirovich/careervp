"use client";

/**
 * CareerVP — Dashboard
 * Figma: tMHabCYB7teMvu7L8lz957 · node 66:262 "Desktop / Dashboard Full"
 *
 * Design tokens (Figma-exact):
 *   Page bg:        #fcf7f5
 *   App shell bg:   #fafafa
 *   Card / sidebar: white
 *   Border:         #cbd5e1
 *   Text primary:   #1e2229
 *   Text muted:     #6b7280
 *   Active green:   #16b44b
 *   Brand orange:   #f97316
 *   Active nav bg:  rgba(217,217,217,0.61)
 *   Status strip:   rgba(245,245,245,0.61)
 */

import { useState } from "react";
import { cn } from "@/lib/utils";

// ─── Figma asset URLs (valid 7 days from extraction) ────────────────────────
const ASSET_CVP_LOGO =
  "https://www.figma.com/api/mcp/asset/661cfe6f-1041-4faa-8666-3d001bb92746";
const ASSET_STATUS_DOT =
  "https://www.figma.com/api/mcp/asset/62714d3b-6e61-40cf-917d-9ad5f45735ac";
const ASSET_DROPDOWN_ARROW =
  "https://www.figma.com/api/mcp/asset/29ba343a-ed50-4f60-ab33-814b014f47b8";

// ─── Types ───────────────────────────────────────────────────────────────────
type JobStatus = "Active" | "Draft" | "Archived";

interface Job {
  id: number;
  title: string;
  company: string;
  status: JobStatus;
  updated: string;
}

// ─── Static data ─────────────────────────────────────────────────────────────
const NAV_ITEMS = [
  { label: "CareerVP", isSection: true },
  { label: "Dashboard", active: true, href: "/dashboard" },
  { label: "Applications", href: "#" },
  { label: "CV Center", href: "#" },
  { label: "Billing", href: "#" },
  { label: "Settings", href: "#" },
] as const;

const TABLE_COLUMNS = [
  { key: "title", label: "Job Title", className: "flex-1 min-w-0" },
  { key: "company", label: "Company", className: "w-[160px] shrink-0" },
  { key: "status", label: "Status", className: "w-[120px] shrink-0" },
  { key: "updated", label: "Updated", className: "w-[140px] shrink-0" },
  { key: "action", label: "Action", className: "w-[140px] shrink-0" },
] as const;

const JOBS: Job[] = [
  {
    id: 1,
    title: "Learning Experience Specialist",
    company: "SysAid",
    status: "Active",
    updated: "Mar 7, 2026",
  },
];

// ─── Sidebar ─────────────────────────────────────────────────────────────────
function Sidebar() {
  return (
    <aside
      className="flex w-60 shrink-0 flex-col bg-white border-r border-[#cbd5e1]"
      style={{ height: "900px" }}
    >
      {/* Logo row */}
      <div className="flex items-center gap-2.5 px-[26px] py-5">
        <img
          src={ASSET_CVP_LOGO}
          alt="CareerVP"
          className="h-[30px] w-[30px] rounded-[4px] object-cover shrink-0"
        />
        <span className="text-lg font-bold text-[#1e2229] leading-none whitespace-nowrap">
          CareerVP
        </span>
      </div>

      {/* Divider */}
      <div className="border-b border-[#cbd5e1] mx-0" />

      {/* Navigation */}
      <nav className="flex flex-col pt-[18px] px-[10px]">
        {NAV_ITEMS.map((item) => {
          if (item.isSection) {
            return (
              <span
                key={item.label}
                className="px-[13px] py-[8px] text-sm font-bold text-[#1e2229] whitespace-nowrap"
              >
                {item.label}
              </span>
            );
          }
          return (
            <a
              key={item.label}
              href={"href" in item ? item.href : "#"}
              className={cn(
                "px-[13px] py-[8px] text-sm font-bold text-[#1e2229] whitespace-nowrap rounded-sm transition-colors",
                "active" in item && item.active
                  ? "bg-[rgba(217,217,217,0.61)]"
                  : "hover:bg-[rgba(217,217,217,0.3)]",
              )}
            >
              {item.label}
            </a>
          );
        })}
      </nav>
    </aside>
  );
}

// ─── Topbar ──────────────────────────────────────────────────────────────────
function Topbar() {
  return (
    <div className="flex h-20 shrink-0 items-center justify-between border-b border-[#cbd5e1] bg-white px-6">
      {/* Left: page title */}
      <span className="text-2xl font-semibold text-[#1e2229] whitespace-nowrap leading-none">
        Dashboard
      </span>

      {/* Right: credits + user menu */}
      <div className="flex items-center gap-3">
        <span className="text-base font-normal text-[#1e2229] whitespace-nowrap">
          Credits: 1 / 3
        </span>

        <div className="flex items-center gap-2.5 rounded-[8px] border border-[#6b7280] bg-[#f0f2f5] px-3 py-1.5">
          <span className="text-base font-normal text-[#1e2229] whitespace-nowrap leading-none">
            Lisi
          </span>
          {/* Dropdown arrow (inverted polygon) */}
          <img
            src={ASSET_DROPDOWN_ARROW}
            alt=""
            aria-hidden
            className="h-[14px] w-[14px] object-contain"
            style={{ transform: "scaleY(-1)" }}
          />
        </div>
      </div>
    </div>
  );
}

// ─── Status Strip ────────────────────────────────────────────────────────────
function StatusStrip() {
  const cardBase =
    "flex items-center justify-center rounded-[4px] border border-[#cbd5e1] bg-[rgba(245,245,245,0.61)] px-4 py-3";

  return (
    <div className="flex items-center gap-8 rounded-[8px] border border-[#cbd5e1] bg-white px-[26px] py-[11px] w-full">
      {/* Plan */}
      <div className={cardBase}>
        <div className="flex items-center gap-1.5 text-sm font-bold text-[#1e2229] whitespace-nowrap">
          <span>Plan:</span>
          <span>Free Tier</span>
        </div>
      </div>

      {/* Credits */}
      <div className={cardBase}>
        <div className="flex items-center gap-1.5 text-sm font-bold text-[#1e2229] whitespace-nowrap">
          <span>Credits Remaining:</span>
          <span>1 / 3</span>
        </div>
      </div>

      {/* Status — pushed to the right */}
      <div className={cn(cardBase, "ml-auto flex-row gap-2")}>
        <div className="flex items-center gap-1.5 text-sm font-bold whitespace-nowrap">
          <span className="text-[#1e2229]">Status:</span>
          <span className="text-[#16b44b]">Active</span>
        </div>
        <img
          src={ASSET_STATUS_DOT}
          alt="active"
          className="h-4 w-4 object-contain shrink-0"
        />
      </div>
    </div>
  );
}

// ─── Jobs Table ──────────────────────────────────────────────────────────────
function JobsCard() {
  return (
    <div className="flex flex-col gap-2.5 rounded-[8px] border border-[#cbd5e1] bg-white p-2.5 w-full">
      {/* Card header */}
      <div className="flex items-center justify-between overflow-hidden p-4">
        <span className="flex-1 min-w-0 text-[18px] font-bold text-[#1e2229] leading-normal">
          My Jobs
        </span>
        <button
          className={cn(
            "flex shrink-0 items-center rounded-[8px] bg-[#f97316] px-3 py-2 transition-opacity",
            "hover:opacity-90 active:opacity-80",
          )}
        >
          <span className="text-sm font-bold text-white whitespace-nowrap leading-normal">
            + New Application
          </span>
        </button>
      </div>

      {/* Table */}
      <div className="flex flex-col p-2.5 w-full overflow-hidden">
        {/* Table header row */}
        <div className="flex items-start gap-4 border-b border-[#e2e8f0] bg-[#cbd5e1] px-4 py-3 text-sm font-medium text-[#6b7280]">
          {TABLE_COLUMNS.map((col) => (
            <span key={col.key} className={col.className}>
              {col.label}
            </span>
          ))}
        </div>

        {/* Data rows */}
        {JOBS.map((job) => (
          <div
            key={job.id}
            className="flex items-start gap-4 border border-[#e2e8f0] px-4 py-3 text-sm font-medium text-[#1e2229] hover:bg-[rgba(245,245,245,0.5)] transition-colors"
          >
            <span className="flex-1 min-w-0">{job.title}</span>
            <span className="w-[160px] shrink-0">{job.company}</span>
            <span className="w-[120px] shrink-0 text-[#16b44b]">
              {job.status}
            </span>
            <span className="w-[140px] shrink-0">{job.updated}</span>
            <span className="w-[140px] shrink-0">
              <a
                href="#"
                className="text-[#1e2229] hover:underline transition-colors"
              >
                View Application
              </a>
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Page ────────────────────────────────────────────────────────────────────
export default function DashboardPage() {
  return (
    // Page background: Figma #fcf7f5
    <div
      className="min-h-screen w-full"
      style={{ backgroundColor: "#fcf7f5" }}
    >
      {/* App Shell: Figma left=100px top=62px width=1239px */}
      <div
        className="mx-auto flex border border-[#cbd5e1] bg-[#fafafa]"
        style={{
          marginLeft: "100px",
          marginTop: "62px",
          width: "1239px",
          minHeight: "900px",
        }}
      >
        <Sidebar />

        {/* Content Area */}
        <div className="flex flex-1 flex-col min-w-0">
          <Topbar />

          {/* Main Content: padding=24px, gap=24px */}
          <main className="flex flex-col gap-6 p-6">
            <StatusStrip />
            <JobsCard />
          </main>
        </div>
      </div>
    </div>
  );
}
