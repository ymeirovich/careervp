import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const nextNavigationMocks = vi.hoisted(() => ({
  pathname: '/dashboard',
}));

vi.mock('next/navigation', () => ({
  usePathname: () => nextNavigationMocks.pathname,
}));

vi.mock('next/link', () => ({
  default: ({
    href,
    children,
    ...rest
  }: {
    href: string;
    children: React.ReactNode;
    className?: string;
    onClick?: () => void;
    'aria-label'?: string;
  }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

import { AppSidebar } from '../../../components/layout/AppSidebar';

function setViewportWidth(width: number) {
  Object.defineProperty(window, 'innerWidth', {
    configurable: true,
    value: width,
    writable: true,
  });
  window.dispatchEvent(new Event('resize'));
}

describe('FE-UI-003 — AppSidebar nav restructure', () => {
  beforeEach(() => {
    nextNavigationMocks.pathname = '/dashboard';
    setViewportWidth(1200);
  });

  it('renders exactly 7 nav items with labels in order (desktop)', () => {
    render(<AppSidebar />);

    const links = screen.getAllByRole('link');
    expect(links).toHaveLength(7);

    const labels = links.map((l) => l.textContent?.trim());
    expect(labels).toEqual([
      'Dashboard',
      'Applications',
      'Base CVs',
      'Tailored CVs',
      'Cover Letters',
      'Billing',
      'Settings',
    ]);

    expect(screen.queryByText(/cv center/i)).toBeNull();
  });

  it('wires Base CVs, Tailored CVs, Cover Letters routes and icons', () => {
    render(<AppSidebar />);

    const base = screen.getByRole('link', { name: 'Base CVs' });
    expect(base).toHaveAttribute('href', '/cv-center');
    expect(base.querySelector('svg.lucide-file-text')).not.toBeNull();

    const tailored = screen.getByRole('link', { name: 'Tailored CVs' });
    expect(tailored).toHaveAttribute('href', '/tailored-cvs');
    expect(tailored.querySelector('svg.lucide-file-pen')).not.toBeNull();

    const coverLetters = screen.getByRole('link', { name: 'Cover Letters' });
    expect(coverLetters).toHaveAttribute('href', '/cover-letters');
    expect(coverLetters.querySelector('svg.lucide-mail')).not.toBeNull();
  });

  it('applies active state styling for /applications/123 to Applications', () => {
    nextNavigationMocks.pathname = '/applications/123';

    render(<AppSidebar />);

    const applications = screen.getByRole('link', { name: 'Applications' });
    expect(applications).toHaveClass('border-primary-action');
    expect(applications.querySelector('svg.text-primary-action')).not.toBeNull();

    const activeLinks = screen
      .getAllByRole('link')
      .filter((l) => l.className.includes('border-primary-action'));

    expect(activeLinks).toHaveLength(1);
    expect(activeLinks[0]).toBe(applications);
  });

  it('renders tablet mode as an icon-only rail (no text labels)', () => {
    setViewportWidth(800);

    render(<AppSidebar />);

    expect(screen.getAllByRole('link')).toHaveLength(7);
    expect(screen.queryByText('Dashboard')).toBeNull();
    expect(screen.queryByText('Applications')).toBeNull();
    expect(screen.getByRole('link', { name: 'Dashboard' })).toBeInTheDocument();

    const aside = document.querySelector('aside');
    expect(aside).not.toBeNull();
    expect(aside).toHaveClass('w-[72px]');
  });

  it('renders mobile mode as a hamburger-triggered overlay drawer', () => {
    setViewportWidth(500);

    render(<AppSidebar />);

    const toggle = screen.getByRole('button', { name: /open sidebar/i });
    expect(toggle).toBeInTheDocument();
    expect(screen.queryAllByRole('link')).toHaveLength(0);

    fireEvent.click(toggle);

    expect(screen.getAllByRole('link')).toHaveLength(7);
    expect(screen.getByRole('link', { name: 'Dashboard' })).toBeInTheDocument();

    const overlayClose = screen.getByRole('button', { name: /close sidebar overlay/i });
    fireEvent.click(overlayClose);

    expect(screen.queryAllByRole('link')).toHaveLength(0);
  });
});
