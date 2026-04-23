'use client';

import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { useState } from 'react';

import { CircuitBackground } from '@/components/ui/circuit-background/CircuitBackground';
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
  path: ['passwordConfirm'],
});

export const CompleteGoogleForm = ({ onSuccess }: CompleteGoogleFormProps) => {
  const searchParams = useSearchParams();
  const { addNotification } = useNotifications();
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
      setError(result.error.issues[0]?.message || 'Please review the form and try again.');
      return;
    }

    if (!isSessionValid) {
      setError('Your registration session has expired. Please start the login process again.');
      return;
    }

    complete.mutate({
      token,
      username: result.data.username,
      password: result.data.password,
    });
  };

  return (
    <div
      className="relative flex min-h-screen items-center justify-center overflow-hidden bg-[hsl(224_30%_8%)]"
      style={{ fontFamily: "'Space Grotesk', sans-serif" }}
    >
      <CircuitBackground />

      <div
        className="pointer-events-none absolute"
        style={{
          width: 600,
          height: 600,
          background: 'radial-gradient(circle, rgba(56,189,248,0.08) 0%, transparent 70%)',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
        }}
      />

      <div
        className="pointer-events-none absolute h-[560px] w-[560px] rounded-full"
        style={{
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          background:
            'conic-gradient(from 0deg, rgba(56,189,248,0) 0deg, rgba(56,189,248,0.22) 90deg, rgba(56,189,248,0) 170deg, rgba(14,165,233,0.14) 250deg, rgba(56,189,248,0) 360deg)',
          filter: 'blur(22px)',
          animation: 'flow-orbit 16s linear infinite',
        }}
      />

      <div
        className="pointer-events-none absolute h-[500px] w-[500px] rounded-full"
        style={{
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          border: '1px solid rgba(56,189,248,0.14)',
          boxShadow: '0 0 40px rgba(56,189,248,0.14), inset 0 0 25px rgba(56,189,248,0.08)',
          animation: 'flow-orbit-rev 20s ease-in-out infinite',
        }}
      />

      <div
        className="relative mx-4 w-full max-w-[380px] rounded-2xl px-8 py-10"
        style={{
          background: 'rgba(255,255,255,0.03)',
          border: '0.5px solid rgba(56,189,248,0.2)',
          backdropFilter: 'blur(12px)',
          boxShadow:
            '0 22px 60px rgba(2,12,27,0.5), inset 0 1px 0 rgba(186,230,253,0.08), 0 0 30px rgba(56,189,248,0.1)',
        }}
      >
        <div
          className="pointer-events-none absolute inset-0 rounded-2xl"
          style={{
            background:
              'linear-gradient(145deg, rgba(186,230,253,0.12) 0%, rgba(56,189,248,0.06) 24%, rgba(255,255,255,0) 55%), radial-gradient(circle at 88% 16%, rgba(56,189,248,0.16), transparent 45%)',
          }}
        />

        <div
          className="pointer-events-none absolute left-[30px] right-[30px] top-[-1px] h-px"
          style={{
            background:
              'linear-gradient(90deg, transparent, rgba(56,189,248,0.5), transparent)',
          }}
        />

        {[
          { top: 12, left: 12, delay: '0s' },
          { top: 12, right: 12, delay: '1s' },
          { bottom: 12, left: 12, delay: '2s' },
          { bottom: 12, right: 12, delay: '0.5s' },
        ].map((pos, i) => (
          <span
            key={i}
            className="absolute h-1 w-1 rounded-full"
            style={{
              ...pos,
              background: 'rgba(56,189,248,0.5)',
              animation: 'pulse-dot 3s ease-in-out infinite',
              animationDelay: pos.delay,
            }}
          />
        ))}

        <div className="mb-8 flex flex-col items-center gap-2.5">
          <div
            className="flex items-center justify-center rounded-[14px]"
            style={{
              width: 52,
              height: 52,
              background: '#0f1923',
              border: '1px solid rgba(56,189,248,0.3)',
            }}
          >
            <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
              <circle cx="14" cy="14" r="3" fill="#38bdf8" />
              <line x1="14" y1="4" x2="14" y2="10" stroke="#38bdf8" strokeWidth="1.5" strokeLinecap="round" />
              <line x1="14" y1="18" x2="14" y2="24" stroke="#f97316" strokeWidth="1.5" strokeLinecap="round" />
              <line x1="4" y1="14" x2="10" y2="14" stroke="#22c55e" strokeWidth="1.5" strokeLinecap="round" />
              <line x1="18" y1="14" x2="24" y2="14" stroke="#a855f7" strokeWidth="1.5" strokeLinecap="round" />
              <circle cx="14" cy="4" r="1.5" fill="rgba(56,189,248,0.4)" />
              <circle cx="14" cy="24" r="1.5" fill="rgba(249,115,22,0.4)" />
              <circle cx="4" cy="14" r="1.5" fill="rgba(34,197,94,0.4)" />
              <circle cx="24" cy="14" r="1.5" fill="rgba(168,85,247,0.4)" />
            </svg>
          </div>
          <span
            className="text-[15px] tracking-[0.08em]"
            style={{ fontFamily: "'DM Mono', monospace", color: 'rgba(56,189,248,0.9)' }}
          >
            ESCAPECIRCUIT
          </span>
        </div>

        <h1 className="mb-1 text-center text-[22px] font-semibold text-slate-50">Complete your account</h1>
        <p className="mb-6 text-center text-[13px]" style={{ color: 'rgba(148,163,184,0.7)' }}>
          {name ? `Hi ${name}! ` : ''}Set your username and password to finish Google sign-up
        </p>

        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <div>
            <label
              className="mb-1.5 block text-[11px] uppercase tracking-[0.1em]"
              style={{ fontFamily: "'DM Mono', monospace", color: 'rgba(56,189,248,0.6)' }}
            >
              Email Address
            </label>
            <div
              className="w-full rounded-lg border px-3.5 py-2.5 text-sm text-slate-300"
              style={{
                background: 'rgba(255,255,255,0.04)',
                borderColor: 'rgba(56,189,248,0.15)',
              }}
            >
              {email || 'Unavailable'}
            </div>
          </div>

          <div>
            <label
              className="mb-1.5 block text-[11px] uppercase tracking-[0.1em]"
              style={{ fontFamily: "'DM Mono', monospace", color: 'rgba(56,189,248,0.6)' }}
            >
              Username
            </label>
            <input
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              placeholder="your_handle"
              autoComplete="username"
              className="w-full rounded-lg border px-3.5 py-2.5 text-sm text-slate-100 outline-none transition-colors placeholder:text-slate-400/30"
              style={{
                background: 'rgba(255,255,255,0.04)',
                borderColor: 'rgba(56,189,248,0.15)',
              }}
              onFocus={e => {
                e.currentTarget.style.borderColor = 'rgba(56,189,248,0.5)';
                e.currentTarget.style.background = 'rgba(56,189,248,0.04)';
              }}
              onBlur={e => {
                e.currentTarget.style.borderColor = 'rgba(56,189,248,0.15)';
                e.currentTarget.style.background = 'rgba(255,255,255,0.04)';
              }}
            />
          </div>

          <div>
            <label
              className="mb-1.5 block text-[11px] uppercase tracking-[0.1em]"
              style={{ fontFamily: "'DM Mono', monospace", color: 'rgba(56,189,248,0.6)' }}
            >
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="••••••••••"
              autoComplete="new-password"
              className="w-full rounded-lg border px-3.5 py-2.5 text-sm text-slate-100 outline-none transition-colors placeholder:text-slate-400/30"
              style={{
                background: 'rgba(255,255,255,0.04)',
                borderColor: 'rgba(56,189,248,0.15)',
              }}
              onFocus={e => {
                e.currentTarget.style.borderColor = 'rgba(56,189,248,0.5)';
                e.currentTarget.style.background = 'rgba(56,189,248,0.04)';
              }}
              onBlur={e => {
                e.currentTarget.style.borderColor = 'rgba(56,189,248,0.15)';
                e.currentTarget.style.background = 'rgba(255,255,255,0.04)';
              }}
            />
          </div>

          <div>
            <label
              className="mb-1.5 block text-[11px] uppercase tracking-[0.1em]"
              style={{ fontFamily: "'DM Mono', monospace", color: 'rgba(56,189,248,0.6)' }}
            >
              Confirm Password
            </label>
            <input
              type="password"
              value={passwordConfirm}
              onChange={e => setPasswordConfirm(e.target.value)}
              placeholder="••••••••••"
              autoComplete="new-password"
              className="w-full rounded-lg border px-3.5 py-2.5 text-sm text-slate-100 outline-none transition-colors placeholder:text-slate-400/30"
              style={{
                background: 'rgba(255,255,255,0.04)',
                borderColor: 'rgba(56,189,248,0.15)',
              }}
              onFocus={e => {
                e.currentTarget.style.borderColor = 'rgba(56,189,248,0.5)';
                e.currentTarget.style.background = 'rgba(56,189,248,0.04)';
              }}
              onBlur={e => {
                e.currentTarget.style.borderColor = 'rgba(56,189,248,0.15)';
                e.currentTarget.style.background = 'rgba(255,255,255,0.04)';
              }}
            />
          </div>

          {!isSessionValid && (
            <p
              className="rounded-lg border px-3 py-2 text-[12px]"
              style={{
                borderColor: 'rgba(248,113,113,0.35)',
                background: 'rgba(127,29,29,0.2)',
                color: 'rgb(254 202 202)',
              }}
            >
              Your registration session has expired. Please start again.
            </p>
          )}

          {error && (
            <p
              className="rounded-lg border px-3 py-2 text-[12px]"
              style={{
                borderColor: 'rgba(248,113,113,0.35)',
                background: 'rgba(127,29,29,0.2)',
                color: 'rgb(254 202 202)',
              }}
            >
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={complete.isPending || !isSessionValid}
            className="mt-2 w-full rounded-lg border py-2.5 text-sm font-semibold tracking-[0.04em] text-sky-300 transition-all active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-60"
            style={{
              background: 'rgba(56,189,248,0.12)',
              borderColor: 'rgba(56,189,248,0.35)',
            }}
            onMouseEnter={e => {
              e.currentTarget.style.background = 'rgba(56,189,248,0.2)';
              e.currentTarget.style.borderColor = 'rgba(56,189,248,0.6)';
            }}
            onMouseLeave={e => {
              e.currentTarget.style.background = 'rgba(56,189,248,0.12)';
              e.currentTarget.style.borderColor = 'rgba(56,189,248,0.35)';
            }}
          >
            {complete.isPending ? 'Completing...' : 'Complete registration →'}
          </button>
        </form>

        <p className="mt-6 text-center text-[13px]" style={{ color: 'rgba(148,163,184,0.5)' }}>
          Already have an account?{' '}
          <Link
            href={paths.auth.login.getHref()}
            className="transition-colors"
            style={{ color: 'rgba(56,189,248,0.8)' }}
            onMouseEnter={e => {
              e.currentTarget.style.color = 'rgba(56,189,248,1)';
            }}
            onMouseLeave={e => {
              e.currentTarget.style.color = 'rgba(56,189,248,0.8)';
            }}
          >
            Back to login
          </Link>
        </p>
      </div>

      <style>{`
        @keyframes pulse-dot {
          0%, 100% { opacity: 0.3; transform: scale(1); }
          50% { opacity: 1; transform: scale(1.5); }
        }

        @keyframes flow-orbit {
          0%   { transform: translate(-50%, -50%) rotate(0deg) scale(1); }
          50%  { transform: translate(-50%, -50%) rotate(180deg) scale(1.03); }
          100% { transform: translate(-50%, -50%) rotate(360deg) scale(1); }
        }

        @keyframes flow-orbit-rev {
          0%   { transform: translate(-50%, -50%) rotate(360deg) scale(0.98); opacity: 0.75; }
          50%  { transform: translate(-50%, -50%) rotate(180deg) scale(1); opacity: 1; }
          100% { transform: translate(-50%, -50%) rotate(0deg) scale(0.98); opacity: 0.75; }
        }
      `}</style>
    </div>
  );
};
