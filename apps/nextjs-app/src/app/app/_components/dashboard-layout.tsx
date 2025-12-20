'use client';

import { Home, PanelLeft, Folder, Users, User2, Gamepad2 } from 'lucide-react';
import NextLink from 'next/link';
import { useRouter, usePathname } from 'next/navigation';
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
import { paths } from '@/config/paths';
import { useLogout, useUser } from '@/lib/auth';
import { cn } from '@/utils/cn';

type SideNavigationItem = {
  name: string;
  to: string;
  icon: (props: React.SVGProps<SVGSVGElement>) => JSX.Element;
};

const Logo = () => {
  return (
    <Link
      className="flex items-center text-gray-900"
      href={paths.home.getHref()}
    >
      <span className="text-lg font-bold text-gray-900">EscapeCircuit</span>
    </Link>
  );
};

const Layout = ({ children }: { children: React.ReactNode }) => {
  const user = useUser();
  const pathname = usePathname();
  const router = useRouter();
  const logout = useLogout({
    onSuccess: () => router.push(paths.auth.login.getHref(pathname)),
  });
  const navigation = [
    { name: 'Dashboard', to: paths.app.root.getHref(), icon: Home },
    { name: 'Puzzles', to: paths.app.puzzles.getHref(), icon: Gamepad2 },
    { name: 'Discussions', to: paths.app.discussions.getHref(), icon: Folder },
    user.data?.role === 'ADMIN' && {
      name: 'Users',
      to: paths.app.users.getHref(),
      icon: Users,
    },
  ].filter(Boolean) as SideNavigationItem[];

  return (
    <div className="flex min-h-screen w-full flex-col bg-gray-50">
      <aside className="fixed inset-y-0 left-0 z-10 hidden w-60 flex-col border-r border-gray-300 bg-white sm:flex">
        <nav className="flex flex-col gap-4 px-4 py-6">
          <div className="flex h-16 shrink-0 items-center px-4">
            <Logo />
          </div>
          {navigation.map((item) => {
            const isActive = pathname === item.to;
            return (
              <NextLink
                key={item.name}
                href={item.to}
                className={cn(
                  'text-gray-600 hover:bg-gray-100 hover:text-gray-900',
                  'group flex items-center rounded-md px-3 py-2 text-sm font-medium transition-colors',
                  isActive && 'bg-blue-50 text-blue-700',
                )}
              >
                <item.icon
                  className={cn(
                    'text-gray-400 group-hover:text-gray-500 mr-3 size-5 shrink-0',
                    isActive && 'text-blue-500',
                  )}
                  aria-hidden="true"
                />
                {item.name}
              </NextLink>
            );
          })}
        </nav>
      </aside>
      <div className="flex flex-col sm:gap-4 sm:py-4 sm:pl-60">
        <header className="sticky top-0 z-30 flex h-14 items-center justify-between gap-4 border-b border-gray-300 bg-white px-4 sm:static sm:h-auto sm:justify-end sm:border-0 sm:bg-transparent sm:px-6">
          {/* <Progress /> */}
          <Drawer>
            <DrawerTrigger asChild>
              <Button size="icon" variant="outline" className="sm:hidden">
                <PanelLeft className="size-5" />
                <span className="sr-only">Toggle Menu</span>
              </Button>
            </DrawerTrigger>
            <DrawerContent
              side="left"
              className="bg-white pt-10 text-gray-900 sm:max-w-60"
            >
              <nav className="grid gap-6 text-lg font-medium">
                <div className="flex h-16 shrink-0 items-center px-4">
                  <Logo />
                </div>
                {navigation.map((item) => {
                  const isActive = pathname === item.to;
                  return (
                    <NextLink
                      key={item.name}
                      href={item.to}
                      className={cn(
                        'text-gray-600 hover:bg-gray-100 hover:text-gray-900',
                        'group flex items-center rounded-md px-3 py-2 text-sm font-medium transition-colors',
                        isActive && 'bg-blue-50 text-blue-700',
                      )}
                    >
                      <item.icon
                        className={cn(
                          'text-gray-400 group-hover:text-gray-500 mr-3 size-5 shrink-0',
                          isActive && 'text-blue-500',
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
                variant="outline"
                size="icon"
                className="overflow-hidden rounded-full"
              >
                <span className="sr-only">Open user menu</span>
                <User2 className="size-6 rounded-full" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem
                onClick={() => router.push(paths.app.profile.getHref())}
                className={cn('block px-4 py-2 text-sm text-gray-700')}
              >
                Your Profile
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                className={cn('block px-4 py-2 text-sm text-gray-700 w-full')}
                onClick={() => logout.mutate()}
              >
                Sign Out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </header>
        <main className="grid flex-1 items-start gap-4 p-4 sm:px-6 sm:py-0 md:gap-8">
          {children}
        </main>
      </div>
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
