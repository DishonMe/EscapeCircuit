import { Meta, StoryObj } from '@storybook/react';

import { Button } from '@/components/ui/button';

import { ConfirmationDialog } from './confirmation-dialog';

const meta: Meta<typeof ConfirmationDialog> = {
  component: ConfirmationDialog,
};

export default meta;

type Story = StoryObj<typeof ConfirmationDialog>;

export const Danger: Story = {
  args: {
    icon: 'danger',
    title: 'Confirmation',
    body: 'Hello World',
    confirmButton: <Button variant="destructive">Confirm</Button>,
    triggerButton: <Button>Open</Button>,
  },
};

export const Info: Story = {
  args: {
    icon: 'info',
    title: 'Confirmation',
    body: 'Hello World',
    confirmButton: <Button>Confirm</Button>,
    triggerButton: <Button>Open</Button>,
  },
};
