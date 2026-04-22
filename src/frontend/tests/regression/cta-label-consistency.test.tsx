import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";
import { ModuleCard } from "../../components/ModuleCard/ModuleCard";
import type { ModuleType, ModuleStatus } from "../../types/enums";

const ALL_MODULE_TYPES: ModuleType[] = [
  "vpr",
  "tailoredCV",
  "coverLetter",
  "interviewPrep",
  "gapAnalysis",
  "companyResearch",
  "baseCV",
];

const EXPECTED_PRIMARY_CTA: Partial<Record<ModuleStatus, string | ((module: ModuleType) => string)>> = {
  notStarted: (module) => (module === "baseCV" ? "Start" : "Generate"),
  ready: "View",
  complete: "View",
  edited: "Regenerate",
  stale: "Regenerate",
  failed: "Retry",
  timeout: "Refresh",
  final: "Export",
};

const STATES_WITH_NO_CTA: ModuleStatus[] = ["processing"];

describe("CTA label consistency — primary CTA matches design spec exactly", () => {
  Object.entries(EXPECTED_PRIMARY_CTA).forEach(([state, expectedLabel]) => {
    ALL_MODULE_TYPES.forEach((module) => {
      const label =
        typeof expectedLabel === "function" ? expectedLabel(module) : expectedLabel;

      it(`${module} in ${state} state shows primary CTA "${label}"`, () => {
        render(
          <ModuleCard
            module={module}
            state={state as ModuleStatus}
            title={`${module} title`}
          />
        );
        const primaryCta = screen.getByTestId("primary-cta");
        expect(primaryCta.textContent?.trim()).toBe(label);
      });
    });
  });

  STATES_WITH_NO_CTA.forEach((state) => {
    ALL_MODULE_TYPES.forEach((module) => {
      it(`${module} in ${state} state has NO primary CTA`, () => {
        render(
          <ModuleCard module={module} state={state} title={`${module} title`} />
        );
        expect(screen.queryByTestId("primary-cta")).toBeNull();
      });
    });
  });
});

describe("CTA label consistency — prohibited label combinations", () => {
  it('notStarted state (non-baseCV) never shows "Regenerate"', () => {
    const nonBaseCVModules = ALL_MODULE_TYPES.filter((m) => m !== "baseCV");
    nonBaseCVModules.forEach((module) => {
      const { unmount } = render(
        <ModuleCard module={module} state="notStarted" title="test" />
      );
      expect(screen.queryByRole("button", { name: /regenerate/i })).toBeNull();
      unmount();
    });
  });

  it('failed state never shows "Generate" or "Regenerate"', () => {
    ALL_MODULE_TYPES.forEach((module) => {
      const { unmount } = render(
        <ModuleCard module={module} state="failed" title="test" />
      );
      expect(screen.queryByRole("button", { name: /^generate$/i })).toBeNull();
      expect(screen.queryByRole("button", { name: /^regenerate$/i })).toBeNull();
      unmount();
    });
  });

  it('ready state never shows "Retry"', () => {
    ALL_MODULE_TYPES.forEach((module) => {
      const { unmount } = render(
        <ModuleCard module={module} state="ready" title="test" />
      );
      expect(screen.queryByRole("button", { name: /retry/i })).toBeNull();
      unmount();
    });
  });

  it('final state never shows "Generate" or "Regenerate"', () => {
    ALL_MODULE_TYPES.forEach((module) => {
      const { unmount } = render(
        <ModuleCard module={module} state="final" title="test" />
      );
      expect(screen.queryByRole("button", { name: /^generate$/i })).toBeNull();
      expect(screen.queryByRole("button", { name: /^regenerate$/i })).toBeNull();
      unmount();
    });
  });
});
