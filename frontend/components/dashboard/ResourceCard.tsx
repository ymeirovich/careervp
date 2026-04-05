import * as React from "react";
import Link from "next/link";

interface ResourceCardProps {
  title: string;
  description: string;
  status: "not_started" | "processing" | "ready" | "partial";
  statusLabel?: string;
  preview?: string;
  primaryAction: {
    label: string;
    href?: string;
    onClick?: () => void;
    disabled?: boolean;
    loading?: boolean;
  };
  secondaryAction?: {
    label: string;
    onClick?: () => void;
    href?: string;
  };
  dependency?: string;
  errorMessage?: string;
}

const statusDotColor: Record<ResourceCardProps["status"], string> = {
  not_started: "#6b7280",
  processing: "#f59e0b",
  partial: "#f59e0b",
  ready: "#16b44b",
};

export function ResourceCard({
  title,
  description,
  status,
  statusLabel,
  preview,
  primaryAction,
  secondaryAction,
  dependency,
  errorMessage,
}: ResourceCardProps) {
  const dotColor = statusDotColor[status];
  const isProcessing = status === "processing";

  return (
    <div className="flex flex-col justify-between min-h-[140px] rounded-[8px] border border-[#cbd5e1] bg-white p-4 gap-3">
      {/* Header */}
      <div className="flex flex-col gap-1">
        <div className="flex items-center gap-2">
          <span
            className={`h-2 w-2 rounded-full flex-shrink-0${isProcessing ? " animate-spin" : ""}`}
            style={{ backgroundColor: dotColor }}
          />
          <span className="text-sm font-bold text-[#1e2229]">{title}</span>
          {statusLabel && (
            <span className="text-xs text-[#6b7280] ml-auto">{statusLabel}</span>
          )}
        </div>
        <p className="text-xs text-[#6b7280] pl-4">{description}</p>
        {errorMessage && (
          <p className="text-xs text-red-600 pl-4 mt-1">{errorMessage}</p>
        )}
        {preview && (
          <p className="text-xs text-[#1e2229] pl-4 line-clamp-2">{preview}</p>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 pl-4">
        {primaryAction.href && !primaryAction.disabled ? (
          <Link
            href={primaryAction.href}
            className="inline-flex items-center justify-center rounded-[4px] bg-[#f97316] px-3 py-1.5 text-xs font-medium text-white hover:bg-[#ea6c0a] transition-colors"
          >
            {primaryAction.label}
          </Link>
        ) : (
          <button
            onClick={primaryAction.onClick}
            disabled={primaryAction.disabled || primaryAction.loading}
            className="inline-flex items-center justify-center rounded-[4px] bg-[#f97316] px-3 py-1.5 text-xs font-medium text-white hover:bg-[#ea6c0a] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {primaryAction.loading ? (
              <span className="flex items-center gap-1.5">
                <span className="h-3 w-3 rounded-full border-2 border-white border-t-transparent animate-spin" />
                Generating…
              </span>
            ) : (
              primaryAction.label
            )}
          </button>
        )}

        {secondaryAction && (
          secondaryAction.href ? (
            <Link
              href={secondaryAction.href}
              className="text-xs font-medium text-[#6b7280] hover:text-[#1e2229] transition-colors"
            >
              {secondaryAction.label}
            </Link>
          ) : (
            <button
              onClick={secondaryAction.onClick}
              className="text-xs font-medium text-[#6b7280] hover:text-[#1e2229] transition-colors"
            >
              {secondaryAction.label}
            </button>
          )
        )}

        {primaryAction.disabled && dependency && (
          <span className="text-xs text-[#6b7280]">{dependency}</span>
        )}
      </div>
    </div>
  );
}
