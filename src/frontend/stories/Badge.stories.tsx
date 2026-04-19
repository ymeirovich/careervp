import type { Meta, StoryObj } from '@storybook/react';
import { Badge } from '../components/ui/Badge';

const meta: Meta<typeof Badge> = {
  component: Badge,
  title: 'UI/Badge',
  tags: ['autodocs'],
};
export default meta;
type Story = StoryObj<typeof Badge>;

export const Success: Story = { args: { variant: 'success', label: 'Active' } };
export const Warning: Story = { args: { variant: 'warning', label: 'Draft' } };
export const Error: Story = { args: { variant: 'error', label: 'Failed' } };
export const Info: Story = { args: { variant: 'info', label: 'Processing' } };
export const Neutral: Story = { args: { variant: 'neutral', label: 'Archived' } };
export const Final: Story = { args: { variant: 'final', label: 'Final' } };
export const Edited: Story = { args: { variant: 'edited', label: 'Edited' } };
export const Stale: Story = { args: { variant: 'stale', label: 'Outdated' } };
