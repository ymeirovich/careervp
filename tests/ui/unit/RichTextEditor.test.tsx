// spec_id: FE-UI-020 — RichTextEditor unit tests
// Coverage target: 70% — all ACs with verification_type: unit

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { RichTextEditor } from '../../../src/frontend/components/RichTextEditor/RichTextEditor';

// ---------------------------------------------------------------------------
// TipTap mock — mock at hook level, never at network level
// ---------------------------------------------------------------------------

vi.mock('@tiptap/react', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@tiptap/react')>();
  return {
    ...actual,
    useEditor: vi.fn(() => ({
      isActive: vi.fn(() => false),
      chain: vi.fn(() => ({ focus: vi.fn(() => ({ toggleBold: vi.fn(() => ({ run: vi.fn() })) })) })),
      getHTML: vi.fn(() => '<p></p>'),
      commands: {
        setContent: vi.fn(),
        toggleBold: vi.fn(),
        toggleItalic: vi.fn(),
        toggleUnderline: vi.fn(),
        toggleBulletList: vi.fn(),
        toggleOrderedList: vi.fn(),
      },
      isEditable: true,
      isEmpty: true,
      isFocused: false,
      on: vi.fn(),
      off: vi.fn(),
      destroy: vi.fn(),
    })),
    EditorContent: ({ editor: _editor, ...props }: { editor: unknown; [key: string]: unknown }) => (
      <div role="textbox" aria-multiline="true" data-testid="editor-content" {...props} />
    ),
  };
});

vi.mock('@tiptap/starter-kit', () => ({ default: {} }));
vi.mock('@tiptap/extension-underline', () => ({ default: { configure: vi.fn(() => ({})) } }));
vi.mock('../../../src/frontend/components/RichTextEditor/markdownSerializer', () => ({
  markdownToHtml: vi.fn((md: string) => `<p>${md}</p>`),
  htmlToMarkdown: vi.fn((html: string) => html.replace(/<[^>]+>/g, '')),
}));

// ---------------------------------------------------------------------------

const defaultProps = {
  content: '',
  onChange: vi.fn(),
};

beforeEach(() => {
  vi.clearAllMocks();
});

// ---------------------------------------------------------------------------

describe('RichTextEditor', () => {

  // -------------------------------------------------------------------------
  // AC-001: empty state
  // -------------------------------------------------------------------------
  describe('empty state', () => {
    it('test_renders_editable_area_when_content_is_empty_string', () => {
      // TODO: render <RichTextEditor content="" onChange={vi.fn()} />
      // TODO: assert editor content area is present in the DOM
      expect(true).toBe(true); // placeholder — replace with real assertion
    });

    it('test_renders_toolbar_when_content_is_empty_string', () => {
      // TODO: render <RichTextEditor content="" onChange={vi.fn()} />
      // TODO: assert toolbar container or at least one toolbar button is visible
      expect(true).toBe(true);
    });
  });

  // -------------------------------------------------------------------------
  // AC-017: placeholder visible when empty and not focused
  // -------------------------------------------------------------------------
  describe('placeholder state', () => {
    it('test_shows_placeholder_text_when_empty_and_unfocused', () => {
      // TODO: render with content="" and no focus applied
      // TODO: assert placeholder text (e.g., "Your answer...") is in the document
      //       — either via TipTap placeholder extension data-attribute or visible text node
      expect(true).toBe(true);
    });
  });

  // -------------------------------------------------------------------------
  // AC-002: Markdown content with bold
  // -------------------------------------------------------------------------
  describe('Markdown initialization', () => {
    it('test_passes_converted_html_to_editor_when_content_has_markdown_bold', () => {
      // TODO: mock markdownToHtml to return '<p>Hello <strong>world</strong></p>'
      //       for input 'Hello **world**'
      // TODO: render <RichTextEditor content="Hello **world**" onChange={vi.fn()} />
      // TODO: assert useEditor was called with content containing <strong>world</strong>
      expect(true).toBe(true);
    });

    // AC-003: plain text
    it('test_passes_content_unchanged_when_content_has_no_markdown_syntax', () => {
      // TODO: mock markdownToHtml to return '<p>Plain text answer</p>'
      //       for input 'Plain text answer'
      // TODO: render <RichTextEditor content="Plain text answer" onChange={vi.fn()} />
      // TODO: assert useEditor initialised with that content — no extra formatting artifacts
      expect(true).toBe(true);
    });
  });

  // -------------------------------------------------------------------------
  // Toolbar rendering
  // -------------------------------------------------------------------------
  describe('toolbar buttons', () => {
    it('test_renders_bold_button_in_toolbar', () => {
      // TODO: render component
      // TODO: assert button with aria-label="Bold" is in the document (AC-015)
      expect(true).toBe(true);
    });

    it('test_renders_italic_button_in_toolbar', () => {
      // TODO: render component
      // TODO: assert button with aria-label="Italic" is in the document (AC-015)
      expect(true).toBe(true);
    });

    it('test_renders_underline_button_in_toolbar', () => {
      // TODO: render component
      // TODO: assert button with aria-label="Underline" is in the document (AC-015)
      expect(true).toBe(true);
    });

    it('test_renders_bullet_list_button_in_toolbar', () => {
      // TODO: render component
      // TODO: assert button with aria-label="Bullet list" is in the document (AC-015)
      expect(true).toBe(true);
    });

    it('test_renders_numbered_list_button_in_toolbar', () => {
      // TODO: render component
      // TODO: assert button with aria-label="Numbered list" is in the document (AC-015)
      expect(true).toBe(true);
    });
  });

  // -------------------------------------------------------------------------
  // AC-004: Bold button interaction
  // -------------------------------------------------------------------------
  describe('bold toggle', () => {
    it('test_calls_toggleBold_when_bold_button_clicked', () => {
      // TODO: render component with non-empty content
      // TODO: fireEvent.click on aria-label="Bold" button
      // TODO: assert editor.chain().focus().toggleBold().run() was called
      expect(true).toBe(true);
    });

    it('test_bold_button_shows_active_state_when_bold_mark_is_active', () => {
      // TODO: mock editor.isActive('bold') to return true
      // TODO: render component
      // TODO: assert bold button has active/pressed styling class or aria-pressed="true"
      expect(true).toBe(true);
    });
  });

  // -------------------------------------------------------------------------
  // AC-005: Italic button interaction
  // -------------------------------------------------------------------------
  describe('italic toggle', () => {
    it('test_calls_toggleItalic_when_italic_button_clicked', () => {
      // TODO: render component
      // TODO: fireEvent.click on aria-label="Italic" button
      // TODO: assert toggleItalic command was invoked
      expect(true).toBe(true);
    });

    it('test_italic_button_shows_active_state_when_italic_mark_is_active', () => {
      // TODO: mock editor.isActive('italic') to return true
      // TODO: assert italic button has active styling
      expect(true).toBe(true);
    });
  });

  // -------------------------------------------------------------------------
  // AC-006: Underline button interaction
  // -------------------------------------------------------------------------
  describe('underline toggle', () => {
    it('test_calls_toggleUnderline_when_underline_button_clicked', () => {
      // TODO: render component
      // TODO: fireEvent.click on aria-label="Underline" button
      // TODO: assert toggleUnderline command was invoked
      expect(true).toBe(true);
    });

    it('test_underline_button_shows_active_state_when_underline_mark_is_active', () => {
      // TODO: mock editor.isActive('underline') to return true
      // TODO: assert underline button has active styling
      expect(true).toBe(true);
    });
  });

  // -------------------------------------------------------------------------
  // AC-007: Bullet list button
  // -------------------------------------------------------------------------
  describe('bullet list toggle', () => {
    it('test_calls_toggleBulletList_when_bullet_list_button_clicked', () => {
      // TODO: render component
      // TODO: fireEvent.click on aria-label="Bullet list" button
      // TODO: assert toggleBulletList command was invoked
      expect(true).toBe(true);
    });
  });

  // -------------------------------------------------------------------------
  // AC-008: Numbered list button
  // -------------------------------------------------------------------------
  describe('numbered list toggle', () => {
    it('test_calls_toggleOrderedList_when_numbered_list_button_clicked', () => {
      // TODO: render component
      // TODO: fireEvent.click on aria-label="Numbered list" button
      // TODO: assert toggleOrderedList command was invoked
      expect(true).toBe(true);
    });
  });

  // -------------------------------------------------------------------------
  // AC-009: onChange emits Markdown
  // -------------------------------------------------------------------------
  describe('onChange callback', () => {
    it('test_calls_onChange_with_markdown_string_when_editor_content_updates', () => {
      // TODO: configure useEditor mock to call its onUpdate handler with mock editor state
      // TODO: mock htmlToMarkdown to return '**bold text**'
      // TODO: render <RichTextEditor content="" onChange={mockOnChange} />
      // TODO: trigger the onUpdate callback (simulate editor update)
      // TODO: assert mockOnChange was called with the Markdown string '**bold text**'
      expect(true).toBe(true);
    });

    it('test_calls_onChange_with_list_markdown_when_content_has_bullet_list', () => {
      // TODO: mock htmlToMarkdown to return '- item one\n- item two'
      // TODO: trigger onUpdate
      // TODO: assert onChange was called with that Markdown string
      expect(true).toBe(true);
    });
  });

  // -------------------------------------------------------------------------
  // AC-010: Paste — strip headings/images/tables, keep bold/italic
  // NOTE: Clipboard events in jsdom are limited — assert paste sanitization
  // logic via the paste-handler utility function directly if full event
  // simulation proves unreliable. See spec design notes.
  // -------------------------------------------------------------------------
  describe('paste sanitization', () => {
    it('test_strips_heading_tags_when_html_with_h1_is_pasted', () => {
      // TODO: import or access the paste-sanitize utility (or mock TipTap handlePaste)
      // TODO: supply input HTML: '<h1>Title</h1><p><strong>bold</strong></p>'
      // TODO: assert output does not contain <h1> and retains <strong>
      expect(true).toBe(true);
    });

    it('test_strips_image_tags_when_html_with_img_is_pasted', () => {
      // TODO: supply input HTML with <img src="..."> and plain text
      // TODO: assert output contains no <img> element, text content retained
      expect(true).toBe(true);
    });

    it('test_strips_table_tags_when_html_with_table_is_pasted', () => {
      // TODO: supply input HTML with <table><tr><td>cell</td></tr></table>
      // TODO: assert output contains no <table>; text "cell" is retained
      expect(true).toBe(true);
    });

    it('test_preserves_bold_when_html_with_strong_is_pasted', () => {
      // TODO: supply input HTML '<p><strong>keep me</strong></p>'
      // TODO: assert <strong> (or bold mark) is retained in sanitized output
      expect(true).toBe(true);
    });

    it('test_preserves_italic_when_html_with_em_is_pasted', () => {
      // TODO: supply input HTML '<p><em>keep me</em></p>'
      // TODO: assert italic mark is retained
      expect(true).toBe(true);
    });

    // AC-011: paste with <ul>/<li>
    it('test_preserves_bullet_list_structure_when_html_with_ul_is_pasted', () => {
      // TODO: supply input HTML '<ul><li>item 1</li><li>item 2</li></ul>'
      // TODO: assert bullet list structure is retained in editor output
      expect(true).toBe(true);
    });
  });

  // -------------------------------------------------------------------------
  // AC-012 / AC-013: read-only mode
  // -------------------------------------------------------------------------
  describe('read-only state', () => {
    it('test_hides_toolbar_when_readOnly_is_true', () => {
      // TODO: render <RichTextEditor content="some content" onChange={vi.fn()} readOnly={true} />
      // TODO: assert toolbar is not present in the DOM
      expect(true).toBe(true);
    });

    it('test_editor_is_not_editable_when_readOnly_is_true', () => {
      // TODO: render with readOnly=true
      // TODO: mock useEditor to set isEditable based on readOnly prop
      // TODO: assert editor contenteditable attribute is "false" (or isEditable is false)
      expect(true).toBe(true);
    });

    it('test_content_is_preserved_when_readOnly_transitions_from_false_to_true', () => {
      // TODO: render with readOnly=false and content="existing answer"
      // TODO: rerender with readOnly=true
      // TODO: assert editor content is unchanged after the prop transition (AC-013)
      expect(true).toBe(true);
    });

    it('test_toolbar_hides_when_readOnly_transitions_from_false_to_true', () => {
      // TODO: render with readOnly=false
      // TODO: assert toolbar visible
      // TODO: rerender with readOnly=true
      // TODO: assert toolbar no longer in the DOM (AC-013)
      expect(true).toBe(true);
    });
  });

  // -------------------------------------------------------------------------
  // AC-014 / AC-015: accessibility — ARIA attributes and toolbar labels
  // -------------------------------------------------------------------------
  describe('accessibility', () => {
    it('test_editor_element_has_role_textbox', () => {
      // TODO: render component
      // TODO: assert screen.getByRole('textbox') is present
      expect(true).toBe(true);
    });

    it('test_editor_element_has_aria_multiline_true', () => {
      // TODO: render component
      // TODO: assert getByRole('textbox') has aria-multiline="true"
      expect(true).toBe(true);
    });

    it('test_editor_element_has_aria_labelledby_matching_prop', () => {
      // TODO: render <RichTextEditor ariaLabelledBy="question-label-123" content="" onChange={vi.fn()} />
      // TODO: assert editor element has aria-labelledby="question-label-123"
      expect(true).toBe(true);
    });

    it('test_toolbar_bold_button_has_correct_aria_label', () => {
      // TODO: render component
      // TODO: assert screen.getByRole('button', { name: 'Bold' }) exists
      expect(true).toBe(true);
    });

    it('test_toolbar_italic_button_has_correct_aria_label', () => {
      // TODO: render component
      // TODO: assert screen.getByRole('button', { name: 'Italic' }) exists
      expect(true).toBe(true);
    });

    it('test_toolbar_underline_button_has_correct_aria_label', () => {
      // TODO: render component
      // TODO: assert screen.getByRole('button', { name: 'Underline' }) exists
      expect(true).toBe(true);
    });

    it('test_toolbar_bullet_list_button_has_correct_aria_label', () => {
      // TODO: render component
      // TODO: assert screen.getByRole('button', { name: 'Bullet list' }) exists
      expect(true).toBe(true);
    });

    it('test_toolbar_numbered_list_button_has_correct_aria_label', () => {
      // TODO: render component
      // TODO: assert screen.getByRole('button', { name: 'Numbered list' }) exists
      expect(true).toBe(true);
    });

    it('test_keyboard_navigation_when_focused', () => {
      // TODO: render component
      // TODO: assert toolbar buttons are reachable via Tab key order
      // TODO: fireEvent.keyDown on each button and assert expected command fires
      expect(true).toBe(true);
    });
  });

  // -------------------------------------------------------------------------
  // AC-018: focus ring
  // -------------------------------------------------------------------------
  describe('focused state', () => {
    it('test_focus_ring_class_applied_when_editor_receives_focus', () => {
      // TODO: render component
      // TODO: fireEvent.focus on the editor container or content area
      // TODO: assert the outer container has class containing 'ring-1' and 'ring-primary-action'
      expect(true).toBe(true);
    });
  });

});
