'use client';

import Link from 'next/link';

import { PuzzlesList } from '@/features/puzzles/components/puzzles-list';
import { useUser } from '@/lib/auth';

export const Puzzles = () => {
  const user = useUser();

  return (
    <div className="relative">
      {/* Absolute Blurred Background Layer */}
      <div className="fixed inset-0 -z-10 pointer-events-none overflow-hidden bg-gradient-to-br from-background via-background to-background">
        <div 
          className="absolute inset-0 opacity-[0.25] dark:opacity-[0.35] blur-[10px]"
          style={{
            backgroundImage: `radial-gradient(circle at 2px 2px, rgb(6, 182, 212) 1px, transparent 1px)`,
            backgroundSize: '40px 40px'
          }}
        />
        {/* Blurred circuit-like blobs for depth */}
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-cyan-500/30 rounded-full blur-[120px]" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-blue-600/20 rounded-full blur-[120px]" />
      </div>

      <div className="mx-auto max-w-7xl px-4 py-8">
        {/* Header - Compact with Circuit Board Background */}
        <div className="relative overflow-hidden w-full py-8 mb-6 rounded-2xl border border-border/50 bg-secondary/20">
          {/* Background Layer */}
          <div className="absolute inset-0 pointer-events-none z-0 flex items-center justify-center overflow-hidden">
            {/* Circuit Board SVG Pattern */}
            <div 
              className="absolute inset-0 opacity-[0.4] dark:opacity-[0.8]"
              style={{
                backgroundImage: `url("data:image/svg+xml,%3Csvg width='40' height='40' viewBox='0 0 40 40' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M0 0h40v40H0V0zm20 20h20v20H20V20zM0 20h20v20H0V20z' fill='none' stroke='%2306b6d4' stroke-width='0.5' stroke-opacity='0.1'/%3E%3Ccircle cx='20' cy='20' r='1.5' fill='%2306b6d4' fill-opacity='0.2'/%3E%3Ccircle cx='40' cy='40' r='1.5' fill='%2306b6d4' fill-opacity='0.2'/%3E%3Ccircle cx='0' cy='40' r='1.5' fill='%2306b6d4' fill-opacity='0.2'/%3E%3C/svg%3E")`,
                backgroundSize: '40px 40px'
              }}
            />
            {/* Blurred glowing blobs for depth */}
            <div className="absolute w-[600px] h-[300px] bg-cyan-400/20 blur-[100px] rounded-full top-[-50%]"></div>
            <div className="absolute w-[400px] h-[400px] bg-blue-600/10 blur-[120px] rounded-full bottom-[-50%] right-[-10%]"></div>
          </div>
          
          {/* Content */}
          <div className="flex flex-col items-center justify-center text-center relative z-10">
            <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight font-mono text-transparent bg-clip-text bg-gradient-to-r from-cyan-600 to-blue-600 dark:from-cyan-400 dark:to-blue-500 mb-4">
              Circuit Puzzles
            </h1>
            <p className="text-muted-foreground text-[13px]">
              Browse and solve challenging circuit design puzzles
            </p>
          </div>
        </div>

        {/* Puzzles List */}
        <PuzzlesList />
      </div>
    </div>
  );
};
