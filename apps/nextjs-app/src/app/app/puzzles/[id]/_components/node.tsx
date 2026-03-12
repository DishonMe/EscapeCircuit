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

export const LogicNode = ({
  node,
  cellPx = 18,
  portPx = 8,
  className,
  style,
  children,
  ...props
}: LogicNodeProps) => {
  return (
    <div
      className={cn(
        'group relative rounded border bg-white text-[10px] text-slate-800 dark:bg-slate-800 dark:text-slate-100',
        className,
      )}
      style={{
        width: node.size.w * cellPx - 2,
        height: node.size.h * cellPx - 2,
        ...style,
      }}
      {...props}
    >
      <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
        <span className="select-none text-[9px] font-semibold tracking-wide text-slate-800 dark:text-slate-100">
          {node.label}
        </span>
      </div>

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