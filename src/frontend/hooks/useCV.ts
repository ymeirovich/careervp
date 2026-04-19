'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { queryKeys } from '../api/queryKeys';
import type { RawCVData } from '../types/hub-state';

export function useCV(): {
  cv: RawCVData | null;
  uploadCV: (file: File) => Promise<void>;
  isUploading: boolean;
} {
  const queryClient = useQueryClient();

  const { data } = useQuery<RawCVData>({
    queryKey: queryKeys.cv.detail(),
    queryFn: async () => {
      const res = await apiClient.get<RawCVData>('/users/me/cv');
      return res.data;
    },
  });

  const { mutateAsync, isPending } = useMutation<void, Error, File>({
    mutationFn: async (file: File) => {
      const form = new FormData();
      form.append('file', file);
      await apiClient.post('/users/me/cv', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.cv.detail() });
    },
  });

  return {
    cv: data ?? null,
    uploadCV: mutateAsync,
    isUploading: isPending,
  };
}
