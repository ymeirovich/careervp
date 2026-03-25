import * as React from "react";

interface FormFieldProps {
  label: string;
  required?: boolean;
  hint?: string;
  error?: string;
  children: React.ReactNode;
}

export function FormField({ label, required, hint, error, children }: FormFieldProps) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-sm font-medium text-[#1e2229]">
        {label}{" "}
        {required && <span className="text-[#ef4444]">*</span>}
      </label>
      {hint && <p className="text-xs text-[#6b7280]">{hint}</p>}
      {children}
      {error && <p className="text-xs text-[#ef4444]">{error}</p>}
    </div>
  );
}

// Shared input className for use with FormField inputs
export const inputClassName =
  "rounded-[4px] border border-[#cbd5e1] px-3 py-2 text-sm text-[#1e2229] focus:outline-none focus:border-[#f97316] focus:ring-1 focus:ring-[#f97316]";
