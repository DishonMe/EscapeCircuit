'use client';

import React, { useEffect, useRef, useState } from 'react';

interface BugCrawlerProps {
  children: React.ReactNode;
  borderRadius?: number;
}

interface BugState {
  position: number;
  speed: number;
  targetSpeed: number;
  burstTime: number;
}

export const BugCrawler = ({ children, borderRadius = 6 }: BugCrawlerProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const bugStateRef = useRef<BugState>({
    position: 0,
    speed: 0.4,
    targetSpeed: 0.4,
    burstTime: 0,
  });
  const pathRef = useRef<{ x: number; y: number }[]>([]);
  const animationFrameRef = useRef<number>();

  // Measure button and rebuild path
  const rebuildPath = () => {
    if (!containerRef.current || !canvasRef.current) return;

    const rect = containerRef.current.getBoundingClientRect();
    const w = rect.width;
    const h = rect.height;
    const r = borderRadius;
    const offset = 8; // Distance outward from border to keep bug off text

    const path: { x: number; y: number }[] = [];

    // Top-left arc (outward)
    for (let i = 0; i <= 90; i += 2) {
      const rad = (i * Math.PI) / 180;
      const cx = r - r * Math.cos(rad);
      const cy = r - r * Math.sin(rad);
      // Distance from corner center
      const dist = Math.sqrt(cx * cx + cy * cy);
      path.push({
        x: cx * (1 + offset / dist),
        y: cy * (1 + offset / dist),
      });
    }

    // Top edge
    for (let x = r; x <= w - r; x += 2) {
      path.push({ x, y: -offset });
    }

    // Top-right arc (outward)
    for (let i = 0; i <= 90; i += 2) {
      const rad = (i * Math.PI) / 180;
      const cx = w - r + r * Math.sin(rad);
      const cy = r - r * Math.cos(rad);
      const dist = Math.sqrt((cx - (w - r)) ** 2 + (cy - r) ** 2);
      path.push({
        x: (w - r) + (cx - (w - r)) * (1 + offset / dist),
        y: r + (cy - r) * (1 + offset / dist),
      });
    }

    // Right edge
    for (let y = r; y <= h - r; y += 2) {
      path.push({ x: w + offset, y });
    }

    // Bottom-right arc (outward)
    for (let i = 0; i <= 90; i += 2) {
      const rad = (i * Math.PI) / 180;
      const cx = w - r + r * Math.cos(rad);
      const cy = h - r + r * Math.sin(rad);
      const dist = Math.sqrt((cx - (w - r)) ** 2 + (cy - (h - r)) ** 2);
      path.push({
        x: (w - r) + (cx - (w - r)) * (1 + offset / dist),
        y: (h - r) + (cy - (h - r)) * (1 + offset / dist),
      });
    }

    // Bottom edge
    for (let x = w - r; x >= r; x -= 2) {
      path.push({ x, y: h + offset });
    }

    // Bottom-left arc (outward)
    for (let i = 0; i <= 90; i += 2) {
      const rad = (i * Math.PI) / 180;
      const cx = r - r * Math.sin(rad);
      const cy = h - r + r * Math.cos(rad);
      const dist = Math.sqrt(cx * cx + (cy - (h - r)) ** 2);
      path.push({
        x: cx * (1 + offset / dist),
        y: (h - r) + (cy - (h - r)) * (1 + offset / dist),
      });
    }

    // Left edge
    for (let y = h - r; y >= r; y -= 2) {
      path.push({ x: -offset, y });
    }

    pathRef.current = path;
  };

  const drawBug = (ctx: CanvasRenderingContext2D, x: number, y: number, angle: number, legPhase: number) => {
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(angle);

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
    const legHeights = [5, 6, 5];

    legOffsets.forEach((offset, idx) => {
      // Left legs
      const leftPhase = (legPhase + idx * (Math.PI * 2 / 3)) % (Math.PI * 2);
      const leftY = offset + Math.sin(leftPhase) * 2;
      ctx.strokeStyle = '#000000';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(-6, leftY);
      ctx.quadraticCurveTo(-9, leftY + 2, -8, leftY + 4);
      ctx.stroke();

      // Right legs
      const rightPhase = (legPhase + idx * (Math.PI * 2 / 3) + Math.PI) % (Math.PI * 2);
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

    const path = pathRef.current;
    if (path.length === 0) return;

    // Update speed
    if (state.burstTime > 0) {
      state.burstTime -= 16;
      state.speed = 3.5;
    } else {
      state.speed += (state.targetSpeed - state.speed) * 0.1;
    }

    // Move position
    state.position = (state.position + state.speed) % path.length;

    // Get current and next position for direction
    const currentIdx = Math.floor(state.position);
    const nextIdx = (currentIdx + 1) % path.length;
    const current = path[currentIdx];
    const next = path[nextIdx];

    const angle = Math.atan2(next.y - current.y, next.x - current.x);

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw bug - offset by 24px to account for canvas positioning
    const bugX = current.x + 24;
    const bugY = current.y + 24;
    const legPhase = (state.position * 0.3) % (Math.PI * 2);
    drawBug(ctx, bugX, bugY, angle, legPhase);

    animationFrameRef.current = requestAnimationFrame(animate);
  };

  useEffect(() => {
    rebuildPath();
    const handleResize = () => rebuildPath();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [borderRadius]);

  useEffect(() => {
    if (!canvasRef.current || !containerRef.current) return;

    const rect = containerRef.current.getBoundingClientRect();
    canvasRef.current.width = rect.width + 48;
    canvasRef.current.height = rect.height + 48;

    animate();

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, []);

  const handleMouseEnter = () => {
    bugStateRef.current.targetSpeed = 1.2;
  };

  const handleMouseLeave = () => {
    bugStateRef.current.targetSpeed = 0.4;
  };

  const handleClick = (e: React.MouseEvent) => {
    // Only trigger burst if click is on the button itself, not the canvas
    if ((e.target as HTMLElement).tagName === 'BUTTON' || (e.target as HTMLElement).closest('button')) {
      bugStateRef.current.burstTime = 800;
    }
  };

  return (
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
