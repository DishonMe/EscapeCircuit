'use client';

import React, { useEffect, useRef } from 'react';

interface BugCrawlerProps {
  children: React.ReactNode;
  borderRadius?: number;
}

interface BugState {
  x: number;
  y: number;
  angle: number;
  targetX: number;
  targetY: number;
  speed: number;
  targetSpeed: number;
  burstTime: number;
  legPhase: number;
}

export const BugCrawler = ({ children }: BugCrawlerProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const bugStateRef = useRef<BugState>({
    x: 0,
    y: 0,
    angle: 0,
    targetX: 0,
    targetY: 0,
    speed: 0.4,
    targetSpeed: 0.4,
    burstTime: 0,
    legPhase: 0,
  });
  const animationFrameRef = useRef<number>();

  // Pick a new random target within the container bounds
  const pickNewTarget = () => {
    if (!containerRef.current) return;

    const rect = containerRef.current.getBoundingClientRect();
    const padding = 16; // Keep bug away from edges

    const targetX = Math.random() * (rect.width - padding * 2) + padding;
    const targetY = Math.random() * (rect.height - padding * 2) + padding;

    bugStateRef.current.targetX = targetX;
    bugStateRef.current.targetY = targetY;
  };

  const drawBug = (
    ctx: CanvasRenderingContext2D,
    x: number,
    y: number,
    angle: number,
    legPhase: number,
  ) => {
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(angle);
    ctx.rotate(Math.PI / 2);

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

    // Antennae
    ctx.strokeStyle = '#000000';
    ctx.lineWidth = 0.8;
    ctx.beginPath();
    ctx.moveTo(-1, -10);
    ctx.quadraticCurveTo(-3, -12, -4, -14);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(1, -10);
    ctx.quadraticCurveTo(3, -12, 4, -14);
    ctx.stroke();

    // Legs (6 total, 3 on each side)
    const legOffsets = [-4, 0, 4];

    legOffsets.forEach((offset, idx) => {
      // Left legs
      const leftPhase = (legPhase + idx * ((Math.PI * 2) / 3)) % (Math.PI * 2);
      const leftY = offset + Math.sin(leftPhase) * 2;
      ctx.strokeStyle = '#000000';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(-6, leftY);
      ctx.quadraticCurveTo(-9, leftY + 2, -8, leftY + 4);
      ctx.stroke();

      // Right legs
      const rightPhase =
        (legPhase + idx * ((Math.PI * 2) / 3) + Math.PI) % (Math.PI * 2);
      const rightY = offset + Math.sin(rightPhase) * 2;
      ctx.beginPath();
      ctx.moveTo(6, rightY);
      ctx.quadraticCurveTo(9, rightY + 2, 8, rightY + 4);
      ctx.stroke();
    });

    ctx.restore();
  };

  const animate = () => {
    const canvas = canvasRef.current;
    const state = bugStateRef.current;

    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Update speed
    if (state.burstTime > 0) {
      state.burstTime -= 16;
      state.speed = 3.5;
    } else {
      state.speed += (state.targetSpeed - state.speed) * 0.1;
    }

    // Calculate direction to target
    const dx = state.targetX - state.x;
    const dy = state.targetY - state.y;
    const distanceToTarget = Math.sqrt(dx * dx + dy * dy);

    // If reached target, pick a new one
    if (distanceToTarget < 5) {
      pickNewTarget();
    } else {
      // Calculate target angle
      const targetAngle = Math.atan2(dy, dx);

      // Smooth angle interpolation with wrap-around handling
      let angleDiff = targetAngle - state.angle;
      // Normalize angle difference to [-PI, PI]
      if (angleDiff > Math.PI) {
        angleDiff -= Math.PI * 2;
      } else if (angleDiff < -Math.PI) {
        angleDiff += Math.PI * 2;
      }

      // Smoothly turn towards target (0.08 is the interpolation factor)
      state.angle += angleDiff * 0.08;
    }

    // Update position based on angle and speed
    state.x += Math.cos(state.angle) * state.speed;
    state.y += Math.sin(state.angle) * state.speed;

    // Update leg animation
    state.legPhase = (state.legPhase + 0.3) % (Math.PI * 2);

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw bug - offset by 24px to account for canvas positioning
    const bugX = state.x + 24;
    const bugY = state.y + 24;
    drawBug(ctx, bugX, bugY, state.angle, state.legPhase);

    animationFrameRef.current = requestAnimationFrame(animate);
  };

  useEffect(() => {
    if (!canvasRef.current || !containerRef.current) return;

    const rect = containerRef.current.getBoundingClientRect();
    canvasRef.current.width = rect.width + 48;
    canvasRef.current.height = rect.height + 48;

    // Initialize bug position to center of container
    bugStateRef.current.x = rect.width / 2;
    bugStateRef.current.y = rect.height / 2;

    // Pick first target
    pickNewTarget();

    animate();

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
    // animate / pickNewTarget read refs only and never need to re-run;
    // mount-only intent is intentional.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleMouseEnter = () => {
    bugStateRef.current.targetSpeed = 1.2;
  };

  const handleMouseLeave = () => {
    bugStateRef.current.targetSpeed = 0.4;
  };

  const handleClick = (e: React.MouseEvent) => {
    // Only trigger burst if click is on the button itself, not the canvas
    if (
      (e.target as HTMLElement).tagName === 'BUTTON' ||
      (e.target as HTMLElement).closest('button')
    ) {
      bugStateRef.current.burstTime = 800;
      pickNewTarget();
    }
  };

  return (
    // eslint-disable-next-line jsx-a11y/no-static-element-interactions, jsx-a11y/click-events-have-key-events -- decorative wrapper around an already-interactive child; click only triggers a visual bug burst.
    <div
      ref={containerRef}
      className="relative inline-block"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onClick={handleClick}
    >
      <canvas
        ref={canvasRef}
        className="pointer-events-none absolute"
        style={{ top: '-24px', left: '-24px', zIndex: 10 }}
      />
      {children}
    </div>
  );
};
