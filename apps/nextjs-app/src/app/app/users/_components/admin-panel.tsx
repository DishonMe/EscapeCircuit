'use client';

import { useState } from 'react';
import { Users, Gamepad2, ClipboardList, Flag } from 'lucide-react';

import { UsersList } from '@/features/users/components/users-list';
import { AdminPuzzlesList } from '@/features/admin/components/admin-puzzles-list';
import { AuditLogList } from '@/features/admin/components/audit-log-list';
import { ReportsList } from '@/features/admin/components/reports-list';
import { cn } from '@/utils/cn';

type Tab = 'users' | 'puzzles' | 'audit' | 'reports';

const tabs: { id: Tab; label: string; icon: any }[] = [
  { id: 'users', label: 'Users', icon: Users },
  { id: 'puzzles', label: 'Puzzles', icon: Gamepad2 },
  { id: 'reports', label: 'Reports', icon: Flag },
  { id: 'audit', label: 'Audit Log', icon: ClipboardList },
];

export const AdminPanel = () => {
  const [activeTab, setActiveTab] = useState<Tab>('users');

  return (
    <div className="space-y-4">
      {/* Tab Navigation */}
      <div className="flex gap-1 border-b border-gray-200">
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px',
                isActive
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
              )}
            >
              <tab.icon className="size-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab Content */}
      {activeTab === 'users' && <UsersList />}
      {activeTab === 'puzzles' && <AdminPuzzlesList />}
      {activeTab === 'reports' && <ReportsList />}
      {activeTab === 'audit' && <AuditLogList />}
    </div>
  );
};
