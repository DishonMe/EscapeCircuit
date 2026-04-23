'use client';

import NextLink from 'next/link';
import { useSearchParams } from 'next/navigation';
import * as React from 'react';

import { Button } from '@/components/ui/button';
import { Form, Input, Select, Label, Switch } from '@/components/ui/form';
import { paths } from '@/config/paths';
import { useRegister, registerInputSchema } from '@/lib/auth';
import { Team } from '@/types/api';

// List of valid animal avatars (must match backend)
const AVATAR_LIST = [
  'Alligator', 'Anteater', 'Armadillo', 'Auroch', 'Axolotl', 'Badger', 'Bat', 'Beaver',
  'Buffalo', 'Camel', 'Capybara', 'Chameleon', 'Cheetah', 'Chinchilla', 'Chipmunk',
  'Chupacabra', 'Cormorant', 'Coyote', 'Crow', 'Dingo', 'Dinosaur', 'Dolphin', 'Duck',
  'Elephant', 'Ferret', 'Fox', 'Frog', 'Giraffe', 'Gopher', 'Grizzly', 'Hedgehog',
  'Hippo', 'Hyena', 'Ibex', 'Ifrit', 'Iguana', 'Jackal', 'Kangaroo', 'Koala',
  'Kraken', 'Lemur', 'Leopard', 'Liger', 'Llama', 'Manatee', 'Mink', 'Monkey',
  'Moose', 'Narwhal', 'Orangutan', 'Otter', 'Panda', 'Penguin', 'Platypus', 'Pumpkin',
  'Python', 'Quagga', 'Rabbit', 'Raccoon', 'Rhino', 'Sheep', 'Shrew', 'Skunk',
  'Squirrel', 'Tiger', 'Turtle', 'Walrus', 'Wolf', 'Wolverine', 'Wombat'
];

type RegisterFormProps = {
  onSuccess: () => void;
  chooseTeam: boolean;
  setChooseTeam: () => void;
  teams?: Team[];
};

export const RegisterForm = ({
  onSuccess,
  chooseTeam,
  setChooseTeam,
  teams,
}: RegisterFormProps) => {
  const registering = useRegister({ onSuccess });
  const searchParams = useSearchParams();
  const redirectTo = searchParams?.get('redirectTo');
  const [selectedAvatar, setSelectedAvatar] = React.useState<string | null>(null);
  const [avatarError, setAvatarError] = React.useState<string>('');

  const handleAvatarSelect = (avatar: string) => {
    setSelectedAvatar(avatar);
    setAvatarError('');
  };

  return (
    <div>
      <Form
        onSubmit={(values) => {
          if (!selectedAvatar) {
            setAvatarError('Please select an avatar to continue');
            return;
          }
          registering.mutate({ ...values, avatar_name: selectedAvatar });
        }}
        schema={registerInputSchema}
        options={{
          shouldUnregister: true,
        }}
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
              type="email"
              label="Email Address"
              error={formState.errors['email']}
              registration={register('email')}
            />
            <Input
              type="password"
              label="Password"
              error={formState.errors['password']}
              registration={register('password')}
            />
            
            {/* Avatar Selection Section */}
            <div className="mt-6 mb-6">
              <Label>
                <span className="font-semibold text-sm">Choose Your Anonymous Animal Avatar</span>
                {avatarError && <span className="text-red-600 text-xs ml-2">{avatarError}</span>}
              </Label>
              <div className="mt-3 max-h-96 overflow-y-auto border rounded-lg p-4 bg-slate-50">
                <div className="grid grid-cols-4 sm:grid-cols-6 md:grid-cols-8 gap-3">
                  {AVATAR_LIST.map((avatar) => (
                    <button
                      key={avatar}
                      type="button"
                      onClick={() => handleAvatarSelect(avatar)}
                      className={`flex flex-col items-center p-3 rounded-lg transition-all ${
                        selectedAvatar === avatar
                          ? 'bg-blue-500 ring-2 ring-blue-600 scale-105'
                          : 'bg-white hover:bg-slate-100 border border-slate-200'
                      }`}
                      title={avatar}
                    >
                      <img
                        src={`/avatars/${avatar}.png`}
                        alt={avatar}
                        className="w-16 h-16 rounded object-cover"
                        loading="lazy"
                      />
                      <span className="text-xs font-medium mt-2 text-center truncate w-full">
                        {avatar}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
            
            <div>
              <Button
                isLoading={registering.isPending}
                type="submit"
                className="w-full"
              >
                Register
              </Button>
            </div>
          </>
        )}
      </Form>
      <div className="mt-2 flex items-center justify-end">
        <div className="text-sm">
          <NextLink
            href={paths.auth.login.getHref(redirectTo)}
            className="font-medium text-foreground underline underline-offset-4 hover:text-foreground/80"
          >
            Log In
          </NextLink>
        </div>
      </div>
    </div>
  );
};
