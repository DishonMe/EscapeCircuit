'use client';

import { Edit2 } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Form, FormDrawer, Textarea } from '@/components/ui/form';
import { useNotifications } from '@/components/ui/notifications';
import { useUser } from '@/lib/auth';
import { z } from 'zod';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api-client';
import { MutationConfig } from '@/lib/react-query';

const editBioSchema = z.object({
  bio: z.string().max(500, 'Bio must be 500 characters or less'),
});

type EditBioInput = z.infer<typeof editBioSchema>;

const updateBio = ({ data }: { data: EditBioInput }) => {
  return api.patch(`/users/me`, data);
};

type UseUpdateBioOptions = {
  mutationConfig?: MutationConfig<typeof updateBio>;
};

const useUpdateBio = ({
  mutationConfig,
}: UseUpdateBioOptions = {}) => {
  const queryClient = useQueryClient();
  const { onSuccess, ...restConfig } = mutationConfig || {};

  return useMutation({
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: ['user'] });
      onSuccess?.(...args);
    },
    ...restConfig,
    mutationFn: updateBio,
  });
};

export const EditBio = () => {
  const user = useUser();
  const { addNotification } = useNotifications();
  const updateBioMutation = useUpdateBio({
    mutationConfig: {
      onSuccess: () => {
        addNotification({
          type: 'success',
          title: 'Bio Updated',
        });
      },
      onError: () => {
        addNotification({
          type: 'error',
          title: 'Failed to update bio',
        });
      }
    },
  });

  return (
    <FormDrawer
      isDone={updateBioMutation.isSuccess}
      triggerButton={
        <Button icon={<Edit2 className="size-4" />} size="sm">
          Edit Bio
        </Button>
      }
      title="Edit Bio"
      submitButton={
        <Button
          form="edit-bio"
          type="submit"
          size="sm"
          isLoading={updateBioMutation.isPending}
        >
          Submit
        </Button>
      }
    >
      <Form
        id="edit-bio"
        onSubmit={(values) => {
          updateBioMutation.mutate({ data: values });
        }}
        options={{
          defaultValues: {
            bio: user.data?.bio ?? '',
          },
        }}
        schema={editBioSchema}
      >
        {({ register, formState }) => (
          <>
            <Textarea
              label="Bio"
              placeholder="Tell us about yourself..."
              error={formState.errors['bio']}
              registration={register('bio')}
            />
          </>
        )}
      </Form>
    </FormDrawer>
  );
};
