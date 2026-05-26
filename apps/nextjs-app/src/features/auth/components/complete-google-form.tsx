'use client';

import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { useState } from 'react';
import { z } from 'zod';

import { CircuitBackground } from '@/components/ui/circuit-background/circuit-background';
import { paths } from '@/config/paths';
import { useCompleteGoogleRegistration } from '@/lib/auth';
import { useNotifications } from '@/components/ui/notifications';
import { Button } from '@/components/ui/button';

type CompleteGoogleFormProps = {
  onSuccess: () => void;
};

const AVATAR_LIST = [
  'Alligator','Anteater','Armadillo','Auroch','Axolotl','Badger','Bat','Beaver',
  'Buffalo','Camel','Capybara','Chameleon','Cheetah','Chinchilla','Chipmunk',
  'Chupacabra','Cormorant','Coyote','Crow','Dingo','Dinosaur','Dolphin','Duck',
  'Elephant','Ferret','Fox','Frog','Giraffe','Gopher','Grizzly','Hedgehog',
  'Hippo','Hyena','Ibex','Ifrit','Iguana','Jackal','Kangaroo','Koala',
  'Kraken','Lemur','Leopard','Liger','Llama','Manatee','Mink','Monkey',
  'Moose','Narwhal','Orangutan','Otter','Panda','Penguin','Platypus','Pumpkin',
  'Python','Quagga','Rabbit','Raccoon','Rhino','Sheep','Shrew','Skunk',
  'Squirrel','Tiger','Turtle','Walrus','Wolf','Wolverine','Wombat',
];

const COLOR_PRESETS = [
  '#38bdf8','#ef4444','#f97316','#eab308','#22c55e',
  '#06b6d4','#3b82f6','#8b5cf6','#ec4899','#64748b',
];

const completeGoogleSchema = z.object({
  username: z.string().min(3, 'Username must be at least 3 characters'),
  password: z.string().min(5, 'Password must be at least 5 characters'),
  passwordConfirm: z.string().min(5, 'Please confirm your password'),
}).refine((data) => data.password === data.passwordConfirm, {
  message: "Passwords don't match",
  path: ['passwordConfirm'],
});

export const CompleteGoogleForm = ({ onSuccess }: CompleteGoogleFormProps) => {
  const searchParams = useSearchParams();
  const { addNotification } = useNotifications();

  const [selectedAvatar, setSelectedAvatar] = useState<string | null>(null);
  const [selectedColor, setSelectedColor] = useState('#38bdf8');
  const [customColor, setCustomColor] = useState('#38bdf8');
  const [useCustomColor, setUseCustomColor] = useState(false);

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');
  const [error, setError] = useState('');

  const email = searchParams?.get('email') || '';
  const name = searchParams?.get('name') || '';
  const token = searchParams?.get('token') || '';

  const complete = useCompleteGoogleRegistration({
    onSuccess: () => {
      addNotification({
        type: 'success',
        title: 'Account Successfully Created',
        message: 'Welcome! Your account is ready.',
      });
      onSuccess();
    },
    onError: (error: any) => {
      let message = error?.message || 'Could not complete registration.';

      if (message.includes('already exists')) {
        message = 'Username already taken.';
      } else if (message.includes('password')) {
        message = 'Password must be at least 5 characters.';
      }

      addNotification({
        type: 'error',
        title: 'Account Setup Failed',
        message,
      });

      setError(message);
    },
  });

  const isSessionValid = !!email && !!token;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    const result = completeGoogleSchema.safeParse({
      username: username.trim(),
      password,
      passwordConfirm,
    });

    if (!result.success) {
      setError(result.error.issues[0]?.message || 'Invalid form');
      return;
    }

    if (!isSessionValid) {
      setError('Session expired. Please login again.');
      return;
    }

    if (!selectedAvatar) {
      setError('Please choose an avatar.');
      return;
    }

    const finalColor = useCustomColor ? customColor : selectedColor;

    if (!/^#[0-9A-F]{6}$/i.test(finalColor)) {
      setError('Invalid color.');
      return;
    }

    complete.mutate({
      token,
      username: result.data.username,
      password: result.data.password,
      avatar_name: selectedAvatar,
      avatar_color: finalColor,
    });
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-[hsl(224_30%_8%)]">
      <CircuitBackground />

      <div className="relative w-full max-w-md rounded-2xl p-6 border border-sky-500/20 bg-white/5 backdrop-blur">

        <h1 className="text-xl text-center text-white mb-2">
          Complete your account
        </h1>

        <p className="text-center text-sm text-slate-400 mb-6">
          {name ? `Hi ${name}! ` : ''}Finish Google sign-up
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">

          <div className="text-sm text-slate-300">{email}</div>

          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Username"
            className="w-full p-2 rounded bg-white/10 text-white"
          />

          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password"
            className="w-full p-2 rounded bg-white/10 text-white"
          />

          <input
            type="password"
            value={passwordConfirm}
            onChange={(e) => setPasswordConfirm(e.target.value)}
            placeholder="Confirm Password"
            className="w-full p-2 rounded bg-white/10 text-white"
          />

          <div>
            <p className="text-sm mb-2 text-white">Choose Avatar</p>
            <div className="grid grid-cols-6 gap-2 max-h-32 overflow-y-auto">
              {AVATAR_LIST.map((avatar) => (
                <button
                  key={avatar}
                  type="button"
                  onClick={() => setSelectedAvatar(avatar)}
                  className={`border rounded ${
                    selectedAvatar === avatar ? 'border-blue-500' : ''
                  }`}
                >
                  <img src={`/avatars/${avatar}.png`} alt={avatar} />
                </button>
              ))}
            </div>
          </div>

          <div>
            <p className="text-sm mb-2 text-white">Choose Color</p>
            <div className="flex gap-2 flex-wrap">
              {COLOR_PRESETS.map((c) => (
                <button
                  key={c}
                  type="button"
                  onClick={() => {
                    setSelectedColor(c);
                    setUseCustomColor(false);
                  }}
                  style={{ background: c }}
                  className="w-8 h-8 rounded"
                />
              ))}
            </div>
          </div>

          {error && (
            <div className="text-red-400 text-sm">{error}</div>
          )}

          <Button
            isLoading={complete.isPending}
            type="submit"
            className="w-full"
          >
            Complete Registration
          </Button>

        </form>

        <p className="text-center text-sm mt-4 text-slate-400">
          Already have an account?{' '}
          <Link href={paths.auth.login.getHref()} className="text-sky-400">
            Login
          </Link>
        </p>

      </div>
    </div>
  );
};