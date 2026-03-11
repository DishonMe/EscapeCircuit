'use client';

import type {
  DragEvent as ReactDragEvent,
  PointerEvent as ReactPointerEvent,
  WheelEvent as ReactWheelEvent,
} from 'react';
import { useEffect, useMemo, useRef, useState } from 'react';

import { Button } from '@/components/ui/button';
import { useNotifications } from '@/components/ui/notifications';
import { Spinner } from '@/components/ui/spinner';
import { RippleEffect } from '@/components/ripple-effect';
import { useAudio } from '@/hooks/useAudio';
import type { Wire } from '@/types/api';
import { cn } from '@/utils/cn';

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
};

export type PlacedGridComponent = {
  id: string; // instance id
  componentId: string; // catalog id
  origin: HoleCoord;
  rotation: 0 | 90;
};

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

// Visual Feature: Dynamic Wire Coloring
const WIRE_COLORS = ['#3b82f6', '#ef4444', '#10b981', '#a855f7', '#f97316']; 
const getWireColor = (id: string) => {
  let hash = 0;
  for (let i = 0; i < id.length; i++) hash = id.charCodeAt(i) + ((hash << 5) - hash);
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

const parseDraggedComponentId = (e: ReactDragEvent) => {
  return e.dataTransfer.getData('application/x-escapecircuit-component');
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
  boardRows,
  boardCols,
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
  boardRows?: number | null;
  boardCols?: number | null;
}) => {
  const gridRows = Math.max(1, boardRows ?? DEFAULT_GRID_ROWS);
  const gridCols = Math.max(1, boardCols ?? DEFAULT_GRID_COLS);
  const notifications = useNotifications();

  const containerRef = useRef<HTMLDivElement | null>(null);
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
    | { type: 'component'; placedId: string }
    | { type: 'wire'; wireId: string }
  >({ type: 'none' });

  const [wireDraft, setWireDraft] = useState<null | {
    start: PortAddress;
    current: { x: number; y: number };
  }>(null);

  const [draggedComponent, setDraggedComponent] = useState<{
    placedId: string;
    startHole: HoleCoord;
    currentHole: HoleCoord;
    offset: { x: number; y: number };
  } | null>(null);

  // Ghost/Preview State
  const [dropPreview, setDropPreview] = useState<HoleCoord | null>(null);
  const [recentlyPlacedId, setRecentlyPlacedId] = useState<string | null>(null);
  const [recentlyConnectedWireId, setRecentlyConnectedWireId] = useState<string | null>(null);
  const [hoveredDeleteComponentId, setHoveredDeleteComponentId] = useState<string | null>(null);
  const [hoveredDeleteWireId, setHoveredDeleteWireId] = useState<string | null>(null);
  const [deletingComponentIds, setDeletingComponentIds] = useState<string[]>([]);
  const [activeRipples, setActiveRipples] = useState<Array<{ id: string; x: number; y: number }>>([]);
  const [cursorSpotlight, setCursorSpotlight] = useState<{ x: number; y: number; visible: boolean }>({
    x: 0,
    y: 0,
    visible: false,
  });
  const [hoveredWireSignal, setHoveredWireSignal] = useState<{
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

  const { playDrop, playWireConnect } = useAudio();

  const activeWireIdsSet = useMemo(() => new Set(activeWireIds), [activeWireIds]);
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

  const previousPlacedIdsRef = useRef<string[]>(placed.map((component) => component.id));
  const previousWireIdsRef = useRef<string[]>(wires.map((wire) => wire.id));

  const STORAGE_KEY = `escapecircuit.workstation.grid.v1:${puzzleId}`;

  // Load/save view state.
  useEffect(() => {
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
  }, [STORAGE_KEY, gridCols, gridRows]);

  useEffect(() => {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ zoom }));
    } catch {
      // ignore
    }
  }, [STORAGE_KEY, zoom]);

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

    const calculatePan = (fit: number, containerWidth: number) => {
      // Inputs are at column -1. We want to position them with a visible left margin.
      // Formula: screen_x = pan.x + (col + 0.5) * CELL_PX * fit
      // To place col -1 at ~15% from left (leaving room for input labels):
      const targetScreenX = containerWidth * 0.15;
      const panX = targetScreenX - (-0.5) * CELL_PX * fit;
      // Pan Y: center vertically
      const panY = 2 * CELL_PX * fit;
      return { x: panX, y: panY };
    };

    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      const fit = updateFit();
      setZoom(fit);
      const pan = calculatePan(fit, el.getBoundingClientRect().width);
      setPan(pan);
    } else {
      const fit = updateFit();
      setZoom((prev) => Math.max(prev, fit));
      const pan = calculatePan(fit, el.getBoundingClientRect().width);
      setPan(pan);
    }

    const ro = new ResizeObserver(() => {
      const fit = updateFit();
      setZoom((prev) => Math.max(prev, fit));
      const rect = el.getBoundingClientRect();
      const pan = calculatePan(fit, rect.width);
      setPan(pan);
    });
    ro.observe(el);

    return () => ro.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [STORAGE_KEY, gridCols, gridRows]);

  const componentRects = useMemo(() => {
    return placed.map((p) => {
      const def = catalog[p.componentId];
      const size = rotatedSize(def.size, p.rotation);
      return { placedId: p.id, origin: p.origin, size };
    });
  }, [catalog, placed]);

  const placedById = useMemo(() => {
    const map: Record<string, PlacedGridComponent> = {};
    for (const p of placed) map[p.id] = p;
    return map;
  }, [placed]);

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

  // Helper function to get display label with numbering
  const getComponentDisplayLabel = (
    componentId: string,
    placedId: string,
  ): string => {
    const def = catalog[componentId];
    if (!def) return componentId;

    // Count how many components have the same componentId
    const sameTypeComponents = placed.filter((p) => p.componentId === componentId);

    // If only one of this type, don't show the number
    if (sameTypeComponents.length <= 1) {
      return def.label;
    }

    // If multiple, find the index of the current component
    const index = sameTypeComponents.findIndex((p) => p.id === placedId);
    if (index === -1) {
      return def.label;
    }

    // Return numbered label like "1-and", "2-and"
    return `${index + 1}-${def.label.toLowerCase()}`;
  };

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

  const canPlaceComponentAt = (
    componentId: string,
    origin: HoleCoord,
    rotation: 0 | 90,
    excludePlacedId?: string,
  ) => {
    const def = catalog[componentId];
    if (!def) return false;

    const size = rotatedSize(def.size, rotation);
    if (origin.row < 0 || origin.col < 0) return false;
    if (origin.row + size.h > gridRows) return false;
    if (origin.col + size.w > gridCols) return false;

    // no component overlap
    for (const rect of componentRects) {
      if (rect.placedId === excludePlacedId) continue;
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
      if (occ && occ.ownerId !== excludePlacedId) return false;
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
    setActiveRipples((prev) => [...prev, { id: ripleId, x: centerX, y: centerY }]);
    
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
      return ioLayout.inputs[port.ownerId] ?? { x: 0, y: 0 };
    }
    if (port.ownerId.startsWith('IO:OUT:')) {
      return ioLayout.outputs[port.ownerId] ?? { x: 0, y: 0 };
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
      // Distribute along the bottom (Layout Update: Outputs to Bottom)
      const colStep = gridCols / (outputs.length + 1);
      // Center based on step
      const col = (i + 1) * colStep - 0.5;
      const row = gridRows + 0.5;
      const anchor = toScreenCenter(row, col);
      outputsPos[id] = { x: anchor.x, y: anchor.y };
    }

    return { inputs: inputsPos, outputs: outputsPos };
  }, [inputs, outputs, pan.x, pan.y, zoom, gridCols, gridRows]);

  const onWheel = (e: ReactWheelEvent) => {
    e.preventDefault();
    const el = containerRef.current;
    if (!el) return;

    const rect = el.getBoundingClientRect();
    const cursor = { x: e.clientX - rect.left, y: e.clientY - rect.top };
    const before = screenToWorld(cursor);

    const delta = -e.deltaY;
    const factor = delta > 0 ? 1.1 : 0.9;
    const nextZoom = clamp(zoom * factor, minZoom, 4);

    // keep cursor world point stable
    let afterPanX = cursor.x - before.col * CELL_PX * nextZoom;
    let afterPanY = cursor.y - before.row * CELL_PX * nextZoom;

    // Apply pan limits - allow full scrolling of the grid
    if (rect) {
      const gridWidthPx = (gridCols + 1) * CELL_PX * nextZoom;
      const gridHeightPx = (gridRows + 1) * CELL_PX * nextZoom;
      
      const minPanX = Math.min(0, rect.width - gridWidthPx);
      const maxPanX = Math.max(0, rect.width - gridWidthPx) + 50;
      const minPanY = Math.min(0, rect.height - gridHeightPx);
      const maxPanY = Math.max(0, rect.height - gridHeightPx) + 20;
      
      afterPanX = clamp(afterPanX, minPanX, maxPanX);
      afterPanY = clamp(afterPanY, minPanY, maxPanY);
    }

    setZoom(nextZoom);
    setPan({ x: afterPanX, y: afterPanY });
  };

  const onPointerDownBackground = (e: ReactPointerEvent<HTMLDivElement>) => {
    if (e.button !== 0) return;
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
    
    // Apply pan limits to keep inputs/outputs in view
    const el = containerRef.current;
    if (el) {
      const rect = el.getBoundingClientRect();
      // Allow panning the full grid - left edge should show col -1, right edge should show the grid
      const gridWidthPx = (gridCols + 1) * CELL_PX * zoom;
      const gridHeightPx = (gridRows + 1) * CELL_PX * zoom;
      
      // Pan limits: ensure grid fits properly in view with margins
      const minPanX = Math.min(0, rect.width - gridWidthPx);
      const maxPanX = Math.max(0, rect.width - gridWidthPx) + 50;
      const minPanY = Math.min(0, rect.height - gridHeightPx);
      const maxPanY = Math.max(0, rect.height - gridHeightPx) + 20;
      
      setPan({
        x: clamp(newPanX, minPanX, maxPanX),
        y: clamp(newPanY, minPanY, maxPanY),
      });
    } else {
      setPan({ x: newPanX, y: newPanY });
    }
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
      setMicroSparks((current) => current.filter((spark) => !ids.has(spark.id)));
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
    setHoveredWireSignal((current) => (current?.wireId === wireId ? null : current));
  };

  const trashRef = useRef<HTMLButtonElement | null>(null);

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
            setHoveredDeleteWireId((current) => (current === w.id ? null : current))
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
    const droopY = Math.max(8, Math.min(42, Math.abs(dy) * 0.22 + Math.abs(dx) * 0.04));
    const c1x = from.x + controlX;
    const c1y = from.y + droopY;
    const c2x = to.x - controlX;
    const c2y = to.y + droopY;
    return `M ${from.x} ${from.y} C ${c1x} ${c1y}, ${c2x} ${c2y}, ${to.x} ${to.y}`;
  };

  return (
    <div className="flex flex-col gap-2">
      <div className="rounded-md border border-gray-300 bg-white p-3">
        <div className="mb-1 text-sm font-medium text-gray-900">
          Working Area
        </div>
        <div className="text-xs text-gray-600">
          {gridRows}×{gridCols} grid. Wheel to zoom. Drag background to pan. Click/drag ports to
          wire. While placing, press R to rotate.
        </div>
      </div>

      <div
        ref={containerRef}
        className={cn(
          'relative h-[calc(100vh-18rem)] overflow-hidden rounded-md border border-gray-300 bg-white transition-[box-shadow,transform,border-color] duration-300 cursor-crosshair',
          isPowerSurge && 'workstation-board-surge',
          boardFeedback === 'success' && 'workstation-board-success border-emerald-400',
          boardFeedback === 'failure' && 'workstation-board-failure border-red-400',
        )}
        onWheel={onWheel}
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
          const world = screenToWorld(local);
          const origin = {
            row: clamp(Math.floor(world.row), 0, gridRows - 1),
            col: clamp(Math.floor(world.col), 0, gridCols - 1),
          };
          setDropPreview(origin);
        }}
        onDragLeave={() => setDropPreview(null)}
        onDrop={(e) => {
          e.preventDefault();
          setDropPreview(null);
          const componentId = parseDraggedComponentId(e);
          if (!componentId) return;
          const el = containerRef.current;
          if (!el) return;
          const rect = el.getBoundingClientRect();
          const local = { x: e.clientX - rect.left, y: e.clientY - rect.top };
          const world = screenToWorld(local);
          const origin = {
            row: clamp(Math.floor(world.row), 0, gridRows - 1),
            col: clamp(Math.floor(world.col), 0, gridCols - 1),
          };

          const rotation =
            selectedComponent.mode === 'placing' &&
            selectedComponent.componentId === componentId
              ? selectedComponent.rotation
              : 0;

          placeComponent(componentId, origin, rotation);
          onSelectedComponentChange({ mode: 'none' });
        }}
      >
        {isChecking && (
          <div className="pointer-events-none absolute inset-0 z-40 flex items-center justify-center bg-white/45 backdrop-blur-[2px]">
            <div className="flex items-center gap-3 rounded-2xl border border-white/70 bg-white/80 px-4 py-3 text-sm font-medium text-slate-700 shadow-xl shadow-blue-500/10">
              <Spinner size="md" className="text-blue-500" />
              <span>Running the circuit...</span>
            </div>
          </div>
        )}

        {showSolvedSlam && (
          <div className="pointer-events-none absolute inset-0 z-50 flex items-center justify-center">
            <div className="rounded-xl border border-emerald-300/70 bg-white/90 px-6 py-3 text-4xl font-extrabold tracking-[0.12em] text-emerald-600 shadow-2xl shadow-emerald-500/30 animate-in fade-in zoom-in-50 duration-300 workstation-solved-slam">
              SOLVED!
            </div>
          </div>
        )}

        {/* Ripple Effects */}
        {activeRipples.map((ripple) => (
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

        {/* Trash */}
        <button
          type="button"
          ref={trashRef}
          className="absolute right-3 top-3 z-30 flex size-10 items-center justify-center rounded border border-gray-200 bg-gray-50 text-gray-600 hover:bg-red-50 hover:text-red-600"
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
              removeComponent(selectedEntity.placedId);
              return;
            }
            if (selectedEntity.type === 'wire') {
              removeWire(selectedEntity.wireId);
              return;
            }
            // Clear all
            if (confirm('Are you sure you want to clear the entire grid?')) {
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
            const wirePath = getCurvedWirePath(a, b);
            const isSurgePowered = isPowerSurge && (activeWireIdsSet.size === 0 || isHighSignal);

            // Visual Feature: Dynamic Wire Coloring
            const strokeColor = isSelected
              ? '#2563eb'
              : isDeleteWarn
                ? '#ef4444'
              : isHighSignal
                ? '#fde047'
              : isRecentlyConnected
                ? '#60a5fa'
                : getWireColor(w.id);

            const flowColor = isHighSignal
              ? '#fef08a'
              : isRecentlyConnected
                ? '#bfdbfe'
                : '#93c5fd';

            return (
              <g key={w.id}>
                <path
                  className={cn(
                    'pointer-events-auto cursor-pointer transition-all duration-300',
                    isRecentlyConnected && 'animate-pulse',
                    isRecentlyConnected && 'workstation-wire-snap',
                  )}
                  d={wirePath}
                  fill="none"
                  stroke={strokeColor}
                  strokeWidth={isPowerSurge ? 4.2 : isSelected ? 3 : isRecentlyConnected ? 4 : 2}
                  style={{
                    filter: isDeleteWarn
                      ? 'drop-shadow(0 0 8px rgba(239,68,68,0.85))'
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
                  strokeWidth={isPowerSurge ? 3.2 : isHighSignal ? 2.4 : 1.4}
                  strokeDasharray={isHighSignal ? '9 7' : '7 9'}
                  className={cn(
                    'pointer-events-none workstation-wire-flow',
                    (isHighSignal || isPowerSurge) && 'workstation-wire-flow-fast',
                  )}
                  style={{
                    opacity: isPowerSurge ? 1 : isHighSignal ? 0.95 : 0.45,
                    filter: isPowerSurge
                      ? 'drop-shadow(0 0 14px rgba(34,211,238,0.95))'
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
                d={getCurvedWirePath(getPortScreenPoint(wireDraft.start, ioLayout), wireDraft.current)}
                fill="none"
                stroke="#2563eb"
                strokeWidth={2}
                strokeDasharray="4 3"
              />
              <path
                d={getCurvedWirePath(getPortScreenPoint(wireDraft.start, ioLayout), wireDraft.current)}
                fill="none"
                stroke="#bfdbfe"
                strokeWidth={1.4}
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
                strokeWidth={1.4}
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
            className="pointer-events-none absolute z-30 size-1 rounded-full bg-yellow-400 workstation-micro-spark"
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
                          portOcc
                            ? 'size-3 bg-blue-400'
                            : occ
                              ? 'size-3 bg-gray-400'
                              : 'size-1 bg-gray-300 hover:bg-gray-400',
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

          {/* Feature: Drag-and-Drop Ghost/Preview */}
          {draggedPaletteComponentId && dropPreview && (() => {
             const def = catalog[draggedPaletteComponentId];
             if (!def) return null;
             const rotation = 0; // Default zero for new drops
             const size = rotatedSize(def.size, rotation);
             const isValid = canPlaceComponentAt(draggedPaletteComponentId, dropPreview, rotation);
             
             // Count how many components of this type will exist after placing this one
             const sameTypeCount = placed.filter((p) => p.componentId === draggedPaletteComponentId).length + 1;
             const displayLabel = sameTypeCount > 1 
               ? `${sameTypeCount}-${def.label.toLowerCase()}` 
               : def.label;
             
             const left = dropPreview.col * CELL_PX;
             const top = dropPreview.row * CELL_PX;

              return (
                <div
                  className={cn(
                    'absolute rounded border text-[10px] flex items-center justify-center font-medium opacity-60 z-50 pointer-events-none',
                    isValid
                      ? 'bg-blue-100 border-blue-400 text-blue-900'
                      : 'bg-red-100 border-red-400 text-red-900',
                  )}
                  style={{
                    left,
                    top,
                    width: size.w * CELL_PX - 2,
                    height: size.h * CELL_PX - 2,
                  }}
                >
                  {displayLabel}
                </div>
              );
          })()}

          {/* Components */}
          {placed.map((p, placedIndex) => {
            const def = catalog[p.componentId];
            const size = rotatedSize(def.size, p.rotation);

            const isDragging = draggedComponent?.placedId === p.id;
            const origin = isDragging ? draggedComponent.currentHole : p.origin;

            const left = origin.col * CELL_PX;
            const top = origin.row * CELL_PX;

            const isSelected =
              selectedEntity.type === 'component' &&
              selectedEntity.placedId === p.id;
            const isActive = activeComponentIdsSet.has(p.id);
            const isDeleteWarn = hoveredDeleteComponentId === p.id;
            const isDeleting = deletingComponentIds.includes(p.id);

            return (
              <div
                key={p.id}
                className={cn(
                  'group absolute rounded border bg-gray-50 text-[10px] text-gray-800 transition-[box-shadow,transform,border-color] duration-300 animate-in fade-in zoom-in-90',
                  isDeleting && 'workstation-component-delete-out',
                  !isDragging && !isDeleting && 'workstation-component-breathe',
                  isDeleteWarn && 'border-red-400 bg-red-50/60 shadow-[0_0_0_1px_rgba(248,113,113,0.45),0_0_18px_rgba(239,68,68,0.25)]',
                  isActive && 'border-cyan-300 shadow-[0_0_0_1px_rgba(34,211,238,0.45),0_0_12px_rgba(59,130,246,0.4),0_0_24px_rgba(34,211,238,0.32)]',
                  isPowerSurge && 'workstation-component-surge',
                  isSelected
                    ? 'border-blue-400 shadow-[0_0_0_1px_rgba(96,165,250,0.55),0_0_18px_rgba(59,130,246,0.28)]'
                    : 'border-gray-300',
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
                  setSelectedEntity({ type: 'component', placedId: p.id });

                  const el = containerRef.current;
                  if (!el) return;
                  const rect = el.getBoundingClientRect();
                  const cursor = {
                    x: e.clientX - rect.left,
                    y: e.clientY - rect.top,
                  };
                  const worldPos = screenToWorld(cursor);

                  setDraggedComponent({
                    placedId: p.id,
                    startHole: p.origin,
                    currentHole: p.origin,
                    offset: {
                      x: worldPos.col - p.origin.col,
                      y: worldPos.row - p.origin.row,
                    },
                  });
                }}
                onPointerMove={(e) => {
                  if (draggedComponent?.placedId === p.id) {
                    e.stopPropagation();
                    const el = containerRef.current;
                    if (!el) return;
                    const rect = el.getBoundingClientRect();
                    const cursor = {
                      x: e.clientX - rect.left,
                      y: e.clientY - rect.top,
                    };
                    const worldPos = screenToWorld(cursor);

                    const newCol = Math.round(
                      worldPos.col - draggedComponent.offset.x,
                    );
                    const newRow = Math.round(
                      worldPos.row - draggedComponent.offset.y,
                    );

                    if (
                      newCol !== draggedComponent.currentHole.col ||
                      newRow !== draggedComponent.currentHole.row
                    ) {
                      setDraggedComponent({
                        ...draggedComponent,
                        currentHole: { row: newRow, col: newCol },
                      });
                    }
                  }
                }}
                onPointerUp={(e) => {
                  e.stopPropagation();
                  e.currentTarget.releasePointerCapture(e.pointerId);

                  if (draggedComponent?.placedId === p.id) {
                    if (isOverTrash(e.clientX, e.clientY)) {
                      removeComponent(p.id);
                    } else {
                      // Commit move
                      if (
                        canPlaceComponentAt(
                          p.componentId,
                          draggedComponent.currentHole,
                          p.rotation,
                          p.id,
                        )
                      ) {
                        const next = placed.map((x) =>
                          x.id === p.id
                            ? { ...x, origin: draggedComponent.currentHole }
                            : x,
                        );
                        onPlacedChange(next);
                      }
                    }
                    setDraggedComponent(null);
                  }
                }}
              >
                 {/* Canvas Rendering: Grid & Labels (Label Visibility) */}
                 {/* Render label with z-20 and pointer-events-none so it stays on top but doesn't block clicks */}
                 {/* Name in the middle-bottom with improved style */}
                <div className="flex size-full items-end justify-center pb-1 z-20 relative pointer-events-none">
                  <div className="max-w-[90%] truncate rounded-sm bg-white/85 px-1 py-px text-[9px] font-bold uppercase tracking-tight text-slate-800 shadow-sm ring-1 ring-black/5 backdrop-blur-[1px] select-none">
                    {getComponentDisplayLabel(p.componentId, p.id)}
                  </div>
                </div>

                {/* Selected Delete Button (Outside) */}
                {isSelected && !isDragging && (
                  <button
                    type="button"
                    className="absolute -top-2 left-1/2 z-50 flex size-5 -translate-x-1/2 items-center justify-center rounded-full bg-white text-red-600 shadow-sm ring-1 ring-gray-200 transition-all hover:scale-110 hover:bg-red-100 hover:text-red-700 hover:ring-red-300"
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
                    title="Delete component"
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

                {/* Port markers */}
                {def.ports.map((port) => {
                  const rot = rotateOffset(port.offset, def.size, p.rotation);
                  const pl = rot.col * CELL_PX;
                  const pt = rot.row * CELL_PX;

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
                  const isPortFlashing = flashingPortKeys.includes(effectiveKey);

                  return (
                    <button
                      type="button"
                      key={port.id}
                      className={cn(
                        'absolute flex items-center justify-center rounded-full border transition-transform duration-200 hover:scale-150 hover:bg-blue-400 cursor-pointer',
                        wireDraft && 'scale-125 shadow-[0_0_10px_rgba(59,130,246,0.45)]',
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
                  );
                })}
              </div>
            );
          })}
        </div>

        {/* Floating IO */}
        <div className="pointer-events-none absolute inset-0 z-20">
          {inputs.map((label, inputIndex) => {
            const id = `IO:IN:${label}`;
            const pt = ioLayout.inputs[id];
            if (!pt) return null;
            return (
              <button
                type="button"
                key={id}
                className={cn(
                  'pointer-events-auto absolute flex items-center gap-2 rounded border border-green-300 bg-green-50 px-2 py-1 text-xs text-green-700 transition-transform hover:scale-125 animate-in fade-in zoom-in-90',
                  highInputOwnerIds.has(id) && 'ring-1 ring-emerald-400/70 animate-pulse shadow-[0_0_12px_rgba(16,185,129,0.3)]',
                  isPowerSurge && 'ring-2 ring-cyan-300/80 shadow-[0_0_18px_rgba(34,211,238,0.45)]',
                )}
                style={{
                  left: pt.x,
                  top: pt.y,
                  transform: 'translate(-100%, -50%)',
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
            );
          })}

          {outputs.map((label) => {
            const id = `IO:OUT:${label}`;
            const pt = ioLayout.outputs[id];
            if (!pt) return null;
            return (
              <button
                type="button"
                key={id}
                className="pointer-events-auto absolute flex items-center gap-2 rounded border border-orange-300 bg-orange-50 px-2 py-1 text-xs text-orange-700 transition-transform hover:scale-125"
                style={{
                  left: pt.x,
                  top: pt.y,
                  transform: 'translate(-50%, 0%)',
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
            );
          })}
        </div>

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
            const lastInput = ioLayout.inputs[`IO:IN:${inputs[inputs.length - 1]}`];
            
            if (firstInput && lastInput) {
              const midY = (firstInput.y + lastInput.y) / 2;
              const midX = firstInput.x;
              
              // Calculate position and rotation
              let rotation = 0;
              let posX = midX - 40; // Position to the left of inputs column
              let posY = Math.max(16, Math.min(containerSize.h - 40, midY - 30));
              
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

          // Output indicator - positioned to the left of outputs
          if (outputs.length > 0) {
            const firstOutput = ioLayout.outputs[`IO:OUT:${outputs[0]}`];
            const lastOutput = ioLayout.outputs[`IO:OUT:${outputs[outputs.length - 1]}`];
            
            if (firstOutput && lastOutput) {
              const midX = (firstOutput.x + lastOutput.x) / 2;
              const midY = firstOutput.y;
              
              // Calculate position and rotation
              let rotation = 0;
              let posX = Math.max(50, Math.min(containerSize.w - 50, midX - 50));
              let posY = midY - 40;
              
              // Determine arrow direction based on where outputs are
              if (midY > containerSize.h) {
                rotation = 90; // point down (outputs are off-screen below)
                posY = containerSize.h - 24;
              } else if (midY < 0) {
                rotation = -90; // point up (outputs are off-screen above)
                posY = 16;
              } else if (midX < 100) {
                rotation = 0; // point right (outputs are off-screen left)
                posX = 16;
              } else if (midX > containerSize.w - 50) {
                rotation = 180; // point left (outputs are off-screen right)
                posX = containerSize.w - 60;
              } else {
                rotation = 0; // point right (outputs are on-screen, position to left)
                posX = firstOutput.x - 90; // Position to the left of leftmost output
                posY = midY - 15;
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
            <div
              key={ind.id}
              className={cn(
                'absolute z-40 flex items-center gap-1 rounded-full px-3 py-1.5 text-xs font-bold shadow-lg ring-1 ring-black/10',
                ind.color,
              )}
              style={{
                left: ind.position.x,
                top: ind.position.y,
              }}
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
            </div>
          ));
        })()}

        {hoveredWireSignal ? (
          <div
            className="pointer-events-none absolute z-40 rounded border border-cyan-500/50 bg-black/90 px-2 py-1 text-xs font-mono text-green-400 backdrop-blur-md"
            style={{
              left: hoveredWireSignal.x + 12,
              top: hoveredWireSignal.y + 12,
            }}
          >
            SIGNAL: {hoveredWireSignal.high ? 'HIGH' : 'LOW'}
          </div>
        ) : null}
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
          box-shadow: 0 0 0 1px rgba(74, 222, 128, 0.55), 0 0 28px rgba(34, 197, 94, 0.3);
        }

        .workstation-board-surge {
          animation: workstation-board-surge 600ms cubic-bezier(0.22, 0.7, 0.2, 1);
          box-shadow: 0 0 0 1px rgba(34, 211, 238, 0.7), 0 0 40px rgba(34, 211, 238, 0.45);
        }

        .workstation-board-failure {
          animation: workstation-shake 420ms ease-in-out, workstation-board-failure 700ms ease-out;
          box-shadow: 0 0 0 1px rgba(248, 113, 113, 0.55), 0 0 28px rgba(239, 68, 68, 0.28);
        }

        .workstation-port-lock-flash {
          animation: workstation-port-lock 220ms ease-out;
        }

        .workstation-wire-snap {
          animation: workstation-wire-snap 360ms cubic-bezier(0.16, 0.84, 0.24, 1);
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
          0% { transform: scale(0.88); }
          65% { transform: scale(1.08); }
          100% { transform: scale(1); }
        }

        @keyframes workstation-board-surge {
          0% {
            box-shadow: 0 0 0 0 rgba(34, 211, 238, 0);
            transform: scale(1);
          }
          38% {
            box-shadow: 0 0 0 2px rgba(34, 211, 238, 0.75), 0 0 46px rgba(34, 211, 238, 0.55);
            transform: scale(1.006);
          }
          100% {
            box-shadow: 0 0 0 1px rgba(34, 211, 238, 0.45), 0 0 24px rgba(34, 211, 238, 0.24);
            transform: scale(1);
          }
        }

        @keyframes workstation-wire-flow {
          0% { stroke-dashoffset: 0; }
          100% { stroke-dashoffset: -64; }
        }

        @keyframes workstation-board-success {
          0% { box-shadow: 0 0 0 0 rgba(34, 197, 94, 0); }
          35% { box-shadow: 0 0 0 2px rgba(74, 222, 128, 0.55), 0 0 36px rgba(34, 197, 94, 0.35); }
          100% { box-shadow: 0 0 0 0 rgba(34, 197, 94, 0); }
        }

        @keyframes workstation-board-failure {
          0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
          30% { box-shadow: 0 0 0 2px rgba(248, 113, 113, 0.55), 0 0 34px rgba(239, 68, 68, 0.35); }
          100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
        }

        @keyframes workstation-shake {
          0%, 100% { transform: translateX(0); }
          20% { transform: translateX(-5px); }
          40% { transform: translateX(4px); }
          60% { transform: translateX(-3px); }
          80% { transform: translateX(2px); }
        }

        @keyframes workstation-wire-snap {
          0% { transform: scaleY(0.88) scaleX(0.98) translateY(0.5px); }
          42% { transform: scaleY(1.18) scaleX(1.03) translateY(-0.6px); }
          68% { transform: scaleY(0.95) scaleX(0.995) translateY(0.3px); }
          100% { transform: scaleY(1) scaleX(1) translateY(0); }
        }

        @keyframes workstation-component-surge {
          0%, 100% {
            box-shadow: 0 0 0 1px rgba(34, 211, 238, 0.35), 0 0 10px rgba(34, 211, 238, 0.22);
            transform: scale(1);
          }
          50% {
            box-shadow: 0 0 0 1px rgba(34, 211, 238, 0.9), 0 0 28px rgba(34, 211, 238, 0.5);
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
          0%, 100% {
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
            transform: translate(calc(-50% + var(--spark-dx)), calc(-50% + var(--spark-dy))) scale(0.2);
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
