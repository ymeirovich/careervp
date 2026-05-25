// spec_id: FE-UI-017  component: BaseCVsTable  tier: unit
// file: src/frontend/components/BaseCVsTable/BaseCVsTable.tsx
// Framework: Vitest + @testing-library/react
// All 31 ACs are verification_type: unit — each AC has a dedicated test below.

import { render, screen, fireEvent, within } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BaseCVsTable } from '../../../src/frontend/components/BaseCVsTable/BaseCVsTable';

// ---------------------------------------------------------------------------
// Shared fixtures
// ---------------------------------------------------------------------------

interface BaseCvFixture {
  id: string;
  full_name: string;
  language: string;
  created_at: string;
  updated_at: string;
  status?: 'ready' | 'processing' | 'failed';
  used_in?: number;
}

const FIXTURE_BASE_CVS: BaseCvFixture[] = [
  {
    id: 'cv-1',
    full_name: 'John Doe',
    language: 'English',
    created_at: '2026-05-20T10:00:00Z',
    updated_at: '2026-05-20T10:00:00Z',
    status: 'ready',
    used_in: 3,
  },
  {
    id: 'cv-2',
    full_name: 'Jane Smith',
    language: 'Hebrew',
    created_at: '2026-05-15T09:00:00Z',
    updated_at: '2026-05-15T09:00:00Z',
    status: 'processing',
    used_in: 1,
  },
  {
    id: 'cv-3',
    full_name: 'Bob Brown',
    language: 'English',
    created_at: '2026-05-10T08:00:00Z',
    updated_at: '2026-05-10T08:00:00Z',
    status: 'failed',
    used_in: 0,
  },
];

const EMPTY_BASE_CVS: BaseCvFixture[] = [];

const DEFAULT_PROPS = {
  cvs: FIXTURE_BASE_CVS,
  isLoading: false,
  error: null as Error | null,
  onRetry: vi.fn(),
  onSetDefault: vi.fn(),
  onDelete: vi.fn(),
  onUploadNew: vi.fn(),
};

beforeEach(() => {
  vi.clearAllMocks();
});

// ===========================================================================
// BaseCVsTable
// ===========================================================================

describe('BaseCVsTable', () => {

  // ─── default state ────────────────────────────────────────────────────────

  describe('default state', () => {
    it('test_renders_without_crash_when_given_populated_array', () => {
      // TODO: render <BaseCVsTable {...DEFAULT_PROPS} />
      // TODO: assert screen.getByRole('table') is in the document
    });
  });

  // ─── AC-001 — semantic <table> markup ────────────────────────────────────

  describe('table structure — semantic markup (AC-001)', () => {
    it('test_renders_semantic_table_element_when_data_present', () => {
      // TODO: render <BaseCVsTable {...DEFAULT_PROPS} />
      // TODO: assert screen.getByRole('table') is in the document
    });

    it('test_renders_thead_with_th_scope_col_and_tbody_when_data_present', () => {
      // TODO: render <BaseCVsTable {...DEFAULT_PROPS} />
      // TODO: assert document.querySelector('thead') is not null
      // TODO: assert document.querySelector('tbody') is not null
      // TODO: assert all <th> elements have scope="col"
    });

    it('test_uses_tr_and_td_elements_in_tbody_when_data_present', () => {
      // TODO: render <BaseCVsTable {...DEFAULT_PROPS} />
      // TODO: assert tbody contains <tr> elements equal to FIXTURE_BASE_CVS.length
      // TODO: assert each row contains <td> elements
    });
  });

  // ─── AC-002 — 7 columns in order ─────────────────────────────────────────

  describe('column headers (AC-002)', () => {
    it('test_renders_seven_column_headers_when_data_present', () => {
      // TODO: render <BaseCVsTable {...DEFAULT_PROPS} />
      // TODO: assert screen.getAllByRole('columnheader').length === 7
    });

    it('test_column_headers_in_order_when_data_present', () => {
      // TODO: render <BaseCVsTable {...DEFAULT_PROPS} />
      // TODO: get all columnheader elements
      // TODO: assert headers[0] contains /file name/i
      // TODO: assert headers[1] contains /upload date/i
      // TODO: assert headers[2] contains /language/i
      // TODO: assert headers[3] contains /last updated/i
      // TODO: assert headers[4] contains /status/i
      // TODO: assert headers[5] contains /used in/i
      // TODO: assert headers[6] contains /actions/i
    });
  });

  // ─── AC-003 — zebra striping ──────────────────────────────────────────────

  describe('zebra striping (AC-003)', () => {
    it('test_odd_rows_have_bg_white_class_when_rendered', () => {
      // TODO: render <BaseCVsTable {...DEFAULT_PROPS} />
      // TODO: get all data rows (tbody tr elements)
      // TODO: assert rows[0] has class containing 'bg-white'
      // TODO: assert rows[2] has class containing 'bg-white'
    });

    it('test_even_rows_have_bg_surface_subtle_class_when_rendered', () => {
      // TODO: render <BaseCVsTable {...DEFAULT_PROPS} />
      // TODO: get all data rows
      // TODO: assert rows[1] has class containing 'bg-surface-subtle'
    });
  });

  // ─── AC-004 — File Name column data mapping ───────────────────────────────

  describe('data mapping — File Name column (AC-004)', () => {
    it('test_file_name_column_displays_full_name_field_when_rendered', () => {
      // TODO: render <BaseCVsTable {...DEFAULT_PROPS} />
      // TODO: assert screen.getByText('John Doe') is in the document
    });
  });

  // ─── AC-005 — Upload Date column locale-aware date ────────────────────────

  describe('data mapping — Upload Date column (AC-005)', () => {
    it('test_upload_date_column_displays_locale_formatted_date_when_rendered', () => {
      // TODO: render <BaseCVsTable {...DEFAULT_PROPS} />
      // TODO: assert the rendered upload date text is NOT the raw ISO string '2026-05-20T10:00:00Z'
      // TODO: assert the date was formatted (check for locale-aware separators)
    });
  });

  // ─── AC-006 — Language column data mapping ────────────────────────────────

  describe('data mapping — Language column (AC-006)', () => {
    it('test_language_column_displays_language_field_when_rendered', () => {
      // TODO: render <BaseCVsTable {...DEFAULT_PROPS} />
      // TODO: assert screen.getAllByText('English').length >= 1
    });
  });

  // ─── AC-007 — Last Updated uses Intl.DateTimeFormat ──────────────────────

  describe('data mapping — Last Updated column (AC-007)', () => {
    it('test_last_updated_column_displays_locale_formatted_date_when_rendered', () => {
      // TODO: render <BaseCVsTable {...DEFAULT_PROPS} />
      // TODO: assert rendered last updated text is NOT the raw ISO string '2026-05-20T10:00:00Z'
    });

    it('test_last_updated_uses_intl_datetimeformat_not_raw_string', () => {
      // TODO: spy on Intl.DateTimeFormat constructor or its format method
      // TODO: render <BaseCVsTable {...DEFAULT_PROPS} />
      // TODO: assert spy was called at least once
    });
  });

  // ─── AC-008 — Status badge: ready / absent → success (green) ─────────────

  describe('status badges (AC-008 – AC-010)', () => {
    it('test_ready_status_renders_badge_with_success_variant_when_status_is_ready', () => {
      // TODO: render <BaseCVsTable cvs={[FIXTURE_BASE_CVS[0]]} {...DEFAULT_PROPS} cvs={[FIXTURE_BASE_CVS[0]]} />
      // TODO: assert the Badge element has data-variant="success" or class matching success styling
    });

    it('test_absent_status_renders_badge_with_success_variant_as_default', () => {
      // TODO: build a fixture with no status field
      // TODO: render <BaseCVsTable cvs={[{ id: 'cv-x', full_name: 'No Status', language: 'English', created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z' }]} isLoading={false} error={null} onRetry={vi.fn()} onSetDefault={vi.fn()} onDelete={vi.fn()} onUploadNew={vi.fn()} />
      // TODO: assert the Badge element has data-variant="success" or label "Ready"
    });

    it('test_processing_status_renders_badge_with_info_variant_when_status_is_processing', () => {
      // TODO: render with only the processing fixture row (FIXTURE_BASE_CVS[1])
      // TODO: assert Badge has data-variant="info" or class matching info/blue styling
    });

    it('test_failed_status_renders_badge_with_destructive_variant_when_status_is_failed', () => {
      // TODO: render with only the failed fixture row (FIXTURE_BASE_CVS[2])
      // TODO: assert Badge has data-variant="destructive" or class matching destructive/red styling
    });
  });

  // ─── AC-011 — Actions column: View is bold ────────────────────────────────

  describe('actions column — View element (AC-011)', () => {
    it('test_view_action_element_is_bold_when_rendered', () => {
      // TODO: render <BaseCVsTable {...DEFAULT_PROPS} />
      // TODO: get View element(s) — e.g. screen.getAllByText(/view/i)[0]
      // TODO: assert the element has font-weight bold (class or inline style)
    });
  });

  // ─── AC-012 — Actions column: Set as Default present ─────────────────────

  describe('actions column — Set as Default element (AC-012)', () => {
    it('test_set_as_default_action_present_in_every_row_when_rendered', () => {
      // TODO: render <BaseCVsTable {...DEFAULT_PROPS} />
      // TODO: assert screen.getAllByText(/set as default/i).length === FIXTURE_BASE_CVS.length
    });
  });

  // ─── AC-013 — Actions column: Delete present ─────────────────────────────

  describe('actions column — Delete element (AC-013)', () => {
    it('test_delete_action_present_in_every_row_when_rendered', () => {
      // TODO: render <BaseCVsTable {...DEFAULT_PROPS} />
      // TODO: assert screen.getAllByText(/delete/i).length === FIXTURE_BASE_CVS.length
    });
  });

  // ─── AC-014 — Default sort: Last Updated descending ──────────────────────

  describe('sorting — default order (AC-014)', () => {
    it('test_rows_sorted_by_last_updated_descending_when_no_user_sort_action', () => {
      // TODO: render <BaseCVsTable {...DEFAULT_PROPS} />
      // TODO: get all data rows
      // TODO: assert first row corresponds to cv-1 (most recent updated_at: 2026-05-20)
      // TODO: assert last row corresponds to cv-3 (oldest updated_at: 2026-05-10)
    });
  });

  // ─── AC-015 — Click unsorted column → ascending + indicator ──────────────

  describe('sorting — user interaction (AC-015, AC-016, AC-017)', () => {
    it('test_clicking_unsorted_column_header_sorts_ascending_when_column_was_unsorted', () => {
      // TODO: render <BaseCVsTable {...DEFAULT_PROPS} />
      // TODO: fireEvent.click on the File Name column header
      // TODO: get all data rows and assert they are in ascending alphabetical order by full_name
    });

    it('test_ascending_sort_indicator_shown_on_th_when_column_sorted_ascending', () => {
      // TODO: render and click File Name header
      // TODO: assert the File Name <th> has aria-sort="ascending" or a visual ascending indicator
    });

    it('test_clicking_same_column_header_twice_toggles_to_descending_when_was_ascending', () => {
      // TODO: render <BaseCVsTable {...DEFAULT_PROPS} />
      // TODO: click File Name header once (ascending)
      // TODO: click File Name header again (descending)
      // TODO: assert rows are in descending order by full_name
    });

    it('test_clicking_different_column_clears_previous_sort_indicator_when_another_column_active', () => {
      // TODO: render <BaseCVsTable {...DEFAULT_PROPS} />
      // TODO: click File Name header (active)
      // TODO: click Language header
      // TODO: assert File Name <th> aria-sort is "none" or indicator is absent
      // TODO: assert Language <th> has aria-sort="ascending"
    });

    it('test_new_column_sorts_ascending_when_switching_from_another_sorted_column', () => {
      // TODO: render <BaseCVsTable {...DEFAULT_PROPS} />
      // TODO: click File Name header, then click Language header
      // TODO: assert rows are in ascending order by language
    });
  });

  // ─── AC-018, AC-019 — Hover states ───────────────────────────────────────

  describe('hover state (AC-018, AC-019)', () => {
    it('test_row_has_hover_highlight_class_when_rendered', () => {
      // TODO: render <BaseCVsTable {...DEFAULT_PROPS} />
      // NOTE: CSS :hover pseudo-classes are not triggerable in jsdom
      // TODO: assert first data row has a hover utility class (e.g. 'hover:bg-surface-muted')
    });

    it('test_view_text_has_hover_underline_class_when_rendered', () => {
      // TODO: render <BaseCVsTable {...DEFAULT_PROPS} />
      // NOTE: CSS :hover is not triggerable in jsdom — assert class declaration
      // TODO: assert View element has class like 'hover:underline'
    });
  });

  // ─── AC-020 — View click → navigates to /cv-center/[cvId] ────────────────

  describe('navigation (AC-020)', () => {
    it('test_view_link_href_points_to_cv_center_cvid_route_when_rendered', () => {
      // TODO: render <BaseCVsTable {...DEFAULT_PROPS} />
      // TODO: get all View links
      // TODO: assert first link href === '/cv-center/cv-1'
    });

    it('test_each_view_link_href_contains_correct_cv_id_when_multiple_rows', () => {
      // TODO: render <BaseCVsTable {...DEFAULT_PROPS} />
      // TODO: assert View link for cv-2 has href '/cv-center/cv-2'
    });
  });

  // ─── AC-021 — Set as Default calls onSetDefault ───────────────────────────

  describe('actions — Set as Default callback (AC-021)', () => {
    it('test_clicking_set_as_default_calls_on_set_default_with_cv_id_when_clicked', () => {
      // TODO: render <BaseCVsTable {...DEFAULT_PROPS} />
      // TODO: fireEvent.click on first "Set as Default" button
      // TODO: expect(DEFAULT_PROPS.onSetDefault).toHaveBeenCalledWith('cv-1')
    });

    it('test_on_set_default_called_once_per_click_not_multiple_times', () => {
      // TODO: render <BaseCVsTable {...DEFAULT_PROPS} />
      // TODO: fireEvent.click on "Set as Default" for cv-2
      // TODO: expect(DEFAULT_PROPS.onSetDefault).toHaveBeenCalledOnce()
      // TODO: expect(DEFAULT_PROPS.onSetDefault).toHaveBeenCalledWith('cv-2')
    });
  });

  // ─── AC-022 — Delete calls onDelete ──────────────────────────────────────

  describe('actions — Delete callback (AC-022)', () => {
    it('test_clicking_delete_calls_on_delete_with_cv_id_when_clicked', () => {
      // TODO: render <BaseCVsTable {...DEFAULT_PROPS} />
      // TODO: fireEvent.click on first "Delete" button
      // TODO: expect(DEFAULT_PROPS.onDelete).toHaveBeenCalledWith('cv-1')
    });

    it('test_on_delete_called_once_per_click_not_multiple_times', () => {
      // TODO: render <BaseCVsTable {...DEFAULT_PROPS} />
      // TODO: fireEvent.click on "Delete" for cv-2
      // TODO: expect(DEFAULT_PROPS.onDelete).toHaveBeenCalledOnce()
      // TODO: expect(DEFAULT_PROPS.onDelete).toHaveBeenCalledWith('cv-2')
    });
  });

  // ─── AC-023 — Loading state ───────────────────────────────────────────────

  describe('loading state (AC-023)', () => {
    it('test_shows_three_skeleton_rows_when_is_loading_true', () => {
      // TODO: render <BaseCVsTable {...DEFAULT_PROPS} isLoading={true} cvs={[]} />
      // TODO: assert 3 skeleton row elements are present (e.g. data-testid="skeleton-row")
      // TODO: assert no real data rows are rendered
    });

    it('test_skeleton_rows_have_shimmer_animation_class_when_loading', () => {
      // TODO: render with isLoading=true
      // TODO: assert skeleton rows have 'animate-pulse' or equivalent shimmer class
    });

    it('test_real_data_rows_absent_when_is_loading_true', () => {
      // TODO: render with isLoading=true and populated cvs
      // TODO: assert no data cell with 'John Doe' is present
    });
  });

  // ─── AC-024 — Error state ─────────────────────────────────────────────────

  describe('error state (AC-024)', () => {
    it('test_shows_inline_error_message_when_error_prop_is_truthy', () => {
      // TODO: render <BaseCVsTable {...DEFAULT_PROPS} error={new Error('Network error')} />
      // TODO: assert an error message element is visible
    });

    it('test_shows_retry_button_when_error_prop_is_truthy', () => {
      // TODO: render with error truthy
      // TODO: assert screen.getByRole('button', { name: /retry/i }) is visible
    });

    it('test_clicking_retry_button_calls_on_retry_when_error_state', () => {
      // TODO: render with error truthy and onRetry spy
      // TODO: fireEvent.click on the Retry button
      // TODO: expect(DEFAULT_PROPS.onRetry).toHaveBeenCalledOnce()
    });

    it('test_error_state_renders_inside_table_card_not_page_level', () => {
      // TODO: render with error truthy
      // TODO: assert error message is inside the table card container, not a full-page takeover
    });
  });

  // ─── AC-025 — Empty state ─────────────────────────────────────────────────

  describe('empty state (AC-025)', () => {
    it('test_table_headers_visible_when_cvs_array_is_empty', () => {
      // TODO: render <BaseCVsTable cvs={EMPTY_BASE_CVS} isLoading={false} error={null} onRetry={vi.fn()} onSetDefault={vi.fn()} onDelete={vi.fn()} onUploadNew={vi.fn()} />
      // TODO: assert 7 column headers still visible
    });

    it('test_empty_state_message_shown_when_cvs_array_is_empty', () => {
      // TODO: render with empty array
      // TODO: assert screen.getByText(/no primary cvs uploaded yet/i) is visible
    });

    it('test_upload_new_cv_cta_button_shown_when_cvs_array_is_empty', () => {
      // TODO: render with empty array
      // TODO: assert screen.getByRole('button', { name: /upload new cv/i }) is visible
      //       OR assert <a> element with text matching /upload new cv/i is present
    });
  });

  // ─── AC-026 — Empty state CTA calls onUploadNew ───────────────────────────

  describe('empty state — Upload New CV CTA (AC-026)', () => {
    it('test_clicking_upload_new_cv_cta_calls_on_upload_new_when_empty_state', () => {
      // TODO: render with empty array and onUploadNew spy
      // TODO: fireEvent.click on "+ Upload New CV" CTA
      // TODO: expect(DEFAULT_PROPS.onUploadNew).toHaveBeenCalledOnce()
    });
  });

  // ─── AC-027 — Responsive card layout ─────────────────────────────────────

  describe('responsive layout (AC-027)', () => {
    it('test_card_layout_responsive_class_applied_when_rendered', () => {
      // TODO: render <BaseCVsTable {...DEFAULT_PROPS} />
      // TODO: assert component root or table wrapper has a responsive card CSS class
      //       (e.g. 'md:hidden' or 'block md:table') indicating card layout < 768px
      // NOTE: viewport resize is not testable in jsdom; assert responsive utility classes
    });

    it('test_each_card_shows_all_seven_fields_stacked_when_in_card_layout', () => {
      // TODO: render <BaseCVsTable {...DEFAULT_PROPS} />
      // TODO: find card elements (e.g. data-testid="base-cv-card")
      // TODO: assert each card contains full_name, upload date, language, last updated, status, used in, and actions
    });
  });

  // ─── AC-028 — th scope="col" ─────────────────────────────────────────────

  describe('accessibility — th scope (AC-028)', () => {
    it('test_all_th_elements_have_scope_col_attribute_when_rendered', () => {
      // TODO: render <BaseCVsTable {...DEFAULT_PROPS} />
      // TODO: get all columnheader elements via screen.getAllByRole('columnheader')
      // TODO: assert each has getAttribute('scope') === 'col'
    });
  });

  // ─── AC-029 — Keyboard Enter/Space toggles sort ───────────────────────────

  describe('accessibility — keyboard navigation (AC-029)', () => {
    it('test_pressing_enter_on_focused_column_header_sorts_ascending', () => {
      // TODO: render <BaseCVsTable {...DEFAULT_PROPS} />
      // TODO: focus the File Name column header
      // TODO: fireEvent.keyDown with key='Enter'
      // TODO: assert rows are now sorted ascending by full_name
    });

    it('test_pressing_space_on_focused_column_header_sorts_ascending', () => {
      // TODO: render <BaseCVsTable {...DEFAULT_PROPS} />
      // TODO: focus the Language column header
      // TODO: fireEvent.keyDown with key=' ' (Space)
      // TODO: assert rows are sorted ascending by language
    });

    it('test_keyboard_sort_equivalent_to_click_sort_when_focused', () => {
      // TODO: render two instances — click one header, keyDown Enter on the same header in the other
      // TODO: assert both produce identical row ordering after one activation
    });
  });

  // ─── AC-030 — aria-sort on active column ──────────────────────────────────

  describe('accessibility — aria-sort (AC-030)', () => {
    it('test_active_sort_column_has_aria_sort_ascending_when_sorted_ascending', () => {
      // TODO: render <BaseCVsTable {...DEFAULT_PROPS} />
      // TODO: click File Name header
      // TODO: assert File Name <th> getAttribute('aria-sort') === 'ascending'
    });

    it('test_active_sort_column_has_aria_sort_descending_when_sorted_descending', () => {
      // TODO: render <BaseCVsTable {...DEFAULT_PROPS} />
      // TODO: click File Name header twice
      // TODO: assert File Name <th> getAttribute('aria-sort') === 'descending'
    });

    it('test_inactive_columns_do_not_have_aria_sort_set_when_another_column_active', () => {
      // TODO: render and click File Name header
      // TODO: assert Language <th> does NOT have aria-sort="ascending" or "descending"
    });
  });

  // ─── AC-031 — Hebrew i18n ─────────────────────────────────────────────────

  describe('i18n — Hebrew strings (AC-031)', () => {
    it('test_column_headers_render_in_hebrew_when_locale_is_he', () => {
      // TODO: render <BaseCVsTable {...DEFAULT_PROPS} locale="he" /> (or wrap in i18n provider with he locale)
      // TODO: assert column headers contain Hebrew translations for all 7 column names
      // TODO: assert English column header text is NOT present
    });

    it('test_view_action_renders_in_hebrew_when_locale_is_he', () => {
      // TODO: render with locale=he
      // TODO: assert View action text is the Hebrew translation
      // TODO: assert English "View" text is NOT present
    });

    it('test_set_as_default_action_renders_in_hebrew_when_locale_is_he', () => {
      // TODO: render with locale=he
      // TODO: assert "Set as Default" text is the Hebrew translation
    });

    it('test_delete_action_renders_in_hebrew_when_locale_is_he', () => {
      // TODO: render with locale=he
      // TODO: assert "Delete" text is the Hebrew translation
    });

    it('test_ready_badge_label_renders_in_hebrew_when_locale_is_he', () => {
      // TODO: render with locale=he and a 'ready' status row
      // TODO: assert badge text is the Hebrew translation for "Ready"
    });

    it('test_processing_badge_label_renders_in_hebrew_when_locale_is_he', () => {
      // TODO: render with locale=he and a 'processing' status row
      // TODO: assert badge text is the Hebrew translation for "Processing"
    });

    it('test_failed_badge_label_renders_in_hebrew_when_locale_is_he', () => {
      // TODO: render with locale=he and a 'failed' status row
      // TODO: assert badge text is the Hebrew translation for "Failed"
    });

    it('test_empty_state_text_renders_in_hebrew_when_locale_is_he', () => {
      // TODO: render with locale=he and empty cvs array
      // TODO: assert empty state message is in Hebrew
      // TODO: assert CTA button text is in Hebrew
    });

    it('test_error_message_and_retry_text_render_in_hebrew_when_locale_is_he', () => {
      // TODO: render with locale=he and error truthy
      // TODO: assert error message text is in Hebrew
      // TODO: assert Retry button text is in Hebrew
    });
  });

});
