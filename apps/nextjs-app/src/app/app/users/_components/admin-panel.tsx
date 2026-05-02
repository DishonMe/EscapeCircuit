'use client';

import { useState } from 'react';
import {
  Users,
  Gamepad2,
  ClipboardList,
  Flag,
  ShieldCheck,
  LogIn,
  CheckSquare,
  type LucideIcon,
} from 'lucide-react';

import { PageHero } from '@/components/ui/page-hero/page-hero';
import { UsersList } from '@/features/users/components/users-list';
import { AdminPuzzlesList } from '@/features/admin/components/admin-puzzles-list';
import { AuditLogList } from '@/features/admin/components/audit-log-list';
import { ReportsList } from '@/features/admin/components/reports-list';
import { SolvingAttemptsList } from '@/features/admin/components/solving-attempts-list';
import { AuthAttemptsList } from '@/features/admin/components/auth-attempts-list';
import { cn } from '@/utils/cn';

type Tab = 'users' | 'puzzles' | 'attempts' | 'auth' | 'audit' | 'reports';

const tabs: { id: Tab; label: string; icon: LucideIcon; description: string }[] = [
  {
    id: 'users',
    label: 'Users',
    icon: Users,
    description: 'Manage accounts, roles, and access.',
  },
  {
    id: 'puzzles',
    label: 'Puzzles',
    icon: Gamepad2,
    description: 'Review and moderate community puzzles.',
  },
  {
    id: 'attempts',
    label: 'Solving Attempts',
    icon: CheckSquare,
    description: 'See submitted attempts, outcomes, and boards.',
  },
  {
    id: 'auth',
    label: 'Login/Register Logs',
    icon: LogIn,
    description: 'Track login and registration attempts.',
  },
  {
    id: 'reports',
    label: 'Reports',
    icon: Flag,
    description: 'Triage flagged content and user reports.',
  },
  {
    id: 'audit',
    label: 'Audit Log',
    icon: ClipboardList,
    description: 'Track administrative actions over time.',
  },
];

export const AdminPanel = () => {
  const [activeTab, setActiveTab] = useState<Tab>('users');
  const current = tabs.find((t) => t.id === activeTab) ?? tabs[0];

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <PageHero
        badge="Admin console"
        icon={ShieldCheck}
        title="Admin Panel"
        description="Manage users, moderate puzzles, review reports, and audit platform activity — all in one place."
      />

      {/* Tab Navigation */}
      <div
        role="tablist"
        aria-label="Admin sections"
        className="mb-5 flex flex-wrap items-center gap-2 rounded-2xl border border-border/60 bg-card/60 p-1.5 shadow-sm backdrop-blur"
      >
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              role="tab"
              aria-selected={isActive}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'inline-flex flex-1 items-center justify-center gap-2 rounded-xl px-4 py-2 text-[13px] font-medium transition-all sm:flex-none',
                isActive
                  ? 'bg-gradient-to-r from-primary to-primary/80 text-primary-foreground shadow-sm'
                  : 'text-muted-foreground hover:bg-secondary/60 hover:text-foreground',
              )}
            >
              <tab.icon className="size-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Active tab descriptor */}
      <div className="mb-4 flex items-center gap-2 text-[13px] text-muted-foreground">
        <current.icon className="size-4 text-primary" />
        <span>{current.description}</span>
      </div>

      {/* Tab Content */}
      {activeTab === 'users' && <UsersList />}
      {activeTab === 'puzzles' && <AdminPuzzlesList />}
      {activeTab === 'attempts' && <SolvingAttemptsList />}
      {activeTab === 'auth' && <AuthAttemptsList />}
      {activeTab === 'reports' && <ReportsList />}
      {activeTab === 'audit' && <AuditLogList />}
    </div>
  );
};
