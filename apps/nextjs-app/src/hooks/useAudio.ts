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

const SOUND_MAP: Record<AudioSoundType, string> = {
  drop: '/sounds/drop-thud.mp3',
  wire: '/sounds/wire-bloop.mp3',
  error: '/sounds/error-buzz.mp3',
  success: '/sounds/success-chime.mp3',
};

export const useAudio = () => {
  const playSound = useCallback((soundType: AudioSoundType, volume: number = 0.6) => {
    try {
      const audio = new Audio(SOUND_MAP[soundType]);
      audio.volume = Math.max(0, Math.min(1, volume)); // Clamp between 0 and 1
      audio.play().catch((err) => {
        // Silently fail if audio playback fails (browser policy, file not found, etc.)
        console.debug(`Audio playback failed for ${soundType}:`, err);
      });
    } catch (err) {
      // Silently fail if Audio constructor fails
      console.debug(`Failed to create audio element for ${soundType}:`, err);
    }
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
