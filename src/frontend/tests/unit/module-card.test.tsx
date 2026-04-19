import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { ModuleCard } from "../../components/ModuleCard/ModuleCard";
import type { ModuleType, ModuleStatus } from "../../types/enums";

const defaultProps = {
  module: "vpr" as ModuleType,
  title: "Value Proposition Report",
  subtitle: "AI-generated match analysis",
};

describe("ModuleCard — notStarted state", () => {
  it("shows Generate CTA for non-baseCV modules", () => {
    render(<ModuleCard {...defaultProps} state="notStarted" />);
    expect(screen.getByRole("button", { name: /generate/i })).toBeDefined();
  });

  it("shows Start CTA for baseCV module", () => {
    render(
      <ModuleCard {...defaultProps} module="baseCV" title="Base CV" state="notStarted" />
    );
    expect(screen.getByRole("button", { name: /start/i })).toBeDefined();
  });

  it("does not render a badge in notStarted state", () => {
    render(<ModuleCard {...defaultProps} state="notStarted" />);
    expect(screen.queryByTestId("status-badge")).toBeNull();
  });

  it("does not render secondary actions in notStarted state", () => {
    render(<ModuleCard {...defaultProps} state="notStarted" />);
    const secondaryButtons = screen.queryAllByRole("button");
    expect(secondaryButtons).toHaveLength(1);
  });
});

describe("ModuleCard — processing state", () => {
  it("shows spinner element", () => {
    render(<ModuleCard {...defaultProps} state="processing" />);
    expect(screen.getByRole("status")).toBeDefined();
  });

  it("spinner has aria-label for screen readers", () => {
    render(<ModuleCard {...defaultProps} state="processing" />);
    const spinner = screen.getByRole("status");
    expect(spinner.getAttribute("aria-label") || spinner.getAttribute("aria-busy")).toBeTruthy();
  });

  it("does not render any CTA buttons", () => {
    render(<ModuleCard {...defaultProps} state="processing" />);
    expect(screen.queryAllByRole("button")).toHaveLength(0);
  });

  it("shows progressText when provided", () => {
    render(
      <ModuleCard {...defaultProps} state="processing" progressText="Stage 3 of 6..." />
    );
    expect(screen.getByText("Stage 3 of 6...")).toBeDefined();
  });
});

describe("ModuleCard — ready state", () => {
  it("shows View as primary CTA", () => {
    render(<ModuleCard {...defaultProps} state="ready" />);
    expect(screen.getByRole("button", { name: /view/i })).toBeDefined();
  });

  it("shows Edit and Regenerate as secondary CTAs", () => {
    render(<ModuleCard {...defaultProps} state="ready" />);
    expect(screen.getByRole("button", { name: /edit/i })).toBeDefined();
    expect(screen.getByRole("button", { name: /regenerate/i })).toBeDefined();
  });

  it("does not show a badge", () => {
    render(<ModuleCard {...defaultProps} state="ready" />);
    expect(screen.queryByTestId("status-badge")).toBeNull();
  });
});

describe("ModuleCard — complete state", () => {
  it("shows View as primary CTA", () => {
    render(<ModuleCard {...defaultProps} state="complete" />);
    expect(screen.getByRole("button", { name: /view/i })).toBeDefined();
  });

  it("shows Edit and History as secondary CTAs", () => {
    render(<ModuleCard {...defaultProps} state="complete" />);
    expect(screen.getByRole("button", { name: /edit/i })).toBeDefined();
    expect(screen.getByRole("button", { name: /history/i })).toBeDefined();
  });
});

describe("ModuleCard — edited state", () => {
  it("shows Edited badge", () => {
    render(<ModuleCard {...defaultProps} state="edited" badgeLabel="Edited" />);
    expect(screen.getByText(/edited/i)).toBeDefined();
  });

  it("shows Regenerate as primary CTA", () => {
    render(<ModuleCard {...defaultProps} state="edited" />);
    expect(screen.getByRole("button", { name: /regenerate/i })).toBeDefined();
  });
});

describe("ModuleCard — stale state", () => {
  it("shows Outdated badge", () => {
    render(<ModuleCard {...defaultProps} state="stale" badgeLabel="Outdated" />);
    expect(screen.getByText(/outdated/i)).toBeDefined();
  });

  it("shows Regenerate as primary CTA", () => {
    render(<ModuleCard {...defaultProps} state="stale" />);
    expect(screen.getByRole("button", { name: /regenerate/i })).toBeDefined();
  });

  it("renders warningText when provided", () => {
    render(
      <ModuleCard
        {...defaultProps}
        state="stale"
        warningText="CV was updated — this artifact is outdated."
      />
    );
    expect(screen.getByText(/cv was updated/i)).toBeDefined();
  });
});

describe("ModuleCard — failed state", () => {
  it("shows Retry as primary CTA", () => {
    render(<ModuleCard {...defaultProps} state="failed" />);
    expect(screen.getByRole("button", { name: /retry/i })).toBeDefined();
  });

  it("does not show Regenerate (wrong label for failed)", () => {
    render(<ModuleCard {...defaultProps} state="failed" />);
    expect(screen.queryByRole("button", { name: /regenerate/i })).toBeNull();
  });
});

describe("ModuleCard — timeout state", () => {
  it("shows Refresh as primary CTA", () => {
    render(<ModuleCard {...defaultProps} state="timeout" />);
    expect(screen.getByRole("button", { name: /refresh/i })).toBeDefined();
  });

  it("shows a 'still processing' message", () => {
    render(<ModuleCard {...defaultProps} state="timeout" />);
    expect(screen.getByText(/still processing/i)).toBeDefined();
  });
});

describe("ModuleCard — final state", () => {
  it("shows Final badge", () => {
    render(<ModuleCard {...defaultProps} state="final" badgeLabel="Final" />);
    expect(screen.getByText(/final/i)).toBeDefined();
  });

  it("shows Export as primary CTA", () => {
    render(<ModuleCard {...defaultProps} state="final" />);
    expect(screen.getByRole("button", { name: /export/i })).toBeDefined();
  });

  it("shows History as secondary CTA", () => {
    render(<ModuleCard {...defaultProps} state="final" />);
    expect(screen.getByRole("button", { name: /history/i })).toBeDefined();
  });
});

describe("ModuleCard — meta display", () => {
  it("renders meta text when provided", () => {
    render(<ModuleCard {...defaultProps} state="ready" meta="ATS score: 74" />);
    expect(screen.getByText("ATS score: 74")).toBeDefined();
  });
});

describe("ModuleCard — all module types render without error", () => {
  const moduleTypes: ModuleType[] = [
    "vpr",
    "tailoredCV",
    "coverLetter",
    "interviewPrep",
    "gapAnalysis",
    "companyResearch",
    "baseCV",
  ];

  const states: ModuleStatus[] = [
    "notStarted",
    "processing",
    "ready",
    "complete",
    "edited",
    "stale",
    "failed",
    "timeout",
    "final",
  ];

  moduleTypes.forEach((module) => {
    states.forEach((state) => {
      it(`renders ${module} in ${state} state without throwing`, () => {
        expect(() =>
          render(
            <ModuleCard
              module={module}
              state={state}
              title={`${module} module`}
            />
          )
        ).not.toThrow();
      });
    });
  });
});
