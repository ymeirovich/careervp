// spec_id: FE-UI-013  component: CoverLettersListTable  tier: unit
// file: src/frontend/components/CoverLettersListTable/CoverLettersListTable.tsx
// Framework: Vitest + @testing-library/react
// All 24 ACs are verification_type: unit — each AC has a dedicated test below.

import { render, screen, fireEvent, within } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { CoverLettersListTable } from '../../../src/frontend/components/CoverLettersListTable/CoverLettersListTable';

// ---------------------------------------------------------------------------
// Shared fixtures
// ---------------------------------------------------------------------------

interface CoverLetterFixture {
  applicationId: string;
  company_name: string;
  job_title: string;
  status: 'ready' | 'processing' | 'failed';
  created_at: string;
}

const FIXTURE_COVER_LETTERS: CoverLetterFixture[] = [
  {
    applicationId: 'app-1',
    company_name: 'Acme Corp',
    job_title: 'Senior Engineer',
    status: 'ready',
    created_at: '2026-05-20T10:00:00Z',
  },
  {
    applicationId: 'app-2',
    company_name: 'Beta Ltd',
    job_title: 'Product Manager',
    status: 'processing',
    created_at: '2026-05-15T09:00:00Z',
  },
  {
    applicationId: 'app-3',
    company_name: 'Gamma Inc',
    job_title: 'Data Analyst',
    status: 'failed',
    created_at: '2026-05-10T08:00:00Z',
  },
];

const EMPTY_COVER_LETTERS: CoverLetterFixture[] = [];

const DEFAULT_PROPS = {
  coverLetters: FIXTURE_COVER_LETTERS,
  isLoading: false,
  error: null as Error | null,
  onRetry: vi.fn(),
};

beforeEach(() => {
  vi.clearAllMocks();
});

// ===========================================================================
// AC-001 — semantic <table> markup
// ===========================================================================

describe('CoverLettersListTable', () => {

  describe('table structure — semantic markup (AC-001)', () => {
    it('test_renders_semantic_table_element_when_data_present', () => {
      // TODO: render <CoverLettersListTable {...DEFAULT_PROPS} />
      // TODO: assert document.querySelector('table') is not null
      // TODO: assert document.querySelector('thead') is not null
      // TODO: assert document.querySelector('tbody') is not null
    });

    it('test_th_elements_have_scope_col_attribute_when_rendered (AC-001/AC-021)', () => {
      // TODO: render <CoverLettersListTable {...DEFAULT_PROPS} />
      // TODO: get all <th> elements
      // TODO: assert each th has attribute scope="col"
    });

    it('test_uses_tr_and_td_elements_in_tbody_when_data_present', () => {
      // TODO: render <CoverLettersListTable {...DEFAULT_PROPS} />
      // TODO: get all <tr> in <tbody>
      // TODO: assert each row contains <td> elements
    });
  });

  // ===========================================================================
  // AC-002 — 5 columns in correct order
  // ===========================================================================

  describe('column headers — count and order (AC-002)', () => {
    it('test_renders_five_column_headers_when_data_present', () => {
      // TODO: render <CoverLettersListTable {...DEFAULT_PROPS} />
      // TODO: get all <th> elements
      // TODO: assert there are exactly 5
    });

    it('test_column_order_is_company_jobtitle_date_status_action_when_rendered', () => {
      // TODO: render <CoverLettersListTable {...DEFAULT_PROPS} />
      // TODO: get all <th> text contents
      // TODO: assert order is ['Company', 'Job Title', 'Date', 'Status', 'Action']
    });
  });

  // ===========================================================================
  // AC-003 — zebra striping
  // ===========================================================================

  describe('zebra striping (AC-003)', () => {
    it('test_odd_rows_have_bg_white_class_when_multiple_rows_rendered', () => {
      // TODO: render <CoverLettersListTable {...DEFAULT_PROPS} />
      // TODO: get all <tr> elements in <tbody>
      // TODO: assert row at index 0 (odd) has className containing 'bg-white'
    });

    it('test_even_rows_have_bg_surface_subtle_class_when_multiple_rows_rendered', () => {
      // TODO: render <CoverLettersListTable {...DEFAULT_PROPS} />
      // TODO: get all <tr> elements in <tbody>
      // TODO: assert row at index 1 (even) has className containing 'bg-surface-subtle'
    });
  });

  // ===========================================================================
  // AC-004, AC-005, AC-006 — badge variants by status
  // ===========================================================================

  describe('status badges (AC-004, AC-005, AC-006)', () => {
    it('test_badge_has_success_variant_when_status_is_ready', () => {
      // TODO: render <CoverLettersListTable coverLetters={[FIXTURE_COVER_LETTERS[0]]} isLoading={false} error={null} onRetry={vi.fn()} />
      // TODO: find the Badge for row 0
      // TODO: assert it has data-variant="success" or className containing 'success'
    });

    it('test_badge_has_info_variant_when_status_is_processing', () => {
      // TODO: render <CoverLettersListTable coverLetters={[FIXTURE_COVER_LETTERS[1]]} isLoading={false} error={null} onRetry={vi.fn()} />
      // TODO: find the Badge for row 0
      // TODO: assert it has data-variant="info" or className containing 'info'
    });

    it('test_badge_has_destructive_variant_when_status_is_failed', () => {
      // TODO: render <CoverLettersListTable coverLetters={[FIXTURE_COVER_LETTERS[2]]} isLoading={false} error={null} onRetry={vi.fn()} />
      // TODO: find the Badge for row 0
      // TODO: assert it has data-variant="destructive" or className containing 'destructive'
    });
  });

  // ===========================================================================
  // AC-007 — View action is bold text link, not ghost Button
  // ===========================================================================

  describe('View action element type (AC-007)', () => {
    it('test_view_action_is_not_button_element_when_rendered', () => {
      // TODO: render <CoverLettersListTable {...DEFAULT_PROPS} />
      // TODO: get all elements with text 'View'
      // TODO: assert none has role="button" or tagName 'BUTTON'
    });

    it('test_view_action_is_bold_text_link_when_rendered', () => {
      // TODO: render <CoverLettersListTable {...DEFAULT_PROPS} />
      // TODO: get the first 'View' element
      // TODO: assert it is an <a> or has font-weight bold class (e.g. 'font-bold')
    });
  });

  // ===========================================================================
  // AC-008 — default sort: Date descending
  // ===========================================================================

  describe('default sort — Date descending (AC-008)', () => {
    it('test_rows_sorted_by_date_descending_when_no_user_sort_applied', () => {
      // TODO: render <CoverLettersListTable {...DEFAULT_PROPS} />
      // TODO: get all rows from <tbody>
      // TODO: extract the Date cell text from each row
      // TODO: assert first row has the most recent date (2026-05-20)
      // TODO: assert last row has the oldest date (2026-05-10)
    });

    it('test_date_column_th_shows_descending_indicator_when_default_render', () => {
      // TODO: render <CoverLettersListTable {...DEFAULT_PROPS} />
      // TODO: find the Date <th>
      // TODO: assert aria-sort="descending" or a descending sort indicator is present
    });
  });

  // ===========================================================================
  // AC-009 — click unsorted column → sort ascending
  // ===========================================================================

  describe('column sort — first click (AC-009)', () => {
    it('test_clicking_company_header_sorts_rows_ascending_when_column_unsorted', () => {
      // TODO: render <CoverLettersListTable {...DEFAULT_PROPS} />
      // TODO: fireEvent.click on the Company <th>
      // TODO: get all rows from <tbody>
      // TODO: assert company names are in ascending alphabetical order
    });

    it('test_company_th_shows_ascending_indicator_when_first_clicked', () => {
      // TODO: render <CoverLettersListTable {...DEFAULT_PROPS} />
      // TODO: fireEvent.click on the Company <th>
      // TODO: assert Company <th> has aria-sort="ascending"
    });
  });

  // ===========================================================================
  // AC-010 — second click same column → sort descending
  // ===========================================================================

  describe('column sort — second click toggles to descending (AC-010)', () => {
    it('test_clicking_company_header_twice_sorts_descending_when_was_ascending', () => {
      // TODO: render <CoverLettersListTable {...DEFAULT_PROPS} />
      // TODO: fireEvent.click on Company <th> (first click → ascending)
      // TODO: fireEvent.click on Company <th> (second click → descending)
      // TODO: assert company names are in descending alphabetical order
    });

    it('test_company_th_aria_sort_is_descending_after_two_clicks', () => {
      // TODO: render <CoverLettersListTable {...DEFAULT_PROPS} />
      // TODO: click Company <th> twice
      // TODO: assert Company <th> has aria-sort="descending"
    });
  });

  // ===========================================================================
  // AC-011 — clicking different column clears previous sort indicator
  // ===========================================================================

  describe('column sort — switching active column (AC-011)', () => {
    it('test_previous_column_indicator_clears_when_new_column_clicked', () => {
      // TODO: render <CoverLettersListTable {...DEFAULT_PROPS} />
      // TODO: click Company <th>
      // TODO: click Job Title <th>
      // TODO: assert Company <th> no longer has aria-sort attribute (or is "none")
    });

    it('test_new_column_sorts_ascending_when_different_column_clicked', () => {
      // TODO: render <CoverLettersListTable {...DEFAULT_PROPS} />
      // TODO: click Company <th> then click Job Title <th>
      // TODO: assert Job Title <th> has aria-sort="ascending"
    });
  });

  // ===========================================================================
  // AC-012 — search filters by Company and Job Title (case-insensitive)
  // ===========================================================================

  describe('search — filters rows (AC-012)', () => {
    it('test_only_matching_rows_shown_when_search_term_matches_company', () => {
      // TODO: render <CoverLettersListTable {...DEFAULT_PROPS} />
      // TODO: find the search input (role="searchbox" or placeholder text)
      // TODO: fireEvent.change with value 'acme'
      // TODO: assert only the Acme Corp row is visible
      // TODO: assert Beta Ltd and Gamma Inc rows are not in the document
    });

    it('test_search_is_case_insensitive_when_term_is_uppercase', () => {
      // TODO: render <CoverLettersListTable {...DEFAULT_PROPS} />
      // TODO: fireEvent.change search input with value 'ACME'
      // TODO: assert Acme Corp row is visible
    });

    it('test_only_matching_rows_shown_when_search_term_matches_job_title', () => {
      // TODO: render <CoverLettersListTable {...DEFAULT_PROPS} />
      // TODO: fireEvent.change search input with value 'product'
      // TODO: assert Beta Ltd / Product Manager row is visible
      // TODO: assert other rows are not visible
    });
  });

  // ===========================================================================
  // AC-013 — no-match search shows "No matching cover letters"
  // ===========================================================================

  describe('search — empty result state (AC-013)', () => {
    it('test_no_matching_message_shown_when_search_yields_zero_results', () => {
      // TODO: render <CoverLettersListTable {...DEFAULT_PROPS} />
      // TODO: fireEvent.change search input with value 'zzznomatch'
      // TODO: assert screen.getByText(/no matching cover letters/i) is visible
    });

    it('test_primary_empty_state_not_shown_when_search_yields_zero_results', () => {
      // TODO: render <CoverLettersListTable {...DEFAULT_PROPS} />
      // TODO: fireEvent.change search input with value 'zzznomatch'
      // TODO: assert screen.queryByText(/no cover letters yet/i) is null
    });
  });

  // ===========================================================================
  // AC-014, AC-015 — hover state (className assertions)
  // ===========================================================================

  describe('row hover — highlight and View underline (AC-014, AC-015)', () => {
    it('test_row_has_hover_highlight_class_when_row_includes_hover_styles', () => {
      // TODO: render <CoverLettersListTable {...DEFAULT_PROPS} />
      // TODO: get first data row (<tr> in <tbody>)
      // TODO: assert row className contains a hover utility (e.g. 'hover:bg-' prefix)
    });

    it('test_view_link_has_hover_underline_class_when_row_includes_hover_styles', () => {
      // TODO: render <CoverLettersListTable {...DEFAULT_PROPS} />
      // TODO: get first View link element
      // TODO: assert its className contains 'hover:underline'
    });
  });

  // ===========================================================================
  // AC-016 — View click navigates to /applications/[applicationId]/cover-letter
  // ===========================================================================

  describe('View action navigation (AC-016)', () => {
    it('test_view_link_href_points_to_correct_application_route_when_rendered', () => {
      // TODO: render <CoverLettersListTable coverLetters={[FIXTURE_COVER_LETTERS[0]]} isLoading={false} error={null} onRetry={vi.fn()} />
      // TODO: get the View link
      // TODO: assert href="/applications/app-1/cover-letter"
    });
  });

  // ===========================================================================
  // AC-017 — loading state: 3 skeleton rows
  // ===========================================================================

  describe('loading state (AC-017)', () => {
    it('test_shows_three_skeleton_rows_when_isLoading_true', () => {
      // TODO: render <CoverLettersListTable coverLetters={[]} isLoading={true} error={null} onRetry={vi.fn()} />
      // TODO: find all skeleton row elements (data-testid="skeleton-row" or role="status")
      // TODO: assert there are exactly 3
    });

    it('test_no_real_data_rows_rendered_when_isLoading_true', () => {
      // TODO: render <CoverLettersListTable coverLetters={FIXTURE_COVER_LETTERS} isLoading={true} error={null} onRetry={vi.fn()} />
      // TODO: assert Acme Corp text is not in the document
    });
  });

  // ===========================================================================
  // AC-018 — error state: inline message + Retry button
  // ===========================================================================

  describe('error state (AC-018)', () => {
    it('test_inline_error_message_shown_when_error_prop_truthy', () => {
      // TODO: render <CoverLettersListTable coverLetters={[]} isLoading={false} error={new Error('fetch failed')} onRetry={vi.fn()} />
      // TODO: assert an error message text is visible in the document
    });

    it('test_retry_button_shown_when_error_prop_truthy', () => {
      // TODO: render <CoverLettersListTable coverLetters={[]} isLoading={false} error={new Error('fetch failed')} onRetry={vi.fn()} />
      // TODO: assert screen.getByRole('button', { name: /retry/i }) is visible
    });

    it('test_onRetry_called_once_when_retry_button_clicked', () => {
      const onRetry = vi.fn();
      // TODO: render <CoverLettersListTable coverLetters={[]} isLoading={false} error={new Error('fetch failed')} onRetry={onRetry} />
      // TODO: fireEvent.click on the Retry button
      // TODO: expect(onRetry).toHaveBeenCalledTimes(1)
    });
  });

  // ===========================================================================
  // AC-019 — empty state: headers visible + "No cover letters yet"
  // ===========================================================================

  describe('empty state (AC-019)', () => {
    it('test_no_cover_letters_yet_text_shown_when_empty_array_and_not_loading', () => {
      // TODO: render <CoverLettersListTable coverLetters={EMPTY_COVER_LETTERS} isLoading={false} error={null} onRetry={vi.fn()} />
      // TODO: assert screen.getByText(/no cover letters yet/i) is visible
    });

    it('test_table_headers_visible_when_empty_state', () => {
      // TODO: render <CoverLettersListTable coverLetters={EMPTY_COVER_LETTERS} isLoading={false} error={null} onRetry={vi.fn()} />
      // TODO: assert Company, Job Title, Date, Status, Action column headers are all in the document
    });
  });

  // ===========================================================================
  // AC-020 — responsive: card layout below 768px
  // ===========================================================================

  describe('responsive layout — mobile card (AC-020)', () => {
    it('test_card_layout_class_applied_when_viewport_below_768px', () => {
      // TODO: render <CoverLettersListTable {...DEFAULT_PROPS} />
      // TODO: assert there is a container element with a responsive class like 'md:hidden' or 'block md:hidden'
      // TODO: assert the card container has one child card per cover letter (3 cards for 3 fixtures)
    });

    it('test_table_element_hidden_on_mobile_via_responsive_class', () => {
      // TODO: render <CoverLettersListTable {...DEFAULT_PROPS} />
      // TODO: get the <table> element
      // TODO: assert it has className containing 'hidden md:block' or equivalent responsive hide class
    });
  });

  // ===========================================================================
  // AC-021 — scope="col" on all <th> elements (also covered in AC-001 block)
  // ===========================================================================

  describe('accessibility — th scope attribute (AC-021)', () => {
    it('test_all_th_elements_have_scope_col_when_rendered', () => {
      // TODO: render <CoverLettersListTable {...DEFAULT_PROPS} />
      // TODO: get all elements with role="columnheader"
      // TODO: assert every element has getAttribute('scope') === 'col'
    });
  });

  // ===========================================================================
  // AC-022 — keyboard: Enter/Space on focused header toggles sort
  // ===========================================================================

  describe('accessibility — keyboard sort toggle (AC-022)', () => {
    it('test_pressing_enter_on_company_header_sorts_ascending_when_unsorted', () => {
      // TODO: render <CoverLettersListTable {...DEFAULT_PROPS} />
      // TODO: focus the Company <th>
      // TODO: fireEvent.keyDown with key 'Enter'
      // TODO: assert Company <th> has aria-sort="ascending"
    });

    it('test_pressing_space_on_company_header_sorts_ascending_when_unsorted', () => {
      // TODO: render <CoverLettersListTable {...DEFAULT_PROPS} />
      // TODO: focus the Company <th>
      // TODO: fireEvent.keyDown with key ' '
      // TODO: assert Company <th> has aria-sort="ascending"
    });
  });

  // ===========================================================================
  // AC-023 — aria-sort attribute on active sort column
  // ===========================================================================

  describe('accessibility — aria-sort on active column (AC-023)', () => {
    it('test_active_sort_column_has_aria_sort_ascending_when_sorted_asc', () => {
      // TODO: render <CoverLettersListTable {...DEFAULT_PROPS} />
      // TODO: fireEvent.click Company <th>
      // TODO: assert Company <th> getAttribute('aria-sort') === 'ascending'
    });

    it('test_active_sort_column_has_aria_sort_descending_when_sorted_desc', () => {
      // TODO: render <CoverLettersListTable {...DEFAULT_PROPS} />
      // TODO: fireEvent.click Company <th> twice
      // TODO: assert Company <th> getAttribute('aria-sort') === 'descending'
    });

    it('test_default_date_column_has_aria_sort_descending_on_initial_render', () => {
      // TODO: render <CoverLettersListTable {...DEFAULT_PROPS} />
      // TODO: get the Date <th>
      // TODO: assert getAttribute('aria-sort') === 'descending'
    });
  });

  // ===========================================================================
  // AC-024 — Hebrew i18n
  // ===========================================================================

  describe('i18n — Hebrew locale (AC-024)', () => {
    it('test_column_headers_render_in_hebrew_when_locale_is_he', () => {
      // TODO: wrap render in a locale provider with locale='he'
      // TODO: render <CoverLettersListTable {...DEFAULT_PROPS} />
      // TODO: assert column header texts match Hebrew translations for Company, Job Title, Date, Status, Action
      // TODO: assert search input placeholder is in Hebrew
    });

    it('test_view_link_text_renders_in_hebrew_when_locale_is_he', () => {
      // TODO: wrap render in locale='he' provider
      // TODO: render <CoverLettersListTable {...DEFAULT_PROPS} />
      // TODO: assert Hebrew translation for "View" is visible (not the English word "View")
    });

    it('test_badge_labels_render_in_hebrew_when_locale_is_he', () => {
      // TODO: wrap render in locale='he' provider
      // TODO: render with all three status variants present
      // TODO: assert Hebrew translations for "Ready", "Processing", "Failed" are visible
    });

    it('test_empty_state_text_renders_in_hebrew_when_locale_is_he', () => {
      // TODO: wrap render in locale='he' provider
      // TODO: render <CoverLettersListTable coverLetters={[]} isLoading={false} error={null} onRetry={vi.fn()} />
      // TODO: assert Hebrew translation for "No cover letters yet" is visible
    });

    it('test_error_and_retry_text_render_in_hebrew_when_locale_is_he', () => {
      // TODO: wrap render in locale='he' provider
      // TODO: render with error prop set
      // TODO: assert Hebrew error message text is visible
      // TODO: assert Hebrew retry button text is visible
    });
  });

});
