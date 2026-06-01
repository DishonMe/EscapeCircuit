'use client';

import { useEffect, useRef } from 'react';

interface ZigzagBugCanvasProps {
  containerRef: React.RefObject<HTMLButtonElement>;
}

interface BugState {
  x: number; // X position (0 to canvas.width)
  y: number; // Y position (0 to canvas.height)
  targetRotation: number; // Target rotation in radians (0 = up, π/2 = right, π = down, -π/2 = left)
  currentRotation: number; // Current rotation in radians
  isWalking: boolean; // Whether we're currently walking
  isIdle: boolean;
  speed: number;
  targetSpeed: number;
  burstTime: number;
  walkUntil: number;
  idleUntil: number;
  isTurning: boolean;
  turnStartTime: number;
  turnDuration: number;
  turnStartRotation: number;
}

export const ZigzagBugCanvas = ({ containerRef }: ZigzagBugCanvasProps) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const bugStateRef = useRef<BugState>({
    x: 0,
    y: 0,
    targetRotation: 0,
    currentRotation: 0,
    isWalking: false,
    isIdle: false,
    speed: 0.5,
    targetSpeed: 0.5,
    burstTime: 0,
    walkUntil: 0,
    idleUntil: 0,
    isTurning: false,
    turnStartTime: 0,
    turnDuration: 0,
    turnStartRotation: 0,
  });
  const animationFrameRef = useRef<number>();

  const drawBug = (
    ctx: CanvasRenderingContext2D,
    x: number,
    y: number,
    rotation: number,
    legPhase: number,
  ) => {
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(rotation);

    // Body (oval red)
    ctx.fillStyle = '#DC2626';
    ctx.beginPath();
    ctx.ellipse(0, 0, 5, 7, 0, 0, Math.PI * 2);
    ctx.fill();

    // Spots on body
    ctx.fillStyle = '#000000';
    ctx.beginPath();
    ctx.arc(-2.5, -2, 1, 0, Math.PI * 2);
    ctx.fill();
    ctx.beginPath();
    ctx.arc(2.5, -2, 1, 0, Math.PI * 2);
    ctx.fill();

    // Center line
    ctx.strokeStyle = '#000000';
    ctx.lineWidth = 0.5;
    ctx.beginPath();
    ctx.moveTo(0, -7);
    ctx.lineTo(0, 7);
    ctx.stroke();

    // Head
    ctx.fillStyle = '#000000';
    ctx.beginPath();
    ctx.arc(0, -8, 3, 0, Math.PI * 2);
    ctx.fill();

    // Eyes
    ctx.fillStyle = '#FFFFFF';
    ctx.beginPath();
    ctx.arc(-1, -8.5, 0.8, 0, Math.PI * 2);
    ctx.fill();
    ctx.beginPath();
    ctx.arc(1, -8.5, 0.8, 0, Math.PI * 2);
    ctx.fill();

    // Antennae (animated with walking phase)
    const antennaWiggle = Math.sin(legPhase * 0.5) * 1;
    ctx.strokeStyle = '#000000';
    ctx.lineWidth = 0.8;
    ctx.beginPath();
    ctx.moveTo(-1, -10);
    ctx.quadraticCurveTo(
      -3 + antennaWiggle * 0.5,
      -12,
      -4 + antennaWiggle,
      -14,
    );
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(1, -10);
    ctx.quadraticCurveTo(3 - antennaWiggle * 0.5, -12, 4 - antennaWiggle, -14);
    ctx.stroke();

    // Legs (6 total, 3 on each side) - natural walking gait
    const legOffsets = [-4, 0, 4];

    legOffsets.forEach((offset, idx) => {
      // Each leg has different phase for realistic gait pattern
      const legPhaseOffset = (idx * Math.PI * 2) / 3; // 120° phase offset between legs

      // Left legs
      const leftPhase = (legPhase + legPhaseOffset) % (Math.PI * 2);
      // Create smooth leg motion: swing forward (0-π), then back (π-2π)
      const leftLegBend = Math.sin(leftPhase) * 3;
      const leftLegHeight = Math.cos(leftPhase * 0.5) * 1.5;

      ctx.strokeStyle = '#000000';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(-6, offset + leftLegHeight);
      ctx.quadraticCurveTo(
        -9 + leftLegBend,
        offset + 2 + leftLegHeight,
        -8,
        offset + 4 + leftLegHeight,
      );
      ctx.stroke();

      // Right legs
      const rightPhase = (legPhase + legPhaseOffset + Math.PI) % (Math.PI * 2);
      const rightLegBend = Math.sin(rightPhase) * 3;
      const rightLegHeight = Math.cos(rightPhase * 0.5) * 1.5;

      ctx.beginPath();
      ctx.moveTo(6, offset + rightLegHeight);
      ctx.quadraticCurveTo(
        9 - rightLegBend,
        offset + 2 + rightLegHeight,
        8,
        offset + 4 + rightLegHeight,
      );
      ctx.stroke();
    });

    ctx.restore();
  };

  const animate = (now: number) => {
    const canvas = canvasRef.current;
    const button = containerRef.current;
    if (!canvas || !button) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const state = bugStateRef.current;
    const width = canvas.width;
    const height = canvas.height;
    const padding = 8;
    const minX = padding;
    const maxX = width - padding;
    const minY = padding;
    const maxY = height - padding;

    const getRandomDirection = (previousDirection?: number) => {
      const normalize = (angle: number) => {
        let value = angle;
        while (value > Math.PI) value -= Math.PI * 2;
        while (value < -Math.PI) value += Math.PI * 2;
        return value;
      };

      const clearanceDistance = (angle: number) => {
        const dx = Math.sin(angle);
        const dy = -Math.cos(angle);
        const limits: number[] = [];

        if (Math.abs(dx) > 1e-6) {
          if (dx > 0) {
            limits.push((maxX - state.x) / dx);
          } else {
            limits.push((minX - state.x) / dx);
          }
        }

        if (Math.abs(dy) > 1e-6) {
          if (dy > 0) {
            limits.push((maxY - state.y) / dy);
          } else {
            limits.push((minY - state.y) / dy);
          }
        }

        const forwardLimits = limits.filter(
          (limit) => Number.isFinite(limit) && limit > 0,
        );
        if (forwardLimits.length === 0) return 0;
        return Math.max(0, Math.min(...forwardLimits));
      };

      const minTurnRadians = (20 * Math.PI) / 180;
      const candidateCount = 28;
      const candidates: Array<{ angle: number; weight: number }> = [];

      for (let i = 0; i < candidateCount; i++) {
        const angle = normalize(Math.random() * Math.PI * 2);
        if (previousDirection != null) {
          const diff = normalize(angle - previousDirection);
          if (Math.abs(diff) < minTurnRadians) {
            continue;
          }
        }

        const distance = clearanceDistance(angle);
        const weight = Math.pow(distance + 1, 2.1);
        candidates.push({ angle, weight });
      }

      if (candidates.length === 0) {
        return previousDirection == null
          ? normalize(Math.random() * Math.PI * 2)
          : normalize(previousDirection + Math.PI);
      }

      const totalWeight = candidates.reduce(
        (sum, candidate) => sum + candidate.weight,
        0,
      );
      let roll = Math.random() * totalWeight;
      for (const candidate of candidates) {
        roll -= candidate.weight;
        if (roll <= 0) {
          return candidate.angle;
        }
      }

      return candidates[candidates.length - 1].angle;
    };

    const getRandomWalkDurationMs = () => {
      const steps = Math.floor(Math.random() * 31) + 10;
      return steps * 100;
    };

    const beginTurn = () => {
      const nextRotation = getRandomDirection(state.currentRotation);
      let angleDiff = nextRotation - state.currentRotation;
      while (angleDiff > Math.PI) angleDiff -= Math.PI * 2;
      while (angleDiff < -Math.PI) angleDiff += Math.PI * 2;

      state.targetRotation = nextRotation;
      state.turnStartRotation = state.currentRotation;
      state.turnStartTime = now;
      state.turnDuration = 420 + (Math.abs(angleDiff) / Math.PI) * 320;
      state.isTurning = true;
      state.isWalking = false;
      state.isIdle = false;
    };

    // Update speed based on burst (with smooth easing)
    if (state.burstTime > 0) {
      state.burstTime -= 16;
      state.speed = 2.0;
    } else {
      state.speed += (state.targetSpeed - state.speed) * 0.12; // Smoother speed transitions
    }

    if (!state.isWalking && !state.isTurning && !state.isIdle) {
      if (Math.random() < 0.05) {
        state.isIdle = true;
        state.idleUntil = now + getRandomWalkDurationMs();
      } else {
        state.targetRotation = getRandomDirection();
        state.currentRotation = state.targetRotation;
        state.walkUntil = now + getRandomWalkDurationMs();
        state.isWalking = true;
      }
    }

    if (state.isIdle && now >= state.idleUntil) {
      state.isIdle = false;
      state.targetRotation = getRandomDirection();
      state.currentRotation = state.targetRotation;
      state.walkUntil = now + getRandomWalkDurationMs();
      state.isWalking = true;
    }

    if (state.isWalking && now >= state.walkUntil) {
      beginTurn();
    }

    if (state.isTurning) {
      const progress = Math.min(
        1,
        Math.max(0, (now - state.turnStartTime) / state.turnDuration),
      );
      const easedProgress = 1 - Math.pow(1 - progress, 3);

      let angleDiff = state.targetRotation - state.turnStartRotation;
      while (angleDiff > Math.PI) angleDiff -= Math.PI * 2;
      while (angleDiff < -Math.PI) angleDiff += Math.PI * 2;

      state.currentRotation =
        state.turnStartRotation + angleDiff * easedProgress;

      if (progress >= 1) {
        state.currentRotation = state.targetRotation;
        state.isTurning = false;
        state.isWalking = true;
        state.walkUntil = now + getRandomWalkDurationMs();
      }
    }

    // Walk in current direction with smooth movement
    if (state.isWalking) {
      const walkSpeed = state.speed;
      state.x += Math.sin(state.currentRotation) * walkSpeed;
      state.y -= Math.cos(state.currentRotation) * walkSpeed;
    }

    // Check for edge collision and pick new direction
    if (
      state.x < padding ||
      state.x > width - padding ||
      state.y < padding ||
      state.y > height - padding
    ) {
      // Clamp position to bounds
      state.x = Math.max(padding, Math.min(width - padding, state.x));
      state.y = Math.max(padding, Math.min(height - padding, state.y));
      beginTurn();
    }

    // Clear canvas
    ctx.clearRect(0, 0, width, height);

    // Calculate walking progress for smooth animations
    const distanceTraveled = (state.x + state.y) * 0.5;
    const legPhase = (distanceTraveled * 0.15) % (Math.PI * 2);

    // Add subtle vertical bobbing based on walking (makes it feel alive)
    const bobHeight = Math.sin(legPhase) * 1.5;

    // Draw bug with smooth positioning
    drawBug(ctx, state.x, state.y + bobHeight, state.currentRotation, legPhase);

    animationFrameRef.current = requestAnimationFrame(animate);
  };

  useEffect(() => {
    const updateCanvasSize = () => {
      const button = containerRef.current;
      const canvas = canvasRef.current;
      if (!button || !canvas) return;

      const rect = button.getBoundingClientRect();
      canvas.width = rect.width;
      canvas.height = rect.height;

      // Initialize bug position to center
      bugStateRef.current.x = canvas.width / 2;
      bugStateRef.current.y = canvas.height / 2;
    };

    updateCanvasSize();
    window.addEventListener('resize', updateCanvasSize);

    animationFrameRef.current = requestAnimationFrame(animate);

    return () => {
      window.removeEventListener('resize', updateCanvasSize);
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
    // animate reads refs only and never needs to re-run; mount-only intent is
    // intentional. containerRef is stable.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const button = containerRef.current;
    if (!button) return;

    const handlePointerEnter = () => {
      bugStateRef.current.targetSpeed = 1.5;
      bugStateRef.current.burstTime = Math.max(
        bugStateRef.current.burstTime,
        250,
      );
    };

    const handlePointerLeave = () => {
      bugStateRef.current.targetSpeed = 0.5;
    };

    const handleClick = () => {
      bugStateRef.current.targetSpeed = 2.0;
      bugStateRef.current.burstTime = 900;
    };

    button.addEventListener('pointerenter', handlePointerEnter);
    button.addEventListener('pointerleave', handlePointerLeave);
    button.addEventListener('click', handleClick);

    return () => {
      button.removeEventListener('pointerenter', handlePointerEnter);
      button.removeEventListener('pointerleave', handlePointerLeave);
      button.removeEventListener('click', handleClick);
    };
  }, [containerRef]);

  return (
    <canvas
      ref={canvasRef}
      className="pointer-events-none absolute inset-0 size-full"
      style={{ borderRadius: 'inherit' }}
    />
  );
};
