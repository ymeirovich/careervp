import figma from '@figma/code-connect';
import { Button } from './Button';

figma.connect(Button, 'REPLACE_WITH_FIGMA_NODE_URL_FOR_BUTTON', {
  props: {
    variant: figma.enum('Variant', {
      Primary: 'primary',
      Secondary: 'secondary',
      Ghost: 'ghost',
    }),
    size: figma.enum('Size', {
      SM: 'sm',
      MD: 'md',
      LG: 'lg',
    }),
    isLoading: figma.boolean('State Loading'),
    disabled: figma.boolean('State Disabled'),
  },
  example: ({ variant, size, isLoading, disabled }) => (
    <Button variant={variant} size={size} isLoading={isLoading} disabled={disabled}>
      Label
    </Button>
  ),
});
