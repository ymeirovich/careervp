'use client';

import React from 'react';
import { usePathname } from 'next/navigation';

const PAGE_TITLES: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/applications': 'Applications',
  '/cv-center': 'CV Center',
  '/billing': 'Billing',
  '/settings': 'Settings',
};

interface AppHeaderProps {
  creditsUsed?: number;
  creditsTotal?: number;
  userName?: string;
}

export function AppHeader({ creditsUsed = 0, creditsTotal = 3, userName = '' }: AppHeaderProps) {
  const pathname = usePathname();
  const pageTitle = PAGE_TITLES[pathname] ?? 'CareerVP';

  return (
    <header className="flex items-center justify-between h-20 px-6 bg-card border-b border-border-default shrink-0">
      <h1 className="font-bold text-text-primary text-2xl tracking-tight">{pageTitle}</h1>

      <div className="flex items-center gap-4">
        <span className="text-text-primary text-base font-medium">
          Credits: {creditsUsed} / {creditsTotal}
        </span>
        <button className="flex items-center gap-2 bg-surface-subtle border border-border-strong rounded-xl px-3 py-1.5 text-text-primary text-base font-medium hover:bg-surface-selected transition-colors">
          {userName || 'Account'}
          <svg className="w-4 h-4" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
            <path d="M4 6l4 4 4-4" stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </div>
    </header>
  );
}
