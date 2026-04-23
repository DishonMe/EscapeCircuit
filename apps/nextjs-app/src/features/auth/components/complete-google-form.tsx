'use client';

import { useState } from 'react';
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

const AVATAR_LIST = [
  'Alligator', 'Anteater', 'Armadillo', 'Auroch', 'Axolotl', 'Badger', 'Bat', 'Beaver',
  'Buffalo', 'Camel', 'Capybara', 'Chameleon', 'Cheetah', 'Chinchilla', 'Chipmunk',
  'Chupacabra', 'Cormorant', 'Coyote', 'Crow', 'Dingo', 'Dinosaur', 'Dolphin', 'Duck',
  'Elephant', 'Ferret', 'Fox', 'Frog', 'Giraffe', 'Gopher', 'Grizzly', 'Hedgehog',
  'Hippo', 'Hyena', 'Ibex', 'Ifrit', 'Iguana', 'Jackal', 'Kangaroo', 'Koala',
  'Kraken', 'Lemur', 'Leopard', 'Liger', 'Llama', 'Manatee', 'Mink', 'Monkey',
  'Moose', 'Narwhal', 'Orangutan', 'Otter', 'Panda', 'Penguin', 'Platypus', 'Pumpkin',
  'Python', 'Quagga', 'Rabbit', 'Raccoon', 'Rhino', 'Sheep', 'Shrew', 'Skunk',
  'Squirrel', 'Tiger', 'Turtle', 'Walrus', 'Wolf', 'Wolverine', 'Wombat',
];

const COLOR_PRESETS = [
  '#38bdf8',
  '#ef4444',
  '#f97316',
  '#eab308',
  '#22c55e',
  '#06b6d4',
  '#3b82f6',
  '#8b5cf6',
  '#ec4899',
  '#64748b',
];

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
  const [selectedAvatar, setSelectedAvatar] = useState<string | null>(null);
  const [selectedColor, setSelectedColor] = useState('#38bdf8');
  const [customColor, setCustomColor] = useState('#38bdf8');
  const [useCustomColor, setUseCustomColor] = useState(false);

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
          if (!selectedAvatar) {
            addNotification({
              type: 'error',
              title: 'Avatar Required',
              message: 'Please choose an avatar to complete registration.',
            });
            return;
          }

          const finalColor = useCustomColor ? customColor : selectedColor;
          if (!/^#[0-9A-F]{6}$/i.test(finalColor)) {
            addNotification({
              type: 'error',
              title: 'Invalid Color',
              message: 'Please choose a valid hex color (for example: #38bdf8).',
            });
            return;
          }

          complete.mutate({
            token,
            username: values.username,
            password: values.password,
            avatar_name: selectedAvatar,
            avatar_color: finalColor,
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
              <p className="mb-2 text-sm font-semibold text-foreground">Choose Avatar</p>
              <div className="max-h-36 overflow-y-auto rounded-lg border border-border bg-secondary/40 p-2">
                <div className="grid grid-cols-6 gap-2">
                  {AVATAR_LIST.map((avatar) => (
                    <button
                      key={avatar}
                      type="button"
                      onClick={() => setSelectedAvatar(avatar)}
                      className={`aspect-square overflow-hidden rounded-md border transition-all ${
                        selectedAvatar === avatar
                          ? 'border-blue-500 ring-2 ring-blue-400'
                          : 'border-border hover:border-foreground/40'
                      }`}
                      title={avatar}
                    >
                      <img
                        src={`/avatars/${avatar}.png`}
                        alt={avatar}
                        className="h-full w-full object-cover"
                        loading="lazy"
                      />
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div>
              <p className="mb-2 text-sm font-semibold text-foreground">Choose Color</p>
              <div className="space-y-2 rounded-lg border border-border bg-secondary/40 p-3">
                <div className="flex flex-wrap gap-2">
                  {COLOR_PRESETS.map((color) => (
                    <button
                      key={color}
                      type="button"
                      onClick={() => {
                        setSelectedColor(color);
                        setUseCustomColor(false);
                      }}
                      className={`h-8 w-8 rounded-md border-2 ${
                        !useCustomColor && selectedColor === color
                          ? 'border-foreground ring-2 ring-foreground/30'
                          : 'border-border hover:border-foreground/40'
                      }`}
                      style={{ backgroundColor: color }}
                      title={color}
                    />
                  ))}
                </div>
                <div className="flex gap-2">
                  <input
                    type="color"
                    value={customColor}
                    onChange={(e) => {
                      setCustomColor(e.target.value);
                      setUseCustomColor(true);
                    }}
                    className="h-9 w-10 cursor-pointer rounded border border-border"
                  />
                  <input
                    type="text"
                    value={customColor}
                    onChange={(e) => {
                      const value = e.target.value;
                      setCustomColor(value);
                      if (/^#[0-9A-F]{6}$/i.test(value)) {
                        setUseCustomColor(true);
                      }
                    }}
                    placeholder="#000000"
                    className="h-9 flex-1 rounded border border-border bg-card px-3 text-sm text-foreground"
                  />
                </div>
              </div>
            </div>

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
