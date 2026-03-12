/**
 * Hook for playing UI sound effects in the puzzle workstation.
 * Uses native Audio API with graceful fallback if sounds aren't available.
 * Sound files should be placed in /public/sounds/ directory.
 * 
 * Usage:
 *   const { playDrop, playBloop, playError, playSuccess } = useAudio();
 *   playDrop(); // Play component drop sound
 */

import { useCallback } from 'react';

export type AudioSoundType = 'drop' | 'wire' | 'error' | 'success';

const SOUND_MAP: Record<AudioSoundType, string[]> = {
  drop: ['/sounds/drop.mp3', '/sounds/drop-thud.mp3'],
  wire: ['/sounds/wire.mp3', '/sounds/wire-bloop.mp3'],
  error: ['/sounds/error.mp3', '/sounds/error-buzz.mp3'],
  success: ['/sounds/success.mp3', '/sounds/success-chime.mp3'],
};

const resolvedSources = new Map<AudioSoundType, string | null>();

export const useAudio = () => {
  const playSound = useCallback((soundType: AudioSoundType, volume: number = 0.6) => {
    const cached = resolvedSources.get(soundType);
    const candidates = cached ? [cached] : SOUND_MAP[soundType];

    const tryPlay = (index: number) => {
      const source = candidates[index];
      if (!source) return;

      try {
        const audio = new Audio(source);
        audio.volume = Math.max(0, Math.min(1, volume));
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
  }, []);

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
