'use client';

import { useEffect, useRef, useState } from 'react';

type PetDirection = 'ltr' | 'rtl';

type Pet = {
  id: number;
  emoji: string;
  durationSec: number;
  verticalOffsetPx: number;
  direction: PetDirection;
};

type ColabPetsProps = {
  topOffsetPx?: number;
  stripHeightPx?: number;
};

const PET_EMOJIS = ['🐕', '🐈', '🦀'];

const randomBetween = (min: number, max: number) => {
  return Math.random() * (max - min) + min;
};

const pickRandom = <T,>(items: T[]): T => {
  return items[Math.floor(Math.random() * items.length)];
};

export function ColabPets({ topOffsetPx = 0, stripHeightPx }: ColabPetsProps) {
  const [pets, setPets] = useState<Pet[]>([]);
  const nextIdRef = useRef(1);
  const inStripMode = typeof stripHeightPx === 'number';

  useEffect(() => {
    let cancelled = false;
    let timeoutId: ReturnType<typeof setTimeout> | null = null;

    const scheduleSpawn = () => {
      const delayMs = randomBetween(1800, 4200);
      timeoutId = setTimeout(() => {
        if (cancelled) return;

        const maxOffset = inStripMode
          ? Math.max(16, (stripHeightPx as number) - 34)
          : Math.max(120, window.innerHeight - 48);

        const newPet: Pet = {
          id: nextIdRef.current++,
          emoji: pickRandom(PET_EMOJIS),
          durationSec: randomBetween(8, 16),
          verticalOffsetPx: randomBetween(6, maxOffset),
          direction: Math.random() > 0.5 ? 'ltr' : 'rtl',
        };

        setPets((prev) => [...prev, newPet]);
        scheduleSpawn();
      }, delayMs);
    };

    scheduleSpawn();

    return () => {
      cancelled = true;
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, [inStripMode, stripHeightPx]);

  const removePet = (id: number) => {
    setPets((prev) => prev.filter((pet) => pet.id !== id));
  };

  return (
    <div
      className="pointer-events-none fixed left-0 w-full overflow-hidden"
      style={{
        top: `${topOffsetPx}px`,
        height: inStripMode ? `${stripHeightPx}px` : '100vh',
        zIndex: 25,
      }}
      aria-hidden="true"
    >
      {pets.map((pet) => {
        const animationName =
          pet.direction === 'ltr' ? 'colab-pet-ltr' : 'colab-pet-rtl';

        return (
          <span
            key={pet.id}
            className="pointer-events-none absolute select-none"
            style={{
              top: `${pet.verticalOffsetPx}px`,
              fontSize: '28px',
              lineHeight: 1,
              willChange: 'transform',
              animation: `${animationName} ${pet.durationSec}s linear forwards`,
            }}
            onAnimationEnd={() => removePet(pet.id)}
          >
            <span
              className="block"
              style={{
                display: 'inline-block',
                transform: pet.direction === 'ltr' ? 'scaleX(-1)' : 'scaleX(1)',
              }}
            >
              {pet.emoji}
            </span>
          </span>
        );
      })}

      <style jsx>{`
        @keyframes colab-pet-ltr {
          from {
            transform: translateX(-60px);
          }
          to {
            transform: translateX(calc(100vw + 60px));
          }
        }

        @keyframes colab-pet-rtl {
          from {
            transform: translateX(calc(100vw + 60px));
          }
          to {
            transform: translateX(-60px);
          }
        }
      `}</style>

      {/*
        Usage in root layout/page:

        1) Import the component:
           import { ColabPets } from '@/components/ui/colab-pets/colab-pets';

        2) Render once near the app root, for example in layout.tsx:
           <body>
             <ColabPets />
             {children}
           </body>

        Because the component is fixed + pointer-events-none, it will float above the UI
        without blocking clicks.
      */}
    </div>
  );
}
