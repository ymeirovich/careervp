import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const nextNavigationMocks = vi.hoisted(() => ({
  pathname: '/dashboard',
  push: vi.fn(),
}));

const authMocks = vi.hoisted(() => ({
  signOut: vi.fn().mockResolvedValue(undefined),
}));

vi.mock('next/navigation', () => ({
  usePathname: () => nextNavigationMocks.pathname,
  useRouter: () => ({ push: nextNavigationMocks.push }),
}));

vi.mock('../../../contexts/AuthContext', () => ({
  useAuth: () => ({ signOut: authMocks.signOut }),
}));

import { AppHeader } from '../../../components/layout/AppHeader';

describe('FE-UI-004 — AppHeader credits + account dropdown', () => {
  beforeEach(() => {
    nextNavigationMocks.pathname = '/dashboard';
    nextNavigationMocks.push.mockReset();
    authMocks.signOut.mockClear();
  });

  it('renders credits as "Credits: 1 / 3" (not "{N} / {N} applications")', () => {
    render(<AppHeader creditsUsed={1} creditsTotal={3} isUnlimited={false} userName="Test User" />);
    expect(screen.getByTestId('credits-label')).toHaveTextContent('Credits: 1 / 3');
    expect(screen.queryByText(/applications/i)).toBeNull();
  });

  it('renders credits as "Credits: 0 / 3"', () => {
    render(<AppHeader creditsUsed={0} creditsTotal={3} isUnlimited={false} />);
    expect(screen.getByTestId('credits-label')).toHaveTextContent('Credits: 0 / 3');
  });

  it('renders "Unlimited" when isUnlimited=true', () => {
    render(<AppHeader isUnlimited />);
    expect(screen.getByTestId('credits-label')).toHaveTextContent('Unlimited');
    expect(screen.queryByText(/credits:/i)).toBeNull();
  });

  it('opens dropdown with Help / Log out / Upgrade items', () => {
    render(<AppHeader userName="Test User" />);

    fireEvent.click(screen.getByRole('button', { name: /test user/i }));

    expect(screen.getByRole('menu', { name: /account menu/i })).toBeInTheDocument();
    expect(screen.getByRole('menuitem', { name: 'Help' })).toBeInTheDocument();
    expect(screen.getByRole('menuitem', { name: 'Log out' })).toBeInTheDocument();
    expect(screen.getByRole('menuitem', { name: 'Upgrade' })).toBeInTheDocument();
  });

  it('styles Log out as red text and Upgrade as orange filled', () => {
    render(<AppHeader userName="Test User" />);

    fireEvent.click(screen.getByRole('button', { name: /test user/i }));

    expect(screen.getByRole('menuitem', { name: 'Log out' })).toHaveClass('text-state-error');

    const upgrade = screen.getByRole('menuitem', { name: 'Upgrade' });
    expect(upgrade).toHaveClass('bg-primary-action');
    expect(upgrade).toHaveClass('text-white');
  });

  it('navigates to /billing when Upgrade is clicked', () => {
    render(<AppHeader userName="Test User" />);

    fireEvent.click(screen.getByRole('button', { name: /test user/i }));
    fireEvent.click(screen.getByRole('menuitem', { name: 'Upgrade' }));

    expect(nextNavigationMocks.push).toHaveBeenCalledWith('/billing');
  });

  it('maps /cv-center to "Base CVs" title', () => {
    nextNavigationMocks.pathname = '/cv-center';
    render(<AppHeader />);
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Base CVs');
  });

  it('maps /tailored-cvs to "Tailored CVs" title', () => {
    nextNavigationMocks.pathname = '/tailored-cvs';
    render(<AppHeader />);
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Tailored CVs');
  });

  it('maps /cover-letters to "Cover Letters" title', () => {
    nextNavigationMocks.pathname = '/cover-letters';
    render(<AppHeader />);
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Cover Letters');
  });

  it('maps /applications/123 to "Job Application Hub" title', () => {
    nextNavigationMocks.pathname = '/applications/123';
    render(<AppHeader />);
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Job Application Hub');
  });
});

