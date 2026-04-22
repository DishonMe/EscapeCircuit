'use client';

import { useState } from 'react';
import { SmilePlus } from 'lucide-react';

import { ReactionCount, ReactionType } from '@/types/api';
import { cn } from '@/utils/cn';

const REACTION_LABELS: Record<ReactionType, { label: string }> = {
  insightful: { label: 'Insightful' },
  helpful: { label: 'Helpful' },
  genius: { label: 'Genius' },
  spot_on: { label: 'Spot On' },
  thinking: { label: 'Thinking' },
};

type ReactionPickerProps = {
  reactions: ReactionCount[];
  userReactions: ReactionType[];
  onReact: (type: string) => void;
  isLoading?: boolean;
};

export const ReactionPicker = ({
  reactions,
  userReactions,
  onReact,
  isLoading,
}: ReactionPickerProps) => {
  const [showPicker, setShowPicker] = useState(false);

  return (
    <div className="flex flex-wrap items-center gap-1">
      {/* Existing reactions */}
      {reactions.map((r) => {
        const config = REACTION_LABELS[r.type];
        if (!config) return null;
        const isActive = userReactions.includes(r.type);
        return (
          <button
            key={r.type}
            className={cn(
              'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] transition-colors',
              isActive
                ? 'border-blue-200/60 bg-blue-50/50 text-blue-700'
                : 'border-border bg-secondary/50 text-muted-foreground hover:border-border',
            )}
            onClick={() => onReact(r.type)}
            disabled={isLoading}
            title={config.label}
          >
            <span>{config.label}</span>
            <span>{r.count}</span>
          </button>
        );
      })}

      {/* Add reaction button */}
      <div className="relative">
        <button
          className="rounded-lg p-1 text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
          onClick={() => setShowPicker(!showPicker)}
          title="Add reaction"
        >
          <SmilePlus className="size-4" />
        </button>

        {showPicker && (
          <>
            <div
              className="fixed inset-0 z-10"
              onClick={() => setShowPicker(false)}
            />
            <div className="absolute bottom-full left-0 z-20 mb-1 flex max-w-[280px] flex-wrap gap-1 rounded-xl border border-border bg-card p-1.5 shadow-elevated">
              {Object.entries(REACTION_LABELS).map(([type, config]) => (
                <button
                  key={type}
                  className={cn(
                    'rounded-lg px-2.5 py-1 text-[12px] font-medium transition-colors hover:bg-secondary',
                    userReactions.includes(type as ReactionType) &&
                      'bg-blue-50/50',
                  )}
                  onClick={() => {
                    onReact(type);
                    setShowPicker(false);
                  }}
                  disabled={isLoading}
                  title={config.label}
                >
                  {config.label}
                </button>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
};
