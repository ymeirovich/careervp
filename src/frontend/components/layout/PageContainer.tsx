import React from 'react';

export interface PageContainerProps {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
}

export function PageContainer({ title, subtitle, actions, children }: PageContainerProps) {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="font-bold text-text-primary text-2xl">{title}</h1>
          {subtitle && <p className="text-text-muted text-base mt-1">{subtitle}</p>}
        </div>
        {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
      </div>
      {children}
    </div>
  );
}
