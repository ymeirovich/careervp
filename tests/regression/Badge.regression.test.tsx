// spec_id: FE-UI-001  component: Badge
// Regression guard: assert that existing solid-variant behaviour and all sibling
// components that import Badge are unaffected by the soft-prop addition.
// See rollback triggers: RT-001, RT-002 in the spec.
import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from '@jest/globals';
import { Badge } from '../../src/frontend/components/ui/Badge';
import { StatusBadge } from '../../src/frontend/components/ui/StatusBadge';
import { ModuleCard } from '../../src/frontend/components/ModuleCard/ModuleCard';

// ---------------------------------------------------------------------------
// Existing solid-variant contract (AC-008, AC-009 are the unit enforcement;
// these regression tests guard against unintended style changes post-merge)
// ---------------------------------------------------------------------------
describe('Badge regression — solid variants unchanged', () => {

  it('test_existing_api_contract_unchanged', () => {
    // Badge has no API endpoints — assert component interface contract instead.
    // TODO: import BadgeProps type and assert required fields match prior contract:
    //   variant: BadgeVariant  (required)
    //   label?: string         (optional)
    //   icon?: React.ReactNode (optional)
    //   children?: React.ReactNode (optional)
    //   className?: string     (optional)
    //   data-testid?: string   (optional)
    //   soft?: boolean | undefined  (NEW — optional, must not break existing callers)
    // TODO: construct a BadgeProps object without soft and assert it is valid
  });

  it('test_solid_success_badge_unchanged', () => {
    // RT-001 guard: variant="success" without soft must render identically to pre-upgrade
    // TODO: render <Badge variant="success" label="Done" data-testid="b" />
    // TODO: assert element classList contains "bg-state-active"
    // TODO: assert element classList contains "text-white"
    // TODO: assert element classList does NOT contain "bg-green-50"
  });

  it('test_solid_warning_badge_unchanged', () => {
    // TODO: render <Badge variant="warning" label="Warning" data-testid="b" />
    // TODO: assert element classList contains "bg-state-warning"
    // TODO: assert element classList contains "text-white"
  });

  it('test_solid_error_badge_unchanged', () => {
    // TODO: render <Badge variant="error" label="Failed" data-testid="b" />
    // TODO: assert element classList contains "bg-state-error"
    // TODO: assert element classList contains "text-white"
  });

  it('test_solid_info_badge_unchanged', () => {
    // TODO: render <Badge variant="info" label="Info" data-testid="b" />
    // TODO: assert element classList contains "bg-state-info"
    // TODO: assert element classList contains "text-white"
  });

  it('test_solid_neutral_badge_unchanged', () => {
    // TODO: render <Badge variant="neutral" label="Neutral" data-testid="b" />
    // TODO: assert element classList contains "bg-surface-subtle"
    // TODO: assert element classList contains "text-text-primary"
  });

  it('test_solid_final_badge_unchanged', () => {
    // TODO: render <Badge variant="final" label="Final" data-testid="b" />
    // TODO: assert element classList contains "bg-state-active"
    // TODO: assert element classList contains "text-white"
  });

  it('test_solid_edited_badge_unchanged', () => {
    // TODO: render <Badge variant="edited" label="Edited" data-testid="b" />
    // TODO: assert element classList contains "bg-state-info"
    // TODO: assert element classList contains "text-white"
  });

  it('test_solid_stale_badge_unchanged', () => {
    // TODO: render <Badge variant="stale" label="Outdated" data-testid="b" />
    // TODO: assert element classList contains "bg-state-warning"
    // TODO: assert element classList contains "text-white"
  });

});

// ---------------------------------------------------------------------------
// StatusBadge solid contract unchanged (no soft prop passed)
// ---------------------------------------------------------------------------
describe('StatusBadge regression — existing solid behaviour unchanged', () => {

  it('test_statusbadge_complete_renders_solid_without_soft_prop', () => {
    // RT-001 guard: existing StatusBadge callers that do not pass soft must be unaffected
    // TODO: render <StatusBadge status="complete" data-testid="sb" />
    // TODO: assert element classList contains "bg-state-active" (solid green)
    // TODO: assert element text is "Complete"
  });

  it('test_statusbadge_failed_renders_solid_without_soft_prop', () => {
    // TODO: render <StatusBadge status="failed" data-testid="sb" />
    // TODO: assert element classList contains "bg-state-error"
    // TODO: assert element text is "Failed"
  });

  it('test_statusbadge_processing_renders_solid_without_soft_prop', () => {
    // TODO: render <StatusBadge status="processing" data-testid="sb" />
    // TODO: assert element classList contains "bg-state-info"
    // TODO: assert element text is "Processing"
  });

});

// ---------------------------------------------------------------------------
// Sibling components unaffected — ModuleCard (RT-002)
// ---------------------------------------------------------------------------
describe('ModuleCard regression — unmodified sibling unaffected', () => {

  it('test_unmodified_modulecard_renders_badge_with_solid_style', () => {
    // RT-002 guard: ModuleCard is NOT in scope for this spec; its Badge output
    // must remain identical after Badge.tsx and StatusBadge.tsx are modified.
    // TODO: render <ModuleCard module="vpr" title="VPR" subtitle="…" state="complete" />
    // TODO: query status badge element via data-testid="status-badge"
    // TODO: assert element classList contains "bg-state-active" (solid, not soft)
    // TODO: assert element does NOT contain "bg-green-50"
  });

  it('test_unmodified_modulecard_processing_badge_unchanged', () => {
    // TODO: render <ModuleCard module="vpr" title="VPR" subtitle="…" state="processing" />
    // TODO: assert status badge classList contains "bg-state-info"
  });

  it('test_unmodified_modulecard_failed_badge_unchanged', () => {
    // TODO: render <ModuleCard module="vpr" title="VPR" subtitle="…" state="failed" />
    // TODO: assert status badge classList contains "bg-state-error"
  });

});
