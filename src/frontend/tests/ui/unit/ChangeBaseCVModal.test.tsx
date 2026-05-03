/**
 * Unit tests: ChangeBaseCVModal
 * Spec: docs/frontend/spec-v4/03-change-base-cv-modal.yaml
 *
 * These tests WILL FAIL until App.jsx correctly implements:
 *   - isOpen guard (null return when false)
 *   - showChoices=true branch with choice buttons and OR divider
 *   - Upload button disabled until file selected
 *   - onClose callback on X button
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeAll } from 'vitest';
import type { FC } from 'react';

// Attempt to import the named ChangeBaseCVModal export.
// If App.jsx does not export it, fall back to rendering the full app and
// triggering the modal through the UI.
const CANVAS_APP_PATH = '../../../canvas-app/App';

interface ChangeBaseCVModalProps {
  isOpen: boolean;
  onClose: () => void;
  showChoices?: boolean;
}

let ChangeBaseCVModal: FC<ChangeBaseCVModalProps> | null = null;

beforeAll(async () => {
  try {
    const mod = await import(CANVAS_APP_PATH);
    // Named export preferred; fall back to a modal-wrapper approach
    ChangeBaseCVModal = mod.ChangeBaseCVModal ?? null;
  } catch {
    ChangeBaseCVModal = null;
  }
});

function renderModal(props: ChangeBaseCVModalProps) {
  if (!ChangeBaseCVModal) {
    // If modal is not exported separately, render a placeholder that will fail
    return render(
      <div data-testid="modal-not-exported">
        ChangeBaseCVModal is not exported from App.jsx
      </div>
    );
  }
  return render(<ChangeBaseCVModal {...props} />);
}

// ---------------------------------------------------------------------------
// MODAL_01
// ---------------------------------------------------------------------------
describe('MODAL_01 — does not render when closed', () => {
  it('does not render when isOpen is false', () => {
    const onClose = vi.fn();
    renderModal({ isOpen: false, onClose, showChoices: false });

    const modal = screen.queryByRole('dialog')
      ?? screen.queryByText(/upload base cv/i)
      ?? screen.queryByText(/choose base cv/i);

    expect(modal, 'modal should not be in DOM when isOpen=false').toBeNull();
  });
});

// ---------------------------------------------------------------------------
// MODAL_02
// ---------------------------------------------------------------------------
describe('MODAL_02 — upload-only mode', () => {
  it("renders with title 'Upload Base CV' and no choice buttons when showChoices=false", () => {
    const onClose = vi.fn();
    renderModal({ isOpen: true, onClose, showChoices: false });

    const heading = screen.queryByRole('heading', { name: /upload base cv/i })
      ?? screen.queryByText(/upload base cv/i);

    expect(heading, '"Upload Base CV" heading').not.toBeNull();

    const selectUploaded = screen.queryByRole('button', { name: /select uploaded cv/i });
    const selectGenerated = screen.queryByRole('button', { name: /select generated cv/i });

    expect(selectUploaded, '"Select Uploaded CV" should NOT be present').toBeNull();
    expect(selectGenerated, '"Select Generated CV" should NOT be present').toBeNull();
  });
});

// ---------------------------------------------------------------------------
// MODAL_03
// ---------------------------------------------------------------------------
describe('MODAL_03 — choice mode', () => {
  it("renders 'Choose Base CV' title with two selection buttons when showChoices=true", () => {
    const onClose = vi.fn();
    renderModal({ isOpen: true, onClose, showChoices: true });

    const heading = screen.queryByRole('heading', { name: /choose base cv/i })
      ?? screen.queryByText(/choose base cv/i);

    expect(heading, '"Choose Base CV" heading').not.toBeNull();

    const selectUploaded = screen.queryByRole('button', { name: /select uploaded cv/i });
    const selectGenerated = screen.queryByRole('button', { name: /select generated cv/i });
    const orDivider = screen.queryByText(/^or$/i);

    expect(selectUploaded, '"Select Uploaded CV" button').not.toBeNull();
    expect(selectGenerated, '"Select Generated CV" button').not.toBeNull();
    expect(orDivider, 'OR divider').not.toBeNull();
  });
});

// ---------------------------------------------------------------------------
// MODAL_04
// ---------------------------------------------------------------------------
describe('MODAL_04 — Upload button disabled before file selection', () => {
  it('Upload button is disabled when no file is selected', () => {
    const onClose = vi.fn();
    renderModal({ isOpen: true, onClose, showChoices: false });

    const uploadBtn = screen.queryByRole('button', { name: /^upload$/i });

    expect(uploadBtn, 'Upload button').not.toBeNull();

    if (uploadBtn) {
      expect(
        (uploadBtn as HTMLButtonElement).disabled,
        'Upload button should be disabled before file is chosen'
      ).toBe(true);
    }
  });
});

// ---------------------------------------------------------------------------
// MODAL_05
// ---------------------------------------------------------------------------
describe('MODAL_05 — Upload button enables after file selection', () => {
  it('Upload button enables and filename appears after file is selected', () => {
    const onClose = vi.fn();
    renderModal({ isOpen: true, onClose, showChoices: false });

    const fileInput = screen.queryByRole('button', { name: /choose file/i })?.closest('form')
      ?.querySelector('input[type="file"]')
      ?? document.querySelector('input[type="file"]') as HTMLInputElement | null;

    if (fileInput) {
      const testFile = new File(['cv content'], 'cv.pdf', { type: 'application/pdf' });
      fireEvent.change(fileInput, { target: { files: [testFile] } });

      const filename = screen.queryByText(/cv\.pdf/i);
      expect(filename, 'Filename "cv.pdf" should appear').not.toBeNull();

      const uploadBtn = screen.queryByRole('button', { name: /^upload$/i });
      if (uploadBtn) {
        expect(
          (uploadBtn as HTMLButtonElement).disabled,
          'Upload button should be enabled after file selection'
        ).toBe(false);
      }
    } else {
      // If file input not found, the test should fail
      expect(fileInput, 'file input element should be present').not.toBeNull();
    }
  });
});

// ---------------------------------------------------------------------------
// MODAL_06
// ---------------------------------------------------------------------------
describe('MODAL_06 — Close button calls onClose', () => {
  it('X button calls onClose callback when clicked', () => {
    const onClose = vi.fn();
    renderModal({ isOpen: true, onClose, showChoices: false });

    // Look for close button: X icon button, "Cancel" link, or aria-label="close"
    const closeBtn = screen.queryByRole('button', { name: /close/i })
      ?? screen.queryByRole('button', { name: /×/i })
      ?? screen.queryByLabelText(/close/i)
      ?? document.querySelector('button[class*="absolute"]') as Element | null;

    // Also try the Cancel text link
    const cancelLink = screen.queryByText(/^cancel$/i);

    const trigger = closeBtn ?? cancelLink;
    expect(trigger, 'Close button or Cancel link').not.toBeNull();

    if (trigger) {
      fireEvent.click(trigger);
      expect(onClose, 'onClose should be called once').toHaveBeenCalledTimes(1);
    }
  });
});
