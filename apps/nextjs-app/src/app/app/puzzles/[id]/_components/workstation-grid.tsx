'use client';

import { ChevronRight, Lock, ZoomIn, ZoomOut } from 'lucide-react';
import type {
  DragEvent as ReactDragEvent,
  PointerEvent as ReactPointerEvent,
} from 'react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { RippleEffect } from '@/components/ripple-effect';
import { Button } from '@/components/ui/button';
import { useNotifications } from '@/components/ui/notifications';
import { Spinner } from '@/components/ui/spinner';
import { ZigzagBugCanvas } from '@/components/ui/zigzag-bug-canvas';
import { useSettings } from '@/context/settings-context';
import { useAudio } from '@/hooks/use-audio';
import type { Wire } from '@/types/api';
import { cn } from '@/utils/cn';

import { LogicNode, type LogicNodeVisualStyle } from './node';

export type HoleCoord = { row: number; col: number };

export type PortKind = 'input' | 'output';

export type PortDef = {
  id: string;
  kind: PortKind;
  // offset in holes relative to component origin (top-left when rotation=0)
  offset: HoleCoord;
};

export type ComponentDef = {
  id: string;
  label: string;
  cost: number;
  size: { w: number; h: number };
  ports: PortDef[];
  visualStyle?: LogicNodeVisualStyle;
};

export type PlacedGridComponent = {
  id: string; // instance id
  componentId: string; // catalog id
  origin: HoleCoord;
  rotation: 0 | 90;
  isLocked?: boolean; // If true, component is immovable, undeletable, and mandatory to use
};
type ClipboardComponent = PlacedGridComponent & {
  label: string;
};
type ClipboardPayload = {
  version: 1;
  sourcePuzzleId: string;
  components: ClipboardComponent[];
  wires: Wire[];
};
const normalizeClipboardKey = (value: string) => value.trim().toLowerCase();

export type PortAddress = {
  ownerId: string; // placedId or IO:IN:* / IO:OUT:*
  portId: string; // stable within owner
  kind: PortKind; // effective kind
  // for placed components, hole coord in grid; for IO ports, undefined
  hole?: HoleCoord;
};

export type SelectedComponentState =
  | { mode: 'none' }
  | { mode: 'placing'; componentId: string; rotation: 0 | 90 };

const DEFAULT_GRID_ROWS = 15;
const DEFAULT_GRID_COLS = 30;
const CELL_PX = 18;
const PUZZLE_IO_Y_OFFSET_PX = 20;
const WORKSTATION_CLIPBOARD_STORAGE_KEY =
  'escapecircuit.workstation.clipboard.v1';

// Visual Feature: Dynamic Wire Coloring
const WIRE_COLORS = ['#3b82f6', '#ef4444', '#10b981', '#a855f7', '#f97316'];
const getWireColor = (id: string) => {
  let hash = 0;
  for (let i = 0; i < id.length; i++)
    hash = id.charCodeAt(i) + ((hash << 5) - hash);
  const index = Math.abs(hash % WIRE_COLORS.length);
  return WIRE_COLORS[index];
};

const clamp = (n: number, min: number, max: number) =>
  Math.max(min, Math.min(max, n));

const rotateOffset = (
  offset: HoleCoord,
  size: { w: number; h: number },
  rotation: 0 | 90,
): HoleCoord => {
  if (rotation === 0) return offset;
  // rotate clockwise around top-left of bounding box
  // point (r,c) in h×w becomes (c, h-1-r) in w×h
  return { row: offset.col, col: size.h - 1 - offset.row };
};

const rotatedSize = (size: { w: number; h: number }, rotation: 0 | 90) => {
  return rotation === 0 ? size : { w: size.h, h: size.w };
};

const getVisualPortOffsets = (
  def: ComponentDef,
  rotation: 0 | 90,
): Map<string, HoleCoord> => {
  const result = new Map<string, HoleCoord>();

  for (const port of def.ports) {
    result.set(port.id, rotateOffset(port.offset, def.size, rotation));
  }

  const grouped: Record<PortKind, Array<{ port: PortDef; index: number }>> = {
    input: [],
    output: [],
  };

  def.ports.forEach((port, index) => {
    grouped[port.kind].push({ port, index });
  });

  const inputCount = grouped.input.length;
  const outputCount = grouped.output.length;

  if (inputCount === outputCount || inputCount === 0 || outputCount === 0) {
    return result;
  }

  const lowerKind: PortKind = inputCount < outputCount ? 'input' : 'output';
  const lowerPorts = grouped[lowerKind].sort(
    (a, b) =>
      a.port.offset.row - b.port.offset.row ||
      a.port.offset.col - b.port.offset.col ||
      a.index - b.index,
  );

  const componentHeight = Math.max(1, def.size.h);

  lowerPorts.forEach(({ port }, index) => {
    const distributedRow =
      -0.5 + ((index + 1) * componentHeight) / (lowerPorts.length + 1);

    result.set(
      port.id,
      rotateOffset(
        { row: distributedRow, col: port.offset.col },
        def.size,
        rotation,
      ),
    );
  });

  return result;
};

const inRect = (
  p: HoleCoord,
  origin: HoleCoord,
  size: { w: number; h: number },
) => {
  return (
    p.row >= origin.row &&
    p.col >= origin.col &&
    p.row < origin.row + size.h &&
    p.col < origin.col + size.w
  );
};

const parseDraggedComponentId = (
  e: ReactDragEvent,
  fallbackComponentId?: string | null,
) => {
  const customType = e.dataTransfer
    .getData('application/x-escapecircuit-component')
    .trim();
  if (customType) return customType;

  const plainText = e.dataTransfer.getData('text/plain').trim();
  if (plainText) return plainText;

  return (fallbackComponentId ?? '').trim();
};

export const WorkstationGrid = ({
  puzzleId,
  inputs,
  outputs,
  catalog,
  placed,
  wires,
  selectedComponent,
  onSelectedComponentChange,
  onPlacedChange,
  onWiresChange,
  draggedPaletteComponentId,
  isChecking = false,
  isPowerSurge = false,
  boardFeedback = 'idle',
  showSolvedSlam = false,
  activeWireIds = [],
  activeComponentIds = [],
  highlightedWireIds = [],
  boardRows,
  boardCols,
  debuggerActive = false,
  debuggerStepIndex = 0,
  debuggerStepCount = 0,
  debuggerInputBits = {},
  debuggerOutputBits = {},
  debuggerGateBits = {},
  debuggerSequences = {},
  onDebuggerSequenceChange,
  onDebuggerSequenceCommit,
  onEnterInlineDebugger,
  onDebuggerStepPrev,
  onDebuggerStepNext,
  onOpenFullDebuggerReport,
  onExitInlineDebugger,
  isEditMode = false,
  viewportClassName,
  disableZoomPersistence = false,
  emptyHoleClassName,
}: {
  puzzleId: string;
  inputs: string[];
  outputs: string[];
  catalog: Record<string, ComponentDef>;
  placed: PlacedGridComponent[];
  wires: Wire[];
  selectedComponent: SelectedComponentState;
  onSelectedComponentChange: (next: SelectedComponentState) => void;
  onPlacedChange: (next: PlacedGridComponent[]) => void;
  onWiresChange: (next: Wire[]) => void;
  draggedPaletteComponentId?: string | null;
  isChecking?: boolean;
  isPowerSurge?: boolean;
  boardFeedback?: 'idle' | 'success' | 'failure';
  showSolvedSlam?: boolean;
  activeWireIds?: string[];
  activeComponentIds?: string[];
  highlightedWireIds?: string[];
  boardRows?: number | null;
  boardCols?: number | null;
  debuggerActive?: boolean;
  debuggerStepIndex?: number;
  debuggerStepCount?: number;
  debuggerInputBits?: Record<string, string>;
  debuggerOutputBits?: Record<string, string>;
  debuggerGateBits?: Record<string, string>;
  debuggerSequences?: Record<string, string>;
  onDebuggerSequenceChange?: (inputName: string, sequence: string) => void;
  onDebuggerSequenceCommit?: (inputName: string, sequence: string) => void;
  onEnterInlineDebugger?: () => void;
  onDebuggerStepPrev?: () => void;
  onDebuggerStepNext?: () => void;
  onOpenFullDebuggerReport?: () => void;
  onExitInlineDebugger?: () => void;
  onInspectComponent?: (placedId: string) => void;
  arsenalComponentDisplayModes?: Record<string, 'circuit' | 'description'>;
  isEditMode?: boolean;
  viewportClassName?: string;
  disableZoomPersistence?: boolean;
  emptyHoleClassName?: string;
}) => {
  const gridRows = Math.max(1, boardRows ?? DEFAULT_GRID_ROWS);
  const gridCols = Math.max(1, boardCols ?? DEFAULT_GRID_COLS);
  const notifications = useNotifications();
  const { playDrop, playWireConnect } = useAudio();
  const { visualEffectsEnabled } = useSettings();

  const containerRef = useRef<HTMLDivElement | null>(null);
  const debuggerButtonRef = useRef<HTMLButtonElement | null>(null);
  const panAnimationFrameRef = useRef<number | null>(null);
  const [zoom, setZoom] = useState(1);
  const [minZoom, setMinZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });

  const [isPanning, setIsPanning] = useState(false);
  const panStartRef = useRef<{
    x: number;
    y: number;
    panX: number;
    panY: number;
  } | null>(null);

  const [selectedEntity, setSelectedEntity] = useState<
    | { type: 'none' }
    | { type: 'component'; placedIds: string[] }
    | { type: 'wire'; wireId: string }
  >({ type: 'none' });

  const [wireDraft, setWireDraft] = useState<null | {
    start: PortAddress;
    current: { x: number; y: number };
  }>(null);

  const [draggedComponent, setDraggedComponent] = useState<{
    placedIds: string[];
    startMouseHole: HoleCoord;
    currentMouseHole: HoleCoord;
    deltaRow: number;
    deltaCol: number;
  } | null>(null);

  // Ghost/Preview State
  const [dropPreview, setDropPreview] = useState<HoleCoord | null>(null);
  const [recentlyPlacedId, setRecentlyPlacedId] = useState<string | null>(null);
  const [recentlyConnectedWireId, setRecentlyConnectedWireId] = useState<
    string | null
  >(null);
  const [hoveredDeleteComponentId, setHoveredDeleteComponentId] = useState<
    string | null
  >(null);
  const [hoveredDeleteWireId, setHoveredDeleteWireId] = useState<string | null>(
    null,
  );
  const [deletingComponentIds, setDeletingComponentIds] = useState<string[]>(
    [],
  );
  const [activeRipples, setActiveRipples] = useState<
    Array<{ id: string; x: number; y: number }>
  >([]);
  const [cursorSpotlight, setCursorSpotlight] = useState<{
    x: number;
    y: number;
    visible: boolean;
  }>({
    x: 0,
    y: 0,
    visible: false,
  });
  const [, setHoveredWireSignal] = useState<{
    wireId: string;
    x: number;
    y: number;
    high: boolean;
  } | null>(null);
  const [flashingPortKeys, setFlashingPortKeys] = useState<string[]>([]);
  const [wireSnapBack, setWireSnapBack] = useState<null | {
    from: { x: number; y: number };
    current: { x: number; y: number };
    startedAt: number;
  }>(null);
  const [microSparks, setMicroSparks] = useState<
    Array<{ id: string; x: number; y: number; dx: number; dy: number }>
  >([]);
  const [clipboard, setClipboard] = useState<ClipboardPayload | null>(null);
  const [bootSequenceActive, setBootSequenceActive] = useState(true);
  const [isWorkingAreaCollapsed, setIsWorkingAreaCollapsed] = useState(false);

  const canCopySelection =
    selectedEntity.type === 'component' && selectedEntity.placedIds.length > 0;
  const canPasteSelection = Boolean(
    clipboard && clipboard.components.length > 0,
  );

  const catalogLookup = useMemo(() => {
    const lookup = new Map<string, string>();

    for (const def of Object.values(catalog)) {
      lookup.set(normalizeClipboardKey(def.id), def.id);
      lookup.set(normalizeClipboardKey(def.label), def.id);
    }

    return lookup;
  }, [catalog]);

  const resolveCatalogComponentId = useCallback(
    (component: ClipboardComponent): string | null => {
      const exact = catalog[component.componentId];
      if (exact) return exact.id;

      const byLabel = catalogLookup.get(
        normalizeClipboardKey(component.label || component.componentId),
      );
      return byLabel ?? null;
    },
    [catalog, catalogLookup],
  );

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(
        WORKSTATION_CLIPBOARD_STORAGE_KEY,
      );
      if (!raw) return;

      const parsed = JSON.parse(raw) as ClipboardPayload;
      if (
        parsed &&
        parsed.version === 1 &&
        Array.isArray(parsed.components) &&
        Array.isArray(parsed.wires)
      ) {
        setClipboard(parsed);
      }
    } catch {
      // ignore clipboard hydration failures
    }
  }, []);

  const persistClipboardPayload = useCallback(
    async (payload: ClipboardPayload) => {
      setClipboard(payload);

      try {
        window.localStorage.setItem(
          WORKSTATION_CLIPBOARD_STORAGE_KEY,
          JSON.stringify(payload),
        );
      } catch {
        // ignore storage failures
      }

      try {
        if (navigator.clipboard?.writeText) {
          await navigator.clipboard.writeText(JSON.stringify(payload));
        }
      } catch {
        // ignore clipboard write failures
      }
    },
    [],
  );

  const readClipboardPayload =
    useCallback(async (): Promise<ClipboardPayload | null> => {
      const parsePayload = (raw: string | null): ClipboardPayload | null => {
        if (!raw) return null;

        try {
          const parsed = JSON.parse(raw) as ClipboardPayload;
          if (
            parsed &&
            parsed.version === 1 &&
            Array.isArray(parsed.components) &&
            Array.isArray(parsed.wires)
          ) {
            return parsed;
          }
        } catch {
          return null;
        }

        return null;
      };

      try {
        const systemText = navigator.clipboard
          ? await navigator.clipboard.readText()
          : '';
        const fromSystem = parsePayload(systemText);
        if (fromSystem) return fromSystem;
      } catch {
        // ignore clipboard read failures
      }

      const fromState = clipboard;
      if (fromState) return fromState;

      try {
        return parsePayload(
          window.localStorage.getItem(WORKSTATION_CLIPBOARD_STORAGE_KEY),
        );
      } catch {
        return null;
      }
    }, [clipboard]);

  const copySelectionToClipboard = useCallback(async () => {
    if (
      selectedEntity.type !== 'component' ||
      selectedEntity.placedIds.length === 0
    ) {
      return;
    }

    const selectedIds = new Set(selectedEntity.placedIds);
    const selectedComps = placed.filter((p) => selectedIds.has(p.id));
    const internalWires = wires.filter(
      (w) =>
        selectedIds.has(w.from.componentId) &&
        selectedIds.has(w.to.componentId),
    );

    const payload: ClipboardPayload = {
      version: 1,
      sourcePuzzleId: puzzleId,
      components: selectedComps.map((component) => ({
        ...component,
        label: catalog[component.componentId]?.label ?? component.componentId,
      })),
      wires: internalWires,
    };

    await persistClipboardPayload(payload);
  }, [
    catalog,
    persistClipboardPayload,
    placed,
    puzzleId,
    selectedEntity,
    wires,
  ]);

  const pasteFromClipboard = useCallback(async () => {
    const payload = await readClipboardPayload();
    if (!payload || payload.components.length === 0) {
      return;
    }

    const resolvedComponents: Array<{
      comp: ClipboardComponent;
      resolvedComponentId: string;
      def: ComponentDef;
      size: { w: number; h: number };
    }> = [];
    const missingComponents: string[] = [];

    for (const comp of payload.components) {
      const resolvedComponentId = resolveCatalogComponentId(comp);
      if (!resolvedComponentId) {
        missingComponents.push(comp.label || comp.componentId);
        continue;
      }

      const def = catalog[resolvedComponentId];
      if (!def) {
        missingComponents.push(comp.label || comp.componentId);
        continue;
      }

      resolvedComponents.push({
        comp,
        resolvedComponentId,
        def,
        size: rotatedSize(def.size, comp.rotation),
      });
    }

    if (!resolvedComponents.length) {
      notifications.addNotification({
        type: 'warning',
        title: 'Cannot paste here',
        message: 'No copied components are available in this workspace.',
      });
      return;
    }

    if (missingComponents.length > 0) {
      notifications.addNotification({
        type: 'warning',
        title: 'Partial paste',
        message: `Skipped ${missingComponents.length} unavailable component${missingComponents.length === 1 ? '' : 's'}.`,
      });
    }

    const copiedWithDefs: Array<{
      resolvedComponentId: string;
      comp: PlacedGridComponent;
      def: ComponentDef;
      size: { w: number; h: number };
    }> = resolvedComponents;

    const minRow = Math.min(
      ...copiedWithDefs.map(({ comp }) => comp.origin.row),
    );
    const minCol = Math.min(
      ...copiedWithDefs.map(({ comp }) => comp.origin.col),
    );
    const maxRowExclusive = Math.max(
      ...copiedWithDefs.map(({ comp, size }) => comp.origin.row + size.h),
    );
    const maxColExclusive = Math.max(
      ...copiedWithDefs.map(({ comp, size }) => comp.origin.col + size.w),
    );

    const groupHeight = maxRowExclusive - minRow;
    const groupWidth = maxColExclusive - minCol;

    if (groupHeight > gridRows || groupWidth > gridCols) {
      notifications.addNotification({
        type: 'warning',
        title: 'Cannot paste here',
        message: 'Copied block is larger than the board.',
      });
      return;
    }

    const existingOccupiedHoles = new Set<string>();
    const existingOccupiedPortHoles = new Set<string>();

    for (const existing of placed) {
      const def = catalog[existing.componentId];
      if (!def) continue;

      const size = rotatedSize(def.size, existing.rotation);
      for (let r = 0; r < size.h; r++) {
        for (let c = 0; c < size.w; c++) {
          existingOccupiedHoles.add(
            `r${existing.origin.row + r}c${existing.origin.col + c}`,
          );
        }
      }

      for (const port of def.ports) {
        const rotOff = rotateOffset(port.offset, def.size, existing.rotation);
        const row = existing.origin.row + rotOff.row;
        const col = existing.origin.col + rotOff.col;
        existingOccupiedPortHoles.add(`r${row}c${col}`);
      }
    }

    const relativeLayout = copiedWithDefs.map((item) => ({
      ...item,
      rowOffset: item.comp.origin.row - minRow,
      colOffset: item.comp.origin.col - minCol,
    }));

    const isValidAnchor = (anchorRow: number, anchorCol: number) => {
      const groupOccupiedHoles = new Set<string>();
      const groupOccupiedPortHoles = new Set<string>();

      for (const item of relativeLayout) {
        const row = anchorRow + item.rowOffset;
        const col = anchorCol + item.colOffset;

        if (row < 0 || col < 0) return false;
        if (row + item.size.h > gridRows) return false;
        if (col + item.size.w > gridCols) return false;

        for (let r = 0; r < item.size.h; r++) {
          for (let c = 0; c < item.size.w; c++) {
            const key = `r${row + r}c${col + c}`;
            if (existingOccupiedHoles.has(key) || groupOccupiedHoles.has(key)) {
              return false;
            }
            groupOccupiedHoles.add(key);
          }
        }

        for (const port of item.def.ports) {
          const rotOff = rotateOffset(
            port.offset,
            item.def.size,
            item.comp.rotation,
          );
          const key = `r${row + rotOff.row}c${col + rotOff.col}`;
          if (
            existingOccupiedPortHoles.has(key) ||
            groupOccupiedPortHoles.has(key)
          ) {
            return false;
          }
          groupOccupiedPortHoles.add(key);
        }
      }

      return true;
    };

    const maxAnchorRow = gridRows - groupHeight;
    const maxAnchorCol = gridCols - groupWidth;

    const preferredAnchor = {
      row: clamp(minRow + 2, 0, maxAnchorRow),
      col: clamp(minCol + 2, 0, maxAnchorCol),
    };

    let chosenAnchor: HoleCoord | null = null;

    if (isValidAnchor(preferredAnchor.row, preferredAnchor.col)) {
      chosenAnchor = preferredAnchor;
    } else {
      for (let row = 0; row <= maxAnchorRow && !chosenAnchor; row++) {
        for (let col = 0; col <= maxAnchorCol; col++) {
          if (row === preferredAnchor.row && col === preferredAnchor.col)
            continue;
          if (isValidAnchor(row, col)) {
            chosenAnchor = { row, col };
            break;
          }
        }
      }
    }

    if (!chosenAnchor) {
      notifications.addNotification({
        type: 'warning',
        title: 'Cannot paste here',
        message: 'No free rectangle is large enough for this copied block.',
      });
      return;
    }

    const idMap = new Map<string, string>();
    const newComponents: PlacedGridComponent[] = [];
    const newWires: Wire[] = [];
    const pasteStamp = Date.now();

    relativeLayout.forEach((item, idx) => {
      const newId = `${item.resolvedComponentId}:${pasteStamp}-${idx}`;
      idMap.set(item.comp.id, newId);
      newComponents.push({
        id: newId,
        componentId: item.resolvedComponentId,
        origin: {
          row: chosenAnchor.row + item.rowOffset,
          col: chosenAnchor.col + item.colOffset,
        },
        rotation: item.comp.rotation,
      });
    });

    payload.wires.forEach((wire, idx) => {
      const newFromId = idMap.get(wire.from.componentId);
      const newToId = idMap.get(wire.to.componentId);
      if (newFromId && newToId) {
        newWires.push({
          id: `${wire.id}:${pasteStamp}-${idx}`,
          from: { ...wire.from, componentId: newFromId },
          to: { ...wire.to, componentId: newToId },
        });
      }
    });

    onPlacedChange([...placed, ...newComponents]);
    onWiresChange([...wires, ...newWires]);
    setSelectedEntity({
      type: 'component',
      placedIds: Array.from(idMap.values()),
    });
  }, [
    catalog,
    gridRows,
    gridCols,
    notifications,
    onPlacedChange,
    onWiresChange,
    placed,
    readClipboardPayload,
    resolveCatalogComponentId,
    wires,
  ]);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      setBootSequenceActive(false);
    }, 1200);

    return () => window.clearTimeout(timeoutId);
  }, []);

  // Copy/Paste keyboard shortcuts (Ctrl+C / Ctrl+V)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const isCopyKey =
        (e.key === 'c' || e.key === 'C') &&
        (e.ctrlKey || e.metaKey) &&
        !e.shiftKey;
      const isPasteKey =
        (e.key === 'v' || e.key === 'V') &&
        (e.ctrlKey || e.metaKey) &&
        !e.shiftKey;

      if (isCopyKey) {
        e.preventDefault();
        void copySelectionToClipboard();
      }

      if (isPasteKey) {
        e.preventDefault();
        void pasteFromClipboard();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [copySelectionToClipboard, pasteFromClipboard]);

  // Keyboard deletion (Delete / Backspace).
  // We stash the live handler in a ref so the listener attaches once and
  // always reads current state — avoiding both stale closures and the
  // re-binding thrash that would come from listing every dep on the effect.
  const deleteKeyHandlerRef = useRef<(e: KeyboardEvent) => void>();
  deleteKeyHandlerRef.current = (e: KeyboardEvent) => {
    if (e.key !== 'Delete' && e.key !== 'Backspace') return;

    // Don't delete if user is typing in an input field
    const activeEl = document.activeElement as HTMLElement;
    if (
      activeEl &&
      (activeEl.tagName === 'INPUT' || activeEl.tagName === 'TEXTAREA')
    ) {
      return;
    }

    e.preventDefault();

    if (
      selectedEntity.type === 'component' &&
      selectedEntity.placedIds.length > 0
    ) {
      // Delete all selected components (skip locked ones unless in edit mode)
      for (const placedId of selectedEntity.placedIds) {
        const component = placed.find((c) => c.id === placedId);
        if (component?.isLocked && !isEditMode) {
          continue;
        }
        removeComponent(placedId);
      }
    } else if (selectedEntity.type === 'wire') {
      const wire = wires.find((w) => w.id === selectedEntity.wireId);
      if (!wire?.isLocked || isEditMode) {
        removeWire(selectedEntity.wireId);
      }
    }
  };

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      deleteKeyHandlerRef.current?.(e);
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const activeWireIdsSet = useMemo(
    () => new Set(activeWireIds),
    [activeWireIds],
  );
  const activeComponentIdsSet = useMemo(
    () => new Set(activeComponentIds),
    [activeComponentIds],
  );

  const highInputOwnerIds = useMemo(() => {
    const set = new Set<string>();
    for (const w of wires) {
      if (!activeWireIdsSet.has(w.id)) continue;
      if (w.from.componentId.startsWith('IO:IN:')) set.add(w.from.componentId);
      if (w.to.componentId.startsWith('IO:IN:')) set.add(w.to.componentId);
    }
    return set;
  }, [wires, activeWireIdsSet]);

  const previousPlacedIdsRef = useRef<string[]>(
    placed.map((component) => component.id),
  );
  const previousWireIdsRef = useRef<string[]>(wires.map((wire) => wire.id));

  const STORAGE_KEY = `escapecircuit.workstation.grid.v1:${puzzleId}`;
  const shouldPersistZoom = !disableZoomPersistence;

  // Load/save view state.
  useEffect(() => {
    if (!shouldPersistZoom) return;

    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      let hasSavedZoom = false;
      if (raw) {
        const parsed = JSON.parse(raw) as any;
        if (typeof parsed?.zoom === 'number') {
          setZoom(parsed.zoom);
          hasSavedZoom = true;
        }
        // Don't load pan, always reset to show inputs
      }

      if (!hasSavedZoom) {
        // Set default zoom if no saved
        const el = containerRef.current;
        if (el) {
          const rect = el.getBoundingClientRect();
          const fit = Math.min(
            rect.width / ((gridCols + 4) * CELL_PX),
            rect.height / ((gridRows + 4) * CELL_PX),
          );
          setZoom(fit);
        }
      }
      // Pan is set in the other useEffect
    } catch {
      // ignore
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [STORAGE_KEY, gridCols, gridRows, shouldPersistZoom]);

  useEffect(() => {
    if (!shouldPersistZoom) return;

    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ zoom }));
    } catch {
      // ignore
    }
  }, [STORAGE_KEY, zoom, shouldPersistZoom]);

  useEffect(() => {
    const previousPlacedIds = previousPlacedIdsRef.current;
    const addedComponent = placed.find(
      (component) => !previousPlacedIds.includes(component.id),
    );

    if (addedComponent) {
      setRecentlyPlacedId(addedComponent.id);
      const timeoutId = window.setTimeout(() => {
        setRecentlyPlacedId((current) =>
          current === addedComponent.id ? null : current,
        );
      }, 320);

      previousPlacedIdsRef.current = placed.map((component) => component.id);
      return () => window.clearTimeout(timeoutId);
    }

    previousPlacedIdsRef.current = placed.map((component) => component.id);
  }, [placed]);

  useEffect(() => {
    const previousWireIds = previousWireIdsRef.current;
    const addedWire = wires.find((wire) => !previousWireIds.includes(wire.id));

    if (addedWire) {
      setRecentlyConnectedWireId(addedWire.id);
      const timeoutId = window.setTimeout(() => {
        setRecentlyConnectedWireId((current) =>
          current === addedWire.id ? null : current,
        );
      }, 500);

      previousWireIdsRef.current = wires.map((wire) => wire.id);
      return () => window.clearTimeout(timeoutId);
    }

    previousWireIdsRef.current = wires.map((wire) => wire.id);
  }, [wires]);

  // Compute minZoom so the entire grid fits; set as default if no saved state.
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const updateFit = () => {
      const rect = el.getBoundingClientRect();
      // Account for IO ports: Inputs at col -1, Outputs at row gridRows.
      // We want to see from col -2 to gridCols + 1, and row -1 to gridRows + 2.
      const fit = Math.min(
        rect.width / ((gridCols + 4) * CELL_PX),
        rect.height / ((gridRows + 4) * CELL_PX),
      );
      setMinZoom(fit);
      return fit;
    };

    const calculatePan = (currentZoom: number, containerWidth: number, containerHeight: number) => {
      const panX = containerWidth / 2 - (gridCols / 2) * CELL_PX * currentZoom;
      const panY = containerHeight / 2 - (gridRows / 2) * CELL_PX * currentZoom;
      return { x: panX, y: panY };
    };

    const raw = shouldPersistZoom
      ? window.localStorage.getItem(STORAGE_KEY)
      : null;
    
    let activeZoom = 1;
    const fit = updateFit();
    if (!raw) {
      activeZoom = fit;
      setZoom(activeZoom);
    } else {
      try {
        const parsed = JSON.parse(raw);
        if (typeof parsed?.zoom === 'number') {
          activeZoom = Math.max(parsed.zoom, fit);
        } else {
          activeZoom = fit;
        }
      } catch {
        activeZoom = fit;
      }
      setZoom(activeZoom);
    }

    const rect = el.getBoundingClientRect();
    setPan(calculatePan(activeZoom, rect.width, rect.height));

    const ro = new ResizeObserver(() => {
      const newFit = updateFit();
      setZoom((prev) => {
        const nextZoom = Math.max(prev, newFit);
        const newRect = el.getBoundingClientRect();
        setPan(calculatePan(nextZoom, newRect.width, newRect.height));
        return nextZoom;
      });
    });
    ro.observe(el);

    return () => ro.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [STORAGE_KEY, gridCols, gridRows, shouldPersistZoom]);

  const componentRects = useMemo(() => {
    return placed
      .map((p) => {
        const def = catalog[p.componentId];
        if (!def) {
          console.warn(`Component definition missing for ID: ${p.componentId}`);
          return null;
        }
        const size = rotatedSize(def.size, p.rotation);
        return { placedId: p.id, origin: p.origin, size };
      })
      .filter((item) => item !== null) as Array<{
      placedId: string;
      origin: { row: number; col: number };
      size: { w: number; h: number };
    }>;
  }, [catalog, placed]);

  const placedById = useMemo(() => {
    const map: Record<string, PlacedGridComponent> = {};
    for (const p of placed) map[p.id] = p;
    return map;
  }, [placed]);

  const visualPortOffsetsByPlacedId = useMemo(() => {
    const map = new Map<string, Map<string, HoleCoord>>();
    for (const p of placed) {
      const def = catalog[p.componentId];
      if (!def) continue;
      map.set(p.id, getVisualPortOffsets(def, p.rotation));
    }
    return map;
  }, [catalog, placed]);

  const portIndexByPortId = useMemo(() => {
    const map = new Map<string, Map<string, number>>();
    for (const [id, def] of Object.entries(catalog)) {
      const m = new Map<string, number>();
      def.ports.forEach((p, idx) => m.set(p.id, idx));
      map.set(id, m);
    }
    return map;
  }, [catalog]);

  const allPorts = useMemo(() => {
    const ports: PortAddress[] = [];

    for (const p of placed) {
      const def = catalog[p.componentId];
      if (!def) {
        console.warn(`Component definition missing for ID: ${p.componentId}`);
        continue;
      }
      const baseSize = def.size;
      for (const port of def.ports) {
        const rot = rotateOffset(port.offset, baseSize, p.rotation);
        ports.push({
          ownerId: p.id,
          portId: port.id,
          kind: port.kind,
          hole: { row: p.origin.row + rot.row, col: p.origin.col + rot.col },
        });
      }
    }

    // Puzzle IO: reversed semantics (inputs act as outputs; outputs act as inputs).
    for (const label of inputs) {
      ports.push({ ownerId: `IO:IN:${label}`, portId: 'P0', kind: 'output' });
    }
    for (const label of outputs) {
      ports.push({ ownerId: `IO:OUT:${label}`, portId: 'P0', kind: 'input' });
    }

    return ports;
  }, [catalog, placed, inputs, outputs]);

  const occupiedHoles = useMemo(() => {
    const occ = new Map<string, { placedId: string }>();
    for (const rect of componentRects) {
      for (let r = 0; r < rect.size.h; r++) {
        for (let c = 0; c < rect.size.w; c++) {
          const key = `r${rect.origin.row + r}c${rect.origin.col + c}`;
          occ.set(key, { placedId: rect.placedId });
        }
      }
    }
    return occ;
  }, [componentRects]);

  const occupiedPortHoles = useMemo(() => {
    const occ = new Map<string, { ownerId: string; portId: string }>();
    for (const p of allPorts) {
      if (!p.hole) continue;
      const key = `r${p.hole.row}c${p.hole.col}`;
      occ.set(key, { ownerId: p.ownerId, portId: p.portId });
    }
    return occ;
  }, [allPorts]);

  const staleLogicalPortHoleKeys = useMemo(() => {
    const keys = new Set<string>();

    for (const p of placed) {
      const def = catalog[p.componentId];
      if (!def) continue;

      const visualOffsets = visualPortOffsetsByPlacedId.get(p.id);
      if (!visualOffsets) continue;

      for (const port of def.ports) {
        const logicalOffset = rotateOffset(port.offset, def.size, p.rotation);
        const visualOffset = visualOffsets.get(port.id) ?? logicalOffset;

        if (
          visualOffset.row !== logicalOffset.row ||
          visualOffset.col !== logicalOffset.col
        ) {
          const key = `r${p.origin.row + logicalOffset.row}c${p.origin.col + logicalOffset.col}`;
          keys.add(key);
        }
      }
    }

    return keys;
  }, [catalog, placed, visualPortOffsetsByPlacedId]);

  const worldToScreen = (hole: HoleCoord) => {
    const x = pan.x + hole.col * CELL_PX * zoom;
    const y = pan.y + hole.row * CELL_PX * zoom;
    return { x, y };
  };

  const screenToWorld = (pt: { x: number; y: number }) => {
    const col = (pt.x - pan.x) / (CELL_PX * zoom);
    const row = (pt.y - pan.y) / (CELL_PX * zoom);
    return { row, col };
  };

  const getVisibleRange = () => {
    const el = containerRef.current;
    if (!el) {
      return { r0: 0, r1: 0, c0: 0, c1: 0 };
    }
    const rect = el.getBoundingClientRect();
    const topLeft = screenToWorld({ x: 0, y: 0 });
    const bottomRight = screenToWorld({ x: rect.width, y: rect.height });

    const c0 = clamp(Math.floor(topLeft.col) - 2, 0, gridCols - 1);
    const r0 = clamp(Math.floor(topLeft.row) - 2, 0, gridRows - 1);
    const c1 = clamp(Math.ceil(bottomRight.col) + 2, 0, gridCols - 1);
    const r1 = clamp(Math.ceil(bottomRight.row) + 2, 0, gridRows - 1);

    return { r0, r1, c0, c1 };
  };

  const [visible, setVisible] = useState(() => getVisibleRange());
  const [containerSize, setContainerSize] = useState({ w: 0, h: 0 });

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const update = () => {
      setVisible(getVisibleRange());
      const r = el.getBoundingClientRect();
      setContainerSize({ w: r.width, h: r.height });
    };
    update();

    const ro = new ResizeObserver(update);
    ro.observe(el);

    return () => ro.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [zoom, pan.x, pan.y]);

  const clampPanToBounds = useCallback(
    (nextPan: { x: number; y: number }, nextZoom: number = zoom) => {
      const el = containerRef.current;
      if (!el) return nextPan;

      const rect = el.getBoundingClientRect();
      const gridWidthPx = (gridCols + 1) * CELL_PX * nextZoom;
      const gridHeightPx = (gridRows + 1) * CELL_PX * nextZoom;

      const paddingX = 250;
      const paddingY = 150;

      const limitX1 = paddingX;
      const limitX2 = rect.width - gridWidthPx - paddingX;
      const minPanX = Math.min(limitX1, limitX2);
      const maxPanX = Math.max(limitX1, limitX2);

      const limitY1 = paddingY;
      const limitY2 = rect.height - gridHeightPx - paddingY;
      const minPanY = Math.min(limitY1, limitY2);
      const maxPanY = Math.max(limitY1, limitY2);

      return {
        x: clamp(nextPan.x, minPanX, maxPanX),
        y: clamp(nextPan.y, minPanY, maxPanY),
      };
    },
    [gridCols, gridRows, zoom],
  );

  const stopPanAnimation = useCallback(() => {
    if (panAnimationFrameRef.current !== null) {
      window.cancelAnimationFrame(panAnimationFrameRef.current);
      panAnimationFrameRef.current = null;
    }
  }, []);

  const animatePanTo = useCallback(
    (targetPan: { x: number; y: number }, durationMs = 320) => {
      stopPanAnimation();

      const startPan = pan;
      const startTime = performance.now();

      const step = (now: number) => {
        const t = Math.min(1, (now - startTime) / durationMs);
        const eased = 1 - Math.pow(1 - t, 3);

        const nextPan = {
          x: startPan.x + (targetPan.x - startPan.x) * eased,
          y: startPan.y + (targetPan.y - startPan.y) * eased,
        };

        setPan(clampPanToBounds(nextPan));

        if (t < 1) {
          panAnimationFrameRef.current = window.requestAnimationFrame(step);
        } else {
          panAnimationFrameRef.current = null;
        }
      };

      panAnimationFrameRef.current = window.requestAnimationFrame(step);
    },
    [clampPanToBounds, pan, stopPanAnimation],
  );

  useEffect(() => {
    return () => {
      stopPanAnimation();
    };
  }, [stopPanAnimation]);

  const panToIOTarget = useCallback(
    (target: 'inputs' | 'outputs') => {
      const el = containerRef.current;
      if (!el) return;

      const ioCount = target === 'inputs' ? inputs.length : outputs.length;
      if (ioCount === 0) return;

      const rect = el.getBoundingClientRect();
      const targetCol = target === 'inputs' ? -1 : gridCols;
      const targetRow = ((ioCount - 1) * 1.6) / 2;
      const targetX = rect.width * (target === 'inputs' ? 0.18 : 0.82);
      const targetY = rect.height * 0.5;

      const rawPan = {
        x: targetX - (targetCol + 0.5) * CELL_PX * zoom,
        y: targetY - (targetRow + 0.5) * CELL_PX * zoom,
      };

      animatePanTo(clampPanToBounds(rawPan, zoom), 360);
    },
    [
      animatePanTo,
      clampPanToBounds,
      gridCols,
      inputs.length,
      outputs.length,
      zoom,
    ],
  );

  const canPlaceComponentAt = (
    componentId: string,
    origin: HoleCoord,
    rotation: 0 | 90,
    excludePlacedId?: string,
    excludePlacedIds?: string[],
  ) => {
    const def = catalog[componentId];
    if (!def) return false;

    const size = rotatedSize(def.size, rotation);
    if (origin.row < 0 || origin.col < 0) return false;
    if (origin.row + size.h > gridRows) return false;
    if (origin.col + size.w > gridCols) return false;

    // Build exclusion set from both parameters
    const excludeSet = new Set<string>();
    if (excludePlacedId) excludeSet.add(excludePlacedId);
    if (excludePlacedIds) excludePlacedIds.forEach((id) => excludeSet.add(id));

    // no component overlap
    for (const rect of componentRects) {
      if (excludeSet.has(rect.placedId)) continue;
      for (let r = 0; r < size.h; r++) {
        for (let c = 0; c < size.w; c++) {
          const hole = { row: origin.row + r, col: origin.col + c };
          if (inRect(hole, rect.origin, rect.size)) return false;
        }
      }
    }

    // no port overlap on same hole
    for (const port of def.ports) {
      const rotOff = rotateOffset(port.offset, def.size, rotation);
      const hole = {
        row: origin.row + rotOff.row,
        col: origin.col + rotOff.col,
      };
      const key = `r${hole.row}c${hole.col}`;
      const occ = occupiedPortHoles.get(key);
      if (occ && !excludeSet.has(occ.ownerId)) return false;
    }

    return true;
  };

  const placeComponent = (
    componentId: string,
    origin: HoleCoord,
    rotation: 0 | 90,
  ) => {
    if (!canPlaceComponentAt(componentId, origin, rotation)) {
      notifications.addNotification({
        type: 'warning',
        title: 'Cannot place here',
        message:
          'Holes are occupied, out of bounds, or port holes already used.',
      });
      return;
    }

    const newId = `${componentId}:${Date.now()}`;

    onPlacedChange(
      placed.concat({
        id: newId,
        componentId,
        origin,
        rotation,
      }),
    );

    // Trigger drop sound and ripple effect
    playDrop();
    const ripleId = `ripple:${Date.now()}`;
    const centerX = (origin.col + 1) * CELL_PX * zoom + pan.x;
    const centerY = (origin.row + 1) * CELL_PX * zoom + pan.y;
    setActiveRipples((prev) => [
      ...prev,
      { id: ripleId, x: centerX, y: centerY },
    ]);

    // Remove ripple after animation completes
    window.setTimeout(() => {
      setActiveRipples((prev) => prev.filter((r) => r.id !== ripleId));
    }, 600);
  };

  const placeSelectedComponent = (origin: HoleCoord) => {
    if (selectedComponent.mode !== 'placing') return;
    const { componentId, rotation } = selectedComponent;

    placeComponent(componentId, origin, rotation);

    onSelectedComponentChange({ mode: 'none' });
  };

  const getPortScreenPoint = (port: PortAddress, ioLayout: IOLayout) => {
    if (port.ownerId.startsWith('IO:IN:')) {
      const pt = ioLayout.inputs[port.ownerId] ?? { x: 0, y: 0 };
      return { x: pt.x, y: pt.y + PUZZLE_IO_Y_OFFSET_PX };
    }
    if (port.ownerId.startsWith('IO:OUT:')) {
      const pt = ioLayout.outputs[port.ownerId] ?? { x: 0, y: 0 };
      return { x: pt.x, y: pt.y + PUZZLE_IO_Y_OFFSET_PX };
    }

    const placedInst = placedById[port.ownerId];
    const visualOffsets = visualPortOffsetsByPlacedId.get(port.ownerId);
    const visualOffset = visualOffsets?.get(port.portId);

    if (placedInst && visualOffset) {
      const visualHole = {
        row: placedInst.origin.row + visualOffset.row,
        col: placedInst.origin.col + visualOffset.col,
      };
      const pt = worldToScreen(visualHole);
      return { x: pt.x + (CELL_PX * zoom) / 2, y: pt.y + (CELL_PX * zoom) / 2 };
    }

    if (!port.hole) return { x: 0, y: 0 };
    const pt = worldToScreen(port.hole);
    // center of hole
    return { x: pt.x + (CELL_PX * zoom) / 2, y: pt.y + (CELL_PX * zoom) / 2 };
  };

  const findPortAtHole = (hole: HoleCoord): PortAddress | null => {
    const key = `r${hole.row}c${hole.col}`;
    const occ = occupiedPortHoles.get(key);
    if (!occ) return null;

    const port = allPorts.find(
      (p: PortAddress) => p.ownerId === occ.ownerId && p.portId === occ.portId,
    );
    return port ?? null;
  };

  const finalizeWire = (a: PortAddress, b: PortAddress) => {
    if (a.ownerId === b.ownerId && a.portId === b.portId) return;

    // Allow any connection direction (input->output, output->input, etc)
    // but we normalize to from=output, to=input if possible, or just as dragged.
    // The user prompt says "click or drag from any output port to any input port (or vice versa)".
    // We will enforce that one end must be effectively an output and one an input.

    const kinds = [a.kind, b.kind];
    if (!(kinds.includes('input') && kinds.includes('output'))) {
      notifications.addNotification({
        type: 'warning',
        title: 'Invalid wire',
        message: 'Wires must connect an output to an input.',
      });
      return;
    }

    const from = a.kind === 'output' ? a : b;
    const to = a.kind === 'input' ? a : b;

    const fromPinIndex = (() => {
      if (from.ownerId.startsWith('IO:')) return 0;
      const placedInst = placedById[from.ownerId];
      const def = placedInst ? catalog[placedInst.componentId] : null;
      if (!def) return 0;
      return portIndexByPortId.get(def.id)?.get(from.portId) ?? 0;
    })();

    const toPinIndex = (() => {
      if (to.ownerId.startsWith('IO:')) return 0;
      const placedInst = placedById[to.ownerId];
      const def = placedInst ? catalog[placedInst.componentId] : null;
      if (!def) return 0;
      return portIndexByPortId.get(def.id)?.get(to.portId) ?? 0;
    })();

    if (
      wires.some(
        (w) =>
          w.from.componentId === from.ownerId &&
          w.from.pinIndex === fromPinIndex &&
          w.to.componentId === to.ownerId &&
          w.to.pinIndex === toPinIndex,
      )
    ) {
      return;
    }

    // Check that the input doesn't already have a wire connected to it
    if (
      wires.some(
        (w) =>
          w.to.componentId === to.ownerId &&
          w.to.pinIndex === toPinIndex,
      )
    ) {
      notifications.addNotification({
        type: 'warning',
        title: 'Invalid wire',
        message: 'An input can only have one wire connected to it.',
      });
      return;
    }

    onWiresChange(
      wires.concat({
        id: `wire:${Date.now()}`,
        from: {
          componentId: from.ownerId,
          pinIndex: fromPinIndex,
          portId: from.portId,
        },
        to: {
          componentId: to.ownerId,
          pinIndex: toPinIndex,
          portId: to.portId,
        },
      }),
    );

    const keyA = `${a.ownerId}:${a.portId}`;
    const keyB = `${b.ownerId}:${b.portId}`;
    setFlashingPortKeys([keyA, keyB]);
    window.setTimeout(() => {
      setFlashingPortKeys((current) =>
        current.filter((k) => k !== keyA && k !== keyB),
      );
    }, 220);

    const pointA = getPortScreenPoint(a, ioLayout);
    const pointB = getPortScreenPoint(b, ioLayout);
    emitSparks(pointA.x, pointA.y);
    emitSparks(pointB.x, pointB.y);

    // Trigger wire connection sound
    playWireConnect();
  };

  // IO layout pinned to viewport.
  type IOLayout = {
    inputs: Record<string, { x: number; y: number }>;
    outputs: Record<string, { x: number; y: number }>;
  };

  const ioLayout = useMemo<IOLayout>(() => {
    const inputsPos: Record<string, { x: number; y: number }> = {};
    const outputsPos: Record<string, { x: number; y: number }> = {};

    const toScreenCenter = (row: number, col: number) => {
      return {
        x: pan.x + (col + 0.5) * CELL_PX * zoom,
        y: pan.y + (row + 0.5) * CELL_PX * zoom,
      };
    };

    for (let i = 0; i < inputs.length; i++) {
      const id = `IO:IN:${inputs[i]}`;
      // Keep a stable vertical offset per input so labels do not overlap.
      const row = i * 1.6;
      const anchor = toScreenCenter(row, -1); // just left of col 0
      inputsPos[id] = { x: anchor.x, y: anchor.y };
    }

    for (let i = 0; i < outputs.length; i++) {
      const id = `IO:OUT:${outputs[i]}`;
      // Distribute along the right side (Layout Update: Outputs to Right)
      const row = i * 1.6;
      const anchor = toScreenCenter(row, gridCols); // just right of last col
      outputsPos[id] = { x: anchor.x, y: anchor.y };
    }

    return { inputs: inputsPos, outputs: outputsPos };
  }, [inputs, outputs, pan.x, pan.y, zoom, gridCols]);

  const wheelHandlerRef = useRef<(e: WheelEvent) => void>();
  wheelHandlerRef.current = (e: WheelEvent) => {
    e.preventDefault();
    stopPanAnimation();
    const el = containerRef.current;
    if (!el) return;

    const rect = el.getBoundingClientRect();
    const cursor = { x: e.clientX - rect.left, y: e.clientY - rect.top };
    const before = screenToWorld(cursor);

    const delta = -e.deltaY;
    const factor = delta > 0 ? 1.1 : 0.9;
    const nextZoom = clamp(zoom * factor, minZoom, 4);

    // keep cursor world point stable
    const afterPanX = cursor.x - before.col * CELL_PX * nextZoom;
    const afterPanY = cursor.y - before.row * CELL_PX * nextZoom;

    const clampedPan = clampPanToBounds(
      { x: afterPanX, y: afterPanY },
      nextZoom,
    );

    setZoom(nextZoom);
    setPan(clampedPan);
  };

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const handler = (e: WheelEvent) => wheelHandlerRef.current?.(e);
    el.addEventListener('wheel', handler, { passive: false });
    return () => el.removeEventListener('wheel', handler);
  }, []);

  const onPointerDownBackground = (e: ReactPointerEvent<HTMLDivElement>) => {
    if (e.button !== 0) return;
    stopPanAnimation();
    // If wire is being drafted, ignore background panning.
    if (wireDraft) return;

    setIsPanning(true);
    (e.currentTarget as HTMLDivElement).setPointerCapture(e.pointerId);
    panStartRef.current = {
      x: e.clientX,
      y: e.clientY,
      panX: pan.x,
      panY: pan.y,
    };
    // cancel placing mode if clicking empty background
    if (selectedComponent.mode === 'placing') {
      onSelectedComponentChange({ mode: 'none' });
    }
    setSelectedEntity({ type: 'none' });
  };

  const onPointerMoveBackground = (e: ReactPointerEvent<HTMLDivElement>) => {
    const spotlightEl = containerRef.current;
    if (spotlightEl) {
      const rect = spotlightEl.getBoundingClientRect();
      setCursorSpotlight({
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
        visible: true,
      });
    }

    if (!isPanning) {
      if (wireDraft) {
        const el = containerRef.current;
        if (!el) return;
        const rect = el.getBoundingClientRect();
        setWireDraft(
          (
            prev: {
              start: PortAddress;
              current: { x: number; y: number };
            } | null,
          ) =>
            prev
              ? {
                  ...prev,
                  current: {
                    x: e.clientX - rect.left,
                    y: e.clientY - rect.top,
                  },
                }
              : prev,
        );
      }
      return;
    }

    const start = panStartRef.current;
    if (!start) return;

    const newPanX = start.panX + (e.clientX - start.x);
    const newPanY = start.panY + (e.clientY - start.y);

    setPan(clampPanToBounds({ x: newPanX, y: newPanY }));
  };

  const onPointerUpBackground = (e: ReactPointerEvent<HTMLDivElement>) => {
    if (isPanning) {
      setIsPanning(false);
      panStartRef.current = null;
      return;
    }

    if (wireDraft) {
      if (isOverTrash(e.clientX, e.clientY)) {
        setWireDraft(null);
        return;
      }
      const startPt = getPortScreenPoint(wireDraft.start, ioLayout);
      setWireSnapBack({
        from: startPt,
        current: { x: wireDraft.current.x, y: wireDraft.current.y },
        startedAt: performance.now(),
      });
      // releasing on background cancels wiring
      setWireDraft(null);
    }
  };

  const onClickHole = (hole: HoleCoord) => {
    if (selectedComponent.mode === 'placing') {
      placeSelectedComponent(hole);
      return;
    }

    // click-to-wire: if clicked on a port
    const port = findPortAtHole(hole);
    if (!port) {
      setSelectedEntity({ type: 'none' });
      return;
    }

    if (!wireDraft) {
      const startPt = getPortScreenPoint(port, ioLayout);
      setWireDraft({ start: port, current: startPt });
      return;
    }

    if (
      wireDraft.start.ownerId === port.ownerId &&
      wireDraft.start.portId === port.portId
    ) {
      // Clicked on the same port that started the draft.
      // Cancel wiring (Toggle/Cancel Logic).
      setWireDraft(null);
      return;
    }

    finalizeWire(wireDraft.start, port);
    setWireDraft(null);
  };

  const onStartWireDrag = (port: PortAddress, e: ReactPointerEvent) => {
    e.stopPropagation();

    // Wiring UX: Toggle/Cancel Logic
    // If clicking a pin that is already the source, cancel.
    if (wireDraft) {
      if (
        wireDraft.start.ownerId === port.ownerId &&
        wireDraft.start.portId === port.portId
      ) {
        setWireDraft(null);
      }
      return;
    }

    const el = containerRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    setWireDraft({
      start: port,
      current: { x: e.clientX - rect.left, y: e.clientY - rect.top },
    });
  };

  const removeComponent = (placedId: string) => {
    onPlacedChange(placed.filter((p) => p.id !== placedId));
    onWiresChange(
      wires.filter(
        (w) => w.from.componentId !== placedId && w.to.componentId !== placedId,
      ),
    );
    setSelectedEntity({ type: 'none' });
  };

  useEffect(() => {
    if (!wireSnapBack) return;

    const duration = 150;
    let rafId = 0;

    const tick = () => {
      const elapsed = performance.now() - wireSnapBack.startedAt;
      const t = clamp(elapsed / duration, 0, 1);
      const eased = 1 - (1 - t) * (1 - t);

      setWireSnapBack((current) => {
        if (!current) return current;
        return {
          ...current,
          current: {
            x: current.current.x + (current.from.x - current.current.x) * eased,
            y: current.current.y + (current.from.y - current.current.y) * eased,
          },
        };
      });

      if (t < 1) {
        rafId = window.requestAnimationFrame(tick);
      } else {
        setWireSnapBack(null);
      }
    };

    rafId = window.requestAnimationFrame(tick);
    return () => window.cancelAnimationFrame(rafId);
  }, [wireSnapBack]);

  const emitSparks = (x: number, y: number) => {
    const created = Array.from({ length: 4 }).map((_, index) => {
      const angle = Math.random() * Math.PI * 2;
      const distance = 8 + Math.random() * 12;
      return {
        id: `spark:${Date.now()}:${index}:${Math.random()}`,
        x,
        y,
        dx: Math.cos(angle) * distance,
        dy: Math.sin(angle) * distance,
      };
    });

    const ids = new Set(created.map((spark) => spark.id));
    setMicroSparks((current) => [...current, ...created]);
    window.setTimeout(() => {
      setMicroSparks((current) =>
        current.filter((spark) => !ids.has(spark.id)),
      );
    }, 320);
  };

  const triggerDeleteComponent = (placedId: string) => {
    if (deletingComponentIds.includes(placedId)) return;
    setDeletingComponentIds((current) => [...current, placedId]);
    window.setTimeout(() => {
      removeComponent(placedId);
      setDeletingComponentIds((current) =>
        current.filter((id) => id !== placedId),
      );
    }, 150);
  };

  const removeWire = (wireId: string) => {
    onWiresChange(wires.filter((w) => w.id !== wireId));
    setSelectedEntity({ type: 'none' });
    setHoveredWireSignal((current) =>
      current?.wireId === wireId ? null : current,
    );
  };

  const trashRef = useRef<HTMLButtonElement | null>(null);

  const getDropOriginFromPointer = (
    pointerLocal: { x: number; y: number },
    componentId: string,
    rotation: 0 | 90,
  ) => {
    const def = catalog[componentId];
    if (!def) {
      const world = screenToWorld(pointerLocal);
      return {
        row: clamp(Math.floor(world.row), 0, gridRows - 1),
        col: clamp(Math.floor(world.col), 0, gridCols - 1),
      };
    }

    const size = rotatedSize(def.size, rotation);
    const world = screenToWorld(pointerLocal);

    // Palette drag preview is anchored at its visual center, so we convert
    // pointer position to top-left origin before snapping to grid holes.
    const originRow = Math.round(world.row - size.h / 2);
    const originCol = Math.round(world.col - size.w / 2);

    return {
      row: clamp(originRow, 0, gridRows - size.h),
      col: clamp(originCol, 0, gridCols - size.w),
    };
  };

  const isOverTrash = (clientX: number, clientY: number) => {
    const el = trashRef.current;
    if (!el) return false;
    const r = el.getBoundingClientRect();
    return (
      clientX >= r.left &&
      clientX <= r.right &&
      clientY >= r.top &&
      clientY <= r.bottom
    );
  };

  const selectedWireOverlay = (() => {
    if (selectedEntity.type !== 'wire') return null;
    const w = wires.find((x) => x.id === selectedEntity.wireId);
    if (!w) return null;

    const fromPort = allPorts.find((p: PortAddress) => {
      if (p.ownerId !== w.from.componentId) return false;
      if (p.ownerId.startsWith('IO:')) return true;
      const placedInst = placedById[w.from.componentId];
      const def = placedInst ? catalog[placedInst.componentId] : null;
      if (!def) return false;
      return (
        (portIndexByPortId.get(def.id)?.get(p.portId) ?? -1) === w.from.pinIndex
      );
    });
    const toPort = allPorts.find((p: PortAddress) => {
      if (p.ownerId !== w.to.componentId) return false;
      if (p.ownerId.startsWith('IO:')) return true;
      const placedInst = placedById[w.to.componentId];
      const def = placedInst ? catalog[placedInst.componentId] : null;
      if (!def) return false;
      return (
        (portIndexByPortId.get(def.id)?.get(p.portId) ?? -1) === w.to.pinIndex
      );
    });
    if (!fromPort || !toPort) return null;

    const a = getPortScreenPoint(fromPort, ioLayout);
    const b = getPortScreenPoint(toPort, ioLayout);
    const mid = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
    return (
      <div
        className="absolute z-30"
        style={{ left: mid.x, top: mid.y, transform: 'translate(-50%, -50%)' }}
        onPointerDown={(e) => {
          // Keep selection intact while interacting with the delete button
          e.stopPropagation();
        }}
      >
        <Button
          size="sm"
          variant="outline"
          className="h-7 px-2 transition-all hover:scale-105 hover:border-red-300 hover:bg-red-50 hover:text-red-600 active:scale-95"
          onMouseEnter={() => setHoveredDeleteWireId(w.id)}
          onMouseLeave={() =>
            setHoveredDeleteWireId((current) =>
              current === w.id ? null : current,
            )
          }
          onClick={(e) => {
            e.stopPropagation();
            removeWire(w.id);
          }}
          title="Remove wire"
        >
          X
        </Button>
      </div>
    );
  })();

  const getCurvedWirePath = (
    from: { x: number; y: number },
    to: { x: number; y: number },
  ) => {
    const dx = to.x - from.x;
    const dy = to.y - from.y;
    const controlX = Math.max(28, Math.abs(dx) * 0.38);
    const droopY = Math.max(
      8,
      Math.min(42, Math.abs(dy) * 0.22 + Math.abs(dx) * 0.04),
    );
    const c1x = from.x + controlX;
    const c1y = from.y + droopY;
    const c2x = to.x - controlX;
    const c2y = to.y + droopY;
    return `M ${from.x} ${from.y} C ${c1x} ${c1y}, ${c2x} ${c2y}, ${to.x} ${to.y}`;
  };

  const getOutputBitForPlaced = (placedId: string, pinIndex: number) => {
    const rawValues = String(debuggerGateBits[placedId] ?? '0');
    if (!rawValues.length) return '0';

    // Handle both formats: single char "0", or semicolon-separated "0;1;0"
    let valueArray: string[];
    if (rawValues.includes(';')) {
      valueArray = rawValues.split(';').map((v) => v.trim());
    } else if (rawValues.length === 1) {
      valueArray = [rawValues];
    } else {
      // Multi-char but no semicolon - treat each character as separate value
      valueArray = rawValues.split('');
    }

    if (valueArray.length === 1) return valueArray[0];

    const placedInst = placedById[placedId];
    const def = placedInst ? catalog[placedInst.componentId] : null;
    if (def) {
      const outputPortIndices = def.ports
        .map((port, idx) => ({ port, idx }))
        .filter((entry) => entry.port.kind === 'output')
        .map((entry) => entry.idx);
      const outputPosition = outputPortIndices.indexOf(pinIndex);
      if (outputPosition >= 0 && outputPosition < valueArray.length) {
        return valueArray[outputPosition];
      }
    }

    // Fallback: try direct pinIndex access with bounds checking
    return (
      valueArray[
        Math.min(
          Math.max(
            pinIndex -
              (def?.ports?.filter((p) => p.kind === 'input').length ?? 0),
            0,
          ),
          valueArray.length - 1,
        )
      ] ??
      valueArray[0] ??
      '0'
    );
  };

  const getPortBitForDisplay = (
    placedId: string,
    portKind: PortKind,
    portIndex: number,
  ) => {
    if (portKind === 'output') {
      return getOutputBitForPlaced(placedId, portIndex);
    }

    const incomingWire = wires.find(
      (w) => w.to.componentId === placedId && w.to.pinIndex === portIndex,
    );
    if (!incomingWire) return '0';

    if (incomingWire.from.componentId.startsWith('IO:IN:')) {
      const inputName = incomingWire.from.componentId.replace('IO:IN:', '');
      return debuggerInputBits[inputName] ?? '0';
    }

    return getOutputBitForPlaced(
      incomingWire.from.componentId,
      incomingWire.from.pinIndex,
    );
  };

  // Calculate highlighted wire IDs based on selected component or passed prop
  // Note: Wire highlighting is disabled for puzzle INPUT nodes
  const computedHighlightedWireIds = useMemo(() => {
    const highlighted = new Set<string>();

    if (selectedEntity.type === 'component') {
      const selectedIds = new Set(selectedEntity.placedIds);

      // Disable highlighting if any selected component is a puzzle INPUT node
      const hasInputNode = Array.from(selectedIds).some((id) =>
        id.startsWith('IO:IN:'),
      );
      if (hasInputNode) {
        return highlighted; // Return empty set for INPUT nodes
      }

      // For selected components: highlight all wires directly connected
      for (const wire of wires) {
        if (
          selectedIds.has(wire.from.componentId) ||
          selectedIds.has(wire.to.componentId)
        ) {
          highlighted.add(wire.id);
        }
      }
    } else if (selectedEntity.type === 'wire') {
      // For selected wires: just highlight that wire (already handled in wire rendering)
      highlighted.add(selectedEntity.wireId);
    }

    return highlighted;
  }, [selectedEntity, wires]);

  // Use the passed highlightedWireIds prop if provided (for cross-highlighting from debugger),
  // otherwise use the computed highlighting based on selected component
  const resolvedHighlightedWireIds = useMemo(() => {
    if (highlightedWireIds && highlightedWireIds.length > 0) {
      return new Set(highlightedWireIds);
    }
    return computedHighlightedWireIds;
  }, [highlightedWireIds, computedHighlightedWireIds]);

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2">
      <div className="rounded-md border border-border bg-card p-3">
        <div className="flex items-center justify-between gap-2">
          <div className="text-sm font-medium text-foreground">
            Working Area
          </div>
          <div className="flex items-center gap-2">
            {onEnterInlineDebugger || onExitInlineDebugger ? (
              !debuggerActive ? (
                <Button
                  ref={debuggerButtonRef}
                  size="sm"
                  variant="outline"
                  className="relative overflow-hidden"
                  onClick={onEnterInlineDebugger}
                >
                  <ZigzagBugCanvas containerRef={debuggerButtonRef} />
                  Debugger
                </Button>
              ) : (
                <>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={onDebuggerStepPrev}
                  >
                    ◄ Previous Step
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={onDebuggerStepNext}
                  >
                    Next Step ►
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={onOpenFullDebuggerReport}
                  >
                    Full Debugger Report
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={onExitInlineDebugger}
                  >
                    Exit Debugger
                  </Button>
                </>
              )
            ) : null}
            <button
              type="button"
              className="-mr-1 inline-flex items-center justify-center rounded p-1 text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
              onClick={() => setIsWorkingAreaCollapsed((prev) => !prev)}
              aria-expanded={!isWorkingAreaCollapsed}
              aria-label={
                isWorkingAreaCollapsed
                  ? 'Expand Working Area info'
                  : 'Collapse Working Area info'
              }
              title={isWorkingAreaCollapsed ? 'Expand' : 'Collapse'}
            >
              <ChevronRight
                className={cn(
                  'size-4 transition-transform duration-200',
                  !isWorkingAreaCollapsed && 'rotate-90',
                )}
              />
            </button>
          </div>
        </div>
        {!isWorkingAreaCollapsed ? (
          <div className="mt-1 space-y-0.5 text-xs text-muted-foreground">
            <p>
              {gridRows} x {gridCols} grid.
            </p>
            <p>Scroll to zoom. Drag the background to pan.</p>
            <p>Click or drag ports to create wires.</p>
            <p>
              Use Shift+Click to select multiple components. Use Ctrl+C / Ctrl+V
              to copy and paste.
            </p>
          </div>
        ) : null}
      </div>

      <div
        ref={containerRef}
        className={cn(
          'relative h-[calc(100vh-18rem)] overflow-hidden rounded-md border border-border bg-card transition-[box-shadow,transform,border-color] duration-300 cursor-crosshair',
          isPowerSurge && 'workstation-board-surge',
          boardFeedback === 'success' &&
            'workstation-board-success border-emerald-400',
          boardFeedback === 'failure' &&
            'workstation-board-failure border-red-400',
          viewportClassName,
        )}
        onPointerDown={onPointerDownBackground}
        onPointerMove={onPointerMoveBackground}
        onPointerUp={onPointerUpBackground}
        onPointerEnter={(e) => {
          const rect = e.currentTarget.getBoundingClientRect();
          setCursorSpotlight({
            x: e.clientX - rect.left,
            y: e.clientY - rect.top,
            visible: true,
          });
        }}
        onPointerLeave={() => {
          setCursorSpotlight((prev) => ({ ...prev, visible: false }));
          setHoveredWireSignal(null);
        }}
        onDragOver={(e) => {
          e.preventDefault();
          if (!draggedPaletteComponentId) return;

          const el = containerRef.current;
          if (!el) return;
          const rect = el.getBoundingClientRect();
          const local = { x: e.clientX - rect.left, y: e.clientY - rect.top };
          const rotation =
            selectedComponent.mode === 'placing' &&
            selectedComponent.componentId === draggedPaletteComponentId
              ? selectedComponent.rotation
              : 0;
          const origin = getDropOriginFromPointer(
            local,
            draggedPaletteComponentId,
            rotation,
          );
          setDropPreview(origin);
        }}
        onDragLeave={() => setDropPreview(null)}
        onDrop={(e) => {
          e.preventDefault();
          setDropPreview(null);
          const componentId = parseDraggedComponentId(
            e,
            draggedPaletteComponentId,
          );
          if (!componentId) return;
          const el = containerRef.current;
          if (!el) return;
          const rect = el.getBoundingClientRect();
          const local = { x: e.clientX - rect.left, y: e.clientY - rect.top };

          const rotation =
            selectedComponent.mode === 'placing' &&
            selectedComponent.componentId === componentId
              ? selectedComponent.rotation
              : 0;

          const origin = getDropOriginFromPointer(local, componentId, rotation);

          placeComponent(componentId, origin, rotation);
          onSelectedComponentChange({ mode: 'none' });
        }}
      >
        {isChecking && (
          <div className="pointer-events-none absolute inset-0 z-40 flex items-center justify-center bg-white/45 backdrop-blur-[2px]">
            <div className="flex items-center gap-3 rounded-2xl border border-border bg-card/80 px-4 py-3 text-sm font-medium text-foreground shadow-xl shadow-blue-500/10">
              <Spinner size="md" className="text-blue-500" />
              <span>Running the circuit...</span>
            </div>
          </div>
        )}

        {showSolvedSlam && (
          <div className="pointer-events-none absolute inset-0 z-50 flex items-center justify-center">
            <div className="workstation-solved-slam rounded-xl border border-emerald-300/70 bg-white/90 px-6 py-3 text-4xl font-extrabold tracking-[0.12em] text-emerald-600 shadow-2xl shadow-emerald-500/30 duration-300 animate-in fade-in zoom-in-50">
              SOLVED!
            </div>
          </div>
        )}

        {/* Ripple Effects */}
        {visualEffectsEnabled &&
          activeRipples.map((ripple) => (
            <RippleEffect key={ripple.id} x={ripple.x} y={ripple.y} />
          ))}

        {/* Interactive Spotlight */}
        <div
          className={cn(
            'pointer-events-none absolute inset-0 z-[5] transition-opacity duration-150',
            cursorSpotlight.visible ? 'opacity-100' : 'opacity-0',
          )}
          style={{
            background: `radial-gradient(600px circle at ${cursorSpotlight.x}px ${cursorSpotlight.y}px, rgba(255,255,255,0.05), transparent 40%)`,
          }}
        />

        {isPowerSurge ? (
          <div className="pointer-events-none absolute inset-0 z-[6] bg-slate-950/25" />
        ) : null}

        {/* Copy, Paste, Trash - Top Flush, Centered Horizontally */}
        <div
          className="absolute left-1/2 top-3 z-30 flex -translate-x-1/2 flex-col items-center gap-3"
          onPointerDown={(e) => e.stopPropagation()}
        >
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              className="h-8 px-2"
              onClick={(e) => {
                e.stopPropagation();
                copySelectionToClipboard();
              }}
              disabled={!canCopySelection}
              title="Copy selected components (Ctrl+C)"
            >
              Copy
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="h-8 px-2"
              onClick={(e) => {
                e.stopPropagation();
                pasteFromClipboard();
              }}
              disabled={!canPasteSelection}
              title="Paste copied components (Ctrl+V)"
            >
              Paste
            </Button>
            <button
              type="button"
              ref={trashRef}
              className="flex size-8 items-center justify-center rounded border border-border bg-secondary text-muted-foreground hover:bg-red-50 hover:text-red-600"
              title={
                wireDraft
                  ? 'Cancel wiring'
                  : selectedEntity.type !== 'none'
                    ? 'Delete selected'
                    : 'Clear Grid'
              }
              onPointerDown={(e) => e.stopPropagation()}
              onClick={(e) => {
                e.stopPropagation();
                if (wireDraft) {
                  setWireDraft(null);
                  return;
                }
                if (selectedEntity.type === 'component') {
                  // Delete all selected components
                  for (const placedId of selectedEntity.placedIds) {
                    removeComponent(placedId);
                  }
                  setSelectedEntity({ type: 'none' });
                  return;
                }
                if (selectedEntity.type === 'wire') {
                  removeWire(selectedEntity.wireId);
                  return;
                }
                // Clear all
                if (
                  confirm('Are you sure you want to clear the entire grid?')
                ) {
                  onWiresChange([]);
                  onPlacedChange([]);
                }
              }}
              aria-label={
                wireDraft
                  ? 'Cancel wiring'
                  : selectedEntity.type !== 'none'
                    ? 'Delete selected'
                    : 'Clear Grid'
              }
            >
              {/* simple inline icon */}
              <svg
                viewBox="0 0 24 24"
                className="size-5"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M3 6h18" />
                <path d="M8 6V4h8v2" />
                <path d="M6 6l1 16h10l1-16" />
              </svg>
            </button>
            <Button
              size="sm"
              variant="outline"
              className="size-8 p-0"
              onClick={(e) => {
                e.stopPropagation();
                setZoom((z) => Math.min(z * 1.15, 3));
              }}
              title="Zoom in (Scroll up)"
            >
              <ZoomIn className="size-4" />
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="size-8 p-0"
              onClick={(e) => {
                e.stopPropagation();
                setZoom((z) => Math.max(z / 1.15, minZoom));
              }}
              title="Zoom out (Scroll down)"
            >
              <ZoomOut className="size-4" />
            </Button>
          </div>
        </div>

        {selectedWireOverlay}

        {/* Wires (SVG overlay) */}
        <svg
          className="pointer-events-none absolute inset-0 z-10"
          width="100%"
          height="100%"
        >
          {wires.map((w) => {
            const fromPort = allPorts.find((p: PortAddress) => {
              if (p.ownerId !== w.from.componentId) return false;
              if (p.ownerId.startsWith('IO:')) return true;
              const placedInst = placedById[w.from.componentId];
              const def = placedInst ? catalog[placedInst.componentId] : null;
              if (!def) return false;
              return (
                (portIndexByPortId.get(def.id)?.get(p.portId) ?? -1) ===
                w.from.pinIndex
              );
            });
            const toPort = allPorts.find((p: PortAddress) => {
              if (p.ownerId !== w.to.componentId) return false;
              if (p.ownerId.startsWith('IO:')) return true;
              const placedInst = placedById[w.to.componentId];
              const def = placedInst ? catalog[placedInst.componentId] : null;
              if (!def) return false;
              return (
                (portIndexByPortId.get(def.id)?.get(p.portId) ?? -1) ===
                w.to.pinIndex
              );
            });
            if (!fromPort || !toPort) return null;

            const a = getPortScreenPoint(fromPort, ioLayout);
            const b = getPortScreenPoint(toPort, ioLayout);
            const isSelected =
              selectedEntity.type === 'wire' && selectedEntity.wireId === w.id;
            const isRecentlyConnected = recentlyConnectedWireId === w.id;
            const isHighSignal = activeWireIdsSet.has(w.id);
            const isDeleteWarn = hoveredDeleteWireId === w.id;
            const isHighlighted = resolvedHighlightedWireIds.has(w.id);
            const wirePath = getCurvedWirePath(a, b);
            const isSurgePowered =
              isPowerSurge && (activeWireIdsSet.size === 0 || isHighSignal);

            // Visual Feature: Dynamic Wire Coloring with Highlight Support
            const strokeColor = isSelected
              ? '#2563eb'
              : isDeleteWarn
                ? '#ef4444'
                : isHighlighted
                  ? '#3b82f6' // Bright blue for highlighted wires
                  : isHighSignal
                    ? '#fde047'
                    : isRecentlyConnected
                      ? '#60a5fa'
                      : getWireColor(w.id);

            const flowColor = isHighlighted
              ? '#60a5fa' // Flow color for highlighted wires
              : isHighSignal
                ? '#fef08a'
                : isRecentlyConnected
                  ? '#bfdbfe'
                  : '#93c5fd';

            // Check if wire is locked (at least one endpoint is locked)
            const isWireLocked = w.isLocked === true;

            return (
              <g key={w.id}>
                <path
                  className={cn(
                    'pointer-events-auto cursor-pointer transition-all duration-200',
                    isRecentlyConnected && 'animate-pulse',
                    isRecentlyConnected && 'workstation-wire-snap',
                  )}
                  d={wirePath}
                  fill="none"
                  stroke={strokeColor}
                  strokeWidth={
                    isPowerSurge
                      ? 5.5
                      : isSelected
                        ? 4
                        : isHighlighted
                          ? 5
                          : isRecentlyConnected
                            ? 5
                            : 2
                  }
                  strokeDasharray={isWireLocked ? '6,3' : undefined}
                  style={{
                    filter: isDeleteWarn
                      ? 'drop-shadow(0 0 8px rgba(239,68,68,0.85))'
                      : isHighlighted
                        ? 'drop-shadow(0 0 8px rgba(59,130,246,0.8))'
                        : isSurgePowered
                          ? 'drop-shadow(0 0 14px rgba(34,211,238,0.95))'
                          : isHighSignal
                            ? 'drop-shadow(0 0 8px rgba(250,204,21,0.9))'
                            : isRecentlyConnected
                              ? 'drop-shadow(0 0 6px rgba(96,165,250,0.95))'
                              : 'drop-shadow(0 0 3px rgba(59,130,246,0.2))',
                  }}
                  onPointerDown={(e) => {
                    e.stopPropagation();
                    setSelectedEntity({ type: 'wire', wireId: w.id });
                  }}
                  onPointerMove={(e) => {
                    const el = containerRef.current;
                    if (!el) return;
                    const rect = el.getBoundingClientRect();
                    setHoveredWireSignal({
                      wireId: w.id,
                      x: e.clientX - rect.left,
                      y: e.clientY - rect.top,
                      high: isHighSignal,
                    });
                  }}
                  onPointerLeave={() => {
                    setHoveredWireSignal((current) =>
                      current?.wireId === w.id ? null : current,
                    );
                  }}
                  onPointerUp={(e) => {
                    e.stopPropagation();
                    if (isOverTrash(e.clientX, e.clientY)) removeWire(w.id);
                  }}
                />
                <path
                  d={wirePath}
                  fill="none"
                  stroke={flowColor}
                  strokeWidth={
                    isPowerSurge
                      ? 4.2
                      : isHighlighted
                        ? 4
                        : isHighSignal
                          ? 3
                          : 2
                  }
                  strokeDasharray={
                    isHighlighted ? '5 5' : isHighSignal ? '9 7' : '7 9'
                  }
                  className={cn(
                    'pointer-events-none workstation-wire-flow transition-all duration-200',
                    (isHighSignal || isPowerSurge || isHighlighted) &&
                      'workstation-wire-flow-fast',
                  )}
                  style={{
                    opacity: isPowerSurge
                      ? 1
                      : isHighlighted
                        ? 0.85
                        : isHighSignal
                          ? 0.95
                          : 0.45,
                    filter: isPowerSurge
                      ? 'drop-shadow(0 0 14px rgba(34,211,238,0.95))'
                      : isHighlighted
                        ? 'drop-shadow(0 0 6px rgba(59,130,246,0.7))'
                        : isHighSignal
                          ? 'drop-shadow(0 0 8px rgba(250,204,21,0.8))'
                          : 'drop-shadow(0 0 4px rgba(96,165,250,0.45))',
                  }}
                />
              </g>
            );
          })}

          {wireDraft ? (
            <>
              <path
                d={getCurvedWirePath(
                  getPortScreenPoint(wireDraft.start, ioLayout),
                  wireDraft.current,
                )}
                fill="none"
                stroke="#2563eb"
                strokeWidth={2}
                strokeDasharray="4 3"
              />
              <path
                d={getCurvedWirePath(
                  getPortScreenPoint(wireDraft.start, ioLayout),
                  wireDraft.current,
                )}
                fill="none"
                stroke="#bfdbfe"
                strokeWidth={2}
                strokeDasharray="8 6"
                className="workstation-wire-flow-fast"
                style={{ filter: 'drop-shadow(0 0 6px rgba(96,165,250,0.7))' }}
              />
            </>
          ) : null}

          {wireSnapBack ? (
            <>
              <path
                d={getCurvedWirePath(wireSnapBack.from, wireSnapBack.current)}
                fill="none"
                stroke="#2563eb"
                strokeWidth={2}
                strokeDasharray="4 3"
                className="workstation-wire-snapback"
              />
              <path
                d={getCurvedWirePath(wireSnapBack.from, wireSnapBack.current)}
                fill="none"
                stroke="#bfdbfe"
                strokeWidth={2}
                strokeDasharray="8 6"
                className="workstation-wire-flow-fast workstation-wire-snapback"
                style={{ filter: 'drop-shadow(0 0 6px rgba(96,165,250,0.7))' }}
              />
            </>
          ) : null}
        </svg>

        {microSparks.map((spark) => (
          <div
            key={spark.id}
            className="workstation-micro-spark pointer-events-none absolute z-30 size-1 rounded-full bg-yellow-400"
            style={{
              left: spark.x,
              top: spark.y,
              ...({
                '--spark-dx': `${spark.dx}px`,
                '--spark-dy': `${spark.dy}px`,
              } as any),
            }}
          />
        ))}

        {/* Grid content (transformed) */}
        <div
          className="absolute inset-0 z-0"
          style={{
            transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
            transformOrigin: '0 0',
          }}
        >
          {/* Visible holes */}
          {Array.from({ length: visible.r1 - visible.r0 + 1 }).flatMap(
            (_, ri) => {
              const r = visible.r0 + ri;
              return Array.from({ length: visible.c1 - visible.c0 + 1 }).map(
                (__, ci) => {
                  const c = visible.c0 + ci;
                  const key = `r${r}c${c}`;
                  const occ = occupiedHoles.get(key);
                  const portOcc = occupiedPortHoles.get(key);
                  const showPortOcc =
                    Boolean(portOcc) && !staleLogicalPortHoleKeys.has(key);

                  const left = c * CELL_PX;
                  const top = r * CELL_PX;

                  // Canvas Rendering: Grid & Labels (Grid Dots)
                  // Use small dots instead of full-size buttons for cleaner look
                  return (
                    <div
                      key={key}
                      className="absolute flex items-center justify-center p-0"
                      style={{
                        left,
                        top,
                        width: CELL_PX,
                        height: CELL_PX,
                      }}
                    >
                      <button
                        className={cn(
                          'rounded-full transition-colors',
                          showPortOcc
                            ? 'size-3 bg-blue-400'
                            : occ
                              ? 'size-3 bg-muted-foreground/50'
                              : (emptyHoleClassName ??
                                'size-1 bg-muted-foreground/30 hover:bg-muted-foreground/50'),
                        )}
                        onPointerDown={(e) => {
                          e.stopPropagation();
                        }}
                        onClick={(e) => {
                          e.stopPropagation();
                          onClickHole({ row: r, col: c });
                        }}
                        title={`(${r},${c})`}
                      />
                    </div>
                  );
                },
              );
            },
          )}

          {/* Components */}
          {placed.map((p, placedIndex) => {
            const def = catalog[p.componentId];

            // Safety check: skip rendering if component definition is missing from catalog
            if (!def) {
              console.warn(
                `Component definition missing for ID: ${p.componentId}`,
              );
              return null;
            }

            const size = rotatedSize(def.size, p.rotation);

            const isDragging =
              draggedComponent && draggedComponent.placedIds.includes(p.id);
            const origin = isDragging
              ? {
                  row: p.origin.row + draggedComponent.deltaRow,
                  col: p.origin.col + draggedComponent.deltaCol,
                }
              : p.origin;

            const left = origin.col * CELL_PX;
            const top = origin.row * CELL_PX;

            const isSelected =
              selectedEntity.type === 'component' &&
              selectedEntity.placedIds.includes(p.id);
            const isActive = activeComponentIdsSet.has(p.id);
            const isDeleteWarn = hoveredDeleteComponentId === p.id;
            const isDeleting = deletingComponentIds.includes(p.id);

            // Calculate the count of this component type that appear before this one
            const countBefore = placed
              .slice(0, placedIndex)
              .filter((comp) => comp.componentId === p.componentId).length;
            const componentNumber = countBefore + 1;
            const totalCount = placed.filter(
              (comp) => comp.componentId === p.componentId,
            ).length;
            // Only add number if there are multiple gates of this type
            const defWithNumber = {
              ...def,
              label:
                totalCount > 1 ? `${def.label} ${componentNumber}` : def.label,
            };
            const visualPortOffsets = visualPortOffsetsByPlacedId.get(p.id);

            return (
              <LogicNode
                key={p.id}
                node={{
                  ...defWithNumber,
                  ports: def.ports.map((port) => ({
                    ...port,
                    offset: visualPortOffsets?.get(port.id) ?? port.offset,
                  })),
                }}
                className={cn(
                  'absolute transition-[box-shadow,transform,border-color] duration-300',
                  bootSequenceActive && 'animate-in fade-in zoom-in-75',
                  isDeleting && 'workstation-component-delete-out',
                  !isDragging && !isDeleting && 'workstation-component-breathe',
                  isDeleteWarn &&
                    'border-red-400 bg-red-50/60 shadow-[0_0_0_1px_rgba(248,113,113,0.45),0_0_18px_rgba(239,68,68,0.25)]',
                  isActive &&
                    'border-cyan-300 drop-shadow-[0_0_8px_rgba(59,130,246,0.8)] shadow-[0_0_0_1px_rgba(34,211,238,0.45),0_0_12px_rgba(59,130,246,0.4),0_0_24px_rgba(34,211,238,0.32)]',
                  isPowerSurge && 'workstation-component-surge',
                  isSelected
                    ? 'border-blue-400 shadow-[0_0_0_1px_rgba(96,165,250,0.55),0_0_18px_rgba(59,130,246,0.28)]'
                    : 'border-border',
                  recentlyPlacedId === p.id && 'workstation-component-pop',
                  isDragging ? 'z-50 opacity-80 shadow-xl' : 'z-10',
                )}
                style={{
                  left,
                  top,
                  width: size.w * CELL_PX - 2,
                  height: size.h * CELL_PX - 2,
                  cursor: isDragging ? 'grabbing' : 'grab',
                  animationDelay: `${Math.min(placedIndex, 12) * 100}ms`,
                  animationFillMode: 'both',
                }}
                onPointerDown={(e) => {
                  e.stopPropagation();
                  e.currentTarget.setPointerCapture(e.pointerId);

                  // Multi-select: Shift+Click toggles component in selection, otherwise single select
                  if (e.shiftKey) {
                    setSelectedEntity((current) => {
                      if (current.type !== 'component') {
                        return { type: 'component', placedIds: [p.id] };
                      }
                      const ids = [...current.placedIds];
                      const idx = ids.indexOf(p.id);
                      if (idx >= 0) {
                        ids.splice(idx, 1); // Remove if present
                      } else {
                        ids.push(p.id); // Add if missing
                      }
                      return {
                        type: 'component',
                        placedIds: ids.length > 0 ? ids : [p.id],
                      };
                    });
                  } else {
                    setSelectedEntity({ type: 'component', placedIds: [p.id] });
                  }

                  // Prevent drag if component is locked (but allow in edit mode)
                  if (p.isLocked && !isEditMode) {
                    return;
                  }

                  const el = containerRef.current;
                  if (!el) return;
                  // Group dragging: if clicked component is in selection, drag all selected
                  const placedIdsToMove =
                    selectedEntity.type === 'component' &&
                    selectedEntity.placedIds.includes(p.id)
                      ? selectedEntity.placedIds
                      : [p.id];

                  setDraggedComponent({
                    placedIds: placedIdsToMove,
                    startMouseHole: p.origin,
                    currentMouseHole: p.origin,
                    deltaRow: 0,
                    deltaCol: 0,
                  });
                }}
                onPointerMove={(e) => {
                  if (
                    !draggedComponent ||
                    !draggedComponent.placedIds.includes(p.id)
                  )
                    return;

                  e.stopPropagation();
                  const el = containerRef.current;
                  if (!el) return;
                  const rect = el.getBoundingClientRect();
                  const cursor = {
                    x: e.clientX - rect.left,
                    y: e.clientY - rect.top,
                  };
                  const worldPos = screenToWorld(cursor);

                  const newDeltaCol = Math.round(
                    worldPos.col - draggedComponent.startMouseHole.col,
                  );
                  const newDeltaRow = Math.round(
                    worldPos.row - draggedComponent.startMouseHole.row,
                  );

                  if (
                    newDeltaCol !== draggedComponent.deltaCol ||
                    newDeltaRow !== draggedComponent.deltaRow
                  ) {
                    setDraggedComponent({
                      ...draggedComponent,
                      deltaRow: newDeltaRow,
                      deltaCol: newDeltaCol,
                    });
                  }
                }}
                onPointerUp={(e) => {
                  e.stopPropagation();
                  e.currentTarget.releasePointerCapture(e.pointerId);

                  if (
                    !draggedComponent ||
                    !draggedComponent.placedIds.includes(p.id)
                  )
                    return;

                  if (isOverTrash(e.clientX, e.clientY)) {
                    // Delete all dragged components
                    for (const placedId of draggedComponent.placedIds) {
                      removeComponent(placedId);
                    }
                  } else {
                    // Commit all moves: validate each component, then update all
                    const allValid = draggedComponent.placedIds.every(
                      (placedId) => {
                        const comp = placed.find((c) => c.id === placedId);
                        if (!comp) return false;
                        const newOrigin = {
                          row: clamp(
                            comp.origin.row + draggedComponent.deltaRow,
                            0,
                            gridRows - 1,
                          ),
                          col: clamp(
                            comp.origin.col + draggedComponent.deltaCol,
                            0,
                            gridCols - 1,
                          ),
                        };
                        return canPlaceComponentAt(
                          comp.componentId,
                          newOrigin,
                          comp.rotation,
                          undefined,
                          draggedComponent.placedIds, // exclude all dragged components from collision
                        );
                      },
                    );

                    if (allValid) {
                      const next = placed.map((comp) => {
                        if (draggedComponent.placedIds.includes(comp.id)) {
                          return {
                            ...comp,
                            origin: {
                              row: clamp(
                                comp.origin.row + draggedComponent.deltaRow,
                                0,
                                gridRows - 1,
                              ),
                              col: clamp(
                                comp.origin.col + draggedComponent.deltaCol,
                                0,
                                gridCols - 1,
                              ),
                            },
                          };
                        }
                        return comp;
                      });
                      onPlacedChange(next);
                    }
                  }
                  setDraggedComponent(null);
                }}
              >
                {/* Selected Action Buttons: Delete (Outside) */}
                {isSelected && !isDragging && (
                  <div className="absolute -top-8 left-1/2 z-50 flex -translate-x-1/2 items-center gap-1">
                    {/* Delete Button */}
                    {(!p.isLocked || isEditMode) && (
                      <button
                        type="button"
                        className="flex size-5 items-center justify-center rounded-full bg-card text-red-600 shadow-sm ring-1 ring-border transition-all hover:scale-110 hover:bg-red-100 hover:text-red-700 hover:ring-red-300"
                        onMouseEnter={() => setHoveredDeleteComponentId(p.id)}
                        onMouseLeave={() =>
                          setHoveredDeleteComponentId((current) =>
                            current === p.id ? null : current,
                          )
                        }
                        onPointerDown={(e) => e.stopPropagation()}
                        onClick={(e) => {
                          e.stopPropagation();
                          triggerDeleteComponent(p.id);
                        }}
                        title={
                          p.isLocked && isEditMode
                            ? 'Delete locked component'
                            : 'Delete component'
                        }
                      >
                        <svg
                          viewBox="0 0 24 24"
                          className="size-3"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                        >
                          <path d="M3 6h18" />
                          <path d="M8 6V4h8v2" />
                          <path d="M6 6l1 16h10l1-16" />
                        </svg>
                      </button>
                    )}
                    {/* Component Name Label */}
                    <span className="ml-1 whitespace-nowrap rounded bg-card/90 px-2 py-1 text-xs font-medium text-foreground shadow-sm ring-1 ring-border">
                      {def.label}
                    </span>
                  </div>
                )}

                {/* Lock indicator for locked components */}
                {p.isLocked && (
                  <div
                    className="lock-indicator absolute -top-3 left-1/2 z-40 flex -translate-x-1/2 -translate-y-1/2 items-center justify-center"
                    style={{
                      width: '24px',
                      height: '24px',
                      backgroundColor: '#fbbf24',
                      borderRadius: '50%',
                      border: '2px solid #f59e0b',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                    title="This component is locked and cannot be moved or deleted"
                  >
                    <Lock className="size-3 text-amber-950" aria-hidden />
                  </div>
                )}

                {/* Port markers */}
                {def.ports.map((port, portIndex) => {
                  const rot = rotateOffset(port.offset, def.size, p.rotation);
                  const visualOffset = visualPortOffsets?.get(port.id) ?? rot;
                  const pl = visualOffset.col * CELL_PX;
                  const pt = visualOffset.row * CELL_PX;

                  const effective: PortAddress = {
                    ownerId: p.id,
                    portId: port.id,
                    kind: port.kind,
                    hole: {
                      row: origin.row + rot.row,
                      col: origin.col + rot.col,
                    },
                  };
                  const effectiveKey = `${effective.ownerId}:${effective.portId}`;
                  const isPortFlashing =
                    flashingPortKeys.includes(effectiveKey);
                  const portBit = debuggerActive
                    ? getPortBitForDisplay(p.id, port.kind, portIndex)
                    : '0';

                  return (
                    <div key={port.id}>
                      {debuggerActive ? (
                        <div
                          className="pointer-events-none absolute z-30 flex size-3 items-center justify-center rounded border border-border bg-card text-[8px] font-bold leading-none text-foreground"
                          style={{
                            left: pl + (CELL_PX - 8) / 2 - 6,
                            top: pt + (CELL_PX - 8) / 2 - 9,
                          }}
                        >
                          {portBit}
                        </div>
                      ) : null}
                      <button
                        type="button"
                        className={cn(
                          'absolute flex items-center justify-center rounded-full border transition-transform duration-200 hover:scale-150 hover:bg-blue-400 cursor-pointer',
                          wireDraft &&
                            'scale-125 shadow-[0_0_10px_rgba(59,130,246,0.45)]',
                          isPortFlashing && 'workstation-port-lock-flash',
                          port.kind === 'input'
                            ? 'border-green-300 bg-green-50'
                            : 'border-purple-300 bg-purple-50',
                        )}
                        style={{
                          left: pl + (CELL_PX - 8) / 2,
                          top: pt + (CELL_PX - 8) / 2,
                          width: 8,
                          height: 8,
                        }}
                        onPointerDown={(e) => onStartWireDrag(effective, e)}
                        onPointerUp={(e) => {
                          e.stopPropagation();
                          if (wireDraft) {
                            if (
                              wireDraft.start.ownerId === effective.ownerId &&
                              wireDraft.start.portId === effective.portId
                            ) {
                              return;
                            }
                            finalizeWire(wireDraft.start, effective);
                            setWireDraft(null);
                          }
                        }}
                        onClick={(e) => {
                          e.stopPropagation();
                        }}
                        title={`${port.kind} ${port.id}`}
                        aria-label={`${port.kind} ${port.id}`}
                      />
                    </div>
                  );
                })}
              </LogicNode>
            );
          })}

          {/* Drop Preview / Ghost Node */}
          {dropPreview &&
            draggedPaletteComponentId &&
            (() => {
              const def = catalog[draggedPaletteComponentId];
              if (!def) return null;
              const rotation =
                selectedComponent.mode === 'placing' &&
                selectedComponent.componentId === draggedPaletteComponentId
                  ? selectedComponent.rotation
                  : 0;
              const size = rotatedSize(def.size, rotation);
              const previewVisualPortOffsets = getVisualPortOffsets(
                def,
                rotation,
              );
              return (
                <LogicNode
                  node={{
                    ...def,
                    ports: def.ports.map((port) => ({
                      ...port,
                      offset:
                        previewVisualPortOffsets.get(port.id) ?? port.offset,
                    })),
                  }}
                  className="pointer-events-none absolute z-40 opacity-50 ring-2 ring-blue-500"
                  style={{
                    left: dropPreview.col * 18,
                    top: dropPreview.row * 18,
                    width: size.w * 18 - 2,
                    height: size.h * 18 - 2,
                  }}
                />
              );
            })()}
        </div>

        {/* Floating IO */}
        <div className="pointer-events-none absolute inset-0 z-20">
          {inputs.map((label, inputIndex) => {
            const id = `IO:IN:${label}`;
            const pt = ioLayout.inputs[id];
            if (!pt) return null;
            const inputBit = debuggerInputBits[label] ?? '0';
            const sequenceValue = debuggerSequences[label] ?? '';
            const sequenceBits = sequenceValue.split('');
            return (
              <div key={id}>
                {debuggerActive ? (
                  <div
                    className="pointer-events-auto absolute z-30 flex items-center gap-1 debugger-sequence-inputs"
                    style={{
                      left: pt.x,
                      top: pt.y,
                      transform: `translate(-102%, -165%) scale(${zoom})`,
                      transformOrigin: 'right bottom',
                    }}
                  >
                    <div
                      className="flex size-4 items-center justify-center rounded border border-green-400 bg-white text-[9px] font-bold text-green-700"
                      title={`Current bit at step ${debuggerStepIndex + 1}`}
                    >
                      {inputBit}
                    </div>
                    <input
                      type="text"
                      value={sequenceValue}
                      onChange={(e) =>
                        onDebuggerSequenceChange?.(
                          label,
                          e.target.value.replace(/[^01]/g, ''),
                        )
                      }
                      onBlur={(e) =>
                        onDebuggerSequenceCommit?.(
                          label,
                          e.target.value.replace(/[^01]/g, ''),
                        )
                      }
                      onKeyDown={(e) => {
                        if (e.key !== 'Enter') return;
                        const target = e.currentTarget;
                        onDebuggerSequenceCommit?.(
                          label,
                          target.value.replace(/[^01]/g, ''),
                        );
                        target.blur();
                      }}
                      className="h-5 w-20 rounded border border-green-300 bg-white px-1 text-[10px] text-green-700"
                      title="Input bit sequence"
                    />
                  </div>
                ) : null}
                {debuggerActive && sequenceBits.length > 0 ? (
                  <div
                    className="pointer-events-none absolute z-30 flex max-w-[90px] flex-wrap items-center gap-[2px]"
                    style={{
                      left: pt.x,
                      top: pt.y,
                      transform: `translate(-102%, -105%) scale(${zoom})`,
                      transformOrigin: 'right bottom',
                    }}
                    title={`Step ${debuggerStepIndex + 1} highlighted in sequence`}
                  >
                    {sequenceBits.map((bit, bitIndex) => (
                      <span
                        key={`${id}-seq-${bitIndex}`}
                        className={cn(
                          'inline-flex h-3 w-3 items-center justify-center rounded border text-[9px] font-bold leading-none',
                          bitIndex === debuggerStepIndex
                            ? 'border-emerald-500 bg-emerald-500 text-white shadow-sm'
                            : 'border-green-200 bg-white/95 text-green-700',
                        )}
                      >
                        {bit}
                      </span>
                    ))}
                  </div>
                ) : null}
                <button
                  type="button"
                  className={cn(
                    'pointer-events-auto absolute flex items-center gap-2 rounded border border-green-500/80 bg-green-500 px-2 py-1 text-xs font-semibold text-white shadow-sm transition-all hover:scale-125 hover:bg-green-600 animate-in fade-in zoom-in-90',
                    highInputOwnerIds.has(id) &&
                      'ring-1 ring-emerald-400/70 animate-pulse shadow-[0_0_12px_rgba(16,185,129,0.3)]',
                    isPowerSurge &&
                      'ring-2 ring-cyan-300/80 shadow-[0_0_18px_rgba(34,211,238,0.45)]',
                  )}
                  style={{
                    left: pt.x,
                    top: pt.y,
                    transform: `translate(-100%, calc(-50% + ${PUZZLE_IO_Y_OFFSET_PX}px)) scale(${zoom})`,
                    transformOrigin: 'right center',
                    animationDelay: `${Math.min(inputIndex, 8) * 110}ms`,
                    animationFillMode: 'both',
                  }}
                  onPointerDown={(e) => {
                    e.stopPropagation();
                    onStartWireDrag(
                      { ownerId: id, portId: 'P0', kind: 'output' },
                      e,
                    );
                  }}
                  onPointerUp={(e) => {
                    e.stopPropagation();
                    if (wireDraft) {
                      if (
                        wireDraft.start.ownerId === id &&
                        wireDraft.start.portId === 'P0'
                      ) {
                        return;
                      }
                      finalizeWire(wireDraft.start, {
                        ownerId: id,
                        portId: 'P0',
                        kind: 'output',
                      });
                      setWireDraft(null);
                    }
                  }}
                  onClick={(e) => {
                    e.stopPropagation();
                    // Handled by onPointerUp
                  }}
                  aria-label={`Puzzle input ${label}`}
                >
                  {label}
                </button>
              </div>
            );
          })}

          {outputs.map((label, outputIndex) => {
            const id = `IO:OUT:${label}`;
            const pt = ioLayout.outputs[id];
            if (!pt) return null;
            const outputBit = debuggerOutputBits[label] ?? '0';
            return (
              <div key={id}>
                {debuggerActive ? (
                  <div
                    className="pointer-events-auto absolute z-30 flex items-center gap-1"
                    style={{
                      left: pt.x,
                      top: pt.y,
                      transform: `translate(-140%, -50%) scale(${zoom})`,
                      transformOrigin: 'right center',
                    }}
                  >
                    <div
                      className="flex size-4 items-center justify-center rounded border border-orange-400 bg-white text-[9px] font-bold text-orange-700"
                      title={`Output bit at step ${debuggerStepIndex + 1}`}
                    >
                      {outputBit}
                    </div>
                  </div>
                ) : null}
                <button
                  type="button"
                  className={cn(
                    'pointer-events-auto absolute flex items-center gap-2 rounded border border-orange-500/80 bg-orange-500 px-2 py-1 text-xs font-semibold text-white shadow-sm transition-all hover:scale-125 hover:bg-orange-600 animate-in fade-in zoom-in-90',
                    isPowerSurge &&
                      'ring-2 ring-cyan-300/80 shadow-[0_0_18px_rgba(34,211,238,0.45)]',
                  )}
                  style={{
                    left: pt.x,
                    top: pt.y,
                    transform: `translate(0%, calc(-50% + ${PUZZLE_IO_Y_OFFSET_PX}px)) scale(${zoom})`,
                    transformOrigin: 'left center',
                    animationDelay: `${Math.min(outputIndex, 8) * 110}ms`,
                    animationFillMode: 'both',
                  }}
                  onPointerDown={(e) => {
                    e.stopPropagation();
                    onStartWireDrag(
                      { ownerId: id, portId: 'P0', kind: 'input' },
                      e,
                    );
                  }}
                  onPointerUp={(e) => {
                    e.stopPropagation();
                    if (wireDraft) {
                      if (
                        wireDraft.start.ownerId === id &&
                        wireDraft.start.portId === 'P0'
                      ) {
                        return;
                      }
                      finalizeWire(wireDraft.start, {
                        ownerId: id,
                        portId: 'P0',
                        kind: 'input',
                      });
                      setWireDraft(null);
                    }
                  }}
                  onClick={(e) => {
                    e.stopPropagation();
                    // Handled by onPointerUp
                  }}
                  aria-label={`Puzzle output ${label}`}
                >
                  {label}
                </button>
              </div>
            );
          })}
        </div>

        {debuggerActive ? (
          <div className="pointer-events-none absolute right-3 top-14 z-30 rounded border border-border bg-card/90 px-2 py-1 text-[11px] text-foreground shadow-sm backdrop-blur-sm">
            Step {debuggerStepCount ? debuggerStepIndex + 1 : 0}/
            {debuggerStepCount || 0}
          </div>
        ) : null}

        {/* Persistent Direction Indicators */}
        {(() => {
          if (containerSize.w === 0) return null;
          const indicators: {
            id: string;
            label: string;
            color: string;
            position: { x: number; y: number };
            rotation: number;
          }[] = [];

          // Input indicator - positioned above the middle of inputs
          if (inputs.length > 0) {
            const firstInput = ioLayout.inputs[`IO:IN:${inputs[0]}`];
            const lastInput =
              ioLayout.inputs[`IO:IN:${inputs[inputs.length - 1]}`];

            if (firstInput && lastInput) {
              const midY = (firstInput.y + lastInput.y) / 2;
              const midX = firstInput.x;

              // Calculate position and rotation
              let rotation = 0;
              let posX = midX - 40; // Position to the left of inputs column
              let posY = Math.max(
                16,
                Math.min(containerSize.h - 40, midY - 30),
              );

              // Determine arrow direction based on where inputs are
              if (midX < 0) {
                rotation = 0; // point right (inputs are off-screen left)
                posX = 16;
              } else if (midX > containerSize.w) {
                rotation = 180; // point left (inputs are off-screen right)
                posX = containerSize.w - 60;
              } else if (midY < 80) {
                rotation = -90; // point up (inputs are off-screen top)
                posY = 16;
                posX = midX - 30;
              } else if (midY > containerSize.h - 50) {
                rotation = 90; // point down (inputs are off-screen bottom)
                posY = containerSize.h - 40;
                posX = midX - 30;
              } else {
                rotation = 90; // point down (inputs are on-screen, position above)
                posY = firstInput.y - 60; // Position above topmost input
                posX = midX - 30;
              }

              indicators.push({
                id: 'inputs',
                label: 'IN',
                color: 'bg-green-500 text-white',
                position: { x: posX, y: posY },
                rotation,
              });
            }
          }

          // Output indicator - positioned above outputs (mirroring IN indicator)
          if (outputs.length > 0) {
            const firstOutput = ioLayout.outputs[`IO:OUT:${outputs[0]}`];
            const lastOutput =
              ioLayout.outputs[`IO:OUT:${outputs[outputs.length - 1]}`];

            if (firstOutput && lastOutput) {
              const midX = firstOutput.x;
              const midY = (firstOutput.y + lastOutput.y) / 2;

              // Calculate position and rotation — arrow always points toward the outputs
              let rotation = 0;
              let posX = midX - 30;
              let posY = firstOutput.y - 60;

              if (midX > containerSize.w) {
                rotation = 0; // point right (outputs off-screen right)
                posX = containerSize.w - 60;
                posY = Math.max(16, Math.min(containerSize.h - 40, midY - 15));
              } else if (midX < 0) {
                rotation = 180; // point left (outputs off-screen left)
                posX = 16;
                posY = Math.max(16, Math.min(containerSize.h - 40, midY - 15));
              } else if (midY < 80) {
                rotation = -90; // point up (outputs off-screen top)
                posY = 16;
                posX = midX - 30;
              } else if (midY > containerSize.h - 50) {
                rotation = 90; // point down (outputs off-screen bottom)
                posY = containerSize.h - 40;
                posX = midX - 30;
              } else {
                rotation = 90; // point down toward outputs
                posY = firstOutput.y - 60;
                posX = midX - 30;
              }

              indicators.push({
                id: 'outputs',
                label: 'OUT',
                color: 'bg-orange-500 text-white',
                position: { x: posX, y: posY },
                rotation,
              });
            }
          }

          return indicators.map((ind) => (
            <button
              type="button"
              key={ind.id}
              className={cn(
                'absolute z-40 flex items-center gap-1 rounded-full px-3 py-1.5 text-xs font-bold shadow-lg ring-1 ring-black/10 cursor-pointer transition-all hover:scale-110 active:scale-95',
                ind.color,
              )}
              onPointerDown={(e) => e.stopPropagation()}
              onPointerUp={(e) => e.stopPropagation()}
              onClick={() => panToIOTarget(ind.id as 'inputs' | 'outputs')}
              style={{
                left: ind.position.x,
                top: ind.position.y,
              }}
              title="Click to scroll to inputs or outputs"
            >
              <span>{ind.label}</span>
              <svg
                viewBox="0 0 16 16"
                className="size-3"
                fill="currentColor"
                style={{
                  transform: `rotate(${ind.rotation}deg)`,
                }}
              >
                <path d="M8 0l8 8-8 8V0z" />
              </svg>
            </button>
          ));
        })()}
      </div>

      <style jsx>{`
        .workstation-solved-slam {
          transform-origin: center;
        }

        .workstation-wire-flow {
          animation: workstation-wire-flow 1.9s linear infinite;
        }

        .workstation-wire-flow-fast {
          animation: workstation-wire-flow 0.9s linear infinite;
        }

        .workstation-component-pop {
          animation: workstation-pop 280ms ease-out;
        }

        .workstation-board-success {
          animation: workstation-board-success 1s ease-out;
          box-shadow:
            0 0 0 1px rgba(74, 222, 128, 0.55),
            0 0 28px rgba(34, 197, 94, 0.3);
        }

        .workstation-board-surge {
          animation: workstation-board-surge 600ms
            cubic-bezier(0.22, 0.7, 0.2, 1);
          box-shadow:
            0 0 0 1px rgba(34, 211, 238, 0.7),
            0 0 40px rgba(34, 211, 238, 0.45);
        }

        .workstation-board-failure {
          animation:
            workstation-shake 420ms ease-in-out,
            workstation-board-failure 700ms ease-out;
          box-shadow:
            0 0 0 1px rgba(248, 113, 113, 0.55),
            0 0 28px rgba(239, 68, 68, 0.28);
        }

        .workstation-port-lock-flash {
          animation: workstation-port-lock 220ms ease-out;
        }

        .workstation-wire-snap {
          animation: workstation-wire-snap 360ms
            cubic-bezier(0.16, 0.84, 0.24, 1);
          transform-origin: center;
        }

        .workstation-wire-snapback {
          transition: all 150ms ease-out;
        }

        .workstation-component-surge {
          animation: workstation-component-surge 360ms ease-in-out infinite;
        }

        .workstation-component-breathe {
          animation: workstation-component-breathe 4s ease-in-out infinite;
        }

        .workstation-component-delete-out {
          animation: workstation-component-delete-out 150ms ease-in forwards;
          transform-origin: center;
        }

        @keyframes workstation-pop {
          0% {
            transform: scale(0.88);
          }
          65% {
            transform: scale(1.08);
          }
          100% {
            transform: scale(1);
          }
        }

        @keyframes workstation-board-surge {
          0% {
            box-shadow: 0 0 0 0 rgba(34, 211, 238, 0);
            transform: scale(1);
          }
          38% {
            box-shadow:
              0 0 0 2px rgba(34, 211, 238, 0.75),
              0 0 46px rgba(34, 211, 238, 0.55);
            transform: scale(1.006);
          }
          100% {
            box-shadow:
              0 0 0 1px rgba(34, 211, 238, 0.45),
              0 0 24px rgba(34, 211, 238, 0.24);
            transform: scale(1);
          }
        }

        @keyframes workstation-wire-flow {
          0% {
            stroke-dashoffset: 0;
          }
          100% {
            stroke-dashoffset: -64;
          }
        }

        @keyframes workstation-board-success {
          0% {
            box-shadow: 0 0 0 0 rgba(34, 197, 94, 0);
          }
          35% {
            box-shadow:
              0 0 0 2px rgba(74, 222, 128, 0.55),
              0 0 36px rgba(34, 197, 94, 0.35);
          }
          100% {
            box-shadow: 0 0 0 0 rgba(34, 197, 94, 0);
          }
        }

        @keyframes workstation-board-failure {
          0% {
            box-shadow: 0 0 0 0 rgba(239, 68, 68, 0);
          }
          30% {
            box-shadow:
              0 0 0 2px rgba(248, 113, 113, 0.55),
              0 0 34px rgba(239, 68, 68, 0.35);
          }
          100% {
            box-shadow: 0 0 0 0 rgba(239, 68, 68, 0);
          }
        }

        @keyframes workstation-shake {
          0%,
          100% {
            transform: translateX(0);
          }
          20% {
            transform: translateX(-5px);
          }
          40% {
            transform: translateX(4px);
          }
          60% {
            transform: translateX(-3px);
          }
          80% {
            transform: translateX(2px);
          }
        }

        @keyframes workstation-wire-snap {
          0% {
            transform: scaleY(0.88) scaleX(0.98) translateY(0.5px);
          }
          42% {
            transform: scaleY(1.18) scaleX(1.03) translateY(-0.6px);
          }
          68% {
            transform: scaleY(0.95) scaleX(0.995) translateY(0.3px);
          }
          100% {
            transform: scaleY(1) scaleX(1) translateY(0);
          }
        }

        @keyframes workstation-component-surge {
          0%,
          100% {
            box-shadow:
              0 0 0 1px rgba(34, 211, 238, 0.35),
              0 0 10px rgba(34, 211, 238, 0.22);
            transform: scale(1);
          }
          50% {
            box-shadow:
              0 0 0 1px rgba(34, 211, 238, 0.9),
              0 0 28px rgba(34, 211, 238, 0.5);
            transform: scale(1.016);
          }
        }

        @keyframes workstation-component-delete-out {
          0% {
            transform: scale(1);
            opacity: 1;
          }
          100% {
            transform: scale(0);
            opacity: 0;
          }
        }

        @keyframes workstation-component-breathe {
          0%,
          100% {
            transform: scale(1);
          }
          50% {
            transform: scale(1.02);
          }
        }

        @keyframes workstation-micro-spark {
          0% {
            opacity: 0.95;
            transform: translate(-50%, -50%) scale(1);
          }
          100% {
            opacity: 0;
            transform: translate(
                calc(-50% + var(--spark-dx)),
                calc(-50% + var(--spark-dy))
              )
              scale(0.2);
          }
        }

        .workstation-micro-spark {
          animation: workstation-micro-spark 300ms ease-out forwards;
          box-shadow: 0 0 8px rgba(250, 204, 21, 0.85);
        }

        @keyframes workstation-port-lock {
          0% {
            transform: scale(1);
            background-color: rgba(255, 255, 255, 0.95);
            box-shadow: 0 0 0 rgba(34, 211, 238, 0);
          }
          50% {
            transform: scale(1.35);
            background-color: rgba(255, 255, 255, 1);
            box-shadow: 0 0 14px rgba(34, 211, 238, 0.75);
          }
          100% {
            transform: scale(1);
            background-color: initial;
            box-shadow: 0 0 0 rgba(34, 211, 238, 0);
          }
        }
      `}</style>
    </div>
  );
};
