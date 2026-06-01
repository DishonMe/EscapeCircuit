'use client';

import { PawPrint, Settings, Volume2, Wand2 } from 'lucide-react';
import { useEffect, useState } from 'react';

import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown';
import { useSettings } from '@/context/settings-context';
import { cn } from '@/utils/cn';

export const SettingsMenu = () => {
  const {
    soundEnabled,
    setSoundEnabled,
    visualEffectsEnabled,
    setVisualEffectsEnabled,
    colabPetsEnabled,
    setColabPetsEnabled,
    soundVolume,
    setSoundVolume,
  } = useSettings();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <Button
        variant="ghost"
        size="icon"
        className="size-8 rounded-full text-muted-foreground"
        aria-label="Settings"
        disabled
      >
        <Settings className="size-4" />
      </Button>
    );
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className={cn(
            'size-8 rounded-full transition-colors',
            'text-muted-foreground hover:text-foreground hover:bg-secondary',
          )}
          aria-label="Settings"
          title="Settings"
        >
          <Settings className="size-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-64">
        <div className="p-2 text-[13px] font-semibold text-foreground">
          Settings
        </div>
        <DropdownMenuSeparator />

        {/* Sound Effects Toggle */}
        <div className="space-y-3 p-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Volume2 className="size-4 text-muted-foreground" />
              <label
                htmlFor="sound-toggle"
                className="cursor-pointer text-[13px] font-medium text-foreground"
              >
                Sound Effects
              </label>
            </div>
            <button
              id="sound-toggle"
              onClick={() => setSoundEnabled(!soundEnabled)}
              className={cn(
                'relative inline-flex h-5 w-9 items-center rounded-full transition-colors',
                soundEnabled ? 'bg-emerald-600' : 'bg-muted',
              )}
              role="switch"
              aria-checked={soundEnabled}
            >
              <span
                className={cn(
                  'inline-block h-4 w-4 transform rounded-full bg-card transition-transform',
                  soundEnabled ? 'translate-x-4' : 'translate-x-0.5',
                )}
              />
            </button>
          </div>

          {/* Volume Slider */}
          <div
            className={cn(
              'space-y-2',
              !soundEnabled && 'opacity-50 pointer-events-none',
            )}
          >
            <label
              htmlFor="volume-slider"
              className="text-[12px] text-muted-foreground"
            >
              Volume: {Math.round(soundVolume * 100)}%
            </label>
            <input
              id="volume-slider"
              type="range"
              min="0"
              max="100"
              value={Math.round(soundVolume * 100)}
              onChange={(e) => setSoundVolume(parseInt(e.target.value) / 100)}
              disabled={!soundEnabled}
              className="h-1.5 w-full cursor-pointer appearance-none rounded-lg bg-muted outline-none [&::-moz-range-thumb]:size-3.5 [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:border-0 [&::-moz-range-thumb]:bg-emerald-600 [&::-webkit-slider-thumb]:size-3.5 [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-emerald-600"
              aria-label="Sound volume"
            />
          </div>
        </div>

        <DropdownMenuSeparator />

        {/* Visual Effects Toggle */}
        <div className="p-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Wand2 className="size-4 text-muted-foreground" />
              <label
                htmlFor="effects-toggle"
                className="cursor-pointer text-[13px] font-medium text-foreground"
              >
                Visual Effects
              </label>
            </div>
            <button
              id="effects-toggle"
              onClick={() => setVisualEffectsEnabled(!visualEffectsEnabled)}
              className={cn(
                'relative inline-flex h-5 w-9 items-center rounded-full transition-colors',
                visualEffectsEnabled ? 'bg-emerald-600' : 'bg-muted',
              )}
              role="switch"
              aria-checked={visualEffectsEnabled}
            >
              <span
                className={cn(
                  'inline-block h-4 w-4 transform rounded-full bg-card transition-transform',
                  visualEffectsEnabled ? 'translate-x-4' : 'translate-x-0.5',
                )}
              />
            </button>
          </div>
        </div>

        <DropdownMenuSeparator />

        <div className="p-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <PawPrint className="size-4 text-muted-foreground" />
              <label
                htmlFor="colab-pets-toggle"
                className="cursor-pointer text-[13px] font-medium text-foreground"
              >
                Colab Pets
              </label>
            </div>
            <button
              id="colab-pets-toggle"
              onClick={() => setColabPetsEnabled(!colabPetsEnabled)}
              className={cn(
                'relative inline-flex h-5 w-9 items-center rounded-full transition-colors',
                colabPetsEnabled ? 'bg-emerald-600' : 'bg-muted',
              )}
              role="switch"
              aria-checked={colabPetsEnabled}
            >
              <span
                className={cn(
                  'inline-block h-4 w-4 transform rounded-full bg-card transition-transform',
                  colabPetsEnabled ? 'translate-x-4' : 'translate-x-0.5',
                )}
              />
            </button>
          </div>
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  );
};
