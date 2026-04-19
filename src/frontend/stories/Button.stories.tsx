import type { Meta, StoryObj } from '@storybook/react';
import { Button } from '../components/ui/Button';

const meta: Meta<typeof Button> = {
  component: Button,
  title: 'UI/Button',
  tags: ['autodocs'],
};
export default meta;
type Story = StoryObj<typeof Button>;

export const Primary: Story = { args: { variant: 'primary', children: 'Generate' } };
export const Secondary: Story = { args: { variant: 'secondary', children: 'View All' } };
export const Ghost: Story = { args: { variant: 'ghost', children: 'View All' } };
export const Destructive: Story = { args: { variant: 'destructive', children: 'Delete' } };
export const SmallSize: Story = { args: { variant: 'primary', size: 'sm', children: 'Retry' } };
export const LargeSize: Story = { args: { variant: 'primary', size: 'lg', children: 'Sign In' } };
export const Loading: Story = { args: { variant: 'primary', isLoading: true, children: 'Generating…' } };
export const Disabled: Story = { args: { variant: 'primary', disabled: true, children: 'Generate' } };
