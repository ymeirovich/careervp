import type { Meta, StoryObj } from '@storybook/react';
import { ModuleCard } from '../components/ModuleCard/ModuleCard';

const meta: Meta<typeof ModuleCard> = {
  component: ModuleCard,
  title: 'Components/ModuleCard',
  tags: ['autodocs'],
  args: {
    module: 'vpr',
    title: 'Value Proposition Report',
  },
};
export default meta;
type Story = StoryObj<typeof ModuleCard>;

export const NotStarted: Story = { args: { state: 'notStarted' } };
export const NotStartedBaseCV: Story = {
  args: { module: 'baseCV', state: 'notStarted', title: 'Base CV' },
  name: 'NotStarted (baseCV → "Start")',
};
export const Processing: Story = {
  args: { state: 'processing', progressText: 'Analyzing your profile…' },
};
export const Ready: Story = { args: { state: 'ready' } };
export const Complete: Story = { args: { state: 'complete', meta: 'ATS score: 74' } };
export const Edited: Story = { args: { state: 'edited' } };
export const Stale: Story = {
  args: {
    state: 'stale',
    warningText: 'Your CV was updated. Regenerate to reflect changes.',
  },
};
export const Failed: Story = { args: { state: 'failed' } };
export const Timeout: Story = { args: { state: 'timeout' } };
export const Final: Story = { args: { state: 'final' } };
export const Disabled: Story = { args: { state: 'notStarted', disabled: true } };
