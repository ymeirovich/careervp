import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ModuleCard } from '../../components/ModuleCard/ModuleCard';
import type { ModuleType } from '../../types/enums';

const ALL_MODULES: ModuleType[] = [
  'vpr',
  'tailoredCV',
  'coverLetter',
  'interviewPrep',
  'gapAnalysis',
  'companyResearch',
  'baseCV',
];

describe('ModuleCard — processing state buttons replaced (TEST-FE-042 § unit-module-card-processing)', () => {
  ALL_MODULES.forEach((module) => {
    it(`[${module}] hides View/Generate/Regenerate/Retry/Export and shows disabled Processing + Cancel when isProcessing with cancelAction`, () => {
      render(
        <ModuleCard
          module={module}
          state="processing"
          title={`${module} title`}
          cancelAction={{ label: 'Cancel', onClick: vi.fn() }}
        />,
      );
      // Primary actions replaced
      expect(screen.queryByRole('button', { name: /^view$/i })).toBeNull();
      expect(screen.queryByRole('button', { name: /^generate$/i })).toBeNull();
      expect(screen.queryByRole('button', { name: /^regenerate$/i })).toBeNull();
      expect(screen.queryByRole('button', { name: /^retry$/i })).toBeNull();
      expect(screen.queryByRole('button', { name: /^export$/i })).toBeNull();

      // Disabled processing button present
      const processingBtn = screen.getByRole('button', { name: /processing/i });
      expect(processingBtn.hasAttribute('disabled')).toBe(true);

      // Cancel button present
      expect(screen.getByRole('button', { name: /cancel/i })).toBeDefined();
    });
  });

  ALL_MODULES.forEach((module) => {
    it(`[${module}] shows spinner (no Cancel) when processing without cancelAction`, () => {
      render(
        <ModuleCard
          module={module}
          state="processing"
          title={`${module} title`}
          cancelAction={undefined}
        />,
      );
      expect(screen.queryByRole('button', { name: /cancel/i })).toBeNull();
      // Spinner present
      expect(screen.getByRole('status')).toBeDefined();
    });
  });

  ALL_MODULES.forEach((module) => {
    it(`[${module}] uses ProcessingDots (not animate-pulse) when cancelAction provided`, () => {
      render(
        <ModuleCard
          module={module}
          state="processing"
          title={`${module} title`}
          cancelAction={{ label: 'Cancel', onClick: vi.fn() }}
        />,
      );
      // No animate-pulse class
      expect(document.querySelector('.animate-pulse')).toBeNull();
      // aria-hidden dots present (from ProcessingDots)
      expect(document.querySelector('[aria-hidden="true"]')).not.toBeNull();
    });
  });

  ALL_MODULES.forEach((module) => {
    it(`[${module}] shows errorMessage below processing indicator`, () => {
      render(
        <ModuleCard
          module={module}
          state="processing"
          title={`${module} title`}
          cancelAction={{ label: 'Cancel', onClick: vi.fn() }}
          errorMessage="Something failed"
        />,
      );
      expect(screen.getByText('Something failed')).toBeDefined();
    });
  });
});
