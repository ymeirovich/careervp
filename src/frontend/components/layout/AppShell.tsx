import React from 'react';
import { AppSidebar } from './AppSidebar';
import { AppHeader } from './AppHeader';

export interface UserProfile {
  name: string;
  email: string;
  creditsUsed?: number;
  creditsTotal?: number;
  isUnlimited?: boolean;
}

export interface AppShellProps {
  user: UserProfile;
  children: React.ReactNode;
}

export function AppShell({ user, children }: AppShellProps) {
  return (
    <div className="flex h-screen overflow-hidden bg-page-bg">
      <AppSidebar />
      <div className="flex flex-col flex-1 overflow-hidden">
        <AppHeader
          userName={user.name}
          creditsUsed={user.creditsUsed ?? 0}
          creditsTotal={user.creditsTotal ?? 3}
          isUnlimited={user.isUnlimited ?? false}
        />
        <main className="flex-1 overflow-y-auto p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
