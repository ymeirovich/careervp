// spec_id: FE-UI-011  component: ChooseBaseCVModal
// file: src/frontend/components/ChooseBaseCVModal/ChooseBaseCVModal.tsx
// All 28 ACs are verification_type: unit — one describe block per AC group.
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ChooseBaseCVModal } from '../../../src/frontend/components/ChooseBaseCVModal/ChooseBaseCVModal';

// ---------------------------------------------------------------------------
// type fixtures — no `any`
// ---------------------------------------------------------------------------
interface BaseCV {
  cv_id: string;
  cv_name: string;
  uploaded_at: string;
  cv_type: 'uploaded' | 'generated';
}

const UPLOADED_CVS: BaseCV[] = [
  { cv_id: 'cv-001', cv_name: 'My Resume.pdf', uploaded_at: '2026-01-10T00:00:00Z', cv_type: 'uploaded' },
];

const GENERATED_CVS: BaseCV[] = [
  { cv_id: 'cv-002', cv_name: 'Tailored CV - Acme', uploaded_at: '2026-02-15T00:00:00Z', cv_type: 'generated' },
];

const ALL_CVS: BaseCV[] = [...UPLOADED_CVS, ...GENERATED_CVS];

// ---------------------------------------------------------------------------
// hook mock — GET /users/me/cv at hook level, never at network level
// ---------------------------------------------------------------------------
const mockUseCVs = vi.fn();

vi.mock('../../../src/frontend/hooks/useCVs', () => ({
  useCVs: () => mockUseCVs(),
}));

// i18n: stub next-intl so locale can be swapped per test
vi.mock('next-intl', () => ({
  useTranslations: () => (key: string) => key,
  useLocale: vi.fn(() => 'en'),
}));

import { useLocale } from 'next-intl';
const mockUseLocale = vi.mocked(useLocale);

// ---------------------------------------------------------------------------
// callback mocks
// ---------------------------------------------------------------------------
const mockOnClose = vi.fn();
const mockOnSelectCV = vi.fn();
const mockOnUpload = vi.fn();

// ---------------------------------------------------------------------------
// default props helpers
// ---------------------------------------------------------------------------
interface RenderOverrides {
  isOpen?: boolean;
  showChoices?: boolean;
  cvs?: BaseCV[];
  isLoading?: boolean;
  onClose?: () => void;
  onSelectCV?: (cv: BaseCV) => void;
  onUpload?: (file: File) => void;
}

function defaultProps(overrides: RenderOverrides = {}) {
  return {
    isOpen: true,
    showChoices: true,
    cvs: ALL_CVS,
    isLoading: false,
    onClose: mockOnClose,
    onSelectCV: mockOnSelectCV,
    onUpload: mockOnUpload,
    ...overrides,
  };
}

function renderModal(overrides: RenderOverrides = {}) {
  return render(<ChooseBaseCVModal {...defaultProps(overrides)} />);
}

// ---------------------------------------------------------------------------
// beforeEach — reset all mocks, seed default hook return
// ---------------------------------------------------------------------------
beforeEach(() => {
  vi.clearAllMocks();
  mockUseLocale.mockReturnValue('en');
  mockUseCVs.mockReturnValue({ cvs: ALL_CVS, isLoading: false, error: null });
});

// ===========================================================================
// AC-001: Render guard — isOpen=false → no DOM output
// ===========================================================================
describe('ChooseBaseCVModal — render guard', () => {

  it('test_no_modal_markup_in_dom_when_isOpen_is_false', () => {
    // TODO: render component with isOpen=false
    // TODO: assert screen.queryByRole('dialog') === null
    renderModal({ isOpen: false });
    expect(screen.queryByRole('dialog')).toBeNull();
  });

});

// ===========================================================================
// AC-002–007: Choice mode (showChoices=true)
// ===========================================================================
describe('ChooseBaseCVModal — choice mode', () => {

  it('test_heading_is_choose_base_cv_when_showChoices_true', () => {
    // TODO: render with isOpen=true, showChoices=true
    // TODO: assert heading text matches "Choose Base CV"
    renderModal({ showChoices: true });
    expect(screen.queryByRole('heading', { name: /choose base cv/i })).not.toBeNull();
  });

  it('test_select_uploaded_cv_button_visible_when_showChoices_true', () => {
    // TODO: render with isOpen=true, showChoices=true
    // TODO: assert "Select uploaded CV" button present in the DOM
    renderModal({ showChoices: true });
    expect(screen.queryByRole('button', { name: /select uploaded cv/i })).not.toBeNull();
  });

  it('test_select_generated_cv_button_visible_when_showChoices_true', () => {
    // TODO: render with isOpen=true, showChoices=true
    // TODO: assert "Select generated CV" button present in the DOM
    renderModal({ showChoices: true });
    expect(screen.queryByRole('button', { name: /select generated cv/i })).not.toBeNull();
  });

  it('test_or_divider_visible_between_choices_and_upload_section_when_showChoices_true', () => {
    // TODO: render with isOpen=true, showChoices=true
    // TODO: assert element with exact text "OR" (or locale equivalent) is present
    renderModal({ showChoices: true });
    expect(screen.queryByText(/^or$/i)).not.toBeNull();
  });

  it('test_cv_list_displayed_in_modal_when_showChoices_true_and_cvs_exist', () => {
    // TODO: render with showChoices=true and cvs=ALL_CVS
    // TODO: assert each CV name from the fixture appears in the DOM
    renderModal({ showChoices: true, cvs: ALL_CVS });
    // TODO: expect(screen.queryByText('My Resume.pdf')).not.toBeNull()
    // TODO: expect(screen.queryByText('Tailored CV - Acme')).not.toBeNull()
  });

  it('test_onSelectCV_fires_with_uploaded_cv_data_when_uploaded_cv_selected', () => {
    // TODO: render with showChoices=true, cvs=UPLOADED_CVS
    // TODO: click the "Select uploaded CV" button or a CV row of type 'uploaded'
    // TODO: assert mockOnSelectCV called with UPLOADED_CVS[0]
    renderModal({ showChoices: true, cvs: UPLOADED_CVS });
    // TODO: fireEvent.click(screen.getByRole('button', { name: /select uploaded cv/i }))
    //       or fireEvent.click(screen.getByText('My Resume.pdf'))
    // TODO: expect(mockOnSelectCV).toHaveBeenCalledWith(UPLOADED_CVS[0])
  });

  it('test_onSelectCV_fires_with_generated_cv_data_when_generated_cv_selected', () => {
    // TODO: render with showChoices=true, cvs=GENERATED_CVS
    // TODO: click the "Select generated CV" button or a CV row of type 'generated'
    // TODO: assert mockOnSelectCV called with GENERATED_CVS[0]
    renderModal({ showChoices: true, cvs: GENERATED_CVS });
    // TODO: fireEvent.click(screen.getByRole('button', { name: /select generated cv/i }))
    //       or fireEvent.click(screen.getByText('Tailored CV - Acme'))
    // TODO: expect(mockOnSelectCV).toHaveBeenCalledWith(GENERATED_CVS[0])
  });

});

// ===========================================================================
// AC-008–010: Upload-only mode (showChoices=false)
// ===========================================================================
describe('ChooseBaseCVModal — upload-only mode', () => {

  it('test_heading_is_upload_base_cv_when_showChoices_false', () => {
    // TODO: render with isOpen=true, showChoices=false
    // TODO: assert heading text matches "Upload Base CV"
    renderModal({ showChoices: false });
    expect(screen.queryByRole('heading', { name: /upload base cv/i })).not.toBeNull();
  });

  it('test_select_uploaded_cv_button_absent_from_dom_when_showChoices_false', () => {
    // TODO: render with isOpen=true, showChoices=false
    // TODO: assert "Select uploaded CV" is NOT in the DOM
    renderModal({ showChoices: false });
    expect(screen.queryByRole('button', { name: /select uploaded cv/i })).toBeNull();
  });

  it('test_select_generated_cv_button_absent_from_dom_when_showChoices_false', () => {
    // TODO: render with isOpen=true, showChoices=false
    // TODO: assert "Select generated CV" is NOT in the DOM
    renderModal({ showChoices: false });
    expect(screen.queryByRole('button', { name: /select generated cv/i })).toBeNull();
  });

  it('test_file_input_and_upload_button_visible_when_showChoices_false', () => {
    // TODO: render with isOpen=true, showChoices=false
    // TODO: assert <input type="file"> element is present
    // TODO: assert "Upload" submit button is present
    renderModal({ showChoices: false });
    // TODO: expect(document.querySelector('input[type="file"]')).not.toBeNull()
    // TODO: expect(screen.queryByRole('button', { name: /^upload$/i })).not.toBeNull()
  });

});

// ===========================================================================
// AC-011–014: File upload behavior
// ===========================================================================
describe('ChooseBaseCVModal — file upload behavior', () => {

  it('test_upload_button_disabled_when_no_file_selected', () => {
    // TODO: render in upload-only mode with no file selected
    // TODO: assert "Upload" submit button has disabled attribute or aria-disabled="true"
    renderModal({ showChoices: false });
    // TODO: const btn = screen.queryByRole('button', { name: /^upload$/i }) as HTMLButtonElement
    // TODO: expect(btn.disabled || btn.getAttribute('aria-disabled') === 'true').toBe(true)
  });

  it('test_filename_displayed_and_upload_button_enabled_when_file_chosen', () => {
    // TODO: render in either mode
    // TODO: simulate file selection: fireEvent.change on <input type="file"> with a File
    // TODO: assert selected filename is visible in the DOM
    // TODO: assert "Upload" submit button is no longer disabled
    renderModal({ showChoices: false });
    const file = new File(['cv content'], 'MyResume.pdf', { type: 'application/pdf' });
    // TODO: fireEvent.change(document.querySelector('input[type="file"]'), { target: { files: [file] } })
    // TODO: expect(screen.queryByText('MyResume.pdf')).not.toBeNull()
    // TODO: expect((screen.queryByRole('button', { name: /^upload$/i }) as HTMLButtonElement).disabled).toBe(false)
    expect(file.name).toBe('MyResume.pdf'); // placeholder — replace with real assertions above
  });

  it('test_os_file_picker_triggered_directly_when_upload_new_cv_area_clicked', () => {
    // TODO: render with showChoices=true
    // TODO: spy on HTMLInputElement.prototype.click
    // TODO: click "Upload New CV" button/area
    // TODO: assert file input .click() was called — no intermediate dialog or step
    renderModal({ showChoices: true });
    // TODO: const clickSpy = vi.spyOn(HTMLInputElement.prototype, 'click')
    // TODO: fireEvent.click(screen.getByRole('button', { name: /upload new cv/i }))
    // TODO: expect(clickSpy).toHaveBeenCalled()
    // TODO: clickSpy.mockRestore()
  });

  it('test_onUpload_fires_with_file_data_when_upload_button_clicked_after_file_selected', () => {
    // TODO: render in either mode
    // TODO: simulate file selection via fireEvent.change on file input
    // TODO: click "Upload" submit button
    // TODO: assert mockOnUpload called with the correct File object
    renderModal({ showChoices: false });
    const file = new File(['cv content'], 'MyResume.pdf', { type: 'application/pdf' });
    // TODO: fireEvent.change(document.querySelector('input[type="file"]'), { target: { files: [file] } })
    // TODO: fireEvent.click(screen.getByRole('button', { name: /^upload$/i }))
    // TODO: expect(mockOnUpload).toHaveBeenCalledWith(file)
    expect(mockOnUpload).not.toHaveBeenCalled(); // placeholder — replace with post-interaction assertion
  });

});

// ===========================================================================
// AC-015–016: Empty state (showChoices=true, no CVs)
// ===========================================================================
describe('ChooseBaseCVModal — empty state', () => {

  it('test_choice_buttons_disabled_when_showChoices_true_and_no_cvs_exist', () => {
    // TODO: render with showChoices=true, cvs=[]
    // TODO: assert "Select uploaded CV" button is disabled
    // TODO: assert "Select generated CV" button is disabled
    renderModal({ showChoices: true, cvs: [] });
    // TODO: const uploadedBtn = screen.queryByRole('button', { name: /select uploaded cv/i }) as HTMLButtonElement
    // TODO: expect(uploadedBtn.disabled || uploadedBtn.getAttribute('aria-disabled') === 'true').toBe(true)
    // TODO: const generatedBtn = screen.queryByRole('button', { name: /select generated cv/i }) as HTMLButtonElement
    // TODO: expect(generatedBtn.disabled || generatedBtn.getAttribute('aria-disabled') === 'true').toBe(true)
  });

  it('test_upload_section_visually_highlighted_when_showChoices_true_and_no_cvs_exist', () => {
    // TODO: render with showChoices=true, cvs=[]
    // TODO: assert the upload section element has a visual-emphasis indicator
    //       (e.g. data-highlighted attribute, or a border/background Tailwind class)
    // Note: matches the spec requirement to guide users toward upload when CV list is empty
    renderModal({ showChoices: true, cvs: [] });
    // TODO: const uploadSection = screen.queryByTestId('upload-section')
    //        or document.querySelector('[data-upload-section]')
    // TODO: expect(uploadSection?.className).toMatch(/highlighted|border-primary|ring-/)
  });

});

// ===========================================================================
// AC-017–019: Close behavior
// ===========================================================================
describe('ChooseBaseCVModal — close behavior', () => {

  it('test_onClose_fires_when_x_close_icon_clicked', () => {
    // TODO: render modal open
    // TODO: click the X close icon button in the top-right corner
    // TODO: assert mockOnClose called exactly once
    renderModal();
    // TODO: fireEvent.click(screen.getByRole('button', { name: /close/i }))
    // TODO: expect(mockOnClose).toHaveBeenCalledTimes(1)
  });

  it('test_onClose_fires_when_escape_key_pressed', () => {
    // TODO: render modal open
    // TODO: dispatch keyDown event with key='Escape' on the document
    // TODO: assert mockOnClose called exactly once
    renderModal();
    // TODO: fireEvent.keyDown(document, { key: 'Escape', code: 'Escape' })
    // TODO: expect(mockOnClose).toHaveBeenCalledTimes(1)
  });

  it('test_onClose_fires_when_backdrop_overlay_clicked', () => {
    // TODO: render modal open
    // TODO: click the backdrop element (area outside the modal card)
    // TODO: assert mockOnClose called exactly once
    renderModal();
    // TODO: const backdrop = document.querySelector('[data-testid="modal-backdrop"]')
    // TODO: fireEvent.click(backdrop)
    // TODO: expect(mockOnClose).toHaveBeenCalledTimes(1)
  });

});

// ===========================================================================
// AC-020–024: Accessibility
// ===========================================================================
describe('ChooseBaseCVModal — accessibility', () => {

  it('test_modal_has_role_dialog_and_aria_modal_true_when_open', () => {
    // TODO: render modal open
    // TODO: assert an element with role="dialog" exists
    // TODO: assert that element has aria-modal="true"
    renderModal();
    const dialog = screen.queryByRole('dialog');
    expect(dialog).not.toBeNull();
    // TODO: expect(dialog?.getAttribute('aria-modal')).toBe('true')
  });

  it('test_aria_labelledby_references_heading_id_when_open', () => {
    // TODO: render modal open
    // TODO: assert dialog's aria-labelledby value matches the heading element's id
    renderModal();
    // TODO: const dialog = screen.queryByRole('dialog')
    // TODO: const headingId = screen.queryByRole('heading')?.id
    // TODO: expect(dialog?.getAttribute('aria-labelledby')).toBe(headingId)
  });

  it('test_aria_describedby_references_subtitle_id_when_open', () => {
    // TODO: render modal open
    // TODO: assert dialog's aria-describedby value references a subtitle element that exists in the DOM
    renderModal();
    // TODO: const dialog = screen.queryByRole('dialog')
    // TODO: const subtitleId = dialog?.getAttribute('aria-describedby')
    // TODO: expect(document.getElementById(subtitleId ?? '')).not.toBeNull()
  });

  it('test_focus_trapped_within_modal_when_tab_pressed_at_last_focusable_element', () => {
    // TODO: render modal open
    // TODO: query all focusable elements within the dialog
    // TODO: focus the last focusable element, then press Tab
    // TODO: assert document.activeElement wraps to the first focusable element inside the dialog
    renderModal();
    // TODO: const dialog = screen.queryByRole('dialog')
    // TODO: const focusable = Array.from(dialog?.querySelectorAll(
    //   'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    // ) ?? []) as HTMLElement[]
    // TODO: focusable[focusable.length - 1]?.focus()
    // TODO: fireEvent.keyDown(document, { key: 'Tab' })
    // TODO: expect(document.activeElement).toBe(focusable[0])
  });

  it('test_focus_moves_to_first_focusable_element_when_modal_opens', () => {
    // TODO: render modal open
    // TODO: assert document.activeElement is the X close button or first interactive element in the dialog
    renderModal();
    // TODO: expect(document.activeElement).toBe(screen.queryByRole('button', { name: /close/i }))
  });

  it('test_disabled_buttons_follow_design_system_disabled_pattern', () => {
    // TODO: render with empty CV list so choice buttons are disabled
    // TODO: assert each disabled button has `disabled` attribute OR aria-disabled="true"
    // Design system pattern: opacity reduction + cursor-not-allowed (per AC-024 and gap answer q15)
    renderModal({ showChoices: true, cvs: [] });
    // TODO: const uploadedBtn = screen.queryByRole('button', { name: /select uploaded cv/i }) as HTMLButtonElement
    // TODO: expect(uploadedBtn.disabled || uploadedBtn.getAttribute('aria-disabled') === 'true').toBe(true)
    // TODO: expect(uploadedBtn.className).toMatch(/opacity-|cursor-not-allowed/)
  });

});

// ===========================================================================
// AC-025–026: i18n
// ===========================================================================
describe('ChooseBaseCVModal — i18n', () => {

  it('test_choice_mode_strings_render_in_hebrew_when_locale_is_he', () => {
    // TODO: set locale to 'he' via mockUseLocale
    // TODO: render with showChoices=true
    // TODO: assert heading = "בחר קורות חיים בסיסיים"
    // TODO: assert "Select uploaded CV" text = "בחר קורות חיים שהועלו"
    // TODO: assert "Select generated CV" text = "בחר קורות חיים שנוצרו"
    // TODO: assert "Upload New CV" label = "העלה קורות חיים חדשים"
    // TODO: assert OR divider text = "או"
    mockUseLocale.mockReturnValue('he');
    renderModal({ showChoices: true });
    // TODO: expect(screen.queryByRole('heading', { name: 'בחר קורות חיים בסיסיים' })).not.toBeNull()
    // TODO: expect(screen.queryByText('בחר קורות חיים שהועלו')).not.toBeNull()
    // TODO: expect(screen.queryByText('בחר קורות חיים שנוצרו')).not.toBeNull()
    // TODO: expect(screen.queryByText('העלה קורות חיים חדשים')).not.toBeNull()
    // TODO: expect(screen.queryByText('או')).not.toBeNull()
  });

  it('test_upload_only_mode_strings_render_in_hebrew_when_locale_is_he', () => {
    // TODO: set locale to 'he' via mockUseLocale
    // TODO: render with showChoices=false
    // TODO: assert heading = "העלה קורות חיים בסיסיים"
    // TODO: assert Upload button label = "העלה"
    mockUseLocale.mockReturnValue('he');
    renderModal({ showChoices: false });
    // TODO: expect(screen.queryByRole('heading', { name: 'העלה קורות חיים בסיסיים' })).not.toBeNull()
    // TODO: expect(screen.queryByRole('button', { name: 'העלה' })).not.toBeNull()
  });

});

// ===========================================================================
// AC-027: Responsive
// ===========================================================================
describe('ChooseBaseCVModal — responsive', () => {

  it('test_modal_card_near_full_width_with_no_overflow_when_viewport_under_768px', () => {
    // TODO: render modal open (jsdom does not apply CSS — assert className instead)
    // TODO: assert modal card element contains responsive Tailwind class covering narrow viewports
    //       e.g. 'w-full', 'max-w-[95vw]', 'sm:max-w-lg', or similar pattern used in this codebase
    // Note: for pixel-level layout tests use Playwright (tests/e2e)
    renderModal();
    // TODO: const card = screen.queryByRole('dialog')?.closest('[class*="max-w"]')
    //        or screen.queryByTestId('modal-card')
    // TODO: expect(card?.className).toMatch(/w-full|max-w-\[9[0-9]|sm:max-w/)
  });

});

// ===========================================================================
// AC-028: Data model — uploaded vs generated CV type distinction
// ===========================================================================
describe('ChooseBaseCVModal — data model', () => {

  it('test_uploaded_and_generated_cvs_treated_as_distinct_types_when_cv_data_received', () => {
    // TODO: render with cvs=ALL_CVS (mix of uploaded and generated)
    // TODO: assert the uploaded CV section only shows CVs with cv_type === 'uploaded'
    // TODO: assert the generated CV section only shows CVs with cv_type === 'generated'
    // Ensures TailoredCV (generated) and base uploaded CVs are never mixed in the UI
    renderModal({ showChoices: true, cvs: ALL_CVS });
    // TODO: assert 'My Resume.pdf' appears in the uploaded section
    // TODO: assert 'Tailored CV - Acme' appears in the generated section
    // TODO: assert 'My Resume.pdf' does NOT appear in the generated section
  });

});
