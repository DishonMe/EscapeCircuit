'use client';

import { Pen } from 'lucide-react';

import { Button } from '@/components/ui/button';
import {
  Form,
  FormDrawer,
  Input,
  Select,
  Textarea,
} from '@/components/ui/form';
import { useNotifications } from '@/components/ui/notifications';
import { useUser } from '@/lib/auth';
import { canUpdateDiscussion } from '@/lib/authorization';

import { useDiscussion } from '../api/get-discussion';
import {
  updateDiscussionInputSchema,
  useUpdateDiscussion,
} from '../api/update-discussion';

const categoryOptions = [
  { label: 'General', value: 'general' },
  { label: 'Puzzle Help', value: 'puzzle_help' },
  { label: 'Tips & Tricks', value: 'puzzle_tips' },
  { label: 'Solutions', value: 'solutions' },
  { label: 'Bug Report', value: 'bug_report' },
  { label: 'Feature Request', value: 'feature_request' },
  { label: 'Showcase', value: 'showcase' },
];

type UpdateDiscussionProps = {
  discussionId: string;
};

export const UpdateDiscussion = ({ discussionId }: UpdateDiscussionProps) => {
  const { addNotification } = useNotifications();
  const discussionQuery = useDiscussion({ discussionId });
  const updateDiscussionMutation = useUpdateDiscussion({
    mutationConfig: {
      onSuccess: () => {
        addNotification({
          type: 'success',
          title: 'Discussion Updated',
        });
      },
    },
  });

  const user = useUser();
  const discussion = discussionQuery.data;

  if (!canUpdateDiscussion(user?.data, discussion ?? undefined)) {
    return null;
  }

  return (
    <FormDrawer
      isDone={updateDiscussionMutation.isSuccess}
      triggerButton={
        <Button icon={<Pen className="size-4" />} size="sm">
          Update Discussion
        </Button>
      }
      title="Update Discussion"
      submitButton={
        <Button
          form="update-discussion"
          type="submit"
          size="sm"
          isLoading={updateDiscussionMutation.isPending}
        >
          Submit
        </Button>
      }
    >
      <Form
        id="update-discussion"
        onSubmit={(values) => {
          updateDiscussionMutation.mutate({
            data: values,
            discussionId,
          });
        }}
        options={{
          defaultValues: {
            title: discussion?.title ?? '',
            body: discussion?.body ?? '',
            category: discussion?.category ?? 'general',
          },
        }}
        schema={updateDiscussionInputSchema}
      >
        {({ register, formState }) => (
          <>
            <Input
              label="Title"
              error={formState.errors['title']}
              registration={register('title')}
            />
            <Select
              label="Category"
              error={formState.errors['category']}
              registration={register('category')}
              options={categoryOptions}
            />
            <Textarea
              label="Body"
              error={formState.errors['body']}
              registration={register('body')}
            />
          </>
        )}
      </Form>
    </FormDrawer>
  );
};
