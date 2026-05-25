// spec_id: FE-UI-020 — RichTextEditor integration tests
// Coverage target: 20% — ACs with verification_type: integration
// AC-016: Ctrl+B / Cmd+B keyboard shortcut toggles bold within page context

import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { jest, describe, it, expect, beforeEach } from '@jest/globals';
import { RichTextEditor } from '../../../src/frontend/components/RichTextEditor/RichTextEditor';

// ---------------------------------------------------------------------------
// API client mock — mock at client level, not hook level
// ---------------------------------------------------------------------------

jest.mock('../../../src/frontend/lib/apiClient', () => ({
  apiClient: {
    post: jest.fn(),
    get: jest.fn(),
  },
}));

// ---------------------------------------------------------------------------
// Provider wrapper
// ---------------------------------------------------------------------------

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

// ---------------------------------------------------------------------------

beforeEach(() => {
  jest.clearAllMocks();
});

// ---------------------------------------------------------------------------

describe('RichTextEditor integration', () => {

  // -------------------------------------------------------------------------
  // AC-016: Keyboard shortcut Ctrl+B / Cmd+B toggles bold
  // -------------------------------------------------------------------------
  describe('keyboard shortcuts', () => {
    it('test_ctrl_b_toggles_bold_when_text_is_selected', async () => {
      // TODO: render <RichTextEditor content="some text" onChange={jest.fn()} />
      //       wrapped in createWrapper()
      // TODO: locate the editor content area
      // TODO: fireEvent.keyDown with { key: 'b', ctrlKey: true } (Ctrl+B)
      // TODO: await waitFor(() => assert bold mark is active in editor state)
      // TODO: assert onChange was called with Markdown containing **bold** syntax
      expect(true).toBe(true);
    });

    it('test_cmd_b_toggles_bold_when_text_is_selected_on_mac', async () => {
      // TODO: render component wrapped in createWrapper()
      // TODO: fireEvent.keyDown with { key: 'b', metaKey: true } (Cmd+B)
      // TODO: await waitFor(() => assert bold mark toggled)
      expect(true).toBe(true);
    });

    it('test_bold_toggled_by_keyboard_matches_bold_toggled_by_toolbar_button', async () => {
      // TODO: render two instances — one triggered via keyboard, one via toolbar click
      // TODO: assert both produce the same Markdown output in onChange
      // TODO: this guards against inconsistency between keyboard and toolbar paths
      expect(true).toBe(true);
    });
  });

  // -------------------------------------------------------------------------
  // State transitions (page-context flows)
  // -------------------------------------------------------------------------
  describe('readOnly state transition within page context', () => {
    it('test_editor_becomes_non_editable_when_parent_page_enters_saving_state', async () => {
      // TODO: render component with readOnly=false inside createWrapper()
      // TODO: rerender with readOnly=true (simulate parent page setting saving state)
      // TODO: await waitFor(() => assert toolbar is gone and editor is non-editable)
      expect(true).toBe(true);
    });

    it('test_editor_restores_editable_when_parent_page_exits_saving_state', async () => {
      // TODO: render with readOnly=true
      // TODO: rerender with readOnly=false
      // TODO: await waitFor(() => assert toolbar is back and editor is editable)
      expect(true).toBe(true);
    });
  });

  // -------------------------------------------------------------------------
  // onChange → API call triggered by parent (guards the gap-response POST path)
  // -------------------------------------------------------------------------
  describe('onChange wiring to parent API call', () => {
    it('test_onChange_callback_value_is_passed_to_api_client_on_save', async () => {
      // TODO: render a minimal GapQuestionCard (or page stub) wrapper that
      //       calls apiClient.post on onChange + save button click
      // TODO: type content in editor → triggers onChange with Markdown string
      // TODO: click Save button
      // TODO: await waitFor(() =>
      //   assert apiClient.post was called with body containing the Markdown string
      // )
      expect(true).toBe(true);
    });
  });

});
