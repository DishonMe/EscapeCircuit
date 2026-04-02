'use client';

import { Folder, Home, PanelLeft, MessageSquare, Users, User2, Gamepad2, Zap, Bell, Shield, Moon, Sun, Flower2 } from 'lucide-react';
import NextLink from 'next/link';
import { useRouter, usePathname } from 'next/navigation';
import { useTheme } from 'next-themes';
import { useEffect, useState } from 'react';
import { ErrorBoundary } from 'react-error-boundary';

import { Button } from '@/components/ui/button';
import { Drawer, DrawerContent, DrawerTrigger } from '@/components/ui/drawer';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown';
import { Link } from '@/components/ui/link';
import { SettingsMenu } from '@/components/ui/settings-menu';
import { XPBar } from '@/components/ui/xp-bar';
import { paths } from '@/config/paths';
import { useLogout, useUser } from '@/lib/auth';
import { cn } from '@/utils/cn';
import { CreatorInviteBanner } from '@/features/admin/components/creator-invite-banner';

type SideNavigationItem = {
  name: string;
  to: string;
  icon: (props: React.SVGProps<SVGSVGElement>) => JSX.Element;
};

const Logo = () => {
  return (
    <Link
      className="flex items-center gap-1.5"
      href={paths.home.getHref()}
    >
      <img src="/logo.svg" alt="EscapeCircuit" className="h-7 w-7 shrink-0" />
      <span className="text-[15px] font-semibold tracking-tight text-foreground">
        EscapeCircuit
      </span>
    </Link>
  );
};

const ThemeToggle = () => {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <Button
        variant="ghost"
        size="icon"
        className="size-8 rounded-full text-yellow-500 dark:text-slate-300"
        aria-label="Toggle dark mode"
      >
        <Sun className="size-4" />
      </Button>
    );
  }

  const isDark = resolvedTheme === 'dark';

  return (
    <Button
      variant="ghost"
      size="icon"
      className={cn(
        'size-8 rounded-full transition-colors',
        isDark
          ? 'bg-slate-800 text-slate-100 hover:bg-slate-700'
          : 'text-yellow-500 hover:text-yellow-600 hover:bg-yellow-50/50',
      )}
      onClick={() => {
        clearPaletteTheme();
        setTheme(isDark ? 'light' : 'dark');
      }}
      aria-label="Toggle dark mode"
      title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
    >
      {isDark ? (
        <Moon className="size-4" />
      ) : (
        <Sun className="size-4" />
      )}
    </Button>
  );
};

const PALETTE_STORAGE_KEY = 'escapecircuit-palette';
const PALETTES = [
  'ruby',
  'ocean',
  'sunflower',
  'cocoa',
  'mint',
  'grape',
  'coral',
  'teal',
  'slate',
  'amber',
] as const;

const clearPaletteTheme = () => {
  document.documentElement.removeAttribute('data-palette');
  localStorage.removeItem(PALETTE_STORAGE_KEY);
};

const PaletteShuffleToggle = () => {
  const [mounted, setMounted] = useState(false);
  const [activePalette, setActivePalette] = useState<string | null>(null);

  useEffect(() => {
    setMounted(true);
    const saved = localStorage.getItem(PALETTE_STORAGE_KEY);
    if (saved && PALETTES.includes(saved as (typeof PALETTES)[number])) {
      document.documentElement.setAttribute('data-palette', saved);
      setActivePalette(saved);
    }
  }, []);

  const applyPalette = (palette: string) => {
    document.documentElement.setAttribute('data-palette', palette);
    localStorage.setItem(PALETTE_STORAGE_KEY, palette);
    setActivePalette(palette);
  };

  const shufflePalette = () => {
    const nextPool = PALETTES.filter((palette) => palette !== activePalette);
    const nextPalette = nextPool[Math.floor(Math.random() * nextPool.length)] || PALETTES[0];
    applyPalette(nextPalette);
  };

  if (!mounted) {
    return (
      <Button
        variant="ghost"
        size="icon"
        className="size-8 rounded-full text-foreground/70"
        aria-label="Shuffle color theme"
        disabled
      >
        <Flower2 className="size-4" />
      </Button>
    );
  }

  return (
    <Button
      variant="ghost"
      size="icon"
      className="size-8 rounded-full transition-colors text-pink-600 hover:bg-pink-50 dark:text-pink-300 dark:hover:bg-pink-950/40"
      onClick={shufflePalette}
      aria-label="Shuffle color theme"
      title={`Shuffle color theme${activePalette ? ` (current: ${activePalette})` : ''}`}
    >
      <Flower2 className="size-4" />
    </Button>
  );
};

const Layout = ({ children }: { children: React.ReactNode }) => {
  const user = useUser();
  const pathname = usePathname();
  const router = useRouter();
  const logout = useLogout({
    onSuccess: () => router.push(paths.auth.login.getHref(pathname)),
  });
  const userRole = user.data?.role?.toLowerCase() || '';
  const isExperienced = (user.data?.level ?? 0) >= 5;
  const navigation = [
    { name: 'Puzzles', to: paths.app.puzzles.getHref(), icon: Gamepad2 },
    (userRole === 'creator' || userRole === 'admin') && {
      name: 'My Puzzles',
      to: paths.app.myPuzzles.getHref(),
      icon: Folder,
    },
    { name: 'Arsenal', to: paths.app.arsenal.root.getHref(), icon: Zap },
    {
      name: 'Discussions',
      to: paths.app.discussions.getHref(),
      icon: MessageSquare,
    },
    (userRole === 'creator' || userRole === 'admin') && {
      name: 'Notifications',
      to: paths.app.notifications.getHref(),
      icon: Bell,
    },
    userRole === 'admin' && {
      name: 'Admin',
      to: paths.app.users.getHref(),
      icon: Shield,
    },
  ].filter(Boolean) as SideNavigationItem[];

  return (
    <div className="flex min-h-screen w-full flex-col bg-background">
      <header className="sticky top-0 z-30 flex h-14 items-center justify-between gap-4 border-b bg-card/80 backdrop-blur-sm px-5">
        <div className="flex items-center gap-8">
          <Logo />
          <nav className="hidden sm:flex items-center gap-0.5">
            {navigation.map((item) => {
              const isActive = pathname === item.to;
              return (
                <NextLink
                  key={item.name}
                  href={item.to}
                  className={cn(
                    'text-muted-foreground hover:text-foreground',
                    'group flex items-center rounded-md px-3 py-1.5 text-[13px] font-medium transition-colors',
                    isActive && 'bg-secondary text-foreground',
                  )}
                >
                  <item.icon
                    className={cn(
                      'text-muted-foreground/60 group-hover:text-foreground/70 mr-1.5 size-3.5 shrink-0',
                      isActive && 'text-foreground/70',
                    )}
                    aria-hidden="true"
                  />
                  <span className="hidden md:inline">{item.name}</span>
                </NextLink>
              );
            })}
          </nav>
        </div>
        <div className="flex items-center gap-3">
          <XPBar currentXP={user.data?.xp ?? 0} />
          <ThemeToggle />
          <PaletteShuffleToggle />
          <SettingsMenu />
          <div className="hidden md:flex items-center gap-2 text-[13px]">
            <span className="font-medium text-foreground">{user.data?.username}</span>
            <span className="text-border">|</span>
            <span className="text-muted-foreground capitalize">{user.data?.role}</span>
            {isExperienced && (
              <>
                <span className="text-border">|</span>
                <span className="rounded-md bg-emerald-50 px-1.5 py-0.5 text-[11px] font-semibold text-emerald-700">
                  Experienced
                </span>
              </>
            )}
          </div>
          <Drawer>
            <DrawerTrigger asChild>
              <Button size="icon" variant="ghost" className="sm:hidden size-8">
                <PanelLeft className="size-4" />
                <span className="sr-only">Toggle Menu</span>
              </Button>
            </DrawerTrigger>
            <DrawerContent
              side="left"
              className="bg-card pt-10 text-foreground sm:max-w-60"
            >
              <nav className="grid gap-1 px-3 text-sm font-medium">
                <div className="flex h-12 shrink-0 items-center px-2 mb-4">
                  <Logo />
                </div>
                {navigation.map((item) => {
                  const isActive = pathname === item.to;
                  return (
                    <NextLink
                      key={item.name}
                      href={item.to}
                      className={cn(
                        'text-muted-foreground hover:text-foreground hover:bg-secondary',
                        'group flex items-center rounded-md px-3 py-2 text-[13px] font-medium transition-colors',
                        isActive && 'bg-secondary text-foreground',
                      )}
                    >
                      <item.icon
                        className={cn(
                          'text-muted-foreground/60 group-hover:text-foreground/70 mr-2.5 size-4 shrink-0',
                          isActive && 'text-foreground/70',
                        )}
                        aria-hidden="true"
                      />
                      {item.name}
                    </NextLink>
                  );
                })}
              </nav>
            </DrawerContent>
          </Drawer>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="size-8 rounded-full"
              >
                <span className="sr-only">Open user menu</span>
                <User2 className="size-4 text-foreground" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem
                onClick={() => router.push(paths.app.profile.getHref())}
                className={cn('block px-3 py-1.5 text-[13px] text-foreground cursor-pointer')}
              >
                Your Profile
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                className={cn('block px-3 py-1.5 text-[13px] text-foreground w-full cursor-pointer')}
                onClick={() => logout.mutate()}
              >
                Sign Out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </header>
      <main className="flex-1 px-5 py-5 md:px-8 md:py-6">
          <CreatorInviteBanner />
          {children}
        </main>
    </div>
  );
};

function Fallback({ error }: { error: Error }) {
  return <p>Error: {error.message ?? 'Something went wrong!'}</p>;
}

export const DashboardLayout = ({
  children,
}: {
  children: React.ReactNode;
}) => {
  const pathname = usePathname();
  return (
    <Layout>
      <ErrorBoundary key={pathname} FallbackComponent={Fallback}>
        {children}
      </ErrorBoundary>
    </Layout>
  );
};
