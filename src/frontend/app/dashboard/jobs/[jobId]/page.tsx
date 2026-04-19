'use client';

import React, { Suspense } from 'react';
import { keepPreviousData, useQueryClient } from '@tanstack/react-query';
import { useApplicationHub } from '../../../../hooks/useApplicationHub';
import { ModuleCard } from '../../../../components/ModuleCard/ModuleCard';
import { queryKeys } from '../../../../api/queryKeys';
import { apiClient } from '../../../../api/client';
import type { ModuleType } from '../../../../types/enums';
import type { RawApplicationData } from '../../../../types/hub-state';

const MODULE_ORDER: ModuleType[] = [
  'vpr',
  'tailoredCV',
  'coverLetter',
  'interviewPrep',
  'gapAnalysis',
  'companyResearch',
  'baseCV',
];

function ModuleCardSkeleton() {
  return (
    <div className="bg-card border border-border-default rounded-xl p-4 flex flex-col gap-3 animate-pulse">
      <div className="h-4 w-2/3 bg-border-default rounded" />
      <div className="h-3 w-1/2 bg-border-default rounded" />
      <div className="h-3 w-1/3 bg-border-default rounded mt-1" />
    </div>
  );
}

function ModuleGrid({ jobId }: { jobId: string }) {
  const { hubState, isLoading } = useApplicationHub(jobId);

  if (isLoading || !hubState) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {MODULE_ORDER.map((m) => (
          <ModuleCardSkeleton key={m} />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {MODULE_ORDER.map((moduleType) => {
        const mod = hubState.modules[moduleType];
        return (
          <ModuleCard
            key={moduleType}
            module={moduleType}
            state={mod.status}
            title={mod.title}
            subtitle={mod.subtitle}
            meta={mod.meta}
            warningText={mod.warningText}
            progressText={mod.progressText ?? undefined}
          />
        );
      })}
    </div>
  );
}

function useApplicationPrefetch() {
  const queryClient = useQueryClient();

  return (jobId: string) => {
    void queryClient.prefetchQuery({
      queryKey: queryKeys.applications.detail(jobId),
      queryFn: async () => {
        const res = await apiClient.get<RawApplicationData>(`/applications/${jobId}`);
        return res.data;
      },
      staleTime: 30_000,
    });
  };
}

export default function JobPage({ params }: { params: { jobId: string } }) {
  const { jobId } = params;
  const prefetchApplication = useApplicationPrefetch();

  return (
    <div
      className="flex flex-col gap-6 p-6"
      onMouseEnter={() => prefetchApplication(jobId)}
    >
      <h1 className="text-xl font-semibold text-text-primary">Application Hub</h1>
      <Suspense
        fallback={
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {MODULE_ORDER.map((m) => (
              <ModuleCardSkeleton key={m} />
            ))}
          </div>
        }
      >
        <ModuleGrid jobId={jobId} />
      </Suspense>
    </div>
  );
}
