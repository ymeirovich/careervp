import { describe, it, expect } from "vitest";
import { deriveHubStatus } from "../../adapters/mapApplicationDataToHubState";
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

function makeStatuses(base: ModuleStatus, overrides: Partial<Record<ModuleType, ModuleStatus>> = {}): Record<ModuleType, ModuleStatus> {
  const result = Object.fromEntries(ALL_MODULE_TYPES.map((m) => [m, base])) as Record<ModuleType, ModuleStatus>;
  return { ...result, ...overrides };
}

describe("deriveHubStatus — FINALIZED always wins", () => {
  it("returns FINALIZED even when all modules are failed", () => {
    expect(deriveHubStatus(makeStatuses("failed"), new Set(), true)).toBe("FINALIZED");
  });

  it("returns FINALIZED even when stale modules exist", () => {
    expect(deriveHubStatus(makeStatuses("ready"), new Set<ModuleType>(["vpr"]), true)).toBe("FINALIZED");
  });

  it("returns FINALIZED when all modules are processing", () => {
    expect(deriveHubStatus(makeStatuses("processing"), new Set(), true)).toBe("FINALIZED");
  });
});

describe("deriveHubStatus — PROCESSING_BLOCKED conditions", () => {
  it("triggers when gapAnalysis is notStarted and companyResearch is ready", () => {
    const statuses = makeStatuses("notStarted", { companyResearch: "ready" });
    expect(deriveHubStatus(statuses, new Set(), false)).toBe("PROCESSING_BLOCKED");
  });

  it("triggers when gapAnalysis is notStarted and baseCV is ready", () => {
    const statuses = makeStatuses("notStarted", { baseCV: "ready" });
    expect(deriveHubStatus(statuses, new Set(), false)).toBe("PROCESSING_BLOCKED");
  });

  it("does NOT trigger when gapAnalysis is already started", () => {
    const statuses = makeStatuses("notStarted", { companyResearch: "ready", gapAnalysis: "processing" });
    expect(deriveHubStatus(statuses, new Set(), false)).not.toBe("PROCESSING_BLOCKED");
  });

  it("does NOT trigger when both companyResearch and baseCV are notStarted", () => {
    const statuses = makeStatuses("notStarted");
    expect(deriveHubStatus(statuses, new Set(), false)).toBe("INIT");
  });
});

describe("deriveHubStatus — ERROR_RECOVERABLE for critical modules", () => {
  const critical: ModuleType[] = ["vpr", "gapAnalysis", "baseCV"];

  critical.forEach((module) => {
    it(`returns ERROR_RECOVERABLE when ${module} fails`, () => {
      const statuses = makeStatuses("ready", { [module]: "failed" });
      expect(deriveHubStatus(statuses, new Set(), false)).toBe("ERROR_RECOVERABLE");
    });
  });
});

describe("deriveHubStatus — non-critical failures do NOT trigger ERROR_RECOVERABLE", () => {
  const nonCritical: ModuleType[] = ["tailoredCV", "coverLetter", "interviewPrep", "companyResearch"];

  nonCritical.forEach((module) => {
    it(`${module} failing alone does not produce ERROR_RECOVERABLE`, () => {
      const statuses = makeStatuses("ready", { [module]: "failed" });
      const result = deriveHubStatus(statuses, new Set(), false);
      expect(result).not.toBe("ERROR_RECOVERABLE");
    });
  });
});
