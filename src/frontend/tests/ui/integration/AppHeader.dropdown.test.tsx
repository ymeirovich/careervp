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

describe('FE-UI-004 — AppHeader dropdown click-outside (integration)', () => {
  beforeEach(() => {
    nextNavigationMocks.pathname = '/dashboard';
    nextNavigationMocks.push.mockReset();
    authMocks.signOut.mockClear();
  });

  it('closes the dropdown when clicking outside', () => {
    render(<AppHeader userName="Test User" />);

    fireEvent.click(screen.getByRole('button', { name: /test user/i }));
    expect(screen.getByRole('menu', { name: /account menu/i })).toBeInTheDocument();

    fireEvent.mouseDown(document.body);
    expect(screen.queryByRole('menu', { name: /account menu/i })).toBeNull();
  });
});

