import type { Meta, StoryObj } from '@storybook/react';
import { StatusBadge } from '../components/ui/StatusBadge';

const meta: Meta<typeof StatusBadge> = {
  component: StatusBadge,
  title: 'UI/StatusBadge',
  tags: ['autodocs'],
};
export default meta;
type Story = StoryObj<typeof StatusBadge>;

export const NotStarted: Story = { args: { status: 'notStarted' } };
export const Processing: Story = { args: { status: 'processing' } };
export const Ready: Story = { args: { status: 'ready' } };
export const Complete: Story = { args: { status: 'complete' } };
export const Edited: Story = { args: { status: 'edited' } };
export const Stale: Story = { args: { status: 'stale' } };
export const Failed: Story = { args: { status: 'failed' } };
export const Timeout: Story = { args: { status: 'timeout' } };
export const Final: Story = { args: { status: 'final' } };
