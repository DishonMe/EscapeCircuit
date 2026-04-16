'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import NextLink from 'next/link';

import Cookies from 'js-cookie';

import { Button } from '@/components/ui/button';
import { paths } from '@/config/paths';
import { useUser } from '@/lib/auth';
import { AUTH_TOKEN_COOKIE_NAME } from '@/utils/auth-constants';

const HomePage = () => {
  const router = useRouter();
  // Defer cookie read to useEffect to avoid SSR/client hydration mismatch
  const [hasToken, setHasToken] = useState(false);
  const user = useUser();

  useEffect(() => {
    setHasToken(!!Cookies.get(AUTH_TOKEN_COOKIE_NAME));
  }, []);

  useEffect(() => {
    // No cookie means definitely not logged in — stay on landing
    if (!hasToken) return;
    // Wait for auth query to resolve, then route appropriately
    if (user.status === 'pending') return;
    if (user.data) {
      router.replace(paths.app.puzzles.getHref());
    }
  }, [user.status, user.data, router, hasToken]);

  // No cookie → show landing immediately (no need to wait for API)
  const showLanding = hasToken ? (user.status !== 'pending' && !user.data) : true;

  return (
    <div className="flex min-h-screen flex-col bg-background">
      {/* Header */}
      <header className="flex items-center justify-between border-b border-border bg-card/80 backdrop-blur-sm px-4 py-3 sm:px-6 sm:py-4">
        <div className="flex items-center gap-2 sm:gap-3 min-w-0">
          <img className="h-7 w-auto sm:h-8 shrink-0" src="/logo.svg" alt="EscapeCircuit" />
          <span className="text-base font-semibold text-foreground sm:text-xl">EscapeCircuit</span>
        </div>
        {showLanding ? (
          <div className="flex items-center gap-1.5 sm:gap-3 shrink-0">
            <NextLink href={paths.auth.login.getHref()}>
              <Button variant="outline" size="sm">Log in</Button>
            </NextLink>
            <NextLink href={paths.auth.register.getHref()}>
              <Button size="sm">Register</Button>
            </NextLink>
          </div>
        ) : (
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-foreground/30 border-t-transparent" />
        )}
      </header>

      {/* Hero */}
      <main className="flex flex-1 flex-col items-center justify-center px-4 py-16">
        <div className="max-w-2xl text-center">
          <img className="mx-auto mb-8 h-24 w-auto" src="/logo.svg" alt="" />
          <h1 className="text-3xl font-semibold tracking-tight text-foreground sm:text-5xl">
            Wire your way out ⚡
          </h1>
          <p className="mt-4 text-base text-muted-foreground sm:text-lg">
            Create and solve logic-circuit puzzles, compete on the leaderboard,
            and discuss strategies with the community.
          </p>

          {showLanding && (
            <div className="mt-10 flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
              <NextLink href={paths.auth.register.getHref()}>
                <Button className="w-48 py-3 text-base">Get Started</Button>
              </NextLink>
              <NextLink href={paths.auth.login.getHref()}>
                <Button variant="outline" className="w-48 py-3 text-base">
                  Log in
                </Button>
              </NextLink>
            </div>
          )}
        </div>

        {/* Feature highlights */}
        {showLanding && (
          <div className="mt-20 grid max-w-4xl grid-cols-1 gap-8 sm:grid-cols-3">
            <div className="rounded-xl border border-border bg-card p-6 text-center shadow-card">
              <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-secondary text-2xl">
                <span role="img" aria-label="Puzzle">&#x1F9E9;</span>
              </div>
              <h3 className="font-semibold text-foreground">Solve Puzzles</h3>
              <p className="mt-1 text-[13px] text-muted-foreground">
                Challenge yourself with logic-circuit puzzles of varying difficulty.
              </p>
            </div>
            <div className="rounded-xl border border-border bg-card p-6 text-center shadow-card">
              <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-secondary text-2xl">
                <span role="img" aria-label="Trophy">&#x1F3C6;</span>
              </div>
              <h3 className="font-semibold text-foreground">Earn XP</h3>
              <p className="mt-1 text-[13px] text-muted-foreground">
                Gain experience points, level up, and climb the leaderboard.
              </p>
            </div>
            <div className="rounded-xl border border-border bg-card p-6 text-center shadow-card">
              <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-secondary text-2xl">
                <span role="img" aria-label="Discussion">&#x1F4AC;</span>
              </div>
              <h3 className="font-semibold text-foreground">Discuss</h3>
              <p className="mt-1 text-[13px] text-muted-foreground">
                Share tips, ask for help, and connect with the community.
              </p>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-border bg-card px-6 py-4 text-center text-[11px] text-muted-foreground">
        EscapeCircuit &mdash; Wire your way out.
      </footer>
    </div>
  );
};

export default HomePage;
