import { describe, it, expect } from "vitest";
import {
  deriveModuleStatus,
  detectStaleness,
  deriveHubStatus,
  mapApplicationDataToHubState,
} from "../../adapters/mapApplicationDataToHubState";
import type { RawModuleData, RawApplicationData, RawGapAnalysisData, RawCVData } from "../../types/hub-state";
import type { ModuleType, ModuleStatus } from "../../types/enums";

const makeRawModule = (
  overrides: Partial<RawModuleData> = {}
): RawModuleData => ({
  job_id: "job-123",
  status: "completed",
  created_at: "2024-01-01T10:00:00Z",
  updated_at: "2024-01-01T10:05:00Z",
  ...overrides,
});

const makeApplication = (
  overrides: Partial<RawApplicationData> = {}
): RawApplicationData => ({
  application_id: "app-123",
  job_id: "job-123",
  user_id: "user-456",
  created_at: "2024-01-01T09:00:00Z",
  updated_at: "2024-01-01T09:00:00Z",
  is_finalized: false,
  ...overrides,
});

const makeCVData = (overrides: Partial<RawCVData> = {}): RawCVData => ({
  cv_id: "cv-789",
  ...overrides,
});

const makeGapAnalysis = (
  overrides: Partial<RawGapAnalysisData> = {}
): RawGapAnalysisData => ({
  job_id: "job-123",
  questions: [],
  responses: [],
  ...overrides,
});

describe("deriveModuleStatus", () => {
  it("null raw status → notStarted", () => {
    expect(deriveModuleStatus("vpr", null, false, false)).toBe("notStarted");
  });

  it("pending → processing", () => {
    expect(deriveModuleStatus("vpr", "pending", false, false)).toBe("processing");
  });

  it("processing → processing", () => {
    expect(deriveModuleStatus("vpr", "processing", false, false)).toBe("processing");
  });

  it("completed → ready", () => {
    expect(deriveModuleStatus("vpr", "completed", false, false)).toBe("ready");
  });

  it("completed + isStale → stale", () => {
    expect(deriveModuleStatus("vpr", "completed", true, false)).toBe("stale");
  });

  it("completed + isFinalized → final", () => {
    expect(deriveModuleStatus("vpr", "completed", false, true)).toBe("final");
  });

  it("finalized takes precedence over stale", () => {
    expect(deriveModuleStatus("vpr", "completed", true, true)).toBe("final");
  });

  it("failed → failed", () => {
    expect(deriveModuleStatus("vpr", "failed", false, false)).toBe("failed");
  });
});

describe("detectStaleness", () => {
  const allModules: Record<ModuleType, RawModuleData> = {
    vpr: makeRawModule({ created_at: "2024-01-01T10:00:00Z" }),
    tailoredCV: makeRawModule({ created_at: "2024-01-01T10:00:00Z" }),
    coverLetter: makeRawModule({ created_at: "2024-01-01T10:00:00Z" }),
    interviewPrep: makeRawModule({ created_at: "2024-01-01T10:00:00Z" }),
    gapAnalysis: makeRawModule({ created_at: "2024-01-01T10:00:00Z" }),
    companyResearch: makeRawModule({ created_at: "2024-01-01T10:00:00Z" }),
    baseCV: makeRawModule({ created_at: "2024-01-01T10:00:00Z" }),
  };

  it("returns empty set when nothing is stale", () => {
    const gapAnalysis = makeGapAnalysis({ responses_submitted_at: "2024-01-01T09:00:00Z" });
    const stale = detectStaleness(allModules, gapAnalysis);
    expect(stale.size).toBe(0);
  });

  it("gap responses edited after vpr creation invalidates 3 modules", () => {
    const gapAnalysis = makeGapAnalysis({
      responses_submitted_at: "2024-01-01T11:00:00Z",
    });
    const modulesWithOlderVPR = {
      ...allModules,
      vpr: makeRawModule({ created_at: "2024-01-01T10:00:00Z" }),
    };
    const stale = detectStaleness(modulesWithOlderVPR, gapAnalysis);

    expect(stale.has("vpr")).toBe(true);
    expect(stale.has("coverLetter")).toBe(true);
    expect(stale.has("interviewPrep")).toBe(true);
  });

  it("gap responses do NOT invalidate gapAnalysis, tailoredCV, companyResearch, baseCV", () => {
    const gapAnalysis = makeGapAnalysis({
      responses_submitted_at: "2024-01-01T11:00:00Z",
    });
    const stale = detectStaleness(allModules, gapAnalysis);

    expect(stale.has("gapAnalysis")).toBe(false);
    expect(stale.has("tailoredCV")).toBe(false);
    expect(stale.has("companyResearch")).toBe(false);
    expect(stale.has("baseCV")).toBe(false);
  });
});

describe("deriveHubStatus", () => {
  const allNotStarted: Record<ModuleType, ModuleStatus> = {
    vpr: 'notStarted',
    tailoredCV: 'notStarted',
    coverLetter: 'notStarted',
    interviewPrep: 'notStarted',
    gapAnalysis: 'notStarted',
    companyResearch: 'notStarted',
    baseCV: 'notStarted',
  };

  it("all modules notStarted → INIT", () => {
    expect(deriveHubStatus(allNotStarted, new Set(), false)).toBe("INIT");
  });

  it("isFinalized → FINALIZED (takes highest priority)", () => {
    expect(deriveHubStatus(allNotStarted, new Set(), true)).toBe("FINALIZED");
  });

  it("any module processing → LOADING", () => {
    const statuses: Record<ModuleType, ModuleStatus> = { ...allNotStarted, vpr: 'processing' };
    expect(deriveHubStatus(statuses, new Set(), false)).toBe("LOADING");
  });

  it("stale modules present → STALE_DEPENDENCIES", () => {
    const statuses: Record<ModuleType, ModuleStatus> = { ...allNotStarted, vpr: 'ready' };
    const staleModules = new Set<ModuleType>(['vpr']);
    expect(deriveHubStatus(statuses, staleModules, false)).toBe("STALE_DEPENDENCIES");
  });

  it("critical module failed → ERROR_RECOVERABLE", () => {
    const statuses: Record<ModuleType, ModuleStatus> = { ...allNotStarted, vpr: 'failed' };
    expect(deriveHubStatus(statuses, new Set(), false)).toBe("ERROR_RECOVERABLE");
  });

  it("non-critical module failed alone → does NOT produce ERROR_RECOVERABLE", () => {
    const statuses: Record<ModuleType, ModuleStatus> = { ...allNotStarted, companyResearch: 'failed' };
    const result = deriveHubStatus(statuses, new Set(), false);
    expect(result).not.toBe("ERROR_RECOVERABLE");
  });

  it("all modules complete or final → READY_COMPLETE", () => {
    const statuses = Object.fromEntries(
      Object.keys(allNotStarted).map((k) => [k, 'complete' as ModuleStatus])
    ) as Record<ModuleType, ModuleStatus>;
    expect(deriveHubStatus(statuses, new Set(), false)).toBe("READY_COMPLETE");
  });

  it("some complete, some notStarted → READY_PARTIAL", () => {
    const statuses: Record<ModuleType, ModuleStatus> = { ...allNotStarted, vpr: 'ready', gapAnalysis: 'complete' };
    expect(deriveHubStatus(statuses, new Set(), false)).toBe("READY_PARTIAL");
  });
});

describe("mapApplicationDataToHubState integration", () => {
  it("returns HubState with all 7 module entries", () => {
    const application = makeApplication();
    const cvData = makeCVData();
    const result = mapApplicationDataToHubState(application, {}, null, cvData);

    expect(Object.keys(result.modules)).toHaveLength(7);
  });

  it("totalCount is always 7", () => {
    const result = mapApplicationDataToHubState(makeApplication(), {}, null, null);
    expect(result.totalCount).toBe(7);
  });

  it("baseCV is ready when cvData has cv_id", () => {
    const result = mapApplicationDataToHubState(makeApplication(), {}, null, makeCVData());
    expect(result.modules.baseCV.status).toBe("ready");
  });

  it("baseCV is notStarted when cvData is null", () => {
    const result = mapApplicationDataToHubState(makeApplication(), {}, null, null);
    expect(result.modules.baseCV.status).toBe("notStarted");
  });

  it("progressPercent includes baseCV when cv exists", () => {
    const result = mapApplicationDataToHubState(makeApplication(), {}, null, makeCVData());
    expect(result.completedCount).toBeGreaterThanOrEqual(1);
  });

  it("progressPercent is 0 when all modules are notStarted and no cv", () => {
    const result = mapApplicationDataToHubState(makeApplication(), {}, null, null);
    expect(result.progressPercent).toBe(0);
  });

  it("progressPercent is 100 when all modules are complete and cv exists", () => {
    const allComplete = Object.fromEntries(
      ["vpr", "tailoredCV", "coverLetter", "interviewPrep", "gapAnalysis", "companyResearch"].map(
        (k) => [k, makeRawModule({ status: "completed" })]
      )
    ) as Record<ModuleType, RawModuleData>;

    const result = mapApplicationDataToHubState(
      makeApplication({ is_finalized: false }),
      allComplete,
      null,
      makeCVData(),
    );
    expect(result.progressPercent).toBe(100);
  });

  it("isFinalized reflects application.is_finalized", () => {
    const result = mapApplicationDataToHubState(
      makeApplication({ is_finalized: true }),
      {},
      null,
      null,
    );
    expect(result.isFinalized).toBe(true);
  });
});
