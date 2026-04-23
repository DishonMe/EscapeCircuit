'use client';

import { Bell, Check, Flower2, Folder, Gamepad2, Home, MessageSquare, Moon, PanelLeft, Shield, Sun, User2, Users, Zap } from 'lucide-react';
import NextLink from 'next/link';
import { useRouter, usePathname } from 'next/navigation';
import { useTheme } from 'next-themes';
import { useEffect, useState } from 'react';
import { ErrorBoundary } from 'react-error-boundary';

import { Button } from '@/components/ui/button';
import { ColabPets } from '@/components/ui/colab-pets/ColabPets';
import { AvatarDisplay } from '@/components/ui/avatar-display';
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
import { useSettings } from '@/context/settings-context';
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
const PALETTE_CHANGE_EVENT = 'escapecircuit:palette-change';
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
  'midnight',
  'forest-night',
  'volcanic',
  'deep-ocean',
  'night-sky',
  'ember-night',
  'violet-noir',
  'evergreen-dark',
  'graphite',
  'ink',
] as const;

type PaletteId = (typeof PALETTES)[number];
type PaletteChangeDetail = { palette: PaletteId | null };

const PALETTE_META: Record<PaletteId, { label: string; swatch: string }> = {
  ruby: {
    label: 'Ruby',
    swatch:
      'linear-gradient(135deg, hsl(350 60% 96%) 0%, hsl(345 55% 90%) 62%, hsl(350 73% 48%) 100%)',
  },
  ocean: {
    label: 'Ocean',
    swatch:
      'linear-gradient(135deg, hsl(202 65% 95%) 0%, hsl(196 65% 88%) 62%, hsl(203 78% 42%) 100%)',
  },
  sunflower: {
    label: 'Sunflower',
    swatch:
      'linear-gradient(135deg, hsl(46 96% 92%) 0%, hsl(52 84% 84%) 62%, hsl(42 88% 45%) 100%)',
  },
  cocoa: {
    label: 'Cocoa',
    swatch:
      'linear-gradient(135deg, hsl(28 45% 92%) 0%, hsl(20 40% 84%) 62%, hsl(24 62% 40%) 100%)',
  },
  mint: {
    label: 'Mint',
    swatch:
      'linear-gradient(135deg, hsl(155 58% 93%) 0%, hsl(164 45% 85%) 62%, hsl(156 62% 38%) 100%)',
  },
  grape: {
    label: 'Grape',
    swatch:
      'linear-gradient(135deg, hsl(274 66% 94%) 0%, hsl(286 50% 86%) 62%, hsl(276 60% 46%) 100%)',
  },
  coral: {
    label: 'Coral',
    swatch:
      'linear-gradient(135deg, hsl(13 88% 94%) 0%, hsl(18 72% 86%) 62%, hsl(12 78% 52%) 100%)',
  },
  teal: {
    label: 'Teal',
    swatch:
      'linear-gradient(135deg, hsl(182 56% 93%) 0%, hsl(175 48% 85%) 62%, hsl(183 68% 38%) 100%)',
  },
  slate: {
    label: 'Slate',
    swatch:
      'linear-gradient(135deg, hsl(220 35% 94%) 0%, hsl(214 30% 87%) 62%, hsl(222 45% 42%) 100%)',
  },
  amber: {
    label: 'Amber',
    swatch:
      'linear-gradient(135deg, hsl(39 92% 93%) 0%, hsl(46 74% 84%) 62%, hsl(36 82% 46%) 100%)',
  },
  midnight: {
    label: 'Midnight',
    swatch:
      'linear-gradient(135deg, hsl(222 32% 10%) 0%, hsl(230 24% 21%) 40%, hsl(210 90% 62%) 74%, hsl(188 82% 58%) 100%)',
  },
  'forest-night': {
    label: 'Forest Night',
    swatch:
      'linear-gradient(135deg, hsl(162 28% 10%) 0%, hsl(170 20% 21%) 40%, hsl(148 60% 50%) 74%, hsl(182 56% 52%) 100%)',
  },
  volcanic: {
    label: 'Volcanic',
    swatch:
      'linear-gradient(135deg, hsl(14 24% 10%) 0%, hsl(6 22% 21%) 40%, hsl(14 80% 60%) 74%, hsl(40 78% 58%) 100%)',
  },
  'deep-ocean': {
    label: 'Deep Ocean',
    swatch:
      'linear-gradient(135deg, hsl(206 38% 10%) 0%, hsl(214 26% 21%) 40%, hsl(198 78% 56%) 74%, hsl(182 70% 52%) 100%)',
  },
  'night-sky': {
    label: 'Night Sky',
    swatch:
      'linear-gradient(135deg, hsl(234 30% 10%) 0%, hsl(246 20% 21%) 40%, hsl(250 80% 68%) 74%, hsl(220 74% 62%) 100%)',
  },
  'ember-night': {
    label: 'Ember Night',
    swatch:
      'linear-gradient(135deg, hsl(18 28% 10%) 0%, hsl(30 20% 21%) 40%, hsl(20 80% 60%) 74%, hsl(42 76% 58%) 100%)',
  },
  'violet-noir': {
    label: 'Violet Noir',
    swatch:
      'linear-gradient(135deg, hsl(274 28% 10%) 0%, hsl(286 20% 21%) 40%, hsl(286 74% 64%) 74%, hsl(248 70% 62%) 100%)',
  },
  'evergreen-dark': {
    label: 'Evergreen Dark',
    swatch:
      'linear-gradient(135deg, hsl(148 26% 10%) 0%, hsl(160 18% 21%) 40%, hsl(146 60% 50%) 74%, hsl(176 60% 50%) 100%)',
  },
  graphite: {
    label: 'Graphite',
    swatch:
      'linear-gradient(135deg, hsl(220 12% 10%) 0%, hsl(210 12% 21%) 40%, hsl(202 72% 60%) 74%, hsl(188 68% 54%) 100%)',
  },
  ink: {
    label: 'Ink',
    swatch:
      'linear-gradient(135deg, hsl(206 22% 8%) 0%, hsl(218 14% 19%) 40%, hsl(190 74% 58%) 74%, hsl(216 74% 64%) 100%)',
  },
};

const isPaletteId = (value: string): value is PaletteId => {
  return PALETTES.includes(value as PaletteId);
};

const emitPaletteChange = (palette: PaletteId | null) => {
  if (typeof window === 'undefined') {
    return;
  }

  window.dispatchEvent(
    new CustomEvent<PaletteChangeDetail>(PALETTE_CHANGE_EVENT, {
      detail: { palette },
    }),
  );
};

const setPaletteTheme = (palette: PaletteId) => {
  document.documentElement.setAttribute('data-palette', palette);
  localStorage.setItem(PALETTE_STORAGE_KEY, palette);
  emitPaletteChange(palette);
};

const clearPaletteTheme = () => {
  document.documentElement.removeAttribute('data-palette');
  localStorage.removeItem(PALETTE_STORAGE_KEY);
  emitPaletteChange(null);
};

const PaletteThemePicker = () => {
  const [mounted, setMounted] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [activePalette, setActivePalette] = useState<PaletteId | null>(null);

  useEffect(() => {
    setMounted(true);
    const saved = localStorage.getItem(PALETTE_STORAGE_KEY);
    if (saved && isPaletteId(saved)) {
      document.documentElement.setAttribute('data-palette', saved);
      setActivePalette(saved);
      return;
    }

    clearPaletteTheme();
  }, []);

  useEffect(() => {
    const handlePaletteChange = (event: Event) => {
      const customEvent = event as CustomEvent<PaletteChangeDetail>;
      setActivePalette(customEvent.detail?.palette ?? null);
    };

    window.addEventListener(PALETTE_CHANGE_EVENT, handlePaletteChange);
    return () => {
      window.removeEventListener(PALETTE_CHANGE_EVENT, handlePaletteChange);
    };
  }, []);

  const applyPalette = (palette: PaletteId) => {
    setPaletteTheme(palette);
    setActivePalette(palette);
  };

  const selectPalette = (palette: PaletteId | null) => {
    if (!palette) {
      clearPaletteTheme();
      setActivePalette(null);
      setMenuOpen(false);
      return;
    }

    applyPalette(palette);
    setMenuOpen(false);
  };

  if (!mounted) {
    return (
      <Button
        variant="ghost"
        size="icon"
        className="size-8 rounded-full text-foreground/70"
        aria-label="Choose color theme"
        disabled
      >
        <Flower2 className="size-4" />
      </Button>
    );
  }

  const currentPaletteLabel = activePalette ? PALETTE_META[activePalette].label : 'Default';

  return (
    <DropdownMenu open={menuOpen} onOpenChange={setMenuOpen}>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className={cn(
            'size-8 rounded-full transition-colors text-muted-foreground hover:bg-secondary hover:text-foreground',
            activePalette && 'text-foreground bg-secondary/70',
          )}
          aria-label="Open color themes"
          title={`Color theme: ${currentPaletteLabel}`}
        >
          <Flower2 className="size-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-72 p-3">
        <div className="mb-2">
          <p className="text-[13px] font-semibold text-foreground">Color Themes</p>
          <p className="text-[11px] text-muted-foreground">Pick a cohesive palette</p>
        </div>

        <button
          type="button"
          onClick={() => selectPalette(null)}
          className={cn(
            'mb-3 flex w-full items-center justify-between rounded-md border px-2.5 py-2 text-left transition-colors',
            activePalette === null
              ? 'border-foreground/25 bg-secondary text-foreground'
              : 'border-border bg-card text-muted-foreground hover:bg-secondary/60 hover:text-foreground',
          )}
          aria-label="Use default theme colors"
        >
          <span className="text-[12px] font-medium">Default</span>
          <span className="inline-flex size-5 rounded-full border border-border bg-[linear-gradient(135deg,hsl(var(--background)),hsl(var(--secondary)))]" />
        </button>

        <div className="grid grid-cols-5 gap-2">
          {PALETTES.map((palette) => {
            const isActive = activePalette === palette;
            const meta = PALETTE_META[palette];

            return (
              <button
                key={palette}
                type="button"
                onClick={() => selectPalette(palette)}
                aria-label={`Apply ${meta.label} palette`}
                title={meta.label}
                className={cn(
                  'relative h-10 rounded-md border border-border transition-all hover:scale-105 hover:border-foreground/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                  isActive && 'border-foreground/40 ring-2 ring-ring/40',
                )}
                style={{ background: meta.swatch }}
              >
                <span className="sr-only">{meta.label}</span>
                {isActive && (
                  <span className="absolute inset-0 grid place-items-center rounded-md bg-black/12">
                    <Check className="size-4 text-white drop-shadow-sm" />
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  );
};

const Layout = ({ children }: { children: React.ReactNode }) => {
  const user = useUser();
  const { colabPetsEnabled } = useSettings();
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
      {colabPetsEnabled && <ColabPets topOffsetPx={56} stripHeightPx={76} />}

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
          <PaletteThemePicker />
          <SettingsMenu />
          <div className="hidden md:flex items-center gap-2 text-[13px]">
            <AvatarDisplay
              avatarName={user.data?.avatar_name ?? 'Dinosaur'}
              avatarColor={user.data?.avatar_color ?? '#38bdf8'}
              size="sm"
            />
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
