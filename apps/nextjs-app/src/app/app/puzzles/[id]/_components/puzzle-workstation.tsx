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
import { CreatorCommentDialog } from '@/features/puzzles/components/creator-comment-dialog';
import { PuzzleDetailsDialog } from '@/features/puzzles/components/puzzle-details-dialog';
import { validateSolution } from '@/features/puzzles/api/validate-solution';
import { useUser } from '@/lib/auth';
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

const BASIC_COMPONENTS: CircuitComponent[] = [
  { id: 'AND', type: 'AND', cost: 1, pins: 3 },
  { id: 'OR', type: 'OR', cost: 1, pins: 3 },
  { id: 'NOT', type: 'NOT', cost: 1, pins: 2 },
  { id: 'XOR', type: 'XOR', cost: 1, pins: 3 },
  { id: 'NAND', type: 'NAND', cost: 1, pins: 3 },
  { id: 'DFF', type: 'DFF', cost: 1, pins: 2 },
];

const EMPTY_STRINGS: string[] = [];
const EMPTY_COMPONENTS: CircuitComponent[] = [];

type PostCheckState =
  | { open: false }
  | { open: true; solved: boolean; message: string };

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
  const [showCreatorComment, setShowCreatorComment] = useState(false);
  const [postCheck, setPostCheck] = useState<PostCheckState>({ open: false });
  const [isChecking, setIsChecking] = useState(false);
  const [isSolved, setIsSolved] = useState(false);
  const [connectivityIssues, setConnectivityIssues] = useState<string[] | null>(
    null,
  );

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
        size: { w: 4, h: 2 },
        ports: [
          { id: 'IN0', kind: 'input', offset: { row: 0, col: 0 } },
          { id: 'IN1', kind: 'input', offset: { row: 1, col: 0 } },
          { id: 'OUT0', kind: 'output', offset: { row: 0, col: 3 } },
        ],
      },
      OR: {
        size: { w: 4, h: 2 },
        ports: [
          { id: 'IN0', kind: 'input', offset: { row: 0, col: 0 } },
          { id: 'IN1', kind: 'input', offset: { row: 1, col: 0 } },
          { id: 'OUT0', kind: 'output', offset: { row: 0, col: 3 } },
        ],
      },
      XOR: {
        size: { w: 4, h: 2 },
        ports: [
          { id: 'IN0', kind: 'input', offset: { row: 0, col: 0 } },
          { id: 'IN1', kind: 'input', offset: { row: 1, col: 0 } },
          { id: 'OUT0', kind: 'output', offset: { row: 0, col: 3 } },
        ],
      },
      NAND: {
        size: { w: 4, h: 2 },
        ports: [
          { id: 'IN0', kind: 'input', offset: { row: 0, col: 0 } },
          { id: 'IN1', kind: 'input', offset: { row: 1, col: 0 } },
          { id: 'OUT0', kind: 'output', offset: { row: 0, col: 3 } },
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
      const hc = hardcoded[def.type];
      const size = hc?.size ?? {
        w: 4,
        h: Math.max(1, Math.min(4, Math.ceil(def.pins / 2))),
      };
      const ports = hc?.ports ?? toDefaultPorts(def.pins, size);
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

  // Load state
  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(STATE_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw) as any;
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
    } catch {
      // ignore
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [STATE_KEY, uiCatalog]);

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
    return <div className="text-sm text-gray-600">Loading…</div>;
  }

  if (!puzzle) {
    return (
      <div className="flex w-full flex-col gap-3">
        <div className="text-sm text-gray-600">Puzzle not found.</div>
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
          title: 'Budget exceeded',
          message: 'You cannot add components beyond the Budget limit.',
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
      setPostCheck({ open: true, solved: res.solved, message: res.message });

      if (res.solved) {
        setIsSolved(true);
        exportWorkingAreaJson();
        // Invalidate caches so the puzzles list shows "Solved" and XP bar updates
        await queryClient.invalidateQueries({ queryKey: ['puzzles'], refetchType: 'all' });
        await queryClient.invalidateQueries({ queryKey: ['user'], refetchType: 'all' });
      }
    } catch (e: any) {
      notifications.addNotification({
        type: 'error',
        title: 'Validation failed',
        message: e?.message ?? 'Something went wrong',
      });
    } finally {
      setIsChecking(false);
    }
  };

  const onExitWithoutSaving = () => {
    router.push(paths.app.puzzles.getHref());
  };

  const onSubmitAndExit = () => {
    router.push(paths.app.puzzles.getHref());
  };

  const visibleBasics = basicComponents;

  return (
    <div className="flex w-full flex-col gap-4">
      <div className="flex flex-col gap-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-semibold text-gray-900">
                {puzzle.title}
              </h1>
              {isSolved && (
                <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-3 py-1 text-sm font-semibold text-green-700">
                  <svg className="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12" /></svg>
                  Solved
                </span>
              )}
            </div>
            <div className="text-sm text-gray-600">
              by {puzzle.creator?.username ?? ''}
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <WorkstationTimer 
              timeLimitSeconds={puzzle.timeLimit ?? (puzzle as any).time_limit_seconds} 
            />
            <Button variant="outline" onClick={() => setShowPuzzleInfo(true)}>
              Puzzle Info
            </Button>
            <Button
              variant="outline"
              disabled={!puzzle.creatorComment}
              onClick={() => setShowCreatorComment(true)}
            >
              Creator Comment
            </Button>
            {/* Logic Constraint: Puzzle Rating */}
            <Button
              variant="outline"
              disabled={!isSolved}
              onClick={() => {
                notifications.addNotification({
                  type: 'info',
                  title: 'Rate Puzzle',
                  message: 'Rating functionality is not implemented yet.',
                });
              }}
            >
              Rate Puzzle
            </Button>
            <Button onClick={checkSolution} isLoading={isChecking}>
              Check Solution
            </Button>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-4 rounded-md border border-gray-300 bg-white p-3 text-sm text-gray-700">
          <div>
            <span className="font-medium">Budget:</span> {budgetLimit}
          </div>
          <div>
            <span className="font-medium">Tight Budget:</span> {tightBudget}
          </div>
          <div>
            <span className="font-medium">Current Cost:</span> {currentCost}
          </div>
          <div className="ml-auto flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2">
              <span className="font-medium">Inputs:</span>
              {inputs.map((i) => (
                <span
                  key={i}
                  className={
                    ioUsage.usedInputs.has(i)
                      ? 'rounded border border-green-200 bg-green-50 px-2 py-0.5 text-xs text-green-700'
                      : 'rounded border border-gray-200 bg-gray-50 px-2 py-0.5 text-xs text-gray-600'
                  }
                >
                  {i}
                </span>
              ))}
            </div>
            <div className="flex items-center gap-2">
              <span className="font-medium">Outputs:</span>
              {outputs.map((o) => (
                <span
                  key={o}
                  className={
                    ioUsage.usedOutputs.has(o)
                      ? 'rounded border border-green-200 bg-green-50 px-2 py-0.5 text-xs text-green-700'
                      : 'rounded border border-gray-200 bg-gray-50 px-2 py-0.5 text-xs text-gray-600'
                  }
                >
                  {o}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="grid w-full grid-cols-1 gap-4 lg:grid-cols-[280px_1fr_320px]">
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
          <div className="rounded-md border border-gray-300 bg-white p-3">
            <div className="mb-2 text-sm font-medium text-gray-900">
              Debugger
            </div>
            <div className="text-xs text-gray-600">
              This debugger shows wiring and IO usage. Backend validation runs
              creator test-cases.
            </div>
            <div className="mt-3">
              <div className="mb-2 text-xs font-medium text-gray-700">
                Wires
              </div>
              {wires.length === 0 ? (
                <div className="text-xs text-gray-500">No wires yet.</div>
              ) : (
                <ul className="space-y-2">
                  {wires.map((w) => (
                    <li
                      key={w.id}
                      className="group flex items-center justify-between gap-2 rounded border border-gray-200 bg-gray-50 px-2 py-1"
                    >
                      <span className="truncate text-xs text-gray-700">
                        {w.from.componentId} ({w.from.portId}) →{' '}
                        {w.to.componentId} ({w.to.portId})
                      </span>
                      <button
                        type="button"
                        className="hidden text-gray-400 hover:text-red-600 group-hover:block"
                        onClick={() =>
                          setWires((prev) => prev.filter((x) => x.id !== w.id))
                        }
                        title="Delete wire"
                      >
                        <svg
                          viewBox="0 0 24 24"
                          className="size-4"
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

          <div className="rounded-md border border-gray-300 bg-white p-3">
            <div className="mb-2 text-sm font-medium text-gray-900">
              Session
            </div>
            <div className="text-xs text-gray-600">
              Signed in as {user.data?.email ?? 'Unknown'}
            </div>
            <Button
              variant="outline"
              className="mt-3 w-full"
              onClick={onExitWithoutSaving}
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
          <div className="space-y-3 text-sm text-gray-700">
            <div>
              <div className="font-medium text-gray-900">Description</div>
              <div className="mt-1 whitespace-pre-wrap">
                {puzzle.description}
              </div>
            </div>
            {puzzle.creatorComment ? (
              <div>
                <div className="font-medium text-gray-900">Creator comment</div>
                <div className="mt-1 whitespace-pre-wrap">
                  {puzzle.creatorComment}
                </div>
              </div>
            ) : null}

            {/* Special instructions for Binary Adder puzzle */}
            {puzzle?.title?.toLowerCase().includes('binary adder') && (
              <div className="mt-4 rounded-lg border border-blue-200 bg-blue-50 p-4">
                <div className="font-medium text-blue-900 mb-2">Binary Adder Instructions</div>
                <div className="text-blue-800 text-sm space-y-2">
                  <p>
                    Design a <strong>full adder</strong> circuit that adds three binary digits:
                    two input bits (A and B) and a carry-in bit (C_in).
                  </p>

                  <div>
                    <div className="font-medium mb-1">Truth Table:</div>
                    <div className="overflow-x-auto">
                      <table className="min-w-full text-xs border border-blue-300">
                        <thead>
                          <tr className="bg-blue-100">
                            <th className="border border-blue-300 px-2 py-1">A</th>
                            <th className="border border-blue-300 px-2 py-1">B</th>
                            <th className="border border-blue-300 px-2 py-1">C_in</th>
                            <th className="border border-blue-300 px-2 py-1">S</th>
                            <th className="border border-blue-300 px-2 py-1">C_out</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr><td className="border border-blue-300 px-2 py-1 text-center">0</td><td className="border border-blue-300 px-2 py-1 text-center">0</td><td className="border border-blue-300 px-2 py-1 text-center">0</td><td className="border border-blue-300 px-2 py-1 text-center">0</td><td className="border border-blue-300 px-2 py-1 text-center">0</td></tr>
                          <tr><td className="border border-blue-300 px-2 py-1 text-center">0</td><td className="border border-blue-300 px-2 py-1 text-center">0</td><td className="border border-blue-300 px-2 py-1 text-center">1</td><td className="border border-blue-300 px-2 py-1 text-center">1</td><td className="border border-blue-300 px-2 py-1 text-center">0</td></tr>
                          <tr><td className="border border-blue-300 px-2 py-1 text-center">0</td><td className="border border-blue-300 px-2 py-1 text-center">1</td><td className="border border-blue-300 px-2 py-1 text-center">0</td><td className="border border-blue-300 px-2 py-1 text-center">1</td><td className="border border-blue-300 px-2 py-1 text-center">0</td></tr>
                          <tr><td className="border border-blue-300 px-2 py-1 text-center">0</td><td className="border border-blue-300 px-2 py-1 text-center">1</td><td className="border border-blue-300 px-2 py-1 text-center">1</td><td className="border border-blue-300 px-2 py-1 text-center">0</td><td className="border border-blue-300 px-2 py-1 text-center">1</td></tr>
                          <tr><td className="border border-blue-300 px-2 py-1 text-center">1</td><td className="border border-blue-300 px-2 py-1 text-center">0</td><td className="border border-blue-300 px-2 py-1 text-center">0</td><td className="border border-blue-300 px-2 py-1 text-center">1</td><td className="border border-blue-300 px-2 py-1 text-center">0</td></tr>
                          <tr><td className="border border-blue-300 px-2 py-1 text-center">1</td><td className="border border-blue-300 px-2 py-1 text-center">0</td><td className="border border-blue-300 px-2 py-1 text-center">1</td><td className="border border-blue-300 px-2 py-1 text-center">0</td><td className="border border-blue-300 px-2 py-1 text-center">1</td></tr>
                          <tr><td className="border border-blue-300 px-2 py-1 text-center">1</td><td className="border border-blue-300 px-2 py-1 text-center">1</td><td className="border border-blue-300 px-2 py-1 text-center">0</td><td className="border border-blue-300 px-2 py-1 text-center">0</td><td className="border border-blue-300 px-2 py-1 text-center">1</td></tr>
                          <tr><td className="border border-blue-300 px-2 py-1 text-center">1</td><td className="border border-blue-300 px-2 py-1 text-center">1</td><td className="border border-blue-300 px-2 py-1 text-center">1</td><td className="border border-blue-300 px-2 py-1 text-center">1</td><td className="border border-blue-300 px-2 py-1 text-center">1</td></tr>
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

                  <div className="bg-yellow-100 border border-yellow-300 rounded p-2 mt-2">
                    <div className="font-medium text-yellow-800 mb-1">💡 Hint:</div>
                    <p className="text-yellow-700 text-xs">
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

      <CreatorCommentDialog
        puzzle={puzzle}
        open={showCreatorComment}
        onOpenChange={setShowCreatorComment}
        showLink={false}
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
            className={cn('max-h-[50vh] overflow-auto text-sm text-gray-700')}
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
        onOpenChange={(open) =>
          setPostCheck(open ? postCheck : ({ open: false } as PostCheckState))
        }
      >
        <DialogContent className="max-w-[90vw] sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>
              {postCheck.open && postCheck.solved
                ? 'Puzzle solved'
                : 'Failed to solve'}
            </DialogTitle>
            <div className="mt-2 max-h-[200px] w-full overflow-y-auto rounded bg-gray-50 p-2 text-sm text-gray-700">
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
          <div className="max-h-[60vh] overflow-y-auto break-words text-sm text-gray-700">
            {postCheck.open && postCheck.solved ? (
              <div>
                Congrats! Time, cost, and other stats can be shown here.
              </div>
            ) : (
              <div>
                Your circuit did not pass the test cases. Try adjusting your
                wiring/components.
              </div>
            )}
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setPostCheck({ open: false })}
            >
              Return to puzzle
            </Button>
            <Button
              onClick={onSubmitAndExit}
              disabled={!postCheck.open || !postCheck.solved}
            >
              Submit solution and exit
            </Button>
            <Button variant="ghost" onClick={onExitWithoutSaving}>
              Exit without saving
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};
