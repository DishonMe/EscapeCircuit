'use client';

import { cn } from '@/utils/cn';

type AvatarDisplayProps = {
  avatarName: string;
  avatarColor?: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
};

const SIZE_MAP = {
  sm: 'w-8 h-8',
  md: 'w-12 h-12',
  lg: 'w-16 h-16',
  xl: 'w-24 h-24',
};

const BORDER_MAP = {
  sm: 'border-2',
  md: 'border-2',
  lg: 'border',
  xl: 'border',
};

export const AvatarDisplay = ({
  avatarName,
  avatarColor = '#38bdf8',
  size = 'md',
  className,
}: AvatarDisplayProps) => {
  return (
    <div
      className={cn(
        SIZE_MAP[size],
        BORDER_MAP[size],
        'rounded-2xl border-border overflow-hidden flex-shrink-0',
        className,
      )}
      style={{
        backgroundColor: avatarColor,
      }}
    >
      <img
        src={`/avatars/${avatarName}.png`}
        alt={avatarName}
        className="w-full h-full object-cover"
        loading="lazy"
      />
    </div>
  );
};
