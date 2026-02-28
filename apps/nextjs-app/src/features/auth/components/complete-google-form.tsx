'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import NextLink from 'next/link';

import { Button } from '@/components/ui/button';
import { Form, Input } from '@/components/ui/form';
import { paths } from '@/config/paths';
import { useCompleteGoogleRegistration } from '@/lib/auth';
import { useNotifications } from '@/components/ui/notifications';
import { z } from 'zod';

type CompleteGoogleFormProps = {
  onSuccess: () => void;
};

const completeGoogleSchema = z.object({
  username: z.string().min(1, 'Username is required').min(3, 'Username must be at least 3 characters'),
  password: z.string().min(5, 'Password must be at least 5 characters'),
  passwordConfirm: z.string().min(5, 'Please confirm your password'),
}).refine((data) => data.password === data.passwordConfirm, {
  message: "Passwords don't match",
  path: ["passwordConfirm"],
});

export const CompleteGoogleForm = ({ onSuccess }: CompleteGoogleFormProps) => {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { addNotification } = useNotifications();

  const email = searchParams?.get('email') || '';
  const name = searchParams?.get('name') || '';
  const token = searchParams?.get('token') || '';

  // Validate that we have the required params
  if (!email || !token) {
    return (
      <div className="space-y-4 text-center">
        <h2 className="text-xl font-semibold text-foreground">Session Expired</h2>
        <p className="text-[13px] text-muted-foreground">Your registration session has expired. Please start the login process again.</p>
        <NextLink href={paths.auth.login.getHref()} className="text-foreground underline underline-offset-4 hover:text-foreground/80">
          Back to Login
        </NextLink>
      </div>
    );
  }

  const complete = useCompleteGoogleRegistration({
    onSuccess: () => {
      addNotification({
        type: 'success',
        title: 'Account Successfully Created',
        message: 'Welcome! Your account is ready. You can now explore puzzles and start solving circuits.',
      });
      onSuccess();
    },
    onError: (error: any) => {
      let message = error?.message || 'Could not complete registration. Please try again.';
      
      if (message.includes('already exists')) {
        message = 'Username already taken. Please choose a different username.';
      } else if (message.includes('password')) {
        message = 'Password does not meet requirements. Please ensure it is at least 5 characters.';
      }
      
      addNotification({
        type: 'error',
        title: 'Account Setup Failed',
        message,
      });
    },
  });

  return (
    <div className="space-y-4">
      <div className="text-center">
        <h2 className="text-xl font-semibold">Complete Your Account</h2>
        <p className="text-[13px] text-muted-foreground mt-2">
          {name && <span>Hi {name}! </span>}
          Set up a username and password for your account.
        </p>
      </div>

      <Form
        onSubmit={(values) => {
          complete.mutate({
            token,
            username: values.username,
            password: values.password,
          });
        }}
        schema={completeGoogleSchema}
      >
        {({ register, formState }) => (
          <>
            <div className="bg-secondary/50 border border-border rounded-lg p-3 text-[13px] text-foreground">
              Email: <strong>{email}</strong>
            </div>

            <Input
              type="text"
              label="Username"
              placeholder="Choose a username"
              error={formState.errors['username']}
              registration={register('username')}
            />
            <Input
              type="password"
              label="Password"
              placeholder="Create a password"
              error={formState.errors['password']}
              registration={register('password')}
            />
            <Input
              type="password"
              label="Confirm Password"
              placeholder="Confirm your password"
              error={formState.errors['passwordConfirm']}
              registration={register('passwordConfirm')}
            />

            <div>
              <Button
                isLoading={complete.isPending}
                type="submit"
                className="w-full"
              >
                Complete Registration
              </Button>
            </div>
          </>
        )}
      </Form>

      <div className="text-center text-sm">
        <NextLink href={paths.auth.login.getHref()} className="text-foreground underline underline-offset-4 hover:text-foreground/80">
          Back to Login
        </NextLink>
      </div>
    </div>
  );
};
