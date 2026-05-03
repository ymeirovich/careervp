/**
 * Unit tests: Applications Table (Dashboard screen)
 * Spec: docs/frontend/spec-v4/01-applications-table.yaml
 *
 * These tests WILL FAIL until App.jsx implements:
 *   - All 6 table columns (Company, Position, Status, Date Applied, Match Score, Actions)
 *   - Empty state UI with "No applications yet" heading and CTA
 *   - "View Hub" action button per row navigating to hub screen
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeAll } from 'vitest';

// NOTE: App.jsx must be placed at src/frontend/canvas-app/App.jsx
// Update this import path once App.jsx is added to the repo.
// import App from '../../../canvas-app/App';

// ---------------------------------------------------------------------------
// Minimal stub app that simulates the App component interface
// Replace with the real import when App.jsx is available in the repo.
// ---------------------------------------------------------------------------
const CANVAS_APP_PATH = '../../../canvas-app/App';

let App: React.ComponentType<Record<string, never>>;

beforeAll(async () => {
  try {
    const mod = await import(CANVAS_APP_PATH);
    App = mod.default;
  } catch {
    // Expected to fail until file is placed — tests will handle this gracefully
    App = () => <div data-testid="app-not-found">App.jsx not found at expected path</div>;
  }
});

// ---------------------------------------------------------------------------
// Mock application data
// ---------------------------------------------------------------------------
const mockApplications = [
  {
    id: 'app-123',
    company: 'Acme Corp',
    position: 'Senior Engineer',
    status: 'Applied',
    dateApplied: '2025-01-15',
    matchScore: 87,
  },
  {
    id: 'app-456',
    company: 'TechCo',
    position: 'Product Manager',
    status: 'Interviewing',
    dateApplied: '2025-01-20',
    matchScore: 72,
  },
];

// ---------------------------------------------------------------------------
// APP_TABLE_01
// ---------------------------------------------------------------------------
describe('APP_TABLE_01 — Applications Table column headers', () => {
  it('renders all 6 required column headers', () => {
    render(<App />);

    // The app should show the dashboard (applications table) by default
    const companyHeader = screen.queryByRole('columnheader', { name: /company/i })
      ?? screen.queryByText(/company/i);
    const positionHeader = screen.queryByRole('columnheader', { name: /position/i })
      ?? screen.queryByText(/position/i);
    const statusHeader = screen.queryByRole('columnheader', { name: /status/i })
      ?? screen.queryByText(/status/i);
    const dateHeader = screen.queryByRole('columnheader', { name: /date/i })
      ?? screen.queryByText(/date applied/i);
    const scoreHeader = screen.queryByRole('columnheader', { name: /score/i })
      ?? screen.queryByText(/match score/i);
    const actionsHeader = screen.queryByRole('columnheader', { name: /actions/i })
      ?? screen.queryByText(/^actions$/i);

    expect(companyHeader, 'Company column header').not.toBeNull();
    expect(positionHeader, 'Position column header').not.toBeNull();
    expect(statusHeader, 'Status column header').not.toBeNull();
    expect(dateHeader, 'Date Applied column header').not.toBeNull();
    expect(scoreHeader, 'Match Score column header').not.toBeNull();
    expect(actionsHeader, 'Actions column header').not.toBeNull();
  });
});

// ---------------------------------------------------------------------------
// APP_TABLE_02
// ---------------------------------------------------------------------------
describe('APP_TABLE_02 — Empty state', () => {
  it('shows empty state heading and CTA when applications list is empty', () => {
    render(<App />);

    // When Firestore returns empty docs, app should show empty state
    const emptyHeading = screen.queryByText(/no applications yet/i);
    const emptyCta = screen.queryByRole('button', { name: /add your first application/i })
      ?? screen.queryByText(/add your first application/i);

    expect(emptyHeading, '"No applications yet" heading').not.toBeNull();
    expect(emptyCta, '"Add Your First Application" CTA').not.toBeNull();
  });
});

// ---------------------------------------------------------------------------
// APP_TABLE_03
// ---------------------------------------------------------------------------
describe('APP_TABLE_03 — View Hub navigation', () => {
  it('View Hub button navigates to hub screen with correct application context', () => {
    render(<App />);

    // Find and click the View Hub button on first row
    const viewHubButton = screen.queryByRole('button', { name: /view hub/i })
      ?? screen.queryByText(/view hub/i);

    expect(viewHubButton, '"View Hub" action button').not.toBeNull();

    if (viewHubButton) {
      fireEvent.click(viewHubButton);

      // After clicking, hub screen should be visible
      const hubHeading = screen.queryByText(/application hub/i)
        ?? screen.queryByTestId('hub-screen');
      expect(hubHeading, 'Hub screen after navigation').not.toBeNull();
    }
  });
});
