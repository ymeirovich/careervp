'use client';

import { useState, useEffect } from 'react';
import { api } from '../api/methods';
import type { UserCV } from '../lib/types';

export function useCV(): {
  cv: UserCV | null;
  isLoading: boolean;
  isSaving: boolean;
  saveCV: (data: Partial<UserCV>) => Promise<UserCV>;
  error: string | null;
} {
  const [cv, setCv] = useState<UserCV | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    setError(null);

    api
      .getCV()
      .then((data) => {
        if (!cancelled) setCv(data);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load CV');
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  async function saveCV(data: Partial<UserCV>): Promise<UserCV> {
    setIsSaving(true);
    setError(null);
    try {
      const saved = await api.saveCV(data);
      setCv(saved);
      return saved;
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to save CV';
      setError(msg);
      throw err;
    } finally {
      setIsSaving(false);
    }
  }

  return { cv, isLoading, isSaving, saveCV, error };
}
