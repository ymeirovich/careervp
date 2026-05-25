// spec_id: FE-UI-001  component: Badge  file: src/frontend/components/ui/Badge.tsx
import { render } from '@testing-library/react';
import { describe, it, expect, beforeEach } from 'vitest';
import { Badge } from '../../../src/frontend/components/ui/Badge';
import { StatusBadge } from '../../../src/frontend/components/ui/StatusBadge';
import type { BadgeProps } from '../../../src/frontend/components/ui/Badge';

// ---------------------------------------------------------------------------
// helpers
// ---------------------------------------------------------------------------
function renderBadge(props: BadgeProps) {
  const { container } = render(<Badge {...props} />);
  // Badge renders a single <span> as the root element
  return container.firstElementChild as HTMLElement;
}

// ---------------------------------------------------------------------------
// default (solid) state — backward-compatibility
// ---------------------------------------------------------------------------
describe('Badge — default / solid state', () => {
  beforeEach(() => {
    // no mocks needed for a pure UI primitive
  });

  it('test_renders_label_when_label_prop_provided', () => {
    // TODO: render Badge with variant="success" and label="Done"
    // TODO: assert element text content equals "Done"
  });

  it('test_renders_children_when_label_prop_omitted', () => {
    // TODO: render Badge with variant="success" and children="Active"
    // TODO: assert element text content equals "Active"
  });

  it('test_applies_solid_success_classes_when_soft_omitted', () => {
    // AC-008: soft omitted → solid style unchanged
    // TODO: render Badge with variant="success" (no soft prop)
    // TODO: assert element classList contains "bg-state-active"
    // TODO: assert element classList contains "text-white"
    // TODO: assert element classList does NOT contain "bg-green-50"
  });

  it('test_applies_solid_success_classes_when_soft_false', () => {
    // AC-009: soft={false} → same as omitting soft
    // TODO: render Badge with variant="success" soft={false}
    // TODO: assert element classList contains "bg-state-active"
    // TODO: assert element classList contains "text-white"
    // TODO: assert element classList does NOT contain "bg-green-50"
  });
});

// ---------------------------------------------------------------------------
// soft — success variant (AC-001)
// ---------------------------------------------------------------------------
describe('Badge — soft success state', () => {
  it('test_applies_green_tinted_background_when_soft_success', () => {
    // AC-001
    // TODO: render Badge with variant="success" soft={true}
    // TODO: assert element classList contains "bg-green-50"
  });

  it('test_applies_green_text_when_soft_success', () => {
    // AC-001
    // TODO: render Badge with variant="success" soft={true}
    // TODO: assert element classList contains "text-green-700"
  });

  it('test_applies_green_border_when_soft_success', () => {
    // AC-001
    // TODO: render Badge with variant="success" soft={true}
    // TODO: assert element classList contains "border-green-200"
  });

  it('test_does_not_apply_solid_classes_when_soft_success', () => {
    // AC-001 — solid classes must be absent
    // TODO: render Badge with variant="success" soft={true}
    // TODO: assert element classList does NOT contain "bg-state-active"
    // TODO: assert element classList does NOT contain "text-white"
  });
});

// ---------------------------------------------------------------------------
// soft — info variant (AC-002)
// ---------------------------------------------------------------------------
describe('Badge — soft info state', () => {
  it('test_applies_blue_tinted_background_when_soft_info', () => {
    // AC-002
    // TODO: render Badge with variant="info" soft={true}
    // TODO: assert element classList contains "bg-blue-50"
  });

  it('test_applies_blue_text_when_soft_info', () => {
    // AC-002
    // TODO: render Badge with variant="info" soft={true}
    // TODO: assert element classList contains "text-blue-700"
  });

  it('test_applies_blue_border_when_soft_info', () => {
    // AC-002
    // TODO: render Badge with variant="info" soft={true}
    // TODO: assert element classList contains "border-blue-200"
  });
});

// ---------------------------------------------------------------------------
// soft — error variant (AC-003) — solid retained even when soft={true}
// ---------------------------------------------------------------------------
describe('Badge — soft error state (no soft override)', () => {
  it('test_retains_solid_error_background_when_soft_error', () => {
    // AC-003: error variant must NOT adopt soft tinting
    // TODO: render Badge with variant="error" soft={true}
    // TODO: assert element classList contains "bg-state-error"
  });

  it('test_retains_white_text_when_soft_error', () => {
    // AC-003
    // TODO: render Badge with variant="error" soft={true}
    // TODO: assert element classList contains "text-white"
  });

  it('test_does_not_apply_soft_classes_to_error_variant', () => {
    // AC-003 — no tinted classes must appear
    // TODO: render Badge with variant="error" soft={true}
    // TODO: assert element classList does NOT contain "bg-red-50" (or any tinted bg)
    // TODO: assert element classList does NOT contain "text-red-700"
  });
});

// ---------------------------------------------------------------------------
// soft — final variant (AC-004) — same green classes as success
// ---------------------------------------------------------------------------
describe('Badge — soft final state', () => {
  it('test_applies_green_tinted_background_when_soft_final', () => {
    // AC-004
    // TODO: render Badge with variant="final" soft={true}
    // TODO: assert element classList contains "bg-green-50"
  });

  it('test_applies_green_text_when_soft_final', () => {
    // AC-004
    // TODO: render Badge with variant="final" soft={true}
    // TODO: assert element classList contains "text-green-700"
  });

  it('test_applies_green_border_when_soft_final', () => {
    // AC-004
    // TODO: render Badge with variant="final" soft={true}
    // TODO: assert element classList contains "border-green-200"
  });
});

// ---------------------------------------------------------------------------
// soft — edited variant (AC-005) — same green classes as success
// ---------------------------------------------------------------------------
describe('Badge — soft edited state', () => {
  it('test_applies_green_tinted_background_when_soft_edited', () => {
    // AC-005
    // TODO: render Badge with variant="edited" soft={true}
    // TODO: assert element classList contains "bg-green-50"
  });

  it('test_applies_green_text_when_soft_edited', () => {
    // AC-005
    // TODO: render Badge with variant="edited" soft={true}
    // TODO: assert element classList contains "text-green-700"
  });

  it('test_applies_green_border_when_soft_edited', () => {
    // AC-005
    // TODO: render Badge with variant="edited" soft={true}
    // TODO: assert element classList contains "border-green-200"
  });
});

// ---------------------------------------------------------------------------
// soft — neutral variant (AC-006)
// ---------------------------------------------------------------------------
describe('Badge — soft neutral state', () => {
  it('test_applies_gray_tinted_background_when_soft_neutral', () => {
    // AC-006
    // TODO: render Badge with variant="neutral" soft={true}
    // TODO: assert element classList contains "bg-gray-50"
  });

  it('test_applies_gray_text_when_soft_neutral', () => {
    // AC-006
    // TODO: render Badge with variant="neutral" soft={true}
    // TODO: assert element classList contains "text-gray-700"
  });

  it('test_applies_gray_border_when_soft_neutral', () => {
    // AC-006
    // TODO: render Badge with variant="neutral" soft={true}
    // TODO: assert element classList contains "border-gray-200"
  });
});

// ---------------------------------------------------------------------------
// soft — warning variant (AC-007)
// ---------------------------------------------------------------------------
describe('Badge — soft warning state', () => {
  it('test_applies_amber_tinted_background_when_soft_warning', () => {
    // AC-007
    // TODO: render Badge with variant="warning" soft={true}
    // TODO: assert element classList contains "bg-amber-50"
  });

  it('test_applies_amber_text_when_soft_warning', () => {
    // AC-007
    // TODO: render Badge with variant="warning" soft={true}
    // TODO: assert element classList contains "text-amber-700"
  });

  it('test_applies_amber_border_when_soft_warning', () => {
    // AC-007
    // TODO: render Badge with variant="warning" soft={true}
    // TODO: assert element classList contains "border-amber-200"
  });
});

// ---------------------------------------------------------------------------
// soft — stale variant (AC-011) — same amber classes as warning
// ---------------------------------------------------------------------------
describe('Badge — soft stale state', () => {
  it('test_applies_amber_tinted_background_when_soft_stale', () => {
    // AC-011
    // TODO: render Badge with variant="stale" soft={true}
    // TODO: assert element classList contains "bg-amber-50"
  });

  it('test_applies_amber_text_when_soft_stale', () => {
    // AC-011
    // TODO: render Badge with variant="stale" soft={true}
    // TODO: assert element classList contains "text-amber-700"
  });

  it('test_applies_amber_border_when_soft_stale', () => {
    // AC-011
    // TODO: render Badge with variant="stale" soft={true}
    // TODO: assert element classList contains "border-amber-200"
  });
});

// ---------------------------------------------------------------------------
// StatusBadge — soft prop forwarding (AC-010)
// ---------------------------------------------------------------------------
describe('StatusBadge — soft prop forwarding', () => {
  it('test_forwards_soft_true_to_inner_badge_when_status_complete', () => {
    // AC-010: StatusBadge soft={true} → inner Badge receives soft={true}
    // TODO: render StatusBadge with status="complete" soft={true} data-testid="sb"
    // TODO: query the rendered span by testId "sb"
    // TODO: assert element classList contains "bg-green-50" (green-tinted, not solid)
  });

  it('test_renders_solid_when_soft_omitted_on_statusbadge', () => {
    // AC-010 inverse: omitting soft on StatusBadge must not enable soft on Badge
    // TODO: render StatusBadge with status="complete" (no soft prop)
    // TODO: assert element classList contains "bg-state-active" (solid)
    // TODO: assert element classList does NOT contain "bg-green-50"
  });
});

// ---------------------------------------------------------------------------
// TypeScript prop type (AC-012) — compile-time assertion
// ---------------------------------------------------------------------------
describe('Badge — TypeScript prop contract', () => {
  it('test_soft_prop_type_is_optional_boolean', () => {
    // AC-012: soft is boolean | undefined — verified at compile time below.
    // If this file compiles without error, the type contract is satisfied.

    // TODO: declare a variable typed as Pick<BadgeProps, 'soft'>
    // TODO: assign { soft: true }, { soft: false }, and {} — all must compile
    // TODO: assert that soft: 'yes' causes a TS error (leave as comment, do not ship)
    // Runtime assertion placeholder:
    const withSoftTrue: BadgeProps = { variant: 'success', soft: true };
    const withSoftFalse: BadgeProps = { variant: 'success', soft: false };
    const withSoftOmitted: BadgeProps = { variant: 'success' };
    // TODO: assert all three render without throwing
    expect(withSoftTrue).toBeDefined();
    expect(withSoftFalse).toBeDefined();
    expect(withSoftOmitted).toBeDefined();
  });
});
