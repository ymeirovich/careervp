import * as React from "react";

interface BadgeProps {
  variant: "green" | "amber" | "gray" | "orange" | "blue" | "purple" | "red";
  size?: "sm" | "md";
  children: React.ReactNode;
}

const variantStyles: Record<
  BadgeProps["variant"],
  { backgroundColor: string; color: string }
> = {
  green: { backgroundColor: "#dcfce7", color: "#16b44b" },
  amber: { backgroundColor: "#fffbeb", color: "#f59e0b" },
  gray: { backgroundColor: "#f1f5f9", color: "#6b7280" },
  orange: { backgroundColor: "#fff7ed", color: "#f97316" },
  blue: { backgroundColor: "#eff6ff", color: "#3b82f6" },
  purple: { backgroundColor: "#f5f3ff", color: "#8b5cf6" },
  red: { backgroundColor: "#fef2f2", color: "#ef4444" },
};

export function Badge({ variant, size = "md", children }: BadgeProps) {
  const colors = variantStyles[variant];
  const sizeClass = size === "sm" ? "px-1.5 py-0.5 text-[10px]" : "px-2 py-0.5 text-xs";

  return (
    <span
      className={`inline-flex items-center rounded-[4px] font-medium ${sizeClass}`}
      style={{ backgroundColor: colors.backgroundColor, color: colors.color }}
    >
      {children}
    </span>
  );
}
