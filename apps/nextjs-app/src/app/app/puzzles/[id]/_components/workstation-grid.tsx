'use client';

import type {
  DragEvent as ReactDragEvent,
  PointerEvent as ReactPointerEvent,
  WheelEvent as ReactWheelEvent,
} from 'react';
import { useEffect, useMemo, useRef, useState } from 'react';

import { Button } from '@/components/ui/button';
import { useNotifications } from '@/components/ui/notifications';
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

const GRID_ROWS = 15;
const GRID_COLS = 30;
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
}) => {
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
            rect.width / ((GRID_COLS + 4) * CELL_PX),
            rect.height / ((GRID_ROWS + 4) * CELL_PX),
          );
          setZoom(fit);
        }
      }
      // Pan is set in the other useEffect
    } catch {
      // ignore
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [STORAGE_KEY]);

  useEffect(() => {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ zoom }));
    } catch {
      // ignore
    }
  }, [STORAGE_KEY, zoom]);

  // Compute minZoom so the entire grid fits; set as default if no saved state.
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const updateFit = () => {
      const rect = el.getBoundingClientRect();
      // Account for IO ports: Inputs at col -1, Outputs at row GRID_ROWS.
      // We want to see from col -2 to GRID_COLS + 1, and row -1 to GRID_ROWS + 2.
      const fit = Math.min(
        rect.width / ((GRID_COLS + 4) * CELL_PX),
        rect.height / ((GRID_ROWS + 4) * CELL_PX),
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
  }, [STORAGE_KEY]);

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

    const c0 = clamp(Math.floor(topLeft.col) - 2, 0, GRID_COLS - 1);
    const r0 = clamp(Math.floor(topLeft.row) - 2, 0, GRID_ROWS - 1);
    const c1 = clamp(Math.ceil(bottomRight.col) + 2, 0, GRID_COLS - 1);
    const r1 = clamp(Math.ceil(bottomRight.row) + 2, 0, GRID_ROWS - 1);

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
    if (origin.row + size.h > GRID_ROWS) return false;
    if (origin.col + size.w > GRID_COLS) return false;

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

    onPlacedChange(
      placed.concat({
        id: `${componentId}:${Date.now()}`,
        componentId,
        origin,
        rotation,
      }),
    );
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
      const row = Math.min(i * 0.8, GRID_ROWS - 1); // Reduced spacing: 0.8 rows per input
      const anchor = toScreenCenter(row, -1); // just left of col 0
      inputsPos[id] = { x: anchor.x, y: anchor.y };
    }

    for (let i = 0; i < outputs.length; i++) {
      const id = `IO:OUT:${outputs[i]}`;
      // Distribute along the bottom (Layout Update: Outputs to Bottom)
      const colStep = GRID_COLS / (outputs.length + 1);
      // Center based on step
      const col = (i + 1) * colStep - 0.5;
      const row = GRID_ROWS + 0.5;
      const anchor = toScreenCenter(row, col);
      outputsPos[id] = { x: anchor.x, y: anchor.y };
    }

    return { inputs: inputsPos, outputs: outputsPos };
  }, [inputs, outputs, pan.x, pan.y, zoom]);

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
      const gridWidthPx = (GRID_COLS + 1) * CELL_PX * nextZoom;
      const gridHeightPx = (GRID_ROWS + 1) * CELL_PX * nextZoom;
      
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
      const gridWidthPx = (GRID_COLS + 1) * CELL_PX * zoom;
      const gridHeightPx = (GRID_ROWS + 1) * CELL_PX * zoom;
      
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

  const removeWire = (wireId: string) => {
    onWiresChange(wires.filter((w) => w.id !== wireId));
    setSelectedEntity({ type: 'none' });
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
          className="h-7 px-2"
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

  return (
    <div className="flex flex-col gap-2">
      <div className="rounded-md border border-gray-300 bg-white p-3">
        <div className="mb-1 text-sm font-medium text-gray-900">
          Working Area
        </div>
        <div className="text-xs text-gray-600">
          15×30 grid. Wheel to zoom. Drag background to pan. Click/drag ports to
          wire. While placing, press R to rotate.
        </div>
      </div>

      <div
        ref={containerRef}
        className="relative h-[calc(100vh-18rem)] overflow-hidden rounded-md border border-gray-300 bg-white"
        onWheel={onWheel}
        onPointerDown={onPointerDownBackground}
        onPointerMove={onPointerMoveBackground}
        onPointerUp={onPointerUpBackground}
        onDragOver={(e) => {
          e.preventDefault();
          if (!draggedPaletteComponentId) return;

          const el = containerRef.current;
          if (!el) return;
          const rect = el.getBoundingClientRect();
          const local = { x: e.clientX - rect.left, y: e.clientY - rect.top };
          const world = screenToWorld(local);
          const origin = {
            row: clamp(Math.floor(world.row), 0, GRID_ROWS - 1),
            col: clamp(Math.floor(world.col), 0, GRID_COLS - 1),
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
            row: clamp(Math.floor(world.row), 0, GRID_ROWS - 1),
            col: clamp(Math.floor(world.col), 0, GRID_COLS - 1),
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

            // Visual Feature: Dynamic Wire Coloring
            const strokeColor = isSelected ? '#2563eb' : getWireColor(w.id);

            return (
              <g key={w.id}>
                <line
                  className="pointer-events-auto cursor-pointer"
                  x1={a.x}
                  y1={a.y}
                  x2={b.x}
                  y2={b.y}
                  stroke={strokeColor}
                  strokeWidth={isSelected ? 3 : 2}
                  onPointerDown={(e) => {
                    e.stopPropagation();
                    setSelectedEntity({ type: 'wire', wireId: w.id });
                  }}
                  onPointerUp={(e) => {
                    e.stopPropagation();
                    if (isOverTrash(e.clientX, e.clientY)) removeWire(w.id);
                  }}
                />
              </g>
            );
          })}

          {wireDraft ? (
            <line
              x1={getPortScreenPoint(wireDraft.start, ioLayout).x}
              y1={getPortScreenPoint(wireDraft.start, ioLayout).y}
              x2={wireDraft.current.x}
              y2={wireDraft.current.y}
              stroke="#2563eb"
              strokeWidth={2}
              strokeDasharray="4 3"
            />
          ) : null}
        </svg>

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
          {placed.map((p) => {
            const def = catalog[p.componentId];
            const size = rotatedSize(def.size, p.rotation);

            const isDragging = draggedComponent?.placedId === p.id;
            const origin = isDragging ? draggedComponent.currentHole : p.origin;

            const left = origin.col * CELL_PX;
            const top = origin.row * CELL_PX;

            const isSelected =
              selectedEntity.type === 'component' &&
              selectedEntity.placedId === p.id;

            return (
              <div
                key={p.id}
                className={cn(
                  'group absolute rounded border bg-gray-50 text-[10px] text-gray-800',
                  isSelected
                    ? 'border-blue-400 ring-2 ring-blue-200'
                    : 'border-gray-300',
                  isDragging ? 'z-50 opacity-80 shadow-xl' : 'z-10',
                )}
                style={{
                  left,
                  top,
                  width: size.w * CELL_PX - 2,
                  height: size.h * CELL_PX - 2,
                  cursor: isDragging ? 'grabbing' : 'grab',
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
                    className="absolute -top-2 left-1/2 z-50 flex size-5 -translate-x-1/2 items-center justify-center rounded-full bg-white text-red-600 shadow-sm ring-1 ring-gray-200 hover:bg-red-50"
                    onPointerDown={(e) => e.stopPropagation()}
                    onClick={(e) => {
                      e.stopPropagation();
                      removeComponent(p.id);
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

                  return (
                    <button
                      type="button"
                      key={port.id}
                      className={cn(
                        'absolute flex items-center justify-center rounded-full border transition-transform hover:scale-150',
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
                        // We handle wiring in onPointerUp.
                        // If we let this propagate, the grid hole click handler might run?
                        // No, we stop propagation.
                        // We do NOT want to run onClickHole here because it might restart the wire draft
                        // immediately after onPointerUp finished it.
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
          {inputs.map((label) => {
            const id = `IO:IN:${label}`;
            const pt = ioLayout.inputs[id];
            if (!pt) return null;
            return (
              <button
                type="button"
                key={id}
                className="pointer-events-auto absolute flex items-center gap-2 rounded border border-green-300 bg-green-50 px-2 py-1 text-xs text-green-700 transition-transform hover:scale-125"
                style={{
                  left: pt.x,
                  top: pt.y,
                  transform: 'translate(-100%, -50%)',
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
      </div>
    </div>
  );
};
