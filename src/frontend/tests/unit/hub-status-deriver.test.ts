import { describe, it, expect } from "vitest";
import { deriveHubStatus } from "../../adapters/mapApplicationDataToHubState";
import type { ModuleType, ModuleStatus } from "../../types/enums";

type StatusMap = Record<ModuleType, ModuleStatus>;

const ALL_MODULES: ModuleType[] = [
  "vpr",
  "tailoredCV",
  "coverLetter",
  "interviewPrep",
  "gapAnalysis",
  "companyResearch",
  "baseCV",
];

function allWith(status: ModuleStatus): StatusMap {
  return Object.fromEntries(ALL_MODULES.map((m) => [m, status])) as StatusMap;
}

const CRITICAL_MODULES: ModuleType[] = ["vpr", "gapAnalysis", "baseCV"];
const NON_CRITICAL_MODULES: ModuleType[] = ["tailoredCV", "coverLetter", "interviewPrep", "companyResearch"];

describe("deriveHubStatus — FINALIZED always wins", () => {
  it("returns FINALIZED when isFinalized=true regardless of module statuses", () => {
    expect(deriveHubStatus(allWith("notStarted"), new Set(), true)).toBe("FINALIZED");
    expect(deriveHubStatus(allWith("processing"), new Set(), true)).toBe("FINALIZED");
    expect(deriveHubStatus(allWith("failed"), new Set(), true)).toBe("FINALIZED");
    expect(deriveHubStatus(allWith("complete"), new Set(), true)).toBe("FINALIZED");
  });

  it("returns FINALIZED even with stale modules when isFinalized=true", () => {
    const stale = new Set<ModuleType>(["vpr", "coverLetter"]);
    expect(deriveHubStatus(allWith("stale"), stale, true)).toBe("FINALIZED");
  });

  it("returns FINALIZED even with critical module failed when isFinalized=true", () => {
    const statuses = { ...allWith("complete"), vpr: "failed" as ModuleStatus };
    expect(deriveHubStatus(statuses, new Set(), true)).toBe("FINALIZED");
  });
});

describe("deriveHubStatus — PROCESSING_BLOCKED", () => {
  it("returns PROCESSING_BLOCKED when gapAnalysis is notStarted and companyResearch is ready", () => {
    const statuses: StatusMap = {
      ...allWith("notStarted"),
      companyResearch: "ready",
      baseCV: "notStarted",
    };
    expect(deriveHubStatus(statuses, new Set(), false)).toBe("PROCESSING_BLOCKED");
  });

  it("returns PROCESSING_BLOCKED when gapAnalysis is notStarted and baseCV is ready", () => {
    const statuses: StatusMap = {
      ...allWith("notStarted"),
      companyResearch: "notStarted",
      baseCV: "ready",
    };
    expect(deriveHubStatus(statuses, new Set(), false)).toBe("PROCESSING_BLOCKED");
  });

  it("returns PROCESSING_BLOCKED when gapAnalysis is notStarted and baseCV is complete", () => {
    const statuses: StatusMap = {
      ...allWith("notStarted"),
      baseCV: "complete",
    };
    expect(deriveHubStatus(statuses, new Set(), false)).toBe("PROCESSING_BLOCKED");
  });

  it("does NOT return PROCESSING_BLOCKED when gapAnalysis has started", () => {
    const statuses: StatusMap = {
      ...allWith("notStarted"),
      gapAnalysis: "processing",
      companyResearch: "ready",
    };
    expect(deriveHubStatus(statuses, new Set(), false)).not.toBe("PROCESSING_BLOCKED");
  });
});

describe("deriveHubStatus — ERROR_RECOVERABLE only for critical modules", () => {
  CRITICAL_MODULES.forEach((module) => {
    it(`returns ERROR_RECOVERABLE when critical module ${module} fails`, () => {
      const statuses = { ...allWith("ready"), [module]: "failed" as ModuleStatus };
      expect(deriveHubStatus(statuses, new Set(), false)).toBe("ERROR_RECOVERABLE");
    });
  });

  NON_CRITICAL_MODULES.forEach((module) => {
    it(`does NOT return ERROR_RECOVERABLE when non-critical module ${module} fails alone`, () => {
      const statuses = { ...allWith("ready"), [module]: "failed" as ModuleStatus };
      expect(deriveHubStatus(statuses, new Set(), false)).not.toBe("ERROR_RECOVERABLE");
    });
  });

  it("non-critical failures alongside ready modules do not trigger ERROR_RECOVERABLE", () => {
    const statuses: StatusMap = {
      ...allWith("ready"),
      tailoredCV: "failed",
      coverLetter: "failed",
    };
    expect(deriveHubStatus(statuses, new Set(), false)).not.toBe("ERROR_RECOVERABLE");
  });
});
