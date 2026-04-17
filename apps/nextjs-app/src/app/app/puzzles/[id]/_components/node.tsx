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
    stroke: 'currentColor',
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
    case 'DFF': {
      // 3x1 gate: D flip-flop symbol with clock notch and Q output
      return (
        <svg viewBox="0 0 54 18" className="w-full h-full">
          {/* Body */}
          <rect x="10" y="1.5" width="26" height="15" rx="2.5" {...commonProps} />
          {/* Clock notch */}
          <path d="M 10 9 L 14 6.3 L 14 11.7 Z" {...commonProps} />
          {/* Output lead */}
          <line x1="36" y1="9" x2="45" y2="9" {...commonProps} />
          {/* Labels */}
          <text x="18" y="11" fill="currentColor" fontSize="5.5" fontWeight="700">D</text>
          <text x="28" y="11" fill="currentColor" fontSize="5.5" fontWeight="700">Q</text>
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
  const isDffGate = gateType === 'DFF';
  const gateInstanceLabel = node.label.startsWith(`${gateType} `)
    ? node.label.slice(gateType.length + 1)
    : '';

  return (
    <div
      className={cn(
        'group relative text-[10px] text-foreground',
        !isBasicGate && 'rounded border bg-card',
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
            "select-none text-[7px] font-bold text-foreground relative z-10",
            gateType === 'XNOR' ? 'text-[6px]' : 'text-[7px]',
            gateType === 'XNOR' && 'translate-x-[2px]', 
            gateType === 'NOT' && 'absolute left-1/4 top-1/2 -translate-y-1/2'
          )}>
            {gateInstanceLabel}
          </span>
        </div>
      ) : isDffGate ? (
        <div className="pointer-events-none absolute inset-0">
          <div className="absolute inset-[1px] rounded-sm bg-gradient-to-b from-card to-card/70" />
          <div className="absolute inset-0">
            {getGateSVG('DFF')}
          </div>
          <span className="absolute right-1 top-0.5 select-none rounded border border-border/60 bg-background/80 px-1 text-[6px] font-semibold leading-none text-muted-foreground">
            {gateInstanceLabel}
          </span>
        </div>
      ) : (
        <div className="pointer-events-none absolute inset-0">
          <div className="absolute inset-[1px] rounded-[5px] border border-border/70 bg-gradient-to-b from-card via-card to-muted/25 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)]" />
          <div className="absolute inset-x-1 inset-y-0 flex items-center justify-center">
            <span className="max-w-full truncate px-2 text-[9px] font-semibold tracking-wide text-foreground">
              {node.label}
            </span>
          </div>
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