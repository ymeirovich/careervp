import React from 'react';
import { afterEach, describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StatsRow } from '../../../components/dashboard/StatsRow';

describe('FE-UI-009 — StatsRow pill radius and loading skeleton', () => {
  afterEach(() => {
    document.documentElement.lang = 'en';
  });

  it('renders data pills with rounded-xl styling', () => {
    render(<StatsRow plan="Monthly Plan" creditsUsed={1} creditsTotal={3} isActive />);

    expect(screen.getByText('Plan:').parentElement).toHaveClass('rounded-xl');
    expect(screen.getByText('Credits Remaining:').parentElement).toHaveClass('rounded-xl');
    expect(screen.getByText('Status:').parentElement).toHaveClass('rounded-xl');
  });

  it('renders three animate-pulse skeleton pills when loading', () => {
    render(<StatsRow plan="Monthly Plan" creditsUsed={1} creditsTotal={3} isActive isLoading />);

    const skeletons = screen.getAllByTestId('stats-pill-skeleton');
    expect(skeletons).toHaveLength(3);

    for (const skeleton of skeletons) {
      expect(skeleton).toHaveClass('rounded-xl');
      expect(skeleton.querySelectorAll('.animate-pulse')).toHaveLength(2);
    }
  });

  it('hides stats text when loading', () => {
    render(<StatsRow plan="Monthly Plan" creditsUsed={1} creditsTotal={3} isActive isLoading />);

    expect(screen.queryByText('Plan:')).not.toBeInTheDocument();
    expect(screen.queryByText('Credits Remaining:')).not.toBeInTheDocument();
    expect(screen.queryByText('Status:')).not.toBeInTheDocument();
    expect(screen.queryByText('Monthly Plan')).not.toBeInTheDocument();
    expect(screen.queryByText('1 / 3')).not.toBeInTheDocument();
    expect(screen.queryByText('Active')).not.toBeInTheDocument();
  });

  it('renders existing Hebrew labels without new keys when locale is he', () => {
    document.documentElement.lang = 'he';

    render(<StatsRow plan="תוכנית חודשית" creditsUsed={1} creditsTotal={3} isActive={false} />);

    expect(screen.getByText('תוכנית:')).toBeInTheDocument();
    expect(screen.getByText('יתרת קרדיטים:')).toBeInTheDocument();
    expect(screen.getByText('סטטוס:')).toBeInTheDocument();
    expect(screen.getByText('לא פעיל')).toBeInTheDocument();
  });
});
