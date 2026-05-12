/**
 * Hook for playing UI sound effects in the puzzle workstation.
 * Uses native Audio API with graceful fallback if sounds aren't available.
 * Sound files should be placed in /public/sounds/ directory.
 * Respects user settings for sound enabled state and volume control.
 * 
 * Usage:
 *   const { playDrop, playWireConnect, playError, playSuccess } = useAudio();
 *   playDrop(); // Play component drop sound
 */

'use client';

import { useCallback } from 'react';
import { useSettings } from '@/context/settings-context';

export type AudioSoundType = 'drop' | 'wire' | 'error' | 'success';

const SOUND_MAP: Record<AudioSoundType, string[]> = {
  drop: ['/sounds/drop.mp3', '/sounds/drop-thud.mp3'],
  wire: ['/sounds/wire.mp3', '/sounds/wire-bloop.mp3'],
  error: ['/sounds/error.mp3', '/sounds/error-buzz.mp3'],
  success: ['/sounds/success-chime.mp3'],
};

const resolvedSources = new Map<AudioSoundType, string | null>();

export const useAudio = () => {
  const { soundEnabled, soundVolume } = useSettings();

  const playSound = useCallback((soundType: AudioSoundType, baseVolume: number = 0.6) => {
    // Don't play sound if sound effects are disabled
    if (!soundEnabled) return;

    const cached = resolvedSources.get(soundType);
    const candidates = cached ? [cached] : SOUND_MAP[soundType];

    const tryPlay = (index: number) => {
      const source = candidates[index];
      if (!source) return;

      try {
        const audio = new Audio(source);
        // Use the user's selected volume multiplied by the base volume for specific sound types
        audio.volume = Math.max(0, Math.min(1, baseVolume * soundVolume));
        const playResult = audio.play();
        if (typeof playResult?.then === 'function') {
          playResult
            .then(() => {
              resolvedSources.set(soundType, source);
            })
            .catch(() => {
              tryPlay(index + 1);
            });
        }
      } catch {
        tryPlay(index + 1);
      }

      // For browsers where play() returns void, keep first source best-effort only.
    };

    tryPlay(0);
  }, [soundEnabled, soundVolume]);

  const playDrop = useCallback(() => {
    playSound('drop', 0.7);
  }, [playSound]);

  const playWireConnect = useCallback(() => {
    playSound('wire', 0.5);
  }, [playSound]);

  const playError = useCallback(() => {
    playSound('error', 0.65);
  }, [playSound]);

  const playSuccess = useCallback(() => {
    playSound('success', 0.7);
  }, [playSound]);

  return { playDrop, playWireConnect, playError, playSuccess };
};
