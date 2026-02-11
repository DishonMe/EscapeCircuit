'use client';

import NextLink from 'next/link';
import { useSearchParams } from 'next/navigation';
import { GoogleLogin } from '@react-oauth/google';

import { Button } from '@/components/ui/button';
import { Form, Input } from '@/components/ui/form';
import { paths } from '@/config/paths';
import { useLogin, loginInputSchema, useGoogleLogin } from '@/lib/auth';
import { useNotifications } from '@/components/ui/notifications';

type LoginFormProps = {
  onSuccess: () => void;
};

export const LoginForm = ({ onSuccess }: LoginFormProps) => {
  const { addNotification } = useNotifications();
  
  const login = useLogin({
    onSuccess,
    onError: (error: any) => {
      addNotification({
        type: 'error',
        title: 'Login Failed',
        message: error?.message || 'Invalid username or password. Please try again.',
      });
    },
  });

  const googleLogin = useGoogleLogin({
    onSuccess,
    onError: (error: any) => {
      addNotification({
        type: 'error',
        title: 'Google Login Failed',
        message: error?.message || 'Could not sign in with Google. Please try again.',
      });
    },
  });

  const searchParams = useSearchParams();
  const redirectTo = searchParams?.get('redirectTo');
  return (
    <div>
      <Form
        onSubmit={(values) => {
          login.mutate(values);
        }}
        schema={loginInputSchema}
      >
        {({ register, formState }) => (
          <>
            <Input
              type="text"
              label="Username"
              error={formState.errors['username']}
              registration={register('username')}
            />
            <Input
              type="password"
              label="Password"
              error={formState.errors['password']}
              registration={register('password')}
            />
            <div>
              <Button
                isLoading={login.isPending}
                type="submit"
                className="w-full"
              >
                Log in
              </Button>
            </div>
          </>
        )}
      </Form>

      <div className="relative my-4">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-gray-300" />
        </div>
        <div className="relative flex justify-center text-sm">
          <span className="bg-white px-2 text-gray-500">OR</span>
        </div>
      </div>

      <div className="flex justify-center">
        <GoogleLogin
          onSuccess={(credentialResponse) => {
            const credential = credentialResponse.credential;
            if (credential) {
              googleLogin.mutate(credential);
            }
          }}
          onError={() => {
            addNotification({
              type: 'error',
              title: 'Google Login Failed',
              message: 'Could not sign in with Google. Please try again.',
            });
          }}
        />
      </div>

      <div className="mt-2 flex items-center justify-end">
        <div className="text-sm">
          <NextLink
            href={paths.auth.register.getHref(redirectTo)}
            className="font-medium text-blue-600 hover:text-blue-500"
          >
            Register
          </NextLink>
        </div>
      </div>
    </div>
  );
};
