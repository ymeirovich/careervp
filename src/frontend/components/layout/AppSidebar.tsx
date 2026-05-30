'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  Briefcase,
  FileText,
  FilePen,
  Mail,
  CreditCard,
  Settings as SettingsIcon,
  Menu,
  X,
  type LucideIcon,
} from 'lucide-react';

const NAV_ITEMS: { href: string; label: string; icon: LucideIcon }[] = [
  { href: '/dashboard',     label: 'Dashboard',     icon: LayoutDashboard },
  { href: '/applications',  label: 'Applications',  icon: Briefcase },
  { href: '/cv-center',     label: 'Base CVs',      icon: FileText },
  { href: '/tailored-cvs',  label: 'Tailored CVs',  icon: FilePen },
  { href: '/cover-letters', label: 'Cover Letters', icon: Mail },
  { href: '/billing',       label: 'Billing',       icon: CreditCard },
  { href: '/settings',      label: 'Settings',      icon: SettingsIcon },
];

type SidebarViewportMode = 'mobile' | 'tablet' | 'desktop';

function getSidebarViewportMode(viewportWidth: number): SidebarViewportMode {
  if (viewportWidth < 768) return 'mobile';
  if (viewportWidth < 1024) return 'tablet';
  return 'desktop';
}

export function AppSidebar() {
  const pathname = usePathname();
  const [viewportMode, setViewportMode] = React.useState<SidebarViewportMode>(() => {
    if (typeof window === 'undefined') return 'desktop';
    return getSidebarViewportMode(window.innerWidth);
  });
  const [isMobileOpen, setIsMobileOpen] = React.useState(false);

  React.useEffect(() => {
    const handleResize = () => {
      setViewportMode(getSidebarViewportMode(window.innerWidth));
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  React.useEffect(() => {
    if (viewportMode !== 'mobile') setIsMobileOpen(false);
  }, [viewportMode]);

  const renderNav = (options: { showLabels: boolean; onNavigate?: () => void }) => {
    const { showLabels, onNavigate } = options;

    return (
      <nav className="flex flex-col gap-1 p-3 pt-4">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const isActive = pathname === href || pathname.startsWith(href + '/');
          const link_classes = [
            'group flex items-center gap-3 rounded-lg text-base transition-colors border-l-[3px]',
            showLabels ? 'px-4 py-3 justify-start' : 'px-3 py-3 justify-center',
            isActive
              ? 'bg-surface-selected text-text-primary font-bold border-primary-action'
              : 'text-text-muted font-medium border-transparent hover:bg-surface-subtle hover:text-text-primary',
          ].join(' ');

          const icon_classes = [
            'shrink-0',
            isActive ? 'text-primary-action' : 'text-text-muted group-hover:text-text-primary',
          ].join(' ');

          return (
            <Link
              key={href}
              href={href}
              aria-label={showLabels ? undefined : label}
              className={link_classes}
              onClick={() => onNavigate?.()}
            >
              <Icon size={18} className={icon_classes} aria-hidden="true" />
              {showLabels ? <span>{label}</span> : null}
            </Link>
          );
        })}
      </nav>
    );
  };

  const renderDesktopShell = (options: { collapsed: boolean }) => {
    const { collapsed } = options;

    return (
      <aside
        className={[
          'flex flex-col h-full bg-card border-r border-border-default shrink-0',
          collapsed ? 'w-[72px]' : 'w-[220px]',
        ].join(' ')}
      >
        <div
          className={[
            'flex items-center gap-3 h-20 border-b border-border-default',
            collapsed ? 'px-3 justify-center' : 'px-6 justify-start',
          ].join(' ')}
        >
          <div className="w-8 h-8 bg-primary-action rounded-md flex items-center justify-center">
            <span className="text-white font-bold text-xs">CV</span>
          </div>
          {collapsed ? null : <span className="font-bold text-text-primary text-2xl tracking-tight">CareerVP</span>}
        </div>

        {renderNav({ showLabels: !collapsed })}
      </aside>
    );
  };

  if (viewportMode === 'mobile') {
    return (
      <>
        <button
          type="button"
          aria-label={isMobileOpen ? 'Close sidebar' : 'Open sidebar'}
          className="fixed top-5 left-4 z-50 flex items-center justify-center w-10 h-10 rounded-xl bg-card border border-border-default text-text-primary hover:bg-surface-selected transition-colors"
          onClick={() => setIsMobileOpen((prev) => !prev)}
        >
          {isMobileOpen ? <X size={18} aria-hidden="true" /> : <Menu size={18} aria-hidden="true" />}
        </button>

        {isMobileOpen ? (
          <div className="fixed inset-0 z-40">
            <button
              type="button"
              aria-label="Close sidebar overlay"
              className="absolute inset-0 bg-black/30"
              onClick={() => setIsMobileOpen(false)}
            />

            <aside className="absolute left-0 top-0 h-full w-[220px] bg-card border-r border-border-default">
              <div className="flex items-center gap-3 px-6 h-20 border-b border-border-default">
                <div className="w-8 h-8 bg-primary-action rounded-md flex items-center justify-center">
                  <span className="text-white font-bold text-xs">CV</span>
                </div>
                <span className="font-bold text-text-primary text-2xl tracking-tight">CareerVP</span>
              </div>

              {renderNav({ showLabels: true, onNavigate: () => setIsMobileOpen(false) })}
            </aside>
          </div>
        ) : null}
      </>
    );
  }

  return renderDesktopShell({ collapsed: viewportMode === 'tablet' });
}
