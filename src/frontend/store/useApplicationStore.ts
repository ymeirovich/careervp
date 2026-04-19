'use client';

import { create } from 'zustand';
import type { ModuleType } from '../types/enums';

interface ApplicationStore {
  selectedCvId: string | null;
  activeJobId: string | null;
  editedModules: Set<ModuleType>;
  dismissedWarnings: Set<string>;

  setSelectedCv: (cvId: string) => void;
  setActiveJob: (jobId: string) => void;
  markModuleEdited: (moduleType: ModuleType) => void;
  dismissWarning: (warningId: string) => void;
  clearJob: () => void;
}

function loadEditedModules(): Set<ModuleType> {
  if (typeof window === 'undefined') return new Set();
  try {
    const raw = sessionStorage.getItem('editedModules');
    if (!raw) return new Set();
    return new Set(JSON.parse(raw) as ModuleType[]);
  } catch {
    return new Set();
  }
}

function saveEditedModules(modules: Set<ModuleType>): void {
  if (typeof window === 'undefined') return;
  try {
    sessionStorage.setItem('editedModules', JSON.stringify(Array.from(modules)));
  } catch {
    // sessionStorage unavailable — silently ignore
  }
}

export const useApplicationStore = create<ApplicationStore>((set) => ({
  selectedCvId: null,
  activeJobId: null,
  editedModules: loadEditedModules(),
  dismissedWarnings: new Set(),

  setSelectedCv: (cvId) => set({ selectedCvId: cvId }),

  setActiveJob: (jobId) => set({ activeJobId: jobId }),

  markModuleEdited: (moduleType) =>
    set((state) => {
      const next = new Set(state.editedModules);
      next.add(moduleType);
      saveEditedModules(next);
      return { editedModules: next };
    }),

  dismissWarning: (warningId) =>
    set((state) => {
      const next = new Set(state.dismissedWarnings);
      next.add(warningId);
      return { dismissedWarnings: next };
    }),

  clearJob: () =>
    set(() => {
      const empty = new Set<ModuleType>();
      saveEditedModules(empty);
      return {
        activeJobId: null,
        editedModules: empty,
        dismissedWarnings: new Set(),
      };
    }),
}));
