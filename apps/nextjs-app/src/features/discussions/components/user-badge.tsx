'use client';

import { User } from '@/types/api';
import { cn } from '@/utils/cn';

function getLevelBadge(level: number): { label: string; color: string } | null {
  if (level >= 20) return { label: 'Master', color: 'bg-violet-50/50 text-violet-700' };
  if (level >= 10) return { label: 'Expert', color: 'bg-blue-50/50 text-blue-700' };
  if (level >= 5) return { label: 'Regular', color: 'bg-emerald-50/50 text-emerald-700' };
  return null;
}

function getRoleBadge(role: string): { label: string; color: string } | null {
  const r = role?.toLowerCase();
  if (r === 'admin') return { label: 'Admin', color: 'bg-red-50/50 text-red-700' };
  if (r === 'creator') return { label: 'Creator', color: 'bg-amber-50/50 text-amber-700' };
  return null;
}

type UserBadgeProps = {
  user?: Pick<User, 'role' | 'level'> | null;
};

export const UserBadge = ({ user }: UserBadgeProps) => {
  if (!user) return null;

  const roleBadge = getRoleBadge(user.role);
  const levelBadge = getLevelBadge(user.level ?? 0);

  return (
    <>
      {roleBadge && (
        <span
          className={cn(
            'inline-flex items-center rounded-lg px-1 py-0.5 text-[10px] font-semibold leading-none',
            roleBadge.color,
          )}
        >
          {roleBadge.label}
        </span>
      )}
      {levelBadge && (
        <span
          className={cn(
            'inline-flex items-center rounded-lg px-1 py-0.5 text-[10px] font-semibold leading-none',
            levelBadge.color,
          )}
        >
          {levelBadge.label}
        </span>
      )}
    </>
  );
};
