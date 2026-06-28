'use client';

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';

import { useAuth } from '../../contexts/AuthContext';

const PAGE_TITLES: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/applications': 'Applications',
  '/cv-center': 'Base CVs',
  '/tailored-cvs': 'Tailored CVs',
  '/cover-letters': 'Cover Letters',
  '/billing': 'Billing',
  '/settings': 'Settings',
};

interface AppHeaderProps {
  creditsUsed?: number;
  creditsTotal?: number;
  isUnlimited?: boolean;
  userName?: string;
}

export function AppHeader({ creditsUsed = 0, creditsTotal = 3, isUnlimited = false, userName = '' }: AppHeaderProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { signOut } = useAuth();

  const pageTitle = useMemo(() => {
    if (PAGE_TITLES[pathname]) return PAGE_TITLES[pathname];

    const segments = pathname.split('/').filter(Boolean);
    if (segments.length === 2 && segments[0] === 'applications') return 'Job Application Hub';

    return 'CareerVP';
  }, [pathname]);

  const creditsLabel = isUnlimited
    ? 'Unlimited'
    : `Credits: ${creditsUsed} / ${creditsTotal}`;

  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement | null>(null);
  const menuItemRefs = useRef<Array<HTMLButtonElement | null>>([]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (!isDropdownOpen) return;
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsDropdownOpen(false);
      }
    }

    function handleKeyDown(e: KeyboardEvent) {
      if (!isDropdownOpen) return;
      if (e.key === 'Escape') {
        setIsDropdownOpen(false);
        return;
      }

      if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp' && e.key !== 'Home' && e.key !== 'End') return;
      e.preventDefault();

      const items = menuItemRefs.current.filter(Boolean) as HTMLButtonElement[];
      if (items.length === 0) return;

      const activeIndex = items.findIndex((el) => el === document.activeElement);
      const safeIndex = activeIndex >= 0 ? activeIndex : 0;

      if (e.key === 'Home') { items[0].focus(); return; }
      if (e.key === 'End') { items[items.length - 1].focus(); return; }

      const delta = e.key === 'ArrowDown' ? 1 : -1;
      const nextIndex = (safeIndex + delta + items.length) % items.length;
      items[nextIndex].focus();
    }

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isDropdownOpen]);

  useEffect(() => {
    if (!isDropdownOpen) return;
    const id = requestAnimationFrame(() => {
      menuItemRefs.current[0]?.focus();
    });
    return () => cancelAnimationFrame(id);
  }, [isDropdownOpen]);

  function closeDropdown() {
    setIsDropdownOpen(false);
  }

  function handleHelp() {
    closeDropdown();
    router.push('/settings');
  }

  function handleUpgrade() {
    closeDropdown();
    router.push('/billing');
  }

  async function handleSignOut() {
    closeDropdown();
    await signOut();
  }

  return (
    <header className="flex items-center justify-between h-20 px-6 bg-card border-b border-border-default shrink-0">
      <h1 className="font-bold text-text-primary text-2xl tracking-tight">{pageTitle}</h1>

      <div className="flex items-center gap-4">
        <span className="text-text-muted text-sm font-medium" data-testid="credits-label">
          {creditsLabel}
        </span>
        <div className="relative" ref={dropdownRef}>
          <button
            type="button"
            aria-haspopup="menu"
            aria-expanded={isDropdownOpen}
            onClick={() => setIsDropdownOpen((o) => !o)}
            className="flex items-center gap-2 bg-surface-subtle border border-border-strong rounded-xl px-3 py-1.5 text-text-primary text-base font-medium hover:bg-surface-selected transition-colors"
          >
            {userName || 'Account'}
            <svg className="w-4 h-4" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
              <path d="M4 6l4 4 4-4" stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>

          {isDropdownOpen && (
            <div
              role="menu"
              aria-label="Account menu"
              className="absolute right-0 mt-2 w-56 rounded-xl border border-border-default bg-card shadow-md z-50 p-1"
            >
              <button
                type="button"
                role="menuitem"
                ref={(el) => { menuItemRefs.current[0] = el; }}
                onClick={handleHelp}
                className="w-full text-left px-3 py-2 text-sm text-text-primary hover:bg-surface-subtle rounded-lg"
              >
                Help
              </button>
              <button
                type="button"
                role="menuitem"
                ref={(el) => { menuItemRefs.current[1] = el; }}
                onClick={() => { void handleSignOut(); }}
                className="w-full text-left px-3 py-2 text-sm text-state-error hover:bg-surface-subtle rounded-lg"
              >
                Log out
              </button>
              <div className="pt-1">
                <button
                  type="button"
                  role="menuitem"
                  ref={(el) => { menuItemRefs.current[2] = el; }}
                  onClick={handleUpgrade}
                  className="w-full inline-flex items-center justify-center bg-primary-action text-white hover:opacity-90 font-bold px-3 py-1.5 text-sm rounded-lg"
                >
                  Upgrade
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
