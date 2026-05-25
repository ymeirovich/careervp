// spec_id: FE-UI-003  component: AppSidebar  file: src/frontend/components/layout/AppSidebar.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AppSidebar } from '../../../src/frontend/components/layout/AppSidebar';

// ---------------------------------------------------------------------------
// mock next/navigation — pathname injected per test
// ---------------------------------------------------------------------------
const mockUsePathname = vi.fn<[], string>();
vi.mock('next/navigation', () => ({
  usePathname: () => mockUsePathname(),
  useRouter: () => ({ push: vi.fn() }),
}));

// ---------------------------------------------------------------------------
// helpers
// ---------------------------------------------------------------------------
function renderSidebar() {
  return render(<AppSidebar />);
}

// ---------------------------------------------------------------------------
// AC-001 — exactly 7 nav items in correct order
// ---------------------------------------------------------------------------
describe('AppSidebar — nav item list (AC-001)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUsePathname.mockReturnValue('/dashboard');
  });

  it('test_renders_exactly_seven_nav_items_when_default', () => {
    // TODO: renderSidebar()
    // TODO: query all nav link elements (role="link" or nav <a> tags)
    // TODO: assert length === 7
  });

  it('test_nav_items_appear_in_correct_order_when_rendered', () => {
    // TODO: renderSidebar()
    // TODO: collect nav item labels in DOM order
    // TODO: assert order equals ['Dashboard', 'Applications', 'Base CVs', 'Tailored CVs', 'Cover Letters', 'Billing', 'Settings']
  });
});

// ---------------------------------------------------------------------------
// AC-002 — Base CVs item
// ---------------------------------------------------------------------------
describe('AppSidebar — Base CVs nav item (AC-002)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUsePathname.mockReturnValue('/dashboard');
  });

  it('test_base_cvs_href_is_cv_center_when_rendered', () => {
    // TODO: renderSidebar()
    // TODO: find element with text "Base CVs"
    // TODO: assert closest anchor href === '/cv-center'
  });

  it('test_base_cvs_icon_is_filetext_when_rendered', () => {
    // TODO: renderSidebar()
    // TODO: find the icon associated with "Base CVs" (svg with lucide-file-text or data-testid)
    // TODO: assert it renders the FileText lucide icon
  });
});

// ---------------------------------------------------------------------------
// AC-003 — Tailored CVs item
// ---------------------------------------------------------------------------
describe('AppSidebar — Tailored CVs nav item (AC-003)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUsePathname.mockReturnValue('/dashboard');
  });

  it('test_tailored_cvs_href_is_tailored_cvs_when_rendered', () => {
    // TODO: renderSidebar()
    // TODO: find element with text "Tailored CVs"
    // TODO: assert closest anchor href === '/tailored-cvs'
  });

  it('test_tailored_cvs_icon_is_filepen_when_rendered', () => {
    // TODO: renderSidebar()
    // TODO: find the icon associated with "Tailored CVs"
    // TODO: assert it renders the FilePen lucide icon
  });
});

// ---------------------------------------------------------------------------
// AC-004 — Cover Letters item
// ---------------------------------------------------------------------------
describe('AppSidebar — Cover Letters nav item (AC-004)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUsePathname.mockReturnValue('/dashboard');
  });

  it('test_cover_letters_href_is_cover_letters_when_rendered', () => {
    // TODO: renderSidebar()
    // TODO: find element with text "Cover Letters"
    // TODO: assert closest anchor href === '/cover-letters'
  });

  it('test_cover_letters_icon_is_mail_when_rendered', () => {
    // TODO: renderSidebar()
    // TODO: find the icon associated with "Cover Letters"
    // TODO: assert it renders the Mail lucide icon
  });
});

// ---------------------------------------------------------------------------
// AC-005 — active state when pathname matches /applications prefix
// ---------------------------------------------------------------------------
describe('AppSidebar — active state on /applications/[id] (AC-005)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUsePathname.mockReturnValue('/applications/123');
  });

  it('test_applications_item_has_orange_left_border_when_pathname_matches', () => {
    // TODO: renderSidebar()
    // TODO: find "Applications" nav item element
    // TODO: assert it has class containing 'border-primary-action' (or 'border-l')
  });

  it('test_applications_icon_has_orange_color_when_pathname_matches', () => {
    // TODO: renderSidebar()
    // TODO: find the icon inside "Applications" nav item
    // TODO: assert icon element has class 'text-primary-action'
  });
});

// ---------------------------------------------------------------------------
// AC-006 — active state when pathname is /cv-center
// ---------------------------------------------------------------------------
describe('AppSidebar — active state on /cv-center (AC-006)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUsePathname.mockReturnValue('/cv-center');
  });

  it('test_base_cvs_item_has_active_styling_when_pathname_is_cv_center', () => {
    // TODO: renderSidebar()
    // TODO: find "Base CVs" nav item element
    // TODO: assert it has 'border-primary-action' class
  });

  it('test_base_cvs_icon_has_orange_color_when_pathname_is_cv_center', () => {
    // TODO: renderSidebar()
    // TODO: find the icon inside "Base CVs" nav item
    // TODO: assert icon element has class 'text-primary-action'
  });
});

// ---------------------------------------------------------------------------
// AC-007 — active state when pathname is /tailored-cvs
// ---------------------------------------------------------------------------
describe('AppSidebar — active state on /tailored-cvs (AC-007)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUsePathname.mockReturnValue('/tailored-cvs');
  });

  it('test_tailored_cvs_item_has_active_styling_when_pathname_is_tailored_cvs', () => {
    // TODO: renderSidebar()
    // TODO: find "Tailored CVs" nav item element
    // TODO: assert it has 'border-primary-action' class
  });

  it('test_tailored_cvs_icon_has_orange_color_when_pathname_is_tailored_cvs', () => {
    // TODO: renderSidebar()
    // TODO: find icon inside "Tailored CVs" nav item
    // TODO: assert icon element has class 'text-primary-action'
  });
});

// ---------------------------------------------------------------------------
// AC-008 — active state when pathname is /cover-letters
// ---------------------------------------------------------------------------
describe('AppSidebar — active state on /cover-letters (AC-008)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUsePathname.mockReturnValue('/cover-letters');
  });

  it('test_cover_letters_item_has_active_styling_when_pathname_is_cover_letters', () => {
    // TODO: renderSidebar()
    // TODO: find "Cover Letters" nav item element
    // TODO: assert it has 'border-primary-action' class
  });

  it('test_cover_letters_icon_has_orange_color_when_pathname_is_cover_letters', () => {
    // TODO: renderSidebar()
    // TODO: find icon inside "Cover Letters" nav item
    // TODO: assert icon element has class 'text-primary-action'
  });
});

// ---------------------------------------------------------------------------
// AC-009 — exactly one active item at a time
// ---------------------------------------------------------------------------
describe('AppSidebar — single active item (AC-009)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUsePathname.mockReturnValue('/dashboard');
  });

  it('test_only_dashboard_has_active_styling_when_pathname_is_dashboard', () => {
    // TODO: renderSidebar()
    // TODO: collect all elements with 'border-primary-action' class
    // TODO: assert exactly 1 element has active styling
    // TODO: assert that element corresponds to the "Dashboard" nav item
  });

  it('test_six_items_have_inactive_styling_when_dashboard_active', () => {
    // TODO: renderSidebar()
    // TODO: collect all nav items without 'border-primary-action'
    // TODO: assert count equals 6
  });
});

// ---------------------------------------------------------------------------
// AC-013 — "CV Center" label must not exist
// ---------------------------------------------------------------------------
describe('AppSidebar — CV Center label removed (AC-013)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUsePathname.mockReturnValue('/dashboard');
  });

  it('test_cv_center_label_absent_when_sidebar_rendered', () => {
    // TODO: renderSidebar()
    // TODO: assert screen.queryByText('CV Center') === null
  });
});
