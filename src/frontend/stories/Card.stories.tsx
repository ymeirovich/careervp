import type { Meta, StoryObj } from '@storybook/react';
import { Card } from '../components/ui/Card';

const meta: Meta<typeof Card> = {
  component: Card,
  title: 'UI/Card',
  tags: ['autodocs'],
  args: { children: <div className="p-4 text-text-primary">Card content</div> },
};
export default meta;
type Story = StoryObj<typeof Card>;

export const Default: Story = { args: { variant: 'default' } };
export const Elevated: Story = { args: { variant: 'elevated' } };
export const Bordered: Story = { args: { variant: 'bordered' } };
