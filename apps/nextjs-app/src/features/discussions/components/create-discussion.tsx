'use client';

import { ArrowLeft } from 'lucide-react';
import NextLink from 'next/link';

import { Button } from '@/components/ui/button';
import { Form, Input, Select, Textarea } from '@/components/ui/form';
import { useNotifications } from '@/components/ui/notifications';
import { paths } from '@/config/paths';
import { useUser } from '@/lib/auth';
import { canCreateDiscussion } from '@/lib/authorization';
import { Discussion } from '@/types/api';

import {
  createDiscussionInputSchema,
  useCreateDiscussion,
} from '../api/create-discussion';

const categoryOptions = [
  { label: 'General', value: 'general' },
  { label: 'Puzzle Help', value: 'puzzle_help' },
  { label: 'Tips & Tricks', value: 'puzzle_tips' },
  { label: 'Solutions', value: 'solutions' },
  { label: 'Bug Report', value: 'bug_report' },
  { label: 'Feature Request', value: 'feature_request' },
  { label: 'Showcase', value: 'showcase' },
];

type CreateDiscussionProps = {
  onSuccess?: (discussion: Discussion) => void;
};

export const CreateDiscussion = ({ onSuccess }: CreateDiscussionProps) => {
  const { addNotification } = useNotifications();
  const createDiscussionMutation = useCreateDiscussion({
    mutationConfig: {
      onSuccess: (data) => {
        addNotification({
          type: 'success',
          title: 'Discussion Created',
        });
        onSuccess?.(data);
      },
    },
  });

  const user = useUser();

  if (!canCreateDiscussion(user?.data)) {
    return null;
  }

  return (
    <div className="space-y-4">
      <NextLink
        href={paths.app.discussions.getHref()}
        className="inline-flex items-center gap-1 text-[13px] text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" />
        Back to Discussions
      </NextLink>

      <div className="rounded-xl border border-border bg-card p-6">
        <h1 className="mb-6 text-xl font-semibold text-foreground">
          New Discussion
        </h1>

        <Form
          id="create-discussion"
          onSubmit={(values) => {
            createDiscussionMutation.mutate({ data: values });
          }}
          schema={createDiscussionInputSchema}
          options={{
            defaultValues: {
              title: '',
              body: '',
              category: 'general',
              puzzle_id: null,
            },
          }}
        >
          {({ register, formState }) => (
            <div className="space-y-4">
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
                defaultValue="general"
              />

              <Textarea
                label="Body"
                error={formState.errors['body']}
                registration={register('body')}
              />

              <div className="flex justify-end gap-2 pt-2">
                <NextLink href={paths.app.discussions.getHref()}>
                  <Button variant="outline" type="button">
                    Cancel
                  </Button>
                </NextLink>
                <Button
                  type="submit"
                  isLoading={createDiscussionMutation.isPending}
                >
                  Create Discussion
                </Button>
              </div>
            </div>
          )}
        </Form>
      </div>
    </div>
  );
};
