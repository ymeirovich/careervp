import { describe, it, expect } from "vitest";
import { detectStaleness } from "../../adapters/mapApplicationDataToHubState";
import type { RawModuleData, RawCVData, RawGapAnalysisData } from "../../types/hub-state";
import type { ModuleType } from "../../types/enums";

const BASE_TIME = "2024-01-01T10:00:00Z";
const AFTER_TIME = "2024-01-01T11:00:00Z";
const BEFORE_TIME = "2024-01-01T09:00:00Z";

function makeModule(overrides: Partial<RawModuleData> = {}): RawModuleData {
  return {
    job_id: "job-reg-001",
    status: "completed",
    created_at: BASE_TIME,
    updated_at: BASE_TIME,
    ...overrides,
  };
}

const ALL_MODULES_COMPLETE: Record<ModuleType, RawModuleData> = {
  vpr: makeModule(),
  tailoredCV: makeModule(),
  coverLetter: makeModule(),
  interviewPrep: makeModule(),
  gapAnalysis: makeModule(),
  companyResearch: makeModule(),
  baseCV: makeModule(),
};

describe("Staleness rule: CV change", () => {
  const CV_CHANGED: RawCVData = {
    cv_id: "cv-001",
    created_at: BEFORE_TIME,
    updated_at: AFTER_TIME,
    version: 2,
  };
  const PREVIOUS_CV_AT = BASE_TIME;

  it("invalidates gapAnalysis", () => {
    const stale = detectStaleness(ALL_MODULES_COMPLETE, CV_CHANGED, PREVIOUS_CV_AT, null);
    expect(stale.has("gapAnalysis")).toBe(true);
  });

  it("invalidates vpr", () => {
    const stale = detectStaleness(ALL_MODULES_COMPLETE, CV_CHANGED, PREVIOUS_CV_AT, null);
    expect(stale.has("vpr")).toBe(true);
  });

  it("invalidates tailoredCV", () => {
    const stale = detectStaleness(ALL_MODULES_COMPLETE, CV_CHANGED, PREVIOUS_CV_AT, null);
    expect(stale.has("tailoredCV")).toBe(true);
  });

  it("invalidates coverLetter", () => {
    const stale = detectStaleness(ALL_MODULES_COMPLETE, CV_CHANGED, PREVIOUS_CV_AT, null);
    expect(stale.has("coverLetter")).toBe(true);
  });

  it("invalidates interviewPrep", () => {
    const stale = detectStaleness(ALL_MODULES_COMPLETE, CV_CHANGED, PREVIOUS_CV_AT, null);
    expect(stale.has("interviewPrep")).toBe(true);
  });

  it("does NOT invalidate companyResearch", () => {
    const stale = detectStaleness(ALL_MODULES_COMPLETE, CV_CHANGED, PREVIOUS_CV_AT, null);
    expect(stale.has("companyResearch")).toBe(false);
  });

  it("does NOT invalidate baseCV", () => {
    const stale = detectStaleness(ALL_MODULES_COMPLETE, CV_CHANGED, PREVIOUS_CV_AT, null);
    expect(stale.has("baseCV")).toBe(false);
  });

  it("does NOT produce stale when CV has not changed since artifacts were generated", () => {
    const unchangedCV: RawCVData = {
      cv_id: "cv-001",
      created_at: BEFORE_TIME,
      updated_at: BASE_TIME,
      version: 1,
    };
    const stale = detectStaleness(ALL_MODULES_COMPLETE, unchangedCV, BASE_TIME, null);
    expect(stale.size).toBe(0);
  });

  it("exactly 5 modules are stale (not 4, not 6)", () => {
    const stale = detectStaleness(ALL_MODULES_COMPLETE, CV_CHANGED, PREVIOUS_CV_AT, null);
    expect(stale.size).toBe(5);
  });
});

describe("Staleness rule: Gap responses edited after VPR creation", () => {
  const GAP_ANALYSIS_WITH_LATE_RESPONSES: RawGapAnalysisData = {
    job_id: "job-reg-001",
    questions: [],
    responses: [],
    responses_submitted_at: AFTER_TIME,
  };

  it("invalidates vpr", () => {
    const stale = detectStaleness(ALL_MODULES_COMPLETE, null, null, GAP_ANALYSIS_WITH_LATE_RESPONSES);
    expect(stale.has("vpr")).toBe(true);
  });

  it("invalidates coverLetter", () => {
    const stale = detectStaleness(ALL_MODULES_COMPLETE, null, null, GAP_ANALYSIS_WITH_LATE_RESPONSES);
    expect(stale.has("coverLetter")).toBe(true);
  });

  it("invalidates interviewPrep", () => {
    const stale = detectStaleness(ALL_MODULES_COMPLETE, null, null, GAP_ANALYSIS_WITH_LATE_RESPONSES);
    expect(stale.has("interviewPrep")).toBe(true);
  });

  it("does NOT invalidate gapAnalysis itself", () => {
    const stale = detectStaleness(ALL_MODULES_COMPLETE, null, null, GAP_ANALYSIS_WITH_LATE_RESPONSES);
    expect(stale.has("gapAnalysis")).toBe(false);
  });

  it("does NOT invalidate tailoredCV", () => {
    const stale = detectStaleness(ALL_MODULES_COMPLETE, null, null, GAP_ANALYSIS_WITH_LATE_RESPONSES);
    expect(stale.has("tailoredCV")).toBe(false);
  });

  it("does NOT invalidate companyResearch", () => {
    const stale = detectStaleness(ALL_MODULES_COMPLETE, null, null, GAP_ANALYSIS_WITH_LATE_RESPONSES);
    expect(stale.has("companyResearch")).toBe(false);
  });

  it("does NOT invalidate baseCV", () => {
    const stale = detectStaleness(ALL_MODULES_COMPLETE, null, null, GAP_ANALYSIS_WITH_LATE_RESPONSES);
    expect(stale.has("baseCV")).toBe(false);
  });

  it("exactly 3 modules are stale (not 2, not 4)", () => {
    const stale = detectStaleness(ALL_MODULES_COMPLETE, null, null, GAP_ANALYSIS_WITH_LATE_RESPONSES);
    expect(stale.size).toBe(3);
  });
});

describe("Staleness rule: no false positives from unrelated changes", () => {
  it("only interviewPrep edited → no other module becomes stale", () => {
    const stale = detectStaleness(ALL_MODULES_COMPLETE, null, null, null);
    expect(stale.size).toBe(0);
  });

  it("gap responses submitted BEFORE VPR creation → no stale modules", () => {
    const earlyGapAnalysis: RawGapAnalysisData = {
      job_id: "job-reg-001",
      questions: [],
      responses: [],
      responses_submitted_at: BEFORE_TIME,
    };
    const stale = detectStaleness(ALL_MODULES_COMPLETE, null, null, earlyGapAnalysis);
    expect(stale.size).toBe(0);
  });
});
