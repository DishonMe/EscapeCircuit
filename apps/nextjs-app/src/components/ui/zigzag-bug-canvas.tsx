'use client';

import React, { useEffect, useRef, useState } from 'react';

interface ZigzagBugCanvasProps {
  containerRef: React.RefObject<HTMLButtonElement>;
}

interface BugState {
  x: number; // X position (0 to canvas.width)
  y: number; // Y position (0 to canvas.height)
  targetRotation: number; // Target rotation in radians (0 = right, π/2 = down, π = left, -π/2 = up)
  currentRotation: number; // Current rotation in radians
  isWalking: boolean; // Whether we're currently walking
  speed: number;
  targetSpeed: number;
  burstTime: number;
}

export const ZigzagBugCanvas = ({ containerRef }: ZigzagBugCanvasProps) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const bugStateRef = useRef<BugState>({
    x: 0,
    y: 0,
    targetRotation: 0,
    currentRotation: 0,
    isWalking: false,
    speed: 0.5,
    targetSpeed: 0.5,
    burstTime: 0,
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
    ctx.quadraticCurveTo(-3 + antennaWiggle * 0.5, -12, -4 + antennaWiggle, -14);
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
      ctx.quadraticCurveTo(-9 + leftLegBend, offset + 2 + leftLegHeight, -8, offset + 4 + leftLegHeight);
      ctx.stroke();

      // Right legs
      const rightPhase = (legPhase + legPhaseOffset + Math.PI) % (Math.PI * 2);
      const rightLegBend = Math.sin(rightPhase) * 3;
      const rightLegHeight = Math.cos(rightPhase * 0.5) * 1.5;
      
      ctx.beginPath();
      ctx.moveTo(6, offset + rightLegHeight);
      ctx.quadraticCurveTo(9 - rightLegBend, offset + 2 + rightLegHeight, 8, offset + 4 + rightLegHeight);
      ctx.stroke();
    });

    ctx.restore();
  };

  const animate = () => {
    const canvas = canvasRef.current;
    const button = containerRef.current;
    if (!canvas || !button) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const state = bugStateRef.current;
    const width = canvas.width;
    const height = canvas.height;

    // Update speed based on burst (with smooth easing)
    if (state.burstTime > 0) {
      state.burstTime -= 16;
      state.speed = 2.0;
    } else {
      state.speed += (state.targetSpeed - state.speed) * 0.12; // Smoother speed transitions
    }

    // If not walking, pick a random direction
    if (!state.isWalking) {
      // Pick a random cardinal direction: 0=right, π/2=down, π=left, -π/2=up
      const directions = [0, Math.PI / 2, Math.PI, -Math.PI / 2];
      state.targetRotation = directions[Math.floor(Math.random() * directions.length)];
      state.isWalking = true;
    }

    // Smoothly rotate toward target direction (with easing)
    let angleDiff = state.targetRotation - state.currentRotation;
    // Normalize to [-π, π]
    while (angleDiff > Math.PI) angleDiff -= Math.PI * 2;
    while (angleDiff < -Math.PI) angleDiff += Math.PI * 2;
    
    // Smooth rotation with easing (faster initial turn, then slows down)
    const rotationSpeed = 0.12;
    if (Math.abs(angleDiff) > rotationSpeed) {
      state.currentRotation += Math.sign(angleDiff) * rotationSpeed;
    } else {
      state.currentRotation = state.targetRotation;
    }

    // Walk in current direction with smooth movement
    const walkSpeed = state.speed;
    state.x += Math.cos(state.currentRotation) * walkSpeed;
    state.y += Math.sin(state.currentRotation) * walkSpeed;

    // Check for edge collision and pick new direction
    const padding = 8;
    if (
      state.x < padding ||
      state.x > width - padding ||
      state.y < padding ||
      state.y > height - padding
    ) {
      // Clamp position to bounds
      state.x = Math.max(padding, Math.min(width - padding, state.x));
      state.y = Math.max(padding, Math.min(height - padding, state.y));
      // Pick new direction on next frame
      state.isWalking = false;
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

    animate();

    return () => {
      window.removeEventListener('resize', updateCanvasSize);
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, []);

  const handleMouseEnter = () => {
    bugStateRef.current.targetSpeed = 1.5; // 3x the normal speed
  };

  const handleMouseLeave = () => {
    bugStateRef.current.targetSpeed = 0.5;
  };

  const handleClick = (e: React.MouseEvent) => {
    // Only burst on canvas click (not on button click)
    if ((e.target as HTMLElement).tagName === 'CANVAS') {
      bugStateRef.current.burstTime = 700;
    }
  };

  return (
    <canvas
      ref={canvasRef}
      className="pointer-events-none absolute inset-0 w-full h-full"
      style={{ borderRadius: 'inherit' }}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onClick={handleClick}
    />
  );
};
