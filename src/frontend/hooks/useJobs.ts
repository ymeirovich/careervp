'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/methods';
import type { Job, CreateJobInput } from '../lib/types';

export function useJobs(): {
  jobs: Job[];
  isLoading: boolean;
  createJob: (input: CreateJobInput) => Promise<Job>;
  isCreating: boolean;
  error: string | null;
  refetch: () => void;
} {
  const queryClient = useQueryClient();

  const { data, isLoading, error, refetch } = useQuery<Job[]>({
    queryKey: ['jobs'],
    queryFn: () => api.getJobs(),
  });

  const { mutateAsync, isPending } = useMutation<Job, Error, CreateJobInput>({
    mutationFn: (input) => api.createJob(input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['jobs'] });
    },
  });

  return {
    jobs: data ?? [],
    isLoading,
    createJob: mutateAsync,
    isCreating: isPending,
    error: error ? (error instanceof Error ? error.message : 'Failed to load jobs') : null,
    refetch: () => {
      void refetch();
    },
  };
}
