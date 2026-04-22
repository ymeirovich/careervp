import figma from '@figma/code-connect';
import { Badge } from './Badge';

figma.connect(Badge, 'REPLACE_WITH_FIGMA_NODE_URL_FOR_BADGE', {
  props: {
    variant: figma.enum('Variant', {
      success: 'success',
      warning: 'warning',
      error: 'error',
      final: 'final',
      edited: 'edited',
      stale: 'stale',
    }),
  },
  example: ({ variant }) => (
    <Badge variant={variant}>Label</Badge>
  ),
});
