// spec_id: FE-UI-015  component: TailoredCVsListTable  tier: unit
// file: src/frontend/components/TailoredCVsListTable/TailoredCVsListTable.tsx
// Framework: Vitest + @testing-library/react
// All 28 ACs are verification_type: unit — each AC has a dedicated test below.

import { render, screen, fireEvent, within } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { TailoredCVsListTable } from '../../../src/frontend/components/TailoredCVsListTable/TailoredCVsListTable';

// ---------------------------------------------------------------------------
// Shared fixtures
// ---------------------------------------------------------------------------

interface TailoredCvFixture {
  id: string;
  applicationId: string;
  title: string;
  language: string;
  lastUpdated: string;
  status: 'ready' | 'processing' | 'failed' | 'edited';
}

const FIXTURE_TAILORED_CVS: TailoredCvFixture[] = [
  {
    id: 'cv-1',
    applicationId: 'app-1',
    title: 'Senior_Engineer_cv.pdf',
    language: 'English',
    lastUpdated: '2026-05-20T10:00:00Z',
    status: 'ready',
  },
  {
    id: 'cv-2',
    applicationId: 'app-2',
    title: 'Product_Manager_cv.pdf',
    language: 'Hebrew',
    lastUpdated: '2026-05-15T09:00:00Z',
    status: 'processing',
  },
  {
    id: 'cv-3',
    applicationId: 'app-3',
    title: 'Data_Analyst_cv.pdf',
    language: 'English',
    lastUpdated: '2026-05-10T08:00:00Z',
    status: 'failed',
  },
  {
    id: 'cv-4',
    applicationId: 'app-4',
    title: 'Designer_cv.pdf',
    language: 'English',
    lastUpdated: '2026-05-01T07:00:00Z',
    status: 'edited',
  },
];

const EMPTY_TAILORED_CVS: TailoredCvFixture[] = [];

const DEFAULT_PROPS = {
  tailoredCvs: FIXTURE_TAILORED_CVS,
  isLoading: false,
  error: null as Error | null,
  onRetry: vi.fn(),
};

beforeEach(() => {
  vi.clearAllMocks();
});

// ===========================================================================
// TailoredCVsListTable
// ===========================================================================

describe('TailoredCVsListTable', () => {

  // ─── default state ────────────────────────────────────────────────────────

  describe('default state', () => {
    it('test_renders_without_crash_when_given_populated_array', () => {
      // TODO: render <TailoredCVsListTable {...DEFAULT_PROPS} />
      // TODO: assert component mounts (e.g. screen.getByRole('table') is in document)
    });
  });

  // ─── AC-001 — semantic <table> markup ─────────────────────────────────────

  describe('table structure — semantic markup (AC-001)', () => {
    it('test_renders_semantic_table_element_when_data_present', () => {
      // TODO: render <TailoredCVsListTable {...DEFAULT_PROPS} />
      // TODO: assert screen.getByRole('table') is in the document
    });

    it('test_renders_thead_and_tbody_when_data_present', () => {
      // TODO: render <TailoredCVsListTable {...DEFAULT_PROPS} />
      // TODO: assert document.querySelector('thead') is not null
      // TODO: assert document.querySelector('tbody') is not null
    });

    it('test_uses_tr_and_td_elements_in_tbody_when_data_present', () => {
      // TODO: render <TailoredCVsListTable {...DEFAULT_PROPS} />
      // TODO: assert tbody contains <tr> elements equal to FIXTURE_TAILORED_CVS.length
      // TODO: assert each row contains <td> elements
    });
  });

  // ─── AC-002 — 5 columns in order ──────────────────────────────────────────

  describe('column headers (AC-002)', () => {
    it('test_renders_five_column_headers_when_data_present', () => {
      // TODO: render <TailoredCVsListTable {...DEFAULT_PROPS} />
      // TODO: assert screen.getAllByRole('columnheader').length === 5
    });

    it('test_column_headers_in_order_title_language_last_updated_status_action', () => {
      // TODO: render <TailoredCVsListTable {...DEFAULT_PROPS} />
      // TODO: get all columnheader elements
      // TODO: assert headers[0] contains /title/i
      // TODO: assert headers[1] contains /language/i
      // TODO: assert headers[2] contains /last updated/i
      // TODO: assert headers[3] contains /status/i
      // TODO: assert headers[4] contains /action/i
    });
  });

  // ─── AC-003 — zebra striping ───────────────────────────────────────────────

  describe('zebra striping (AC-003)', () => {
    it('test_odd_rows_have_bg_white_class_when_rendered', () => {
      // TODO: render <TailoredCVsListTable {...DEFAULT_PROPS} />
      // TODO: get all data rows (tbody tr elements)
      // TODO: assert rows[0] has class containing 'bg-white'
      // TODO: assert rows[2] has class containing 'bg-white'
    });

    it('test_even_rows_have_bg_surface_subtle_class_when_rendered', () => {
      // TODO: render <TailoredCVsListTable {...DEFAULT_PROPS} />
      // TODO: get all data rows
      // TODO: assert rows[1] has class containing 'bg-surface-subtle'
      // TODO: assert rows[3] has class containing 'bg-surface-subtle'
    });
  });

  // ─── AC-004 — Title column data mapping ───────────────────────────────────

  describe('data mapping — Title column (AC-004)', () => {
    it('test_title_column_displays_base_cv_filename_with_suffix_when_rendered', () => {
      // TODO: render <TailoredCVsListTable {...DEFAULT_PROPS} />
      // TODO: assert screen.getByText('Senior_Engineer_cv.pdf') is in the document
    });
  });

  // ─── AC-005 — Language column data mapping ────────────────────────────────

  describe('data mapping — Language column (AC-005)', () => {
    it('test_language_column_displays_language_from_base_cv_record_when_rendered', () => {
      // TODO: render <TailoredCVsListTable {...DEFAULT_PROPS} />
      // TODO: assert screen.getAllByText('English').length >= 1
    });
  });

  // ─── AC-006 — Last Updated locale-aware date ──────────────────────────────

  describe('data mapping — Last Updated column (AC-006)', () => {
    it('test_last_updated_column_displays_locale_formatted_date_when_rendered', () => {
      // TODO: render <TailoredCVsListTable {...DEFAULT_PROPS} />
      // TODO: assert the rendered date text is NOT the raw ISO string '2026-05-20T10:00:00Z'
      // TODO: assert the date was formatted via Intl.DateTimeFormat (check for locale-aware separators)
    });

    it('test_last_updated_uses_intl_datetimeformat_not_raw_string', () => {
      // TODO: spy on Intl.DateTimeFormat constructor or its format method
      // TODO: render <TailoredCVsListTable {...DEFAULT_PROPS} />
      // TODO: assert spy was called at least once
    });
  });

  // ─── AC-007 — Badge ready → success (green) ───────────────────────────────

  describe('status badges (AC-007 – AC-010)', () => {
    it('test_ready_status_renders_badge_with_success_variant_when_status_is_ready', () => {
      // TODO: render <TailoredCVsListTable tailoredCvs={[FIXTURE_TAILORED_CVS[0]]} isLoading={false} error={null} onRetry={vi.fn()} />
      // TODO: assert the Badge element has data-variant="success" or class matching success styling
    });

    it('test_processing_status_renders_badge_with_info_variant_when_status_is_processing', () => {
      // TODO: render with only the 'processing' fixture row
      // TODO: assert Badge has data-variant="info" or class matching info/blue styling
    });

    it('test_failed_status_renders_badge_with_destructive_variant_when_status_is_failed', () => {
      // TODO: render with only the 'failed' fixture row
      // TODO: assert Badge has data-variant="destructive" or class matching destructive/red styling
    });

    it('test_edited_status_renders_badge_with_info_variant_when_status_is_edited', () => {
      // TODO: render with only the 'edited' fixture row (FIXTURE_TAILORED_CVS[3])
      // TODO: assert Badge has data-variant="info" — same blue as processing
    });

    it('test_edited_and_processing_badges_share_same_color_token_when_both_present', () => {
      // TODO: render with both 'processing' and 'edited' rows
      // TODO: assert both badge elements share the same color class or data-variant="info"
    });
  });

  // ─── AC-011 — View is bold text, not ghost Button ─────────────────────────

  describe('View action element (AC-011)', () => {
    it('test_view_action_is_not_a_ghost_button_component_when_rendered', () => {
      // TODO: render <TailoredCVsListTable {...DEFAULT_PROPS} />
      // TODO: get View element(s) — e.g. screen.getAllByText(/view/i)[0]
      // TODO: assert the element is a link (<a>) or bold <span>/<strong>, NOT a <button>
    });

    it('test_view_action_element_is_bold_when_rendered', () => {
      // TODO: render <TailoredCVsListTable {...DEFAULT_PROPS} />
      // TODO: assert the View text element has font-weight bold (class or inline style)
    });
  });

  // ─── AC-012 — Default sort Last Updated descending ────────────────────────

  describe('sorting — default order (AC-012)', () => {
    it('test_rows_sorted_by_last_updated_descending_when_no_user_sort_action', () => {
      // TODO: render <TailoredCVsListTable {...DEFAULT_PROPS} />
      // TODO: get all data rows
      // TODO: assert first row corresponds to cv-1 (most recent: 2026-05-20)
      // TODO: assert last row corresponds to cv-4 (oldest: 2026-05-01)
    });
  });

  // ─── AC-013 — Click unsorted col → ascending + indicator ─────────────────

  describe('sorting — user interaction (AC-013, AC-014, AC-015)', () => {
    it('test_clicking_unsorted_column_header_sorts_ascending_when_column_was_unsorted', () => {
      // TODO: render <TailoredCVsListTable {...DEFAULT_PROPS} />
      // TODO: fireEvent.click on the Title column header
      // TODO: get all data rows and assert they are in ascending alphabetical order by title
    });

    it('test_ascending_sort_indicator_shown_on_th_when_column_sorted_ascending', () => {
      // TODO: render and click Title header
      // TODO: assert the Title <th> has an aria-sort="ascending" or a visual ascending icon
    });

    it('test_clicking_same_column_header_twice_toggles_to_descending_when_was_ascending', () => {
      // TODO: render <TailoredCVsListTable {...DEFAULT_PROPS} />
      // TODO: click Title header once (ascending)
      // TODO: click Title header again (descending)
      // TODO: assert rows are in descending order by title
    });

    it('test_clicking_different_column_clears_previous_sort_indicator_when_another_column_active', () => {
      // TODO: render <TailoredCVsListTable {...DEFAULT_PROPS} />
      // TODO: click Title header (active)
      // TODO: click Language header
      // TODO: assert Title <th> aria-sort is "none" or indicator is absent
      // TODO: assert Language <th> has aria-sort="ascending"
    });

    it('test_new_column_sorts_ascending_when_switching_from_another_sorted_column', () => {
      // TODO: render <TailoredCVsListTable {...DEFAULT_PROPS} />
      // TODO: click Title header, then click Language header
      // TODO: assert rows are in ascending order by language
    });
  });

  // ─── AC-016 — Search filters Title and Language ───────────────────────────

  describe('search (AC-016, AC-017)', () => {
    it('test_search_filters_rows_by_title_case_insensitive_when_term_entered', () => {
      // TODO: render <TailoredCVsListTable {...DEFAULT_PROPS} />
      // TODO: fireEvent.change on search input with value 'senior'
      // TODO: assert only one row visible with title 'Senior_Engineer_cv.pdf'
    });

    it('test_search_filters_rows_by_language_case_insensitive_when_term_entered', () => {
      // TODO: render <TailoredCVsListTable {...DEFAULT_PROPS} />
      // TODO: fireEvent.change on search input with value 'hebrew'
      // TODO: assert only the Hebrew-language row is visible
    });

    it('test_search_filters_across_both_title_and_language_simultaneously', () => {
      // TODO: render <TailoredCVsListTable {...DEFAULT_PROPS} />
      // TODO: enter a search term that matches both a title and a language
      // TODO: assert all matching rows are shown, not just title or just language matches
    });

    it('test_no_match_search_renders_no_matching_tailored_cvs_message_when_zero_results', () => {
      // TODO: render <TailoredCVsListTable {...DEFAULT_PROPS} />
      // TODO: fireEvent.change on search input with value 'xyzzy-no-match'
      // TODO: assert screen.getByText(/no matching tailored cvs/i) is visible
    });

    it('test_no_match_search_does_not_show_primary_empty_state_when_query_yields_zero', () => {
      // TODO: render <TailoredCVsListTable {...DEFAULT_PROPS} />
      // TODO: enter a non-matching search term
      // TODO: assert screen.queryByText(/no tailored cvs yet/i) is NOT in the document
    });
  });

  // ─── AC-018, AC-019 — Hover states ────────────────────────────────────────

  describe('hover state (AC-018, AC-019)', () => {
    it('test_row_background_changes_to_highlight_when_hovered', () => {
      // TODO: render <TailoredCVsListTable {...DEFAULT_PROPS} />
      // TODO: fireEvent.mouseEnter on first data row
      // TODO: assert row has a hover highlight class (e.g. 'hover:bg-surface-muted' or data-hovered)
      // NOTE: CSS :hover pseudo-classes are not testable via fireEvent in jsdom;
      //       assert presence of hover utility class on the element instead
    });

    it('test_view_text_gains_underline_class_when_row_hovered', () => {
      // TODO: render <TailoredCVsListTable {...DEFAULT_PROPS} />
      // TODO: assert the View element has a class like 'hover:underline' applied
      // NOTE: CSS :hover is not triggerable in jsdom — assert class declaration, not computed style
    });
  });

  // ─── AC-020 — View click → navigation ────────────────────────────────────

  describe('navigation (AC-020)', () => {
    it('test_view_link_href_points_to_application_cv_tailored_route_when_rendered', () => {
      // TODO: render <TailoredCVsListTable {...DEFAULT_PROPS} />
      // TODO: get all View links
      // TODO: assert first link href === '/applications/app-1/cv-tailored'
    });

    it('test_each_view_link_href_contains_correct_applicationId_when_multiple_rows', () => {
      // TODO: render <TailoredCVsListTable {...DEFAULT_PROPS} />
      // TODO: assert View link for cv-2 has href '/applications/app-2/cv-tailored'
    });
  });

  // ─── AC-021 — Loading state ────────────────────────────────────────────────

  describe('loading state (AC-021)', () => {
    it('test_shows_three_skeleton_rows_when_is_loading_true', () => {
      // TODO: render <TailoredCVsListTable {...DEFAULT_PROPS} isLoading={true} tailoredCvs={[]} />
      // TODO: assert 3 skeleton row elements are present (e.g. data-testid="skeleton-row")
      // TODO: assert no real data rows are rendered
    });

    it('test_skeleton_rows_have_shimmer_animation_class_when_loading', () => {
      // TODO: render with isLoading=true
      // TODO: assert skeleton rows have 'animate-pulse' or equivalent shimmer class
    });

    it('test_real_data_rows_absent_when_is_loading_true', () => {
      // TODO: render with isLoading=true and populated tailoredCvs
      // TODO: assert no data cell with 'Senior_Engineer_cv.pdf' is present
    });
  });

  // ─── AC-022 — Error state ─────────────────────────────────────────────────

  describe('error state (AC-022)', () => {
    it('test_shows_inline_error_message_when_error_prop_is_truthy', () => {
      // TODO: render <TailoredCVsListTable {...DEFAULT_PROPS} error={new Error('Network error')} />
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

  // ─── AC-023 — Empty state ─────────────────────────────────────────────────

  describe('empty state (AC-023)', () => {
    it('test_table_headers_visible_when_tailored_cvs_array_is_empty', () => {
      // TODO: render <TailoredCVsListTable tailoredCvs={EMPTY_TAILORED_CVS} isLoading={false} error={null} onRetry={vi.fn()} />
      // TODO: assert 5 column headers still visible
    });

    it('test_empty_state_message_shown_when_tailored_cvs_array_is_empty', () => {
      // TODO: render with empty array
      // TODO: assert screen.getByText(/no tailored cvs yet/i) is visible
    });

    it('test_empty_state_contains_link_to_applications_when_array_is_empty', () => {
      // TODO: render with empty array
      // TODO: assert an <a> or Link element with href='/applications' is present
      // TODO: assert the link text contains 'application'
    });

    it('test_empty_state_link_navigates_to_applications_route_when_clicked', () => {
      // TODO: render with empty array
      // TODO: assert the CTA link href is exactly '/applications'
    });
  });

  // ─── AC-024 — Responsive card layout ──────────────────────────────────────

  describe('responsive layout (AC-024)', () => {
    it('test_card_layout_class_applied_when_viewport_below_768px', () => {
      // TODO: render <TailoredCVsListTable {...DEFAULT_PROPS} />
      // TODO: assert component root or table wrapper has a responsive card CSS class
      //       (e.g. 'md:hidden' or 'block md:table') indicating card layout < 768px
      // NOTE: viewport resize is not testable in jsdom; assert responsive utility classes
    });

    it('test_each_card_shows_all_five_fields_stacked_when_in_card_layout', () => {
      // TODO: render <TailoredCVsListTable {...DEFAULT_PROPS} />
      // TODO: find card elements (e.g. data-testid="tailored-cv-card")
      // TODO: assert each card contains title, language, lastUpdated, status, and View link
    });
  });

  // ─── AC-025 — th scope="col" ──────────────────────────────────────────────

  describe('accessibility — th scope (AC-025)', () => {
    it('test_all_th_elements_have_scope_col_attribute_when_rendered', () => {
      // TODO: render <TailoredCVsListTable {...DEFAULT_PROPS} />
      // TODO: get all columnheader elements via screen.getAllByRole('columnheader')
      // TODO: assert each has getAttribute('scope') === 'col'
    });
  });

  // ─── AC-026 — Keyboard Enter/Space toggles sort ───────────────────────────

  describe('accessibility — keyboard navigation (AC-026)', () => {
    it('test_pressing_enter_on_focused_column_header_toggles_sort_ascending', () => {
      // TODO: render <TailoredCVsListTable {...DEFAULT_PROPS} />
      // TODO: focus the Title column header
      // TODO: fireEvent.keyDown with key='Enter'
      // TODO: assert rows are now sorted ascending by title
    });

    it('test_pressing_space_on_focused_column_header_toggles_sort_ascending', () => {
      // TODO: render <TailoredCVsListTable {...DEFAULT_PROPS} />
      // TODO: focus the Language column header
      // TODO: fireEvent.keyDown with key=' ' (Space)
      // TODO: assert rows are sorted ascending by language
    });

    it('test_keyboard_sort_equivalent_to_click_sort_when_focused', () => {
      // TODO: render two instances — click one, keyboard the other
      // TODO: assert both produce identical row ordering after one activation
    });
  });

  // ─── AC-027 — aria-sort on active column ─────────────────────────────────

  describe('accessibility — aria-sort (AC-027)', () => {
    it('test_active_sort_column_has_aria_sort_ascending_when_sorted_ascending', () => {
      // TODO: render <TailoredCVsListTable {...DEFAULT_PROPS} />
      // TODO: click Title header
      // TODO: assert Title <th> getAttribute('aria-sort') === 'ascending'
    });

    it('test_active_sort_column_has_aria_sort_descending_when_sorted_descending', () => {
      // TODO: render <TailoredCVsListTable {...DEFAULT_PROPS} />
      // TODO: click Title header twice
      // TODO: assert Title <th> getAttribute('aria-sort') === 'descending'
    });

    it('test_inactive_columns_do_not_have_aria_sort_ascending_when_another_column_active', () => {
      // TODO: render and click Title header
      // TODO: assert Language <th> does NOT have aria-sort="ascending" or "descending"
    });
  });

  // ─── AC-028 — Hebrew i18n ─────────────────────────────────────────────────

  describe('i18n — Hebrew strings (AC-028)', () => {
    it('test_column_headers_render_in_hebrew_when_locale_is_he', () => {
      // TODO: render <TailoredCVsListTable {...DEFAULT_PROPS} locale="he" /> (or wrap in i18n provider with he locale)
      // TODO: assert column headers contain Hebrew translations for Title, Language, Last Updated, Status, Action
      // TODO: assert English column header text is NOT present
    });

    it('test_view_text_renders_in_hebrew_when_locale_is_he', () => {
      // TODO: render with locale=he
      // TODO: assert View action text is in Hebrew
      // TODO: assert English "View" text is NOT present
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

    it('test_edited_badge_label_renders_in_hebrew_when_locale_is_he', () => {
      // TODO: render with locale=he and an 'edited' status row
      // TODO: assert badge text is the Hebrew translation for "Edited"
    });

    it('test_empty_state_text_renders_in_hebrew_when_locale_is_he', () => {
      // TODO: render with locale=he and empty tailoredCvs array
      // TODO: assert empty state message is in Hebrew
    });

    it('test_error_message_and_retry_text_render_in_hebrew_when_locale_is_he', () => {
      // TODO: render with locale=he and error truthy
      // TODO: assert error message text is in Hebrew
      // TODO: assert Retry button text is in Hebrew
    });

    it('test_search_placeholder_renders_in_hebrew_when_locale_is_he', () => {
      // TODO: render with locale=he
      // TODO: assert search input placeholder text is in Hebrew
    });
  });

});
