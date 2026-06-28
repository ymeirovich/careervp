import '../../vitest-setup';
import '../setup';

import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { HubLayout } from '../../../components/layout/HubLayout';

describe('FE-UI-005 — HubLayout job detail header slot + grid defaults', () => {
  it('renders children normally when jobDetailHeaderSlot is not provided (backward compatible)', () => {
    render(
      <HubLayout hubStatus="INIT">
        <div data-testid="hub-children">Children</div>
      </HubLayout>
    );

    expect(screen.getByTestId('hub-children')).toBeInTheDocument();
    expect(screen.queryByTestId('job-detail-header')).toBeNull();
  });

  it('renders jobDetailHeaderSlot above banners and children when provided', () => {
    render(
      <HubLayout
        hubStatus="PROCESSING_BLOCKED"
        jobDetailHeaderSlot={<div data-testid="job-detail-header">Job Header</div>}
      >
        <div data-testid="hub-children">Children</div>
      </HubLayout>
    );

    const header = screen.getByTestId('job-detail-header');
    const banner = screen.getByTestId('hub-blocked-banner');
    const children = screen.getByTestId('hub-children');

    expect(header).toBeInTheDocument();

    // Order contract: header first, then banners, then children.
    expect(header.compareDocumentPosition(banner) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(banner.compareDocumentPosition(children) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });
});

