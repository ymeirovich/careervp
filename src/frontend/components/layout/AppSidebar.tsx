'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

const NAV_ITEMS = [
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/applications', label: 'Applications' },
  { href: '/cv-center', label: 'CV Center' },
  { href: '/billing', label: 'Billing' },
  { href: '/settings', label: 'Settings' },
];

export function AppSidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex flex-col w-[220px] h-full bg-card border-r border-border-default shrink-0">
      <div className="flex items-center gap-3 px-6 h-20 border-b border-border-default">
        <div className="w-8 h-8 bg-primary-action rounded-md flex items-center justify-center">
          <span className="text-white font-bold text-xs">CV</span>
        </div>
        <span className="font-bold text-text-primary text-2xl tracking-tight">CareerVP</span>
      </div>

      <nav className="flex flex-col gap-1 p-3 pt-4">
        {NAV_ITEMS.map(({ href, label }) => {
          const isActive = pathname === href || pathname.startsWith(href + '/');
          return (
            <Link
              key={href}
              href={href}
              className={`
                flex items-center gap-3 px-4 py-3 rounded-lg text-base font-bold transition-colors
                ${isActive
                  ? 'bg-surface-selected text-text-primary'
                  : 'text-text-primary hover:bg-surface-subtle'
                }
              `}
            >
              {label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
