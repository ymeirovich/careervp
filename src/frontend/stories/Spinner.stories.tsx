import type { Meta, StoryObj } from '@storybook/react';
import { Spinner } from '../components/ui/Spinner';

const meta: Meta<typeof Spinner> = {
  component: Spinner,
  title: 'UI/Spinner',
  tags: ['autodocs'],
};
export default meta;
type Story = StoryObj<typeof Spinner>;

export const Small: Story = { args: { size: 'sm' } };
export const Medium: Story = { args: { size: 'md' } };
export const Large: Story = { args: { size: 'lg' } };
export const WithLabel: Story = { args: { size: 'md', 'aria-label': 'Generating VPR…' } };
