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
  
  // Check if Google login is configured
  const googleClientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
  const isGoogleLoginEnabled = 
    googleClientId && 
    googleClientId !== 'your_google_client_id_here' &&
    googleClientId.length > 0;
  
  const login = useLogin({
    onSuccess,
    onError: (error: any) => {
      let message = error?.message || 'Invalid username or password. Please try again.';
      
      // Provide specific guidance based on error
      if (message.includes('not found')) {
        message = 'Username not found. Please check your username or create a new account.';
      } else if (message.includes('invalid password')) {
        message = 'Incorrect password. Please try again or use the password reset feature.';
      }
      
      addNotification({
        type: 'error',
        title: 'Failed to log in',
        message,
      });
    },
  });

  const googleLogin = useGoogleLogin({
    onSuccess,
    onError: (error: any) => {
      // Handle disabled Google login gracefully
      if (error?.message === 'google_login_disabled') {
        addNotification({
          type: 'info',
          title: 'Google Login Not Available',
          message: 'Google login has not been configured on this server. Please use your username and password to log in.',
        });
        return;
      }
      addNotification({
        type: 'error',
        title: 'Google Sign-In Failed',
        message: error?.message || 'Could not authenticate with Google. Please make sure your Google account is verified and try again.',
      });
    },
    onNeedsPassword: (data) => {
      // Redirect to password setup page with email, name, and token
      const params = new URLSearchParams({
        email: data.email,
        name: data.name,
        token: data.token,
      });
      window.location.href = `${paths.auth.completeGoogle.getHref()}?${params.toString()}`;
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

      {isGoogleLoginEnabled && (
        <>
          <div className="relative my-5">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-border" />
            </div>
            <div className="relative flex justify-center text-[13px]">
              <span className="bg-card px-3 text-muted-foreground">OR</span>
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
                  title: 'Google Sign-In Failed',
                  message: 'Could not authenticate with Google. Please try again or use username/password login.',
                });
              }}
            />
          </div>
        </>
      )}

      <div className="mt-2 flex items-center justify-end">
        <div className="text-sm">
          <NextLink
            href={paths.auth.register.getHref(redirectTo)}
            className="font-medium text-foreground underline underline-offset-4 hover:text-foreground/80"
          >
            Register
          </NextLink>
        </div>
      </div>
    </div>
  );
};
