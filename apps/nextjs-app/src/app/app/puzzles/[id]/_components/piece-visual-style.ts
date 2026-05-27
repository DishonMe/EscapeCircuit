import type { LogicNodeVisualStyle } from './node';

const LEGACY_PRESETS = new Set([
  'clean-lab',
  'retro-chip',
  'blueprint',
  'playful',
]);
const LEGACY_CORNER_STYLES = new Set(['rounded', 'sharp', 'capsule']);
const BORDER_STYLES = new Set(['solid', 'double', 'etched']);
const EDGE_ADDONS = new Set(['none', 'chip-legs', 'chip']);
const SURFACE_STYLES = new Set([
  'flat',
  'brushed',
  'gradient',
  'matte',
  'glass',
  'carbon',
]);

const HEX_COLOR_RE = /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/;
const MIN_ROUNDNESS = 0;
const MAX_ROUNDNESS = 10;

const LEGACY_PRESET_DEFAULTS: Record<string, Required<LogicNodeVisualStyle>> = {
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

export const DEFAULT_PIECE_VISUAL_STYLE: Required<LogicNodeVisualStyle> = {
  accentColor: '#3b82f6',
  roundness: 4,
  borderStyle: 'solid',
  edgeAddon: 'none',
  surfaceStyle: 'gradient',
};

const asRecord = (value: unknown): Record<string, unknown> | null => {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
};

const asString = (value: unknown): string | undefined => {
  return typeof value === 'string' ? value : undefined;
};

const asNumber = (value: unknown): number | undefined => {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value === 'string' && value.trim()) {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return undefined;
};

const clampRoundness = (value: number) =>
  Math.max(MIN_ROUNDNESS, Math.min(MAX_ROUNDNESS, Math.round(value)));

const resolveLegacyCornerToRoundness = (
  cornerStyle: string,
): number | undefined => {
  if (cornerStyle === 'sharp') return 0;
  if (cornerStyle === 'capsule') return MAX_ROUNDNESS;
  if (cornerStyle === 'rounded') return 4;
  return undefined;
};

export const normalizeLogicNodeVisualStyle = (
  raw: unknown,
): LogicNodeVisualStyle | undefined => {
  const rec = asRecord(raw);
  if (!rec) return undefined;

  const presetRaw = asString(rec.preset);
  const accentRaw = asString(rec.accentColor ?? rec.accent_color);
  const roundnessRaw = asNumber(
    rec.roundness ?? rec.cornerRadius ?? rec.corner_radius,
  );
  const legacyCornerRaw = asString(rec.cornerStyle ?? rec.corner_style);
  const borderRaw = asString(rec.borderStyle ?? rec.border_style);
  const edgeAddonRaw = asString(rec.edgeAddon ?? rec.edge_addon);
  const surfaceRaw = asString(rec.surfaceStyle ?? rec.surface_style);

  const style: LogicNodeVisualStyle = {
    ...(presetRaw && LEGACY_PRESETS.has(presetRaw)
      ? LEGACY_PRESET_DEFAULTS[presetRaw]
      : {}),
  };

  if (accentRaw && HEX_COLOR_RE.test(accentRaw)) {
    style.accentColor = accentRaw;
  }
  if (typeof roundnessRaw === 'number') {
    style.roundness = clampRoundness(roundnessRaw);
  } else if (legacyCornerRaw && LEGACY_CORNER_STYLES.has(legacyCornerRaw)) {
    const legacyRoundness = resolveLegacyCornerToRoundness(legacyCornerRaw);
    if (typeof legacyRoundness === 'number') {
      style.roundness = legacyRoundness;
    }
  }
  if (borderRaw === 'chip') {
    style.edgeAddon = 'chip-legs';
    style.borderStyle = style.borderStyle ?? 'double';
  } else if (borderRaw && BORDER_STYLES.has(borderRaw)) {
    style.borderStyle = borderRaw as LogicNodeVisualStyle['borderStyle'];
  }

  if (edgeAddonRaw && EDGE_ADDONS.has(edgeAddonRaw)) {
    style.edgeAddon =
      edgeAddonRaw === 'chip'
        ? 'chip-legs'
        : (edgeAddonRaw as LogicNodeVisualStyle['edgeAddon']);
  }

  if (surfaceRaw && SURFACE_STYLES.has(surfaceRaw)) {
    style.surfaceStyle = surfaceRaw as LogicNodeVisualStyle['surfaceStyle'];
  }

  if (
    style.accentColor ||
    typeof style.roundness === 'number' ||
    style.borderStyle ||
    style.edgeAddon ||
    style.surfaceStyle
  ) {
    return style;
  }

  return undefined;
};

export const extractVisualStyleFromStructureJson = (
  structureJson: unknown,
): LogicNodeVisualStyle | undefined => {
  if (typeof structureJson !== 'string' || !structureJson.trim()) {
    return undefined;
  }

  try {
    const parsed = JSON.parse(structureJson);
    const rec = asRecord(parsed);
    if (!rec) return undefined;

    return (
      normalizeLogicNodeVisualStyle(rec.visualStyle) ??
      normalizeLogicNodeVisualStyle(rec.visual_style)
    );
  } catch {
    return undefined;
  }
};

export const extractVisualStyleFromComponentLike = (
  component: unknown,
): LogicNodeVisualStyle | undefined => {
  const rec = asRecord(component);
  if (!rec) return undefined;

  const direct =
    normalizeLogicNodeVisualStyle(rec.visualStyle) ??
    normalizeLogicNodeVisualStyle(rec.visual_style);
  if (direct) return direct;

  const solutionRec = asRecord(rec.solution);
  const fromSolution = solutionRec
    ? (normalizeLogicNodeVisualStyle(solutionRec.visualStyle) ??
      normalizeLogicNodeVisualStyle(solutionRec.visual_style))
    : undefined;
  if (fromSolution) return fromSolution;

  return extractVisualStyleFromStructureJson(rec.structure_json);
};
