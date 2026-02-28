'use client';

import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';

import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { useNotifications } from '@/components/ui/notifications';
import { paths } from '@/config/paths';
import { usePuzzle } from '@/features/puzzles/api/get-puzzle';
import { PuzzleDetailsDialog } from '@/features/puzzles/components/puzzle-details-dialog';
import { validateSolution } from '@/features/puzzles/api/validate-solution';
import { useUser } from '@/lib/auth';
import { api } from '@/lib/api-client';
import { CircuitComponent, CircuitSolution, Wire } from '@/types/api';
import { cn } from '@/utils/cn';

import {
  WorkstationGrid,
  type ComponentDef,
  type PlacedGridComponent,
  type SelectedComponentState,
} from './workstation-grid';
import { WorkstationMenu } from './workstation-menu';
import { WorkstationTimer } from './workstation-timer';
import { CircuitDebugger } from '@/components/circuit-debugger';

const BASIC_COMPONENTS: CircuitComponent[] = [
  { id: 'AND', type: 'AND', cost: 1, pins: 3 },
  { id: 'OR', type: 'OR', cost: 1, pins: 3 },
  { id: 'NOT', type: 'NOT', cost: 1, pins: 2 },
  { id: 'XOR', type: 'XOR', cost: 1, pins: 3 },
  { id: 'NAND', type: 'NAND', cost: 1, pins: 3 },
  { id: 'NOR', type: 'NOR', cost: 1, pins: 3 },
  { id: 'XNOR', type: 'XNOR', cost: 1, pins: 3 },
  { id: 'DFF', type: 'DFF', cost: 1, pins: 2 },
];

const EMPTY_STRINGS: string[] = [];
const EMPTY_COMPONENTS: CircuitComponent[] = [];

type PostCheckState =
  | { open: false }
  | { open: true; solved: boolean; message: string; medal?: string };

export const PuzzleWorkstation = ({ puzzleId }: { puzzleId: string }) => {
  const router = useRouter();
  const user = useUser();
  const startTime = useRef(Date.now());
  const queryClient = useQueryClient();

  const puzzleQuery = usePuzzle({ id: puzzleId });
  const puzzle = puzzleQuery.data;

  const [placed, setPlaced] = useState<PlacedGridComponent[]>([]);
  const [wires, setWires] = useState<Wire[]>([]);
  const [selectedComponent, setSelectedComponent] =
    useState<SelectedComponentState>({ mode: 'none' });
  // Feature: Drag-and-Drop Ghost/Preview
  const [draggedPaletteComponentId, setDraggedPaletteComponentId] = useState<string | null>(null);

  const [showPuzzleInfo, setShowPuzzleInfo] = useState(false);
  const [showDebugger, setShowDebugger] = useState(false);
  const [postCheck, setPostCheck] = useState<PostCheckState>({ open: false });
  const [isChecking, setIsChecking] = useState(false);
  const [isSolved, setIsSolved] = useState(false);
  const [connectivityIssues, setConnectivityIssues] = useState<string[] | null>(
    null,
  );

  // Draft version tracking for optimistic concurrency control
  const draftUpdatedAtRef = useRef<number | null>(null);

  // Sync isSolved from API data (so page refresh preserves solved state)
  useEffect(() => {
    if (puzzle?.is_solved) {
      setIsSolved(true);
    }
  }, [puzzle?.is_solved]);

  const notifications = useNotifications();

  const inputs = puzzle?.inputs ?? EMPTY_STRINGS;
  const outputs = puzzle?.outputs ?? EMPTY_STRINGS;

  const budgetLimit = puzzle?.budgetLimit ?? 0;
  const tightBudget = Math.ceil((puzzle?.budgetLimit ?? 0) * 1.25);

  const allowedGates = useMemo(() => {
    // Whitelist approach: if defaultGateSet is provided, use it.
    if (puzzle?.defaultGateSet && puzzle.defaultGateSet.length > 0) {
      return new Set(puzzle.defaultGateSet);
    }
    // Fallback to blacklist approach
    // If no blacklist provided, everything is allowed (empty set of blocked).
    const blocked = new Set(puzzle?.filteredBasicComponents ?? EMPTY_STRINGS);
    const allTypes = BASIC_COMPONENTS.map((c) => c.type);
    return new Set(allTypes.filter((t) => !blocked.has(t)));
  }, [puzzle?.defaultGateSet, puzzle?.filteredBasicComponents]);

  const specialComponents = useMemo(() => {
    return puzzle?.specialComponents ?? EMPTY_COMPONENTS;
  }, [puzzle?.specialComponents]);

  const allowArsenal = puzzle?.allowArsenal ?? true;

  const basicComponents = useMemo(() => {
    return BASIC_COMPONENTS.filter((c) => allowedGates.has(c.type));
  }, [allowedGates]);

  const filteredBasicTypes = useMemo(() => {
    // WorkstationMenu expects a blacklist (to hide/dim items).
    // We calculate it as ALL_BASIC - ALLOWED.
    const all = new Set(BASIC_COMPONENTS.map(c => c.type));
    return Array.from(all).filter(t => !allowedGates.has(t));
  }, [allowedGates]);

  const componentCatalog = useMemo(() => {
    const byId = new Map<string, CircuitComponent>();
    for (const c of basicComponents) byId.set(c.id, c);
    for (const c of specialComponents) byId.set(c.id, c);
    return byId;
  }, [basicComponents, specialComponents]);

  const uiCatalog = useMemo(() => {
    const toDefaultPorts = (pins: number, size: { w: number; h: number }) => {
      // Default: 1 output, remaining are inputs.
      const outputsCount = 1;
      const inputsCount = Math.max(1, pins - outputsCount);

      const ports: Array<{
        id: string;
        kind: 'input' | 'output';
        offset: { row: number; col: number };
      }> = [];

      // inputs along left edge
      for (let i = 0; i < inputsCount; i++) {
        ports.push({
          id: `IN${i}`,
          kind: 'input',
          offset: { row: Math.min(i, size.h - 1), col: 0 },
        });
      }

      // outputs along right edge
      for (let i = 0; i < outputsCount; i++) {
        ports.push({
          id: `OUT${i}`,
          kind: 'output',
          offset: { row: 0, col: Math.max(0, size.w - 1) },
        });
      }

      // Ensure unique hole offsets.
      const seen = new Set<string>();
      return ports.filter((p) => {
        const k = `${p.offset.row}:${p.offset.col}`;
        if (seen.has(k)) return false;
        seen.add(k);
        return true;
      });
    };

    const hardcoded: Record<
      string,
      { size: { w: number; h: number }; ports: ComponentDef['ports'] }
    > = {
      AND: {
        size: { w: 3, h: 2 },
        ports: [
          { id: 'IN0', kind: 'input', offset: { row: 0, col: 0 } },
          { id: 'IN1', kind: 'input', offset: { row: 1, col: 0 } },
          { id: 'OUT0', kind: 'output', offset: { row: 0, col: 2 } },
        ],
      },
      OR: {
        size: { w: 3, h: 2 },
        ports: [
          { id: 'IN0', kind: 'input', offset: { row: 0, col: 0 } },
          { id: 'IN1', kind: 'input', offset: { row: 1, col: 0 } },
          { id: 'OUT0', kind: 'output', offset: { row: 0, col: 2 } },
        ],
      },
      XOR: {
        size: { w: 3, h: 2 },
        ports: [
          { id: 'IN0', kind: 'input', offset: { row: 0, col: 0 } },
          { id: 'IN1', kind: 'input', offset: { row: 1, col: 0 } },
          { id: 'OUT0', kind: 'output', offset: { row: 0, col: 2 } },
        ],
      },
      NAND: {
        size: { w: 3, h: 2 },
        ports: [
          { id: 'IN0', kind: 'input', offset: { row: 0, col: 0 } },
          { id: 'IN1', kind: 'input', offset: { row: 1, col: 0 } },
          { id: 'OUT0', kind: 'output', offset: { row: 0, col: 2 } },
        ],
      },
      NOR: {
        size: { w: 3, h: 2 },
        ports: [
          { id: 'IN0', kind: 'input', offset: { row: 0, col: 0 } },
          { id: 'IN1', kind: 'input', offset: { row: 1, col: 0 } },
          { id: 'OUT0', kind: 'output', offset: { row: 0, col: 2 } },
        ],
      },
      XNOR: {
        size: { w: 3, h: 2 },
        ports: [
          { id: 'IN0', kind: 'input', offset: { row: 0, col: 0 } },
          { id: 'IN1', kind: 'input', offset: { row: 1, col: 0 } },
          { id: 'OUT0', kind: 'output', offset: { row: 0, col: 2 } },
        ],
      },
      NOT: {
        size: { w: 3, h: 1 },
        ports: [
          { id: 'IN0', kind: 'input', offset: { row: 0, col: 0 } },
          { id: 'OUT0', kind: 'output', offset: { row: 0, col: 2 } },
        ],
      },
      DFF: {
        size: { w: 3, h: 1 },
        ports: [
          { id: 'IN0', kind: 'input', offset: { row: 0, col: 0 } },
          { id: 'OUT0', kind: 'output', offset: { row: 0, col: 2 } },
        ],
      },
    };

    const ui = new Map<string, ComponentDef>();
    for (const [id, def] of componentCatalog.entries()) {
      // Arsenal pieces have custom sizing: width 4, height = max(inputs, outputs)
      const isArsenal = (def as any).is_arsenal === true;
      
      let size: { w: number; h: number };
      let ports: ComponentDef['ports'];
      
      if (isArsenal) {
        // Arsenal piece sizing: width=3 (fixed), height=max(inputs, outputs)
        const num_inputs = (def as any).num_inputs ?? 0;
        const num_outputs = (def as any).num_outputs ?? 0;
        
        // If inputs or outputs are 0, fall back to pins-based calculation
        if (num_inputs > 0 && num_outputs > 0) {
          size = {
            h: Math.max(num_inputs, num_outputs),
            w: 3,
          };
          
          // Generate ports for arsenal pieces
          ports = [];
          
          // Place inputs on the left (col 0), distributed vertically
          for (let i = 0; i < num_inputs; i++) {
            ports.push({
              id: `IN${i}`,
              kind: 'input',
              offset: { row: i, col: 0 },
            });
          }
          
          // Place outputs on the right (col = width - 1), distributed vertically
          for (let i = 0; i < num_outputs; i++) {
            ports.push({
              id: `OUT${i}`,
              kind: 'output',
              offset: { row: i, col: size.w - 1 },
            });
          }
        } else {
          // Fallback: use pins to estimate size
          size = {
            w: 3,
            h: Math.max(1, Math.min(4, Math.ceil(def.pins / 2))),
          };
          ports = toDefaultPorts(def.pins, size);
        }
      } else {
        // Basic component sizing (hardcoded or dynamic)
        const hc = hardcoded[def.type];
        size = hc?.size ?? {
          w: 4,
          h: Math.max(1, Math.min(4, Math.ceil(def.pins / 2))),
        };
        ports = (hardcoded[def.type]?.ports) ?? toDefaultPorts(def.pins, size);
      }
      
      ui.set(id, {
        id,
        label: def.type,
        cost: def.cost,
        size,
        ports,
      });
    }
    return Object.fromEntries(Array.from(ui.entries())) as Record<
      string,
      ComponentDef
    >;
  }, [componentCatalog]);

  const currentCost = useMemo(() => {
    return placed.reduce((acc, p) => {
      const def = componentCatalog.get(p.componentId);
      return acc + (def?.cost ?? 0);
    }, 0);
  }, [componentCatalog, placed]);

  const canAddCost = (extraCost: number) => {
    return currentCost + extraCost <= budgetLimit;
  };

  const ioUsage = useMemo(() => {
    const usedInputs = new Set<string>();
    const usedOutputs = new Set<string>();

    for (const w of wires) {
      if (w.from.componentId.startsWith('IO:IN:')) {
        usedInputs.add(w.from.componentId.replace('IO:IN:', ''));
      }
      if (w.to.componentId.startsWith('IO:IN:')) {
        usedInputs.add(w.to.componentId.replace('IO:IN:', ''));
      }
      if (w.from.componentId.startsWith('IO:OUT:')) {
        usedOutputs.add(w.from.componentId.replace('IO:OUT:', ''));
      }
      if (w.to.componentId.startsWith('IO:OUT:')) {
        usedOutputs.add(w.to.componentId.replace('IO:OUT:', ''));
      }
    }

    const missingInputs = inputs.filter((i) => !usedInputs.has(i));
    const missingOutputs = outputs.filter((o) => !usedOutputs.has(o));

    return {
      usedInputs,
      usedOutputs,
      missingInputs,
      missingOutputs,
    };
  }, [inputs, outputs, wires]);

  const STATE_KEY = `escapecircuit.workstation.state.v2:${puzzleId}`;

  const buildHoleState = useCallback(() => {
    const holes: Record<
      string,
      | { kind: 'empty' }
      | { kind: 'component'; placedId: string; componentId: string }
      | {
        kind: 'port';
        placedId: string;
        componentId: string;
        portIndex: number;
        portKind: 'input' | 'output';
      }
    > = {};

    const rotateOffset = (
      offset: { row: number; col: number },
      size: { w: number; h: number },
      rotation: 0 | 90,
    ) => {
      if (rotation === 0) return offset;
      return { row: offset.col, col: size.h - 1 - offset.row };
    };

    const rotatedSize = (size: { w: number; h: number }, rotation: 0 | 90) =>
      rotation === 0 ? size : { w: size.h, h: size.w };

    for (const inst of placed) {
      const def = uiCatalog[inst.componentId];
      if (!def) continue;

      const size = rotatedSize(def.size, inst.rotation);
      for (let r = 0; r < size.h; r++) {
        for (let c = 0; c < size.w; c++) {
          const key = `r${inst.origin.row + r}c${inst.origin.col + c}`;
          holes[key] = {
            kind: 'component',
            placedId: inst.id,
            componentId: inst.componentId,
          };
        }
      }

      def.ports.forEach((p, idx) => {
        const rot = rotateOffset(p.offset, def.size, inst.rotation);
        const key = `r${inst.origin.row + rot.row}c${inst.origin.col + rot.col}`;
        holes[key] = {
          kind: 'port',
          placedId: inst.id,
          componentId: inst.componentId,
          portIndex: idx,
          portKind: p.kind,
        };
      });
    }

    return holes;
  }, [placed, uiCatalog]);

  const applyParsedState = useCallback((parsed: any) => {
    if (Array.isArray(parsed?.placed)) setPlaced(parsed.placed);
    if (Array.isArray(parsed?.wires)) {
      const migratedWires = parsed.wires.map((w: any) => {
        const migrateEndpoint = (ep: any) => {
          if (ep.portId) return ep;
          if (ep.componentId.startsWith('IO:')) {
            return { ...ep, portId: 'P0' };
          }
          const placedInst = parsed.placed.find(
            (p: any) => p.id === ep.componentId,
          );
          if (!placedInst) return ep;
          const def = uiCatalog[placedInst.componentId];
          if (!def) return ep;
          const port = def.ports[ep.pinIndex];
          return { ...ep, portId: port?.id ?? `unknown-${ep.pinIndex}` };
        };
        return {
          ...w,
          from: migrateEndpoint(w.from),
          to: migrateEndpoint(w.to),
        };
      });
      setWires(migratedWires);
    }
  }, [uiCatalog]);

  // Load state: try backend first, fall back to localStorage
  useEffect(() => {
    let cancelled = false;

    const loadState = async () => {
      // Try backend draft first
      try {
        const draft = await api.get<{ state_json: string | null; updated_at: number | null }>(`/puzzles/${puzzleId}/draft`, {
          suppressErrorNotification: true,
        });
        if (!cancelled && draft.state_json) {
          const parsed = JSON.parse(draft.state_json);
          applyParsedState(parsed);
          draftUpdatedAtRef.current = draft.updated_at;
          return;
        }
      } catch {
        // Backend unavailable, fall through to localStorage
      }

      // Fall back to localStorage
      if (cancelled) return;
      try {
        const raw = window.localStorage.getItem(STATE_KEY);
        if (!raw) return;
        const parsed = JSON.parse(raw);
        applyParsedState(parsed);
      } catch {
        // ignore
      }
    };

    loadState();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [STATE_KEY, puzzleId, applyParsedState]);

  // Save to localStorage (immediate)
  useEffect(() => {
    try {
      window.localStorage.setItem(
        STATE_KEY,
        JSON.stringify({
          grid: { rows: 10, cols: 14 },
          placed,
          wires,
          holes: buildHoleState(),
        }),
      );
    } catch {
      // ignore
    }
  }, [STATE_KEY, placed, wires, buildHoleState]);

  // Auto-save to backend (debounced, 2s after last change)
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const initialLoadDone = useRef(false);

  useEffect(() => {
    // Skip the first render (initial load sets placed/wires)
    if (!initialLoadDone.current) {
      initialLoadDone.current = true;
      return;
    }

    if (saveTimerRef.current) clearTimeout(saveTimerRef.current);

    saveTimerRef.current = setTimeout(async () => {
      const stateJson = JSON.stringify({
        grid: { rows: 10, cols: 14 },
        placed,
        wires,
        holes: buildHoleState(),
      });
      try {
        const res = await api.put<{ ok: boolean; updated_at: number }>(
          `/puzzles/${puzzleId}/draft`,
          {
            state_json: stateJson,
            expected_updated_at: draftUpdatedAtRef.current,
          },
          { suppressErrorNotification: true },
        );
        // Track the new version for the next save
        draftUpdatedAtRef.current = res.updated_at;
      } catch (err: any) {
        if (err?.response?.status === 409) {
          notifications.addNotification({
            type: 'warning',
            title: 'Draft Conflict',
            message: 'Your draft was modified in another session. Reload to get the latest version.',
          });
        }
        // Other errors silently ignored — localStorage is the fallback
      }
    }, 2000);

    return () => {
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    };
  }, [placed, wires, puzzleId, buildHoleState]);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (selectedComponent.mode !== 'placing') return;
      if (e.key.toLowerCase() !== 'r') return;
      setSelectedComponent((prev) => {
        if (prev.mode !== 'placing') return prev;
        return { ...prev, rotation: prev.rotation === 0 ? 90 : 0 };
      });
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [selectedComponent.mode]);

  if (puzzleQuery.isLoading) {
    return <div className="text-[13px] text-muted-foreground">Loading…</div>;
  }

  if (!puzzle) {
    return (
      <div className="flex w-full flex-col gap-3">
        <div className="text-[13px] text-muted-foreground">Puzzle not found.</div>
        <Button
          variant="outline"
          onClick={() => router.push(paths.app.puzzles.getHref())}
        >
          Back to puzzles
        </Button>
      </div>
    );
  }

  const onPlacedChange = (next: PlacedGridComponent[]) => {
    // Budget guard: detect a new placement.
    if (next.length > placed.length) {
      const added = next[next.length - 1];
      const def = componentCatalog.get(added.componentId);
      if (def && !canAddCost(def.cost)) {
        notifications.addNotification({
          type: 'warning',
          title: 'Budget Limit Exceeded',
          message: `This component costs ${def.cost} but only ${budgetLimit - currentCost} budget remaining. Remove or replace existing components to stay within the limit.`,
        });
        return;
      }
    }
    setPlaced(next);
  };

  const buildSolution = (): CircuitSolution => {
    return {
      placedComponents: placed.map((p) => ({
        id: p.id,
        componentId: p.componentId,
        x: p.origin.col,
        y: p.origin.row,
      })),
      wires,
      totalCost: currentCost,
    };
  };

  const validateConnectivity = () => {
    const issues: string[] = [];

    const resolveKind = (
      ownerId: string,
      pinIndex: number,
    ): 'input' | 'output' | null => {
      if (ownerId.startsWith('IO:IN:')) return 'output';
      if (ownerId.startsWith('IO:OUT:')) return 'input';
      const inst = placed.find((p) => p.id === ownerId);
      if (!inst) return null;
      const def = uiCatalog[inst.componentId];
      const port = def?.ports?.[pinIndex];
      return port?.kind ?? null;
    };

    const portKey = (ownerId: string, pinIndex: number) =>
      `${ownerId}::${pinIndex}`;
    const counts = new Map<string, number>();

    for (const w of wires) {
      // owner existence check
      const fromKind = resolveKind(w.from.componentId, w.from.pinIndex);
      const toKind = resolveKind(w.to.componentId, w.to.pinIndex);
      if (!fromKind)
        issues.push(
          `Extra/invalid wire endpoint: ${w.from.componentId}#${w.from.pinIndex}`,
        );
      if (!toKind)
        issues.push(
          `Extra/invalid wire endpoint: ${w.to.componentId}#${w.to.pinIndex}`,
        );
      if (fromKind && toKind && (fromKind !== 'output' || toKind !== 'input')) {
        issues.push(
          `Invalid wire direction: ${w.from.componentId} → ${w.to.componentId}`,
        );
      }

      counts.set(
        portKey(w.from.componentId, w.from.pinIndex),
        (counts.get(portKey(w.from.componentId, w.from.pinIndex)) ?? 0) + 1,
      );
      counts.set(
        portKey(w.to.componentId, w.to.pinIndex),
        (counts.get(portKey(w.to.componentId, w.to.pinIndex)) ?? 0) + 1,
      );
    }

    for (const label of inputs) {
      const id = `IO:IN:${label}`;
      if ((counts.get(portKey(id, 0)) ?? 0) === 0)
        issues.push(`Missing puzzle input connection: ${label}`);
    }
    for (const label of outputs) {
      const id = `IO:OUT:${label}`;
      if ((counts.get(portKey(id, 0)) ?? 0) === 0)
        issues.push(`Missing puzzle output connection: ${label}`);
    }

    for (const inst of placed) {
      const def = uiCatalog[inst.componentId];
      const portCount = def?.ports?.length ?? 0;
      for (let idx = 0; idx < portCount; idx++) {
        if ((counts.get(portKey(inst.id, idx)) ?? 0) === 0) {
          issues.push(
            `Missing component port connection: ${inst.id} port #${idx}`,
          );
        }
      }
    }

    return issues;
  };

  const exportWorkingAreaJson = () => {
    const payload = {
      version: 1,
      grid: { rows: 10, cols: 14 },
      puzzle: { id: puzzle.id, inputs, outputs },
      placed,
      wires,
      holes: buildHoleState(),
      totalCost: currentCost,
    };

    const blob = new Blob([JSON.stringify(payload, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `puzzle-${puzzle.id}-circuit.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const checkSolution = async () => {
    const issues = validateConnectivity();
    if (issues.length) {
      setConnectivityIssues(issues);
      return;
    }

    setIsChecking(true);
    try {
      const timeTaken = Math.floor((Date.now() - startTime.current) / 1000);
      const res = await validateSolution({
        puzzleId: puzzle.id,
        solution: buildSolution(),
        timeTaken,
      });
      setPostCheck({ open: true, solved: res.solved, message: res.message, medal: res.medal });

      if (res.solved) {
        setIsSolved(true);
        // Invalidate caches so the puzzles list shows "Solved" and XP bar updates
        await queryClient.invalidateQueries({ queryKey: ['puzzles'], refetchType: 'all' });
        await queryClient.invalidateQueries({ queryKey: ['user'], refetchType: 'all' });
      }
    } catch (e: any) {
      let errorTitle = 'Validation Failed';
      let errorMessage = e?.message ?? 'Something went wrong';
      
      // Provide more specific error messages
      if (errorMessage.includes('Circuit cost') || errorMessage.includes('exceeds')) {
        errorTitle = 'Budget Exceeded';
        errorMessage = 'Your circuit exceeds the budget limit. Try removing some components or using less expensive alternatives.';
      } else if (errorMessage.includes('not found')) {
        errorTitle = 'Puzzle Not Found';
        errorMessage = 'This puzzle could not be found. Please refresh the page and try again.';
      } else if (errorMessage.includes('test case') || errorMessage.includes('test cases')) {
        errorTitle = 'Puzzle Test Cases Issue';
        errorMessage = 'This puzzle has no test cases configured. Please contact the puzzle creator.';
      }
      
      notifications.addNotification({
        type: 'error',
        title: errorTitle,
        message: errorMessage,
      });
    } finally {
      setIsChecking(false);
    }
  };

  const onSolveAgain = () => {
    // Reset all state for a fresh start
    setPlaced([]);
    setWires([]);
    setSelectedComponent({ mode: 'none' });
    setDraggedPaletteComponentId(null);
    setShowPuzzleInfo(false);
    setShowDebugger(false);
    setPostCheck({ open: false });
    setIsChecking(false);
    setIsSolved(false);
    setConnectivityIssues(null);
    startTime.current = Date.now();
    // Refresh the page to ensure clean state
    router.refresh();
  };

  const onBrowsePuzzles = () => {
    router.push(paths.app.puzzles.getHref());
  };

  const visibleBasics = basicComponents;

  return (
    <div className="flex w-full flex-col gap-4">
      <div className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-xl font-semibold tracking-tight text-foreground">
                {puzzle.title}
              </h1>
              {isSolved && (
                <span className="inline-flex items-center gap-1 rounded-md bg-emerald-50 px-2.5 py-0.5 text-[11px] font-medium text-emerald-700">
                  <svg className="size-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12" /></svg>
                  Solved
                </span>
              )}
            </div>
            <div className="text-[13px] text-muted-foreground">
              by {puzzle.creator?.username ?? ''}
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <WorkstationTimer
              timeLimitSeconds={puzzle.timeLimit ?? (puzzle as any).time_limit_seconds}
            />
            <Button variant="outline" onClick={() => setShowDebugger(true)}>
              Debug
            </Button>
            <Button variant="outline" onClick={() => setShowPuzzleInfo(true)}>
              Puzzle Info
            </Button>
            <Button onClick={checkSolution} isLoading={isChecking}>
              Check Solution
            </Button>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-4 rounded-lg border border-border bg-card p-3 text-[13px] text-foreground">
          <div>
            <span className="text-muted-foreground">Budget:</span> {budgetLimit}
          </div>
          <div>
            <span className="text-muted-foreground">Tight:</span> {tightBudget}
          </div>
          <div>
            <span className="text-muted-foreground">Cost:</span> {currentCost}
          </div>
          <div className="ml-auto flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-1.5">
              <span className="text-muted-foreground">Inputs:</span>
              {inputs.map((i) => (
                <span
                  key={i}
                  className={
                    ioUsage.usedInputs.has(i)
                      ? 'rounded-md border border-emerald-200/60 bg-emerald-50/50 px-2 py-0.5 text-[11px] font-medium text-emerald-700'
                      : 'rounded-md border border-border bg-secondary px-2 py-0.5 text-[11px] font-medium text-muted-foreground'
                  }
                >
                  {i}
                </span>
              ))}
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-muted-foreground">Outputs:</span>
              {outputs.map((o) => (
                <span
                  key={o}
                  className={
                    ioUsage.usedOutputs.has(o)
                      ? 'rounded-md border border-emerald-200/60 bg-emerald-50/50 px-2 py-0.5 text-[11px] font-medium text-emerald-700'
                      : 'rounded-md border border-border bg-secondary px-2 py-0.5 text-[11px] font-medium text-muted-foreground'
                  }
                >
                  {o}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="grid w-full grid-cols-1 gap-4 lg:grid-cols-[260px_1fr_280px]">
        <WorkstationMenu
          basic={visibleBasics}
          special={specialComponents}
          allowArsenal={allowArsenal}
          filteredBasicTypes={filteredBasicTypes}
          selectedComponentId={
            selectedComponent.mode === 'placing'
              ? selectedComponent.componentId
              : undefined
          }
          onSelectComponent={(componentId) =>
            setSelectedComponent({ mode: 'placing', componentId, rotation: 0 })
          }
          onDragStart={setDraggedPaletteComponentId}
          onDragEnd={() => setDraggedPaletteComponentId(null)}
        />

        <WorkstationGrid
          puzzleId={puzzle.id}
          inputs={inputs}
          outputs={outputs}
          catalog={uiCatalog}
          placed={placed}
          wires={wires}
          selectedComponent={selectedComponent}
          onSelectedComponentChange={setSelectedComponent}
          onPlacedChange={onPlacedChange}
          onWiresChange={setWires}
          draggedPaletteComponentId={draggedPaletteComponentId}
        />

        <div className="flex flex-col gap-3">
          <div className="rounded-lg border border-border bg-card p-3">
            <div className="mb-1.5 text-[13px] font-medium text-foreground">
              Debugger
            </div>
            <div className="text-[11px] text-muted-foreground">
              This debugger shows wiring and IO usage. Backend validation runs
              creator test-cases.
            </div>
            <div className="mt-3">
              <div className="mb-2 text-[11px] font-medium text-muted-foreground">
                Wires
              </div>
              {wires.length === 0 ? (
                <div className="text-[11px] text-muted-foreground/60">No wires yet.</div>
              ) : (
                <ul className="space-y-1.5">
                  {wires.map((w) => (
                    <li
                      key={w.id}
                      className="group flex items-center justify-between gap-2 rounded-md border border-border bg-secondary/50 px-2.5 py-1.5"
                    >
                      <span className="truncate text-[11px] text-foreground">
                        {w.from.componentId} ({w.from.portId}) →{' '}
                        {w.to.componentId} ({w.to.portId})
                      </span>
                      <button
                        type="button"
                        className="hidden text-muted-foreground hover:text-destructive group-hover:block"
                        onClick={() =>
                          setWires((prev) => prev.filter((x) => x.id !== w.id))
                        }
                        title="Delete wire"
                      >
                        <svg
                          viewBox="0 0 24 24"
                          className="size-3.5"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                        >
                          <path d="M3 6h18" />
                          <path d="M8 6V4h8v2" />
                          <path d="M6 6l1 16h10l1-16" />
                        </svg>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          <div className="rounded-lg border border-border bg-card p-3">
            <div className="mb-1.5 text-[13px] font-medium text-foreground">
              Session
            </div>
            <div className="text-[11px] text-muted-foreground">
              Signed in as {user.data?.email ?? 'Unknown'}
            </div>
            <Button
              variant="outline"
              className="mt-3 w-full"
              onClick={onBrowsePuzzles}
            >
              Exit Puzzle
            </Button>
          </div>
        </div>
      </div>

      <Dialog open={showPuzzleInfo} onOpenChange={setShowPuzzleInfo}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{puzzle.title}</DialogTitle>
            <DialogDescription>
              Puzzle description and creator comment.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3 text-[13px] text-foreground">
            <div>
              <div className="font-medium text-foreground">Description</div>
              <div className="mt-1 whitespace-pre-wrap text-muted-foreground">
                {puzzle.description}
              </div>
            </div>
            {puzzle.creatorComment ? (
              <div>
                <div className="font-medium text-foreground">Creator comment</div>
                <div className="mt-1 whitespace-pre-wrap text-muted-foreground">
                  {puzzle.creatorComment}
                </div>
              </div>
            ) : null}

            {/* Special instructions for Binary Adder puzzle */}
            {puzzle?.title?.toLowerCase().includes('binary adder') && (
              <div className="mt-4 rounded-lg border border-border bg-secondary/50 p-4">
                <div className="font-medium text-foreground mb-2">Binary Adder Instructions</div>
                <div className="text-foreground text-[13px] space-y-2">
                  <p>
                    Design a <strong>full adder</strong> circuit that adds three binary digits:
                    two input bits (A and B) and a carry-in bit (C_in).
                  </p>

                  <div>
                    <div className="font-medium mb-1">Truth Table:</div>
                    <div className="overflow-x-auto">
                      <table className="min-w-full text-xs border border-border">
                        <thead>
                          <tr className="bg-secondary">
                            <th className="border border-border px-2 py-1">A</th>
                            <th className="border border-border px-2 py-1">B</th>
                            <th className="border border-border px-2 py-1">C_in</th>
                            <th className="border border-border px-2 py-1">S</th>
                            <th className="border border-border px-2 py-1">C_out</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr><td className="border border-border px-2 py-1 text-center">0</td><td className="border border-border px-2 py-1 text-center">0</td><td className="border border-border px-2 py-1 text-center">0</td><td className="border border-border px-2 py-1 text-center">0</td><td className="border border-border px-2 py-1 text-center">0</td></tr>
                          <tr><td className="border border-border px-2 py-1 text-center">0</td><td className="border border-border px-2 py-1 text-center">0</td><td className="border border-border px-2 py-1 text-center">1</td><td className="border border-border px-2 py-1 text-center">1</td><td className="border border-border px-2 py-1 text-center">0</td></tr>
                          <tr><td className="border border-border px-2 py-1 text-center">0</td><td className="border border-border px-2 py-1 text-center">1</td><td className="border border-border px-2 py-1 text-center">0</td><td className="border border-border px-2 py-1 text-center">1</td><td className="border border-border px-2 py-1 text-center">0</td></tr>
                          <tr><td className="border border-border px-2 py-1 text-center">0</td><td className="border border-border px-2 py-1 text-center">1</td><td className="border border-border px-2 py-1 text-center">1</td><td className="border border-border px-2 py-1 text-center">0</td><td className="border border-border px-2 py-1 text-center">1</td></tr>
                          <tr><td className="border border-border px-2 py-1 text-center">1</td><td className="border border-border px-2 py-1 text-center">0</td><td className="border border-border px-2 py-1 text-center">0</td><td className="border border-border px-2 py-1 text-center">1</td><td className="border border-border px-2 py-1 text-center">0</td></tr>
                          <tr><td className="border border-border px-2 py-1 text-center">1</td><td className="border border-border px-2 py-1 text-center">0</td><td className="border border-border px-2 py-1 text-center">1</td><td className="border border-border px-2 py-1 text-center">0</td><td className="border border-border px-2 py-1 text-center">1</td></tr>
                          <tr><td className="border border-border px-2 py-1 text-center">1</td><td className="border border-border px-2 py-1 text-center">1</td><td className="border border-border px-2 py-1 text-center">0</td><td className="border border-border px-2 py-1 text-center">0</td><td className="border border-border px-2 py-1 text-center">1</td></tr>
                          <tr><td className="border border-border px-2 py-1 text-center">1</td><td className="border border-border px-2 py-1 text-center">1</td><td className="border border-border px-2 py-1 text-center">1</td><td className="border border-border px-2 py-1 text-center">1</td><td className="border border-border px-2 py-1 text-center">1</td></tr>
                        </tbody>
                      </table>
                    </div>
                  </div>

                  <div>
                    <div className="font-medium mb-1">Available Gates:</div>
                    <ul className="list-disc list-inside space-y-1">
                      <li><strong>AND</strong>: Outputs 1 only if both inputs are 1</li>
                      <li><strong>NAND</strong>: Outputs 0 only if both inputs are 1 (NOT of AND)</li>
                      <li><strong>DFF</strong>: Passes input signal unchanged with one-time-unit DFF</li>
                    </ul>
                  </div>

                  <div className="bg-amber-50/50 border border-amber-200/60 rounded-lg p-2.5 mt-2">
                    <div className="font-medium text-amber-800 mb-1">Hint:</div>
                    <p className="text-amber-700 text-xs">
                      NAND gates are universal - you can build any logic function with NAND gates.
                      Think about how to combine these gates to create XOR operations.
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowPuzzleInfo(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      <PuzzleDetailsDialog
        puzzle={puzzle}
        open={showPuzzleInfo}
        onOpenChange={setShowPuzzleInfo}
        showLink={false}
      />

      <CircuitDebugger
        isOpen={showDebugger}
        onClose={() => setShowDebugger(false)}
        inputs={inputs}
        outputs={outputs}
        placed={placed}
        wires={wires}
        catalog={uiCatalog}
        puzzleId={puzzleId}
      />

      <Dialog
        open={Boolean(connectivityIssues?.length)}
        onOpenChange={(open) => (open ? null : setConnectivityIssues(null))}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Cannot check circuit</DialogTitle>
            <DialogDescription>
              Some inputs/outputs are missing or extra. Fix these before
              checking.
            </DialogDescription>
          </DialogHeader>
          <div
            className={cn('max-h-[50vh] overflow-auto text-[13px] text-foreground')}
          >
            <ul className="list-disc space-y-1 pl-5">
              {(connectivityIssues ?? []).map((m, idx) => (
                <li key={`${idx}:${m}`}>{m}</li>
              ))}
            </ul>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setConnectivityIssues(null)}
            >
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={postCheck.open}
        onOpenChange={(open) => {
          setPostCheck(open ? postCheck : ({ open: false } as PostCheckState));
        }}
      >
        <DialogContent className="max-w-[90vw] sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>
              {postCheck.open && postCheck.solved
                ? 'Puzzle solved'
                : 'Failed to solve'}
            </DialogTitle>
            <div className="mt-2 max-h-[200px] w-full overflow-y-auto rounded-lg bg-secondary/50 p-3 text-[13px] text-foreground">
               <p className="whitespace-pre-wrap break-words">
                {postCheck.open ? postCheck.message : ''}
              </p>
            </div>
            {/* Hidden Description for accessibility but we render custom content above */}
            <DialogDescription className="sr-only">
              {postCheck.open ? postCheck.message : 'Solution check result'}
            </DialogDescription>
          </DialogHeader>
          {/* Visual Fix: Modal Text Overflow */}
          <div className="max-h-[60vh] overflow-y-auto break-words text-[13px] text-foreground">
            {postCheck.open && postCheck.solved ? (
              <div className="space-y-2">
                {postCheck.medal && postCheck.medal !== 'NONE' && (
                  <div className="flex items-center gap-2 text-lg font-semibold">
                    <span>
                      {postCheck.medal === 'GOLD' ? '🥇' : postCheck.medal === 'SILVER' ? '🥈' : '🥉'}
                    </span>
                    <span className={
                      postCheck.medal === 'GOLD' ? 'text-amber-500' :
                      postCheck.medal === 'SILVER' ? 'text-muted-foreground' :
                      'text-amber-700'
                    }>
                      {postCheck.medal} Medal
                    </span>
                  </div>
                )}
                <p>Congrats! Your solution passed all test cases.</p>
              </div>
            ) : (
              <div className="text-muted-foreground">
                Your circuit did not pass the test cases. Try adjusting your
                wiring/components.
              </div>
            )}
          </div>
          <DialogFooter>
            <Button
              onClick={onSolveAgain}
              disabled={!postCheck.open}
            >
              {postCheck.open && postCheck.solved ? 'Solve again' : 'Try again'}
            </Button>
            <Button
              onClick={onBrowsePuzzles}
              disabled={!postCheck.open}
            >
              Browse puzzles
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

    </div>
  );
};
