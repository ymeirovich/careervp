import React from 'react';
import { Badge } from './Badge';
import type { BadgeVariant } from './Badge';
import type { ModuleStatus } from '../../types/enums';

const STATUS_TO_BADGE: Record<ModuleStatus, BadgeVariant> = {
  ready:      'success',
  complete:   'success',
  processing: 'info',
  stale:      'warning',
  edited:     'warning',
  failed:     'error',
  timeout:    'error',
  notStarted: 'neutral',
  final:      'final',
};

const STATUS_LABELS: Record<ModuleStatus, string> = {
  ready:      'Ready',
  complete:   'Complete',
  processing: 'Processing',
  stale:      'Outdated',
  edited:     'Edited',
  failed:     'Failed',
  timeout:    'Timed out',
  notStarted: 'Not started',
  final:      'Final',
};

export interface StatusBadgeProps {
  status: ModuleStatus;
  soft?: boolean;
  'data-testid'?: string;
}

export function StatusBadge({ status, soft = false, 'data-testid': testId }: StatusBadgeProps) {
  return (
    <Badge
      variant={STATUS_TO_BADGE[status]}
      soft={soft}
      label={STATUS_LABELS[status]}
      data-testid={testId}
    />
  );
}
