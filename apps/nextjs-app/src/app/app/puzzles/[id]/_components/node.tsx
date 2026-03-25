import type { CSSProperties, HTMLAttributes } from 'react';

import { cn } from '@/utils/cn';

export type LogicNodePort = {
  id: string;
  kind: 'input' | 'output';
  offset: { row: number; col: number };
};

export type LogicNodeDefinition = {
  label: string;
  size: { w: number; h: number };
  ports: LogicNodePort[];
};

type LogicNodeProps = HTMLAttributes<HTMLDivElement> & {
  node: LogicNodeDefinition;
  cellPx?: number;
  portPx?: number;
  style?: CSSProperties;
};

const BASIC_GATES = ['AND', 'OR', 'NOT', 'NAND', 'NOR', 'XOR', 'XNOR'];

/**
 * Generate SVG schematic symbol for a logic gate.
 * Uses fixed viewBox dimensions matching grid coordinates for pixel-perfect port alignment.
 * 2-row gates (AND/OR/XOR/NAND/NOR/XNOR): viewBox="0 0 54 36"
 * 1-row gates (NOT): viewBox="0 0 54 18"
 */
const getGateSVG = (label: string) => {
  const commonProps = {
    stroke: 'black',
    fill: 'none',
    strokeWidth: 2.5,
    strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const,
  };

  switch (label) {
    case 'AND': {
      // 3x2 gate: inputs at (9,9) and (9,27), output at (48,18)
      return (
        <svg viewBox="0 0 54 36" className="w-full h-full">
          {/* Left vertical line */}
          <line x1="9" y1="9" x2="9" y2="27" {...commonProps} />
          {/* Top horizontal line */}
          <line x1="9" y1="9" x2="32" y2="9" {...commonProps} />
          {/* Bottom horizontal line */}
          <line x1="9" y1="27" x2="32" y2="27" {...commonProps} />
          {/* Right curve - AND shape */}
          <path d="M 32 9 Q 58 18 32 27" {...commonProps} />
        </svg>
      );
    }
    case 'OR': {
      // 3x2 gate: inputs at (9,9) and (9,27), output at (48,18)
      return (
        <svg viewBox="0 0 54 36" className="w-full h-full">
          {/* Curved input side */}
          <path d="M 9 9 Q 24 18 9 27" {...commonProps} />
          {/* Top horizontal line */}
          <line x1="14" y1="9" x2="32" y2="9" {...commonProps} />
          {/* Bottom horizontal line */}
          <line x1="14" y1="27" x2="32" y2="27" {...commonProps} />
          {/* Right curve - OR shape wider than AND */}
          <path d="M 32 9 Q 58 18 32 27" {...commonProps} />
        </svg>
      );
    }
    case 'NOT': {
      // 3x1 gate: input at (9,9), output at (48,9), large triangle centered
      return (
        <svg viewBox="0 0 54 18" className="w-full h-full">
          {/* Triangle - larger and centered */}
          <path d="M 4 0 L 4 18 L 35 9 Z" {...commonProps} />
          {/* Negation bubble at output */}
          <circle cx="40" cy="9" r="2.5" {...commonProps} />
        </svg>
      );
    }
    case 'NAND': {
      // 3x2 gate: AND with negation bubble connected
      return (
        <svg viewBox="0 0 54 36" className="w-full h-full">
          {/* Left vertical line */}
          <line x1="9" y1="9" x2="9" y2="27" {...commonProps} />
          {/* Top horizontal line */}
          <line x1="9" y1="9" x2="32" y2="9" {...commonProps} />
          {/* Bottom horizontal line */}
          <line x1="9" y1="27" x2="32" y2="27" {...commonProps} />
          {/* Right curve - AND shape extended to bubble */}
          <path d="M 32 9 Q 60 18 32 27" {...commonProps} />
          {/* Negation bubble at output - closer to body */}
          <circle cx="50" cy="18" r="2.5" {...commonProps} />
        </svg>
      );
    }
    case 'NOR': {
      // 3x2 gate: OR with negation bubble connected
      return (
        <svg viewBox="0 0 54 36" className="w-full h-full">
          {/* Curved input side */}
          <path d="M 9 9 Q 17 18 9 27" {...commonProps} />
          {/* Top horizontal line */}
          <line x1="14" y1="9" x2="32" y2="9" {...commonProps} />
          {/* Bottom horizontal line */}
          <line x1="14" y1="27" x2="32" y2="27" {...commonProps} />
          {/* Right curve - OR shape */}
          <path d="M 32 9 Q 58 18 32 27" {...commonProps} />
          {/* Negation bubble at output - closer to body */}
          <circle cx="48" cy="18" r="2.5" {...commonProps} />
        </svg>
      );
    }
    case 'XOR': {
      // 3x2 gate: OR-like with extra curved input line
      return (
        <svg viewBox="0 0 54 36" className="w-full h-full">
          {/* Curved input side - first curve */}
          <path d="M 9 9 Q 17 18 9 27" {...commonProps} />
          {/* Curved input side - second curve for XOR */}
          <path d="M 12 9 Q 20 18 12 27" {...commonProps} />
          {/* Top horizontal line */}
          <line x1="17" y1="9" x2="32" y2="9" {...commonProps} />
          {/* Bottom horizontal line */}
          <line x1="17" y1="27" x2="32" y2="27" {...commonProps} />
          {/* Right curve - OR-like shape */}
          <path d="M 32 9 Q 58 18 32 27" {...commonProps} />
        </svg>
      );
    }
    case 'XNOR': {
      // 3x2 gate: XOR with negation bubble connected
      return (
        <svg viewBox="0 0 54 36" className="w-full h-full">
          {/* Curved input side - first curve */}
          <path d="M 9 9 Q 17 18 9 27" {...commonProps} />
          {/* Curved input side - second curve for XOR */}
          <path d="M 12 9 Q 20 18 12 27" {...commonProps} />
          {/* Top horizontal line */}
          <line x1="17" y1="9" x2="32" y2="9" {...commonProps} />
          {/* Bottom horizontal line */}
          <line x1="17" y1="27" x2="32" y2="27" {...commonProps} />
          {/* Right curve - OR-like shape */}
          <path d="M 32 9 Q 58 18 32 27" {...commonProps} />
          {/* Negation bubble at output - closer to body */}
          <circle cx="48" cy="18" r="2.5" {...commonProps} />
        </svg>
      );
    }
    default:
      return null;
  }
};

export const LogicNode = ({
  node,
  cellPx = 18,
  portPx = 8,
  className,
  style,
  children,
  ...props
}: LogicNodeProps) => {
  // Extract gate type (e.g., "AND" from "AND 1" or just "AND")
  const gateType = node.label.split(' ')[0];
  const isBasicGate = BASIC_GATES.includes(gateType);

  return (
    <div
      className={cn(
        'group relative text-[10px] text-slate-800 dark:text-slate-100',
        !isBasicGate && 'rounded border bg-white dark:bg-slate-800',
        className,
      )}
      style={{
        width: node.size.w * cellPx - 2,
        height: node.size.h * cellPx - 2,
        ...style,
      }}
      {...props}
    >
      {isBasicGate ? (
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <div className="absolute inset-0">
            {getGateSVG(gateType)}
          </div>
          <span className={cn(
            "select-none text-[7px] font-bold text-black relative z-10",
            gateType === 'XNOR' ? 'text-[6px]' : 'text-[7px]',
            gateType === 'XNOR' && 'translate-x-[2px]', 
            gateType === 'NOT' && 'absolute left-1/4 top-1/2 -translate-y-1/2'
          )}>
            {node.label.includes(' ') ? node.label.split(' ')[1] : ''}
          </span>
        </div>
      ) : (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
          <span className="select-none text-[9px] font-semibold tracking-wide text-slate-800 dark:text-slate-100">
            {node.label}
          </span>
        </div>
      )}

      {node.ports.map((port) => {
        const left = port.offset.col * cellPx + (cellPx - portPx) / 2;
        const top = port.offset.row * cellPx + (cellPx - portPx) / 2;

        return (
          <div
            key={port.id}
            className={cn(
              'pointer-events-none absolute rounded-full border',
              port.kind === 'input'
                ? 'border-green-300 bg-green-50'
                : 'border-purple-300 bg-purple-50',
            )}
            style={{
              left,
              top,
              width: portPx,
              height: portPx,
            }}
          />
        );
      })}

      {children}
    </div>
  );
};