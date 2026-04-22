import { describe, it, expect } from "vitest";
import { deriveHubStatus } from "../../adapters/mapApplicationDataToHubState";
import type { ModuleType, ModuleStatus } from "../../types/enums";

type ModuleStatusMap = Record<ModuleType, ModuleStatus>;

const ALL_MODULE_TYPES: ModuleType[] = [
  "vpr",
  "tailoredCV",
  "coverLetter",
  "interviewPrep",
  "gapAnalysis",
  "companyResearch",
  "baseCV",
];

function allWith(status: ModuleStatus): ModuleStatusMap {
  return Object.fromEntries(ALL_MODULE_TYPES.map((m) => [m, status])) as ModuleStatusMap;
}

describe("HubStatus — all reachable states", () => {
  it("INIT is reachable when all 7 modules are notStarted", () => {
    expect(deriveHubStatus(allWith("notStarted"), new Set(), false)).toBe("INIT");
  });

  it("LOADING is reachable when any module is processing", () => {
    const statuses = { ...allWith("notStarted"), vpr: "processing" };
    expect(deriveHubStatus(statuses as ModuleStatusMap, new Set(), false)).toBe("LOADING");
  });

  it("FINALIZED is reachable when isFinalized=true", () => {
    expect(deriveHubStatus(allWith("final"), new Set(), true)).toBe("FINALIZED");
  });

  it("ERROR_RECOVERABLE is reachable when a critical module fails", () => {
    const critical: ModuleType[] = ["vpr", "gapAnalysis", "baseCV"];
    critical.forEach((module) => {
      const statuses = { ...allWith("ready"), [module]: "failed" };
      expect(
        deriveHubStatus(statuses as ModuleStatusMap, new Set(), false),
        `Expected ERROR_RECOVERABLE when ${module} fails`
      ).toBe("ERROR_RECOVERABLE");
    });
  });

  it("STALE_DEPENDENCIES is reachable when staleModules is non-empty", () => {
    const statuses = { ...allWith("ready") };
    const stale = new Set<ModuleType>(["vpr"]);
    expect(deriveHubStatus(statuses, stale, false)).toBe("STALE_DEPENDENCIES");
  });

  it("PROCESSING_BLOCKED is reachable when gap analysis not started and VPR exists", () => {
    const statuses = {
      ...allWith("notStarted"),
      vpr: "notStarted",
      gapAnalysis: "notStarted",
      companyResearch: "ready",
      baseCV: "ready",
    };
    expect(
      deriveHubStatus(statuses as ModuleStatusMap, new Set(), false)
    ).toBe("PROCESSING_BLOCKED");
  });

  it("READY_COMPLETE is reachable when all modules are complete", () => {
    expect(deriveHubStatus(allWith("complete"), new Set(), false)).toBe("READY_COMPLETE");
  });

  it("READY_COMPLETE also holds when all modules are final (without isFinalized flag)", () => {
    expect(deriveHubStatus(allWith("final"), new Set(), false)).toBe("READY_COMPLETE");
  });

  it("READY_PARTIAL is reachable when some complete, some notStarted", () => {
    const statuses = { ...allWith("notStarted"), vpr: "ready", gapAnalysis: "complete" };
    expect(deriveHubStatus(statuses as ModuleStatusMap, new Set(), false)).toBe("READY_PARTIAL");
  });
});

describe("HubStatus — priority rules (no ambiguity)", () => {
  it("FINALIZED always overrides any other condition", () => {
    const contradictingStatuses = { ...allWith("failed"), vpr: "failed" };
    expect(
      deriveHubStatus(contradictingStatuses as ModuleStatusMap, new Set<ModuleType>(["vpr"]), true)
    ).toBe("FINALIZED");
  });

  it("LOADING takes precedence over READY_PARTIAL", () => {
    const statuses = { ...allWith("complete"), vpr: "processing" };
    expect(deriveHubStatus(statuses as ModuleStatusMap, new Set(), false)).toBe("LOADING");
  });

  it("STALE_DEPENDENCIES takes precedence over READY_PARTIAL", () => {
    const statuses = { ...allWith("ready") };
    const stale = new Set<ModuleType>(["coverLetter"]);
    const result = deriveHubStatus(statuses, stale, false);
    expect(result).not.toBe("READY_PARTIAL");
    expect(result).toBe("STALE_DEPENDENCIES");
  });
});

describe("HubStatus — non-critical module failure does not trigger ERROR_RECOVERABLE alone", () => {
  const nonCritical: ModuleType[] = ["tailoredCV", "coverLetter", "interviewPrep", "companyResearch"];

  nonCritical.forEach((module) => {
    it(`${module} failing alone does not produce ERROR_RECOVERABLE`, () => {
      const statuses = { ...allWith("ready"), [module]: "failed" };
      const result = deriveHubStatus(statuses as ModuleStatusMap, new Set(), false);
      expect(result).not.toBe("ERROR_RECOVERABLE");
    });
  });
});

describe("HubStatus — INIT requires ALL 7 modules to be notStarted", () => {
  ALL_MODULE_TYPES.forEach((module) => {
    it(`INIT is NOT produced when ${module} has any non-notStarted status`, () => {
      const statuses = { ...allWith("notStarted"), [module]: "processing" };
      expect(
        deriveHubStatus(statuses as ModuleStatusMap, new Set(), false)
      ).not.toBe("INIT");
    });
  });
});
