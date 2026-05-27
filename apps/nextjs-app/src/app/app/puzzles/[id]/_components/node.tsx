import type { CSSProperties, HTMLAttributes } from 'react';

import { cn } from '@/utils/cn';

export type LogicNodePort = {
  id: string;
  kind: 'input' | 'output';
  offset: { row: number; col: number };
};

export type LogicNodeBorderStyle = 'solid' | 'double' | 'etched';

export type LogicNodeEdgeAddon = 'none' | 'chip-legs';

export type LogicNodeSurfaceStyle =
  | 'flat'
  | 'brushed'
  | 'gradient'
  | 'matte'
  | 'glass'
  | 'carbon';

export type LogicNodeVisualStyle = {
  accentColor?: string;
  // Bounded in UI and renderer to keep shapes readable across gate sizes.
  roundness?: number;
  borderStyle?: LogicNodeBorderStyle;
  edgeAddon?: LogicNodeEdgeAddon;
  surfaceStyle?: LogicNodeSurfaceStyle;
};

export type LogicNodeDefinition = {
  label: string;
  size: { w: number; h: number };
  ports: LogicNodePort[];
  visualStyle?: LogicNodeVisualStyle;
};

type LogicNodeProps = HTMLAttributes<HTMLDivElement> & {
  node: LogicNodeDefinition;
  cellPx?: number;
  portPx?: number;
  style?: CSSProperties;
};

const BASIC_GATES = ['AND', 'OR', 'NOT', 'NAND', 'NOR', 'XOR', 'XNOR'];

const DEFAULT_VISUAL_STYLE: Required<LogicNodeVisualStyle> = {
  accentColor: '#3b82f6',
  roundness: 4,
  borderStyle: 'solid',
  edgeAddon: 'none',
  surfaceStyle: 'gradient',
};

const LEGACY_PRESET_OVERRIDES: Record<
  string,
  Partial<Required<LogicNodeVisualStyle>>
> = {
  'clean-lab': {
    accentColor: '#3b82f6',
    roundness: 4,
    borderStyle: 'solid',
    edgeAddon: 'none',
    surfaceStyle: 'gradient',
  },
  'retro-chip': {
    accentColor: '#f59e0b',
    roundness: 2,
    borderStyle: 'double',
    edgeAddon: 'chip-legs',
    surfaceStyle: 'brushed',
  },
  blueprint: {
    accentColor: '#22d3ee',
    roundness: 2,
    borderStyle: 'etched',
    edgeAddon: 'none',
    surfaceStyle: 'flat',
  },
  playful: {
    accentColor: '#10b981',
    roundness: 8,
    borderStyle: 'solid',
    edgeAddon: 'none',
    surfaceStyle: 'gradient',
  },
};

const BORDER_STYLES: LogicNodeBorderStyle[] = ['solid', 'double', 'etched'];
const EDGE_ADDONS: LogicNodeEdgeAddon[] = ['none', 'chip-legs'];
const SURFACE_STYLES: LogicNodeSurfaceStyle[] = [
  'flat',
  'brushed',
  'gradient',
  'matte',
  'glass',
  'carbon',
];

const clampRoundness = (value: number) =>
  Math.max(0, Math.min(10, Math.round(value)));

const isHexColor = (value: string) =>
  /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/.test(value);

const hexToRgba = (hex: string, alpha: number) => {
  const normalized = hex.replace('#', '');
  const full =
    normalized.length === 3
      ? normalized
          .split('')
          .map((c) => c + c)
          .join('')
      : normalized;

  const r = Number.parseInt(full.slice(0, 2), 16);
  const g = Number.parseInt(full.slice(2, 4), 16);
  const b = Number.parseInt(full.slice(4, 6), 16);

  if ([r, g, b].some((n) => Number.isNaN(n))) {
    return `rgba(59,130,246,${alpha})`;
  }

  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
};

const resolveVisualStyle = (
  visualStyle?: LogicNodeVisualStyle,
): Required<LogicNodeVisualStyle> => {
  const legacyPreset = (visualStyle as { preset?: string } | undefined)?.preset;
  const base = {
    ...DEFAULT_VISUAL_STYLE,
    ...(legacyPreset && LEGACY_PRESET_OVERRIDES[legacyPreset]
      ? LEGACY_PRESET_OVERRIDES[legacyPreset]
      : {}),
  };

  const accentColor = visualStyle?.accentColor;
  const legacyCornerStyle = (
    visualStyle as { cornerStyle?: string } | undefined
  )?.cornerStyle;
  const legacyBorderStyle = (
    visualStyle as { borderStyle?: string } | undefined
  )?.borderStyle;
  const legacyEdgeAddonRaw = (
    visualStyle as { edgeAddon?: string; edge_addon?: string } | undefined
  )?.edgeAddon;
  const legacyEdgeAddonAltRaw = (
    visualStyle as { edgeAddon?: string; edge_addon?: string } | undefined
  )?.edge_addon;

  const legacyRoundness =
    legacyCornerStyle === 'sharp'
      ? 0
      : legacyCornerStyle === 'capsule'
        ? 10
        : legacyCornerStyle === 'rounded'
          ? 4
          : undefined;

  const requestedRoundness =
    typeof visualStyle?.roundness === 'number'
      ? visualStyle.roundness
      : legacyRoundness;

  const borderStyle =
    typeof visualStyle?.borderStyle === 'string'
      ? visualStyle.borderStyle
      : undefined;

  const resolvedBorderStyle =
    borderStyle && BORDER_STYLES.includes(borderStyle as LogicNodeBorderStyle)
      ? (borderStyle as LogicNodeBorderStyle)
      : legacyBorderStyle === 'chip'
        ? 'double'
        : base.borderStyle;

  const edgeAddonRaw =
    visualStyle?.edgeAddon ?? legacyEdgeAddonRaw ?? legacyEdgeAddonAltRaw;
  const resolvedEdgeAddon =
    edgeAddonRaw === 'chip'
      ? 'chip-legs'
      : edgeAddonRaw && EDGE_ADDONS.includes(edgeAddonRaw as LogicNodeEdgeAddon)
        ? (edgeAddonRaw as LogicNodeEdgeAddon)
        : legacyBorderStyle === 'chip'
          ? 'chip-legs'
          : base.edgeAddon;

  const surfaceStyle = visualStyle?.surfaceStyle;
  const resolvedSurfaceStyle =
    surfaceStyle && SURFACE_STYLES.includes(surfaceStyle)
      ? surfaceStyle
      : base.surfaceStyle;

  return {
    accentColor:
      accentColor && isHexColor(accentColor) ? accentColor : base.accentColor,
    roundness:
      typeof requestedRoundness === 'number'
        ? clampRoundness(requestedRoundness)
        : base.roundness,
    borderStyle: resolvedBorderStyle,
    edgeAddon: resolvedEdgeAddon,
    surfaceStyle: resolvedSurfaceStyle,
  };
};

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
        <svg viewBox="0 0 54 36" className="size-full">
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
        <svg viewBox="0 0 54 36" className="size-full">
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
        <svg viewBox="0 0 54 18" className="size-full">
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
        <svg viewBox="0 0 54 36" className="size-full">
          {/* Left vertical line */}
          <line x1="9" y1="9" x2="9" y2="27" {...commonProps} />
          {/* Top horizontal line */}
          <line x1="9" y1="9" x2="25" y2="9" {...commonProps} />
          {/* Bottom horizontal line */}
          <line x1="9" y1="27" x2="25" y2="27" {...commonProps} />
          {/* Right curve - AND shape compressed */}
          <path d="M 25 9 Q 48 18 25 27" {...commonProps} />
          {/* Negation bubble at output */}
          <circle cx="40" cy="18" r="2.5" {...commonProps} />
        </svg>
      );
    }
    case 'NOR': {
      // 3x2 gate: OR with negation bubble connected
      return (
        <svg viewBox="0 0 54 36" className="size-full">
          {/* Curved input side */}
          <path d="M 9 9 Q 17 18 9 27" {...commonProps} />
          {/* Top horizontal line */}
          <line x1="14" y1="9" x2="25" y2="9" {...commonProps} />
          {/* Bottom horizontal line */}
          <line x1="14" y1="27" x2="25" y2="27" {...commonProps} />
          {/* Right curve - OR shape compressed */}
          <path d="M 25 9 Q 48 18 25 27" {...commonProps} />
          {/* Negation bubble at output */}
          <circle cx="40" cy="18" r="2.5" {...commonProps} />
        </svg>
      );
    }
    case 'XOR': {
      // 3x2 gate: OR-like with extra curved input line
      return (
        <svg viewBox="0 0 54 36" className="size-full">
          {/* Curved input side - first curve */}
          <path d="M 9 9 Q 17 18 9 27" {...commonProps} />
          {/* Curved input side - second curve for XOR */}
          <path d="M 12 9 Q 20 18 12 27" {...commonProps} />
          {/* Top horizontal line */}
          <line x1="17" y1="9" x2="32" y2="9" {...commonProps} />
          {/* Bottom horizontal line */}
          <line x1="17" y1="27" x2="32" y2="27" {...commonProps} />
          {/* Right curve - OR-like shape compressed */}
          <path d="M 32 9 Q 50 18 32 27" {...commonProps} />
        </svg>
      );
    }
    case 'XNOR': {
      // 3x2 gate: XOR with negation bubble connected
      return (
        <svg viewBox="0 0 54 36" className="size-full">
          {/* Curved input side - first curve */}
          <path d="M 9 9 Q 17 18 9 27" {...commonProps} />
          {/* Curved input side - second curve for XOR */}
          <path d="M 12 9 Q 20 18 12 27" {...commonProps} />
          {/* Top horizontal line */}
          <line x1="17" y1="9" x2="25" y2="9" {...commonProps} />
          {/* Bottom horizontal line */}
          <line x1="17" y1="27" x2="25" y2="27" {...commonProps} />
          {/* Right curve - OR-like shape compressed */}
          <path d="M 25 9 Q 48 18 25 27" {...commonProps} />
          {/* Negation bubble at output */}
          <circle cx="40" cy="18" r="2.5" {...commonProps} />
        </svg>
      );
    }
    case 'DFF': {
      // 3x1 gate: D flip-flop symbol with clock notch and Q output
      return (
        <svg viewBox="0 0 54 18" className="size-full">
          {/* Body */}
          <rect
            x="10"
            y="1.5"
            width="26"
            height="15"
            rx="2.5"
            {...commonProps}
          />
          {/* Clock notch */}
          <path d="M 10 9 L 14 6.3 L 14 11.7 Z" {...commonProps} />
          {/* Output lead */}
          <line x1="36" y1="9" x2="45" y2="9" {...commonProps} />
          {/* Labels */}
          <text
            x="18"
            y="11"
            fill="currentColor"
            fontSize="5.5"
            fontWeight="700"
          >
            D
          </text>
          <text
            x="28"
            y="11"
            fill="currentColor"
            fontSize="5.5"
            fontWeight="700"
          >
            Q
          </text>
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

  const rawVisualStyle = node.visualStyle as
    | (LogicNodeVisualStyle & {
        preset?: string;
        cornerStyle?: string;
        borderStyle?: string;
      })
    | undefined;

  const hasCustomVisualStyle = Boolean(
    rawVisualStyle &&
    (rawVisualStyle.preset ||
      rawVisualStyle.cornerStyle ||
      rawVisualStyle.accentColor ||
      typeof rawVisualStyle.roundness === 'number' ||
      rawVisualStyle.borderStyle ||
      rawVisualStyle.edgeAddon ||
      rawVisualStyle.surfaceStyle),
  );
  const resolvedVisualStyle = hasCustomVisualStyle
    ? resolveVisualStyle(node.visualStyle)
    : null;
  const accentColorStrong = resolvedVisualStyle
    ? hexToRgba(resolvedVisualStyle.accentColor, 0.48)
    : '';
  const accentColorSoft = resolvedVisualStyle
    ? hexToRgba(resolvedVisualStyle.accentColor, 0.22)
    : '';
  const accentColorGlow = resolvedVisualStyle
    ? hexToRgba(resolvedVisualStyle.accentColor, 0.28)
    : '';

  const shellRoundness =
    resolvedVisualStyle?.roundness ?? DEFAULT_VISUAL_STYLE.roundness;
  const shellRadiusPx = 2 + shellRoundness * 1.2;
  const shellRadius = `${shellRadiusPx}px`;

  const shellSurfaceClass = resolvedVisualStyle
    ? resolvedVisualStyle.surfaceStyle === 'gradient'
      ? 'bg-gradient-to-b from-card via-card to-muted/30'
      : resolvedVisualStyle.surfaceStyle === 'matte'
        ? 'bg-muted/35'
        : resolvedVisualStyle.surfaceStyle === 'glass'
          ? 'bg-background/75'
          : 'bg-card'
    : 'bg-gradient-to-b from-card via-card to-muted/30';

  const shellBorderWidthClass =
    resolvedVisualStyle?.borderStyle === 'double' ? 'border-2' : 'border';

  const brushedPattern =
    'repeating-linear-gradient(135deg, rgba(255,255,255,0.07) 0px, rgba(255,255,255,0.07) 2px, rgba(0,0,0,0) 2px, rgba(0,0,0,0) 6px)';
  const carbonPattern =
    'repeating-linear-gradient(45deg, rgba(255,255,255,0.06) 0px, rgba(255,255,255,0.06) 2px, rgba(0,0,0,0) 2px, rgba(0,0,0,0) 6px), repeating-linear-gradient(-45deg, rgba(0,0,0,0.08) 0px, rgba(0,0,0,0.08) 2px, rgba(0,0,0,0) 2px, rgba(0,0,0,0) 6px)';
  const mattePattern =
    'radial-gradient(circle at 2px 2px, rgba(255,255,255,0.08) 0.6px, rgba(0,0,0,0) 0.8px)';
  const showChipLegs = resolvedVisualStyle?.edgeAddon === 'chip-legs';
  const chipLegsHorizontal = `repeating-linear-gradient(90deg,
    rgba(0,0,0,0) 0px,
    rgba(0,0,0,0) 4px,
    ${accentColorStrong} 4px,
    ${accentColorStrong} 7px,
    rgba(0,0,0,0) 7px,
    rgba(0,0,0,0) 11px
  )`;
  const chipLegsVertical = `repeating-linear-gradient(180deg,
    rgba(0,0,0,0) 0px,
    rgba(0,0,0,0) 4px,
    ${accentColorStrong} 4px,
    ${accentColorStrong} 7px,
    rgba(0,0,0,0) 7px,
    rgba(0,0,0,0) 11px
  )`;

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
          <div className="absolute inset-0">{getGateSVG(gateType)}</div>
          <span
            className={cn(
              'select-none text-[7px] font-bold text-foreground relative z-10',
              gateType === 'XNOR' ? 'text-[6px]' : 'text-[7px]',
              gateType === 'XNOR' && 'translate-x-[2px]',
              gateType === 'NOT' &&
                'absolute left-1/4 top-1/2 -translate-y-1/2',
            )}
          >
            {gateInstanceLabel}
          </span>
        </div>
      ) : isDffGate ? (
        <div className="pointer-events-none absolute inset-0">
          <div className="absolute inset-px rounded-sm bg-gradient-to-b from-card to-card/70" />
          <div className="absolute inset-0">{getGateSVG('DFF')}</div>
          <span className="absolute right-1 top-0.5 select-none rounded border border-border/60 bg-background/80 px-1 text-[6px] font-semibold leading-none text-muted-foreground">
            {gateInstanceLabel}
          </span>
        </div>
      ) : (
        <div className="pointer-events-none absolute inset-0">
          {showChipLegs ? (
            <>
              <div
                className="absolute inset-x-[6px] top-[-2px] h-[2px] opacity-95"
                style={{ backgroundImage: chipLegsHorizontal }}
              />
              <div
                className="absolute inset-x-[6px] bottom-[-2px] h-[2px] opacity-95"
                style={{ backgroundImage: chipLegsHorizontal }}
              />
              <div
                className="absolute inset-y-[6px] left-[-2px] w-[2px] opacity-90"
                style={{ backgroundImage: chipLegsVertical }}
              />
              <div
                className="absolute inset-y-[6px] right-[-2px] w-[2px] opacity-90"
                style={{ backgroundImage: chipLegsVertical }}
              />
            </>
          ) : null}

          {resolvedVisualStyle ? (
            <div
              className={cn(
                'absolute inset-[1px] overflow-hidden',
                shellBorderWidthClass,
                shellSurfaceClass,
                resolvedVisualStyle.borderStyle === 'etched'
                  ? 'shadow-[inset_0_1px_0_rgba(255,255,255,0.28),inset_0_-1px_0_rgba(0,0,0,0.2)]'
                  : 'shadow-[inset_0_1px_0_rgba(255,255,255,0.08)]',
              )}
              style={{
                borderRadius: shellRadius,
                borderColor: accentColorStrong,
                boxShadow:
                  resolvedVisualStyle.borderStyle === 'double'
                    ? `inset 0 1px 0 rgba(255,255,255,0.14), 0 0 0 1px ${accentColorSoft}`
                    : undefined,
              }}
            >
              {resolvedVisualStyle.surfaceStyle === 'brushed' ? (
                <div
                  className="absolute inset-0"
                  style={{
                    backgroundImage: brushedPattern,
                    opacity: 0.55,
                  }}
                />
              ) : null}
              {resolvedVisualStyle.surfaceStyle === 'carbon' ? (
                <div
                  className="absolute inset-0"
                  style={{
                    backgroundImage: carbonPattern,
                    opacity: 0.55,
                  }}
                />
              ) : null}
              {resolvedVisualStyle.surfaceStyle === 'matte' ? (
                <div
                  className="absolute inset-0"
                  style={{
                    backgroundImage: mattePattern,
                    backgroundSize: '4px 4px',
                    opacity: 0.35,
                  }}
                />
              ) : null}
              {resolvedVisualStyle.surfaceStyle === 'gradient' ? (
                <div
                  className="absolute inset-0"
                  style={{
                    background: `linear-gradient(180deg, ${accentColorSoft} 0%, rgba(0,0,0,0) 60%)`,
                  }}
                />
              ) : null}
              {resolvedVisualStyle.surfaceStyle === 'glass' ? (
                <>
                  <div
                    className="absolute inset-0"
                    style={{
                      background:
                        'linear-gradient(180deg, rgba(255,255,255,0.28) 0%, rgba(255,255,255,0.05) 32%, rgba(0,0,0,0.04) 100%)',
                    }}
                  />
                  <div
                    className="absolute left-[-20%] top-[8%] h-[35%] w-[70%] -rotate-12"
                    style={{
                      background:
                        'linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.35) 60%, rgba(255,255,255,0) 100%)',
                      opacity: 0.5,
                    }}
                  />
                </>
              ) : null}
              <div
                className="absolute left-0 top-0 h-full w-[3px]"
                style={{
                  borderTopLeftRadius: shellRadius,
                  borderBottomLeftRadius: shellRadius,
                  background: `linear-gradient(180deg, ${accentColorStrong} 0%, ${accentColorGlow} 100%)`,
                }}
              />
            </div>
          ) : (
            <div className="absolute inset-px rounded-[5px] border border-border/70 bg-gradient-to-b from-card via-card to-muted/25 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)]" />
          )}
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
