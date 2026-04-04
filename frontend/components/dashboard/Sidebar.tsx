"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

type SectionItem = { label: string; isSection: true };
type NavLinkItem = { label: string; href: string; exact?: boolean };
type NavItem = SectionItem | NavLinkItem;

const NAV_ITEMS: NavItem[] = [
  { label: "CareerVP", isSection: true },
  { label: "Dashboard", href: "/dashboard", exact: true },
  { label: "Applications", href: "/dashboard/jobs" },
  { label: "CV Center", href: "/dashboard/cv" },
  { label: "Billing", href: "#" },
  { label: "Settings", href: "#" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside
      className="flex w-60 shrink-0 flex-col bg-white border-r border-[#cbd5e1]"
      style={{ minHeight: "900px" }}
    >
      <div className="flex items-center gap-2.5 px-[26px] py-5">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 30 30"
          className="h-[30px] w-[30px] rounded-[4px] object-cover shrink-0"
        >
          <rect width="30" height="30" rx="4" fill="#2563eb" />
          <text x="15" y="20" textAnchor="middle" fontSize="14" fontWeight="bold" fill="white">C</text>
        </svg>
        <span className="text-lg font-bold text-[#1e2229] leading-none whitespace-nowrap">
          CareerVP
        </span>
      </div>

      <div className="border-b border-[#cbd5e1] mx-0" />

      <nav className="flex flex-col pt-[18px] px-[10px]">
        {NAV_ITEMS.map((item) => {
          if ("isSection" in item) {
            return (
              <span
                key={item.label}
                className="px-[13px] py-[8px] text-sm font-bold text-[#1e2229] whitespace-nowrap"
              >
                {item.label}
              </span>
            );
          }

          const isActive =
            item.href !== "#" &&
            (item.exact
              ? pathname === item.href
              : pathname.startsWith(item.href));

          return (
            <Link
              key={item.label}
              href={item.href}
              className={cn(
                "px-[13px] py-[8px] text-sm font-bold text-[#1e2229] whitespace-nowrap rounded-sm transition-colors",
                isActive
                  ? "bg-[rgba(217,217,217,0.61)]"
                  : "hover:bg-[rgba(217,217,217,0.3)]"
              )}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
