'use client';

import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import Confetti from 'react-confetti';

import { Button } from '@/components/ui/button';
import { useAudio } from '@/hooks/useAudio';
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
import { startPuzzleAttempt } from '@/features/puzzles/api/start-attempt';
import { CreatorCommentDialog } from '@/features/puzzles/components/creator-comment-dialog';
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
import { PuzzleXPBar } from '@/components/ui/puzzle-xp-bar';
import { PuzzleLeaderboard } from '@/features/puzzles/components/puzzle-leaderboard';
import { RatingDialog } from '@/features/ratings/components/rating-dialog';
import { InfoPopup } from '@/components/ui/info-popup';
import { ChevronDown } from 'lucide-react';

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
  | {
      open: true;
      solved: boolean;
      message: string;
      medal?: string;
      xpEarned?: number;
      puzzleTotalXP?: number;
      xpLeftForMax?: number;
    };

type BoardFeedbackState = 'idle' | 'success' | 'failure';

type VictoryFxState = {
  key: number;
  xp?: number;
  visible: boolean;
};

const wait = (ms: number) => new Promise((resolve) => window.setTimeout(resolve, ms));

export const PuzzleWorkstation = ({ puzzleId }: { puzzleId: string }) => {
  const router = useRouter();
  const user = useUser();
  const startTime = useRef(Date.now());
  const queryClient = useQueryClient();
  const { playError, playSuccess } = useAudio();

  const puzzleQuery = usePuzzle({ id: puzzleId });
  const puzzle = puzzleQuery.data;

  const [placed, setPlaced] = useState<PlacedGridComponent[]>([]);
  const [wires, setWires] = useState<Wire[]>([]);
  const [selectedComponent, setSelectedComponent] =
    useState<SelectedComponentState>({ mode: 'none' });
  // Feature: Drag-and-Drop Ghost/Preview
  const [draggedPaletteComponentId, setDraggedPaletteComponentId] = useState<string | null>(null);

  // Sandbox state
  const [sandboxPlaced, setSandboxPlaced] = useState<PlacedGridComponent[]>([]);
  const [sandboxWires, setSandboxWires] = useState<Wire[]>([]);
  const [sandboxSelectedComponent, setSandboxSelectedComponent] =
    useState<SelectedComponentState>({ mode: 'none' });
  const [sandboxDraggedPaletteComponentId, setSandboxDraggedPaletteComponentId] = useState<string | null>(null);
  const [showSandbox, setShowSandbox] = useState(false);
  const [sandboxNumInputs, setSandboxNumInputs] = useState(2);
  const [sandboxNumOutputs, setSandboxNumOutputs] = useState(1);
  const [showSandboxDebugger, setShowSandboxDebugger] = useState(false);

  const [showPuzzleInfo, setShowPuzzleInfo] = useState(false);
  const [showDebugger, setShowDebugger] = useState(false);
  const [showLeaderboard, setShowLeaderboard] = useState(false);
  const [showCreatorComment, setShowCreatorComment] = useState(false);
  const [showRating, setShowRating] = useState(false);
  const [postCheck, setPostCheck] = useState<PostCheckState>({ open: false });
  const [isChecking, setIsChecking] = useState(false);
  const [isSolved, setIsSolved] = useState(false);
  const [boardFeedback, setBoardFeedback] = useState<BoardFeedbackState>('idle');
  const [isPowerSurge, setIsPowerSurge] = useState(false);
  const [showSolvedSlam, setShowSolvedSlam] = useState(false);
  const [victoryFx, setVictoryFx] = useState<VictoryFxState>({
    key: 0,
    visible: false,
  });
  const [showFirstSolveCelebration, setShowFirstSolveCelebration] = useState(false);
  const [viewportSize, setViewportSize] = useState({ width: 0, height: 0 });
  const [typedInstructionText, setTypedInstructionText] = useState('');
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [connectivityIssues, setConnectivityIssues] = useState<string[] | null>(
    null,
  );

  // Sync isSolved from API data (so page refresh preserves solved state)
  useEffect(() => {
    if (puzzle?.is_solved) {
      setIsSolved(true);
    }
  }, [puzzle?.is_solved]);

  useEffect(() => {
    const tick = () => {
      setElapsedSeconds(Math.floor((Date.now() - startTime.current) / 1000));
    };

    tick();
    const intervalId = window.setInterval(tick, 1000);
    return () => window.clearInterval(intervalId);
  }, []);

  useEffect(() => {
    let cancelled = false;

    const startAttempt = async () => {
      try {
        if (!puzzle?.id) return;
        await startPuzzleAttempt({ puzzleId: puzzle.id });
      } catch {
        // Best-effort only: rating still falls back to client elapsed on submit.
      }
    };

    if (!cancelled) {
      startAttempt();
    }

    return () => {
      cancelled = true;
    };
  }, [puzzle?.id]);

  const notifications = useNotifications();

  const triggerVictoryFx = useCallback((xpEarned?: number) => {
    setVictoryFx({
      key: Date.now(),
      xp: xpEarned,
      visible: true,
    });

    window.setTimeout(() => {
      setVictoryFx((current) => ({ ...current, visible: false }));
    }, 1900);
  }, []);

  useEffect(() => {
    const updateViewport = () => {
      setViewportSize({
        width: window.innerWidth,
        height: window.innerHeight,
      });
    };

    updateViewport();
    window.addEventListener('resize', updateViewport);
    return () => window.removeEventListener('resize', updateViewport);
  }, []);

  const terminalInstructionText = useMemo(() => {
    const segments = [
      puzzle?.description?.trim(),
      puzzle?.creatorComment?.trim() ? `Creator comment: ${puzzle.creatorComment.trim()}` : '',
    ].filter(Boolean);

    return segments.join('\n\n');
  }, [puzzle?.description, puzzle?.creatorComment]);

  useEffect(() => {
    if (!showPuzzleInfo) return;

    setTypedInstructionText('');
    if (!terminalInstructionText) return;

    let index = 0;
    const tick = window.setInterval(() => {
      index += 1;
      setTypedInstructionText(terminalInstructionText.slice(0, index));
      if (index >= terminalInstructionText.length) {
        window.clearInterval(tick);
      }
    }, 14);

    return () => window.clearInterval(tick);
  }, [showPuzzleInfo, terminalInstructionText]);

  const inputs = puzzle?.inputs ?? EMPTY_STRINGS;
  const outputs = puzzle?.outputs ?? EMPTY_STRINGS;

  const budgetLimit = puzzle?.budgetLimit ?? 0;
  const creatorBudget = puzzle?.creatorBudget ?? null;

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

  const allowArsenal = puzzle?.allowArsenal ?? true;

  const customComponents = useMemo(() => {
    // Custom pieces are always available
    return puzzle?.customComponents ?? EMPTY_COMPONENTS;
  }, [puzzle?.customComponents]);

  const arsenalComponents = useMemo(() => {
    // Arsenal pieces only show if allowArsenal is true
    if (!allowArsenal) {
      return EMPTY_COMPONENTS;
    }
    return puzzle?.arsenalComponents ?? EMPTY_COMPONENTS;
  }, [puzzle?.arsenalComponents, allowArsenal]);

  const specialComponents = useMemo(() => {
    // For backward compatibility with componentCatalog
    return [...customComponents, ...arsenalComponents];
  }, [customComponents, arsenalComponents]);

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

  // Keep a ref to applyParsedState so the load-state effect doesn't re-run
  // every time uiCatalog changes (which would reset the board from localStorage).
  const applyParsedStateRef = useRef(applyParsedState);
  useEffect(() => {
    applyParsedStateRef.current = applyParsedState;
  }, [applyParsedState]);

  // Load state from localStorage
  useEffect(() => {
    let cancelled = false;

    const loadState = async () => {
      // Load from localStorage
      if (cancelled) return;
      try {
        const raw = window.localStorage.getItem(STATE_KEY);
        if (!raw) return;
        const parsed = JSON.parse(raw);
        applyParsedStateRef.current(parsed);
      } catch {
        // ignore
      }
    };

    loadState();
    return () => { cancelled = true; };
  }, [STATE_KEY, puzzleId]);

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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [STATE_KEY, placed, wires]);

  const ratingMinAttemptSeconds = puzzle?.rating_min_attempt_seconds;
  const hasAttemptedMinTime = ratingMinAttemptSeconds != null
    ? elapsedSeconds >= ratingMinAttemptSeconds
    : false;
  const canRatePuzzle = Boolean(puzzle?.can_rate) || isSolved || hasAttemptedMinTime;

  useEffect(() => {
    if (!puzzle?.id) return;
    if (!hasAttemptedMinTime) return;
    if (puzzle.can_rate) return;

    // Refresh cached puzzle/list data once threshold is reached so rating
    // options update without a manual page reload.
    queryClient.invalidateQueries({ queryKey: ['puzzle', { id: puzzle.id }], refetchType: 'active' });
    queryClient.invalidateQueries({ queryKey: ['puzzles'], refetchType: 'active' });
  }, [hasAttemptedMinTime, puzzle?.id, puzzle?.can_rate, queryClient]);

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

    setIsPowerSurge(true);
    setIsChecking(true);
    try {
      const timeTaken = Math.floor((Date.now() - startTime.current) / 1000);
      await wait(600);
      const res = await validateSolution({
        puzzleId: puzzle.id,
        solution: buildSolution(),
        timeTaken,
      });

      setIsPowerSurge(false);

      setBoardFeedback(res.solved ? 'success' : 'failure');
      if (res.solved) {
        const isFirstSolve = Boolean(
          (res as any).is_first_solve ??
            (res as any).first_solve ??
            ((res.xp_earned ?? 0) > 0),
        );

        playSuccess();
        setShowSolvedSlam(true);
        window.setTimeout(() => setShowSolvedSlam(false), 650);
        if (isFirstSolve) {
          setShowFirstSolveCelebration(true);
          window.setTimeout(() => setShowFirstSolveCelebration(false), 3200);
          triggerVictoryFx(res.xp_earned);
        }
      } else {
        playError();
      }
      await wait(res.solved ? 1000 : 700);
      setBoardFeedback('idle');

      setPostCheck({
        open: true,
        solved: res.solved,
        message: res.solved
          ? Boolean(
              (res as any).is_first_solve ??
                (res as any).first_solve ??
                ((res.xp_earned ?? 0) > 0),
            )
            ? (res.message || 'You earned XP!')
            : 'Correct! You rebuilt it.'
          : res.message,
        medal: res.medal,
        xpEarned: res.xp_earned,
        puzzleTotalXP: res.puzzle_total_xp,
        xpLeftForMax: res.xp_left_for_max,
      });

      if (res.solved) {
        setIsSolved(true);
        const isFirstSolve = Boolean(
          (res as any).is_first_solve ??
            (res as any).first_solve ??
            ((res.xp_earned ?? 0) > 0),
        );

        // Update user XP immediately for first solves.
        const currentUser = queryClient.getQueryData(['user']) as
          | { xp?: number; [key: string]: unknown }
          | undefined;
        if (isFirstSolve && currentUser && res.xp_earned) {
          queryClient.setQueryData(['user'], {
            ...currentUser,
            xp: (currentUser.xp || 0) + res.xp_earned,
          });
        }
        // Refresh user profile stats (including medal counters) from backend source of truth.
        await queryClient.invalidateQueries({ queryKey: ['user'], refetchType: 'all' });
        // Invalidate caches so the puzzles list shows "Solved"
        await queryClient.invalidateQueries({ queryKey: ['puzzles'], refetchType: 'all' });
      }
    } catch (e: any) {
      setIsPowerSurge(false);
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
      setIsPowerSurge(false);
      setBoardFeedback('idle');
      setIsChecking(false);
    }
  };

  const onSolveAgain = () => {
    const shouldResetBoard = postCheck.open && postCheck.solved;

    // For "Try again" after a failed check, keep the user's board.
    // For "Solve again" after success, start from a clean board.
    if (shouldResetBoard) {
      try {
        window.localStorage.removeItem(STATE_KEY);
      } catch {
        // ignore
      }
      setPlaced([]);
      setWires([]);
      setIsSolved(false);
      startTime.current = Date.now();
    }

    // Always reset interaction/UI state
    setSelectedComponent({ mode: 'none' });
    setDraggedPaletteComponentId(null);
    setShowPuzzleInfo(false);
    setShowDebugger(false);
    setPostCheck({ open: false });
    setIsChecking(false);
    setConnectivityIssues(null);
  };

  const applySandboxToWorkstation = () => {
    // Filter wires: keep only those that don't connect to IO:IN or IO:OUT
    const filteredWires = sandboxWires.filter(w => {
      const fromIsIO = w.from.componentId.startsWith('IO:IN:') || w.from.componentId.startsWith('IO:OUT:');
      const toIsIO = w.to.componentId.startsWith('IO:IN:') || w.to.componentId.startsWith('IO:OUT:');
      return !fromIsIO && !toIsIO;
    });

    // Create mapping of old component IDs to new IDs
    const oldToNewId = new Map<string, string>();
    sandboxPlaced.forEach(p => {
      oldToNewId.set(p.id, `${p.id}-applied`);
    });

    // Clear main workstation and apply sandbox content
    const newPlaced = sandboxPlaced.map(p => ({...p, id: `${p.id}-applied`}));
    
    // Update wire component IDs to match renamed components
    const newWires = filteredWires.map(w => ({
      ...w,
      id: `${w.id}-applied`,
      from: {
        ...w.from,
        componentId: oldToNewId.get(w.from.componentId) || w.from.componentId
      },
      to: {
        ...w.to,
        componentId: oldToNewId.get(w.to.componentId) || w.to.componentId
      }
    }));
    
    setPlaced(newPlaced);
    setWires(newWires);
    setSelectedComponent({ mode: 'none' });
    
    // Clear sandbox after applying
    setSandboxPlaced([]);
    setSandboxWires([]);
    setSandboxSelectedComponent({ mode: 'none' });
    setShowSandbox(false);
    
    const removedWireCount = sandboxWires.length - filteredWires.length;
    notifications.addNotification({
      type: 'success',
      title: 'Sandbox Applied',
      message: `Sandbox circuit transferred to main workstation${removedWireCount > 0 ? ` (${removedWireCount} I/O wires removed)` : ''}`,
    });
  };

  const clearSandbox = () => {
    setSandboxPlaced([]);
    setSandboxWires([]);
    setSandboxSelectedComponent({ mode: 'none' });
  };

  // Sandbox I/O and cost (non-hook values to avoid conditional hook order issues)
  const sandboxInputs = Array.from({ length: sandboxNumInputs }, (_, i) => `in${i}`);

  const sandboxOutputs = Array.from({ length: sandboxNumOutputs }, (_, i) => `out${i}`);

  const sandboxCurrentCost = sandboxPlaced.reduce((acc, p) => {
    const def = componentCatalog.get(p.componentId);
    return acc + (def?.cost ?? 0);
  }, 0);

  const onBrowsePuzzles = () => {
    router.push(paths.app.puzzles.getHref());
  };

  const visibleBasics = basicComponents;

  return (
    <div className="flex w-full flex-col gap-3">
      {showFirstSolveCelebration && viewportSize.width > 0 && viewportSize.height > 0 ? (
        <Confetti
          width={viewportSize.width}
          height={viewportSize.height}
          numberOfPieces={220}
          recycle={false}
          gravity={0.18}
          tweenDuration={4500}
        />
      ) : null}

      {victoryFx.visible ? (
        <div
          key={victoryFx.key}
          className="pointer-events-none fixed left-1/2 top-1/2 z-[120] -translate-x-1/2 -translate-y-1/2 rounded-full border border-sky-200 bg-white px-5 py-2 font-semibold text-sky-700 shadow-xl"
        >
          +{victoryFx.xp ?? 'XP'} • You earned XP!
        </div>
      ) : null}

      <div className="flex flex-col gap-2.5">
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border/60 bg-card/80 px-4 py-3 shadow-subtle backdrop-blur-sm">
          <div className="min-w-0">
            <div className="flex items-center gap-2.5">
              <h1 className="truncate text-lg font-semibold tracking-tight text-foreground sm:text-xl">
                {puzzle.title}
              </h1>
              {isSolved && (
                <span className="inline-flex shrink-0 items-center gap-1 rounded-md bg-emerald-50/50 px-2.5 py-0.5 text-[11px] font-medium text-emerald-700">
                  <svg className="size-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12" /></svg>
                  Solved
                </span>
              )}
            </div>
            <div className="text-[13px] text-muted-foreground">
              by {puzzle.creator?.username ?? ''}
            </div>
            {puzzle.description && (
              <div className="text-[13px] text-muted-foreground">
                {puzzle.description}
              </div>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <WorkstationTimer
              timeLimitSeconds={puzzle.timeLimit ?? (puzzle as any).time_limit_seconds}
            />
            <Button variant="outline" size="sm" onClick={() => setShowDebugger(true)}>
              Debug
            </Button>
            <Button variant="outline" size="sm" onClick={() => setShowLeaderboard(true)}>
              Leaderboard
            </Button>
            <Button variant="outline" size="sm" onClick={() => setShowCreatorComment(true)}>
              Creator Comment
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={!canRatePuzzle}
              title={canRatePuzzle ? 'Rate this puzzle' : `Available after solving or ${ratingMinAttemptSeconds} seconds of trying`}
              onClick={() => setShowRating(true)}
            >
              Rate Puzzle
            </Button>
            <Button variant="outline" size="sm" onClick={() => setShowPuzzleInfo(true)}>
              Instructions
            </Button>
            <div className="relative">
              <Button
                size="sm"
                className="transition-all hover:scale-105 active:scale-95"
                onClick={checkSolution}
                isLoading={isChecking}
              >
                {isChecking ? 'Checking...' : 'Check Solution'}
              </Button>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-4 rounded-xl border border-border/60 bg-card/80 px-4 py-2.5 text-[13px] text-foreground shadow-subtle backdrop-blur-sm">
          <div className="flex items-center gap-1">
            <span className="text-muted-foreground">Budget:</span> {budgetLimit}
            {creatorBudget !== null && (
              <><span className="text-muted-foreground ml-2">Creator Cost:</span> {creatorBudget}</>
            )}
            <span className="text-muted-foreground ml-2">Cost:</span> {currentCost}
            <InfoPopup>
              <p className="font-medium text-foreground mb-1">Circuit Cost Limits</p>
              <p><span className="font-medium text-foreground">Budget</span> — Max gate cost allowed. Your circuit must stay within this limit.</p>
              {creatorBudget !== null && (
                <p className="mt-1"><span className="font-medium text-foreground">Creator Cost</span> — The creator&apos;s solution cost. Match or beat it to earn a better medal.</p>
              )}
              <p className="mt-1"><span className="font-medium text-foreground">Cost</span> — Your current circuit&apos;s total gate cost.</p>
            </InfoPopup>
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

      <div className="grid w-full grid-cols-1 gap-3 lg:grid-cols-[260px_1fr_280px]">
        <WorkstationMenu
          basic={visibleBasics}
          custom={customComponents}
          arsenal={arsenalComponents}
          componentDefs={uiCatalog}
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
          isChecking={isChecking}
          isPowerSurge={isPowerSurge}
          boardFeedback={boardFeedback}
          showSolvedSlam={showSolvedSlam}
          boardRows={puzzle.board_rows ?? 15}
          boardCols={puzzle.board_cols ?? 30}
        />

        <div className="flex flex-col gap-3">
          <div className="rounded-xl border border-border/60 bg-card/80 p-3 shadow-subtle backdrop-blur-sm">
            <div className="mb-1.5 text-[13px] font-semibold tracking-tight text-foreground">
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
                        className="hidden rounded-sm px-1.5 py-0.5 text-muted-foreground transition-all group-hover:block hover:scale-105 hover:bg-red-100 hover:text-red-700"
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

          <div className="rounded-xl border border-border/60 bg-card/80 p-3 shadow-subtle backdrop-blur-sm">
            <div className="mb-1.5 text-[13px] font-semibold tracking-tight text-foreground">
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

      {/* Sandbox Section */}
      <div className="w-full">
        <button
          type="button"
          onClick={() => setShowSandbox(!showSandbox)}
          className="flex w-full items-center gap-2 rounded-xl border border-border/60 bg-card/80 px-4 py-3 shadow-subtle backdrop-blur-sm hover:bg-card transition-colors"
        >
          <ChevronDown
            size={16}
            className={cn(
              'transition-transform',
              showSandbox ? 'rotate-180' : ''
            )}
          />
          <span className="text-[13px] font-semibold tracking-tight text-foreground">
            Sandbox Workstation
          </span>
          {sandboxPlaced.length > 0 && (
            <span className="ml-auto text-[11px] text-muted-foreground">
              {sandboxPlaced.length} components · {sandboxWires.length} wires
            </span>
          )}
        </button>

        {showSandbox && (
          <div className="mt-3 rounded-xl border border-border/60 bg-card/80 p-4 shadow-subtle backdrop-blur-sm">
            <div className="mb-4 text-[13px] text-muted-foreground">
              Design and test circuits here, then transfer to main workstation
            </div>

            <div className="grid w-full grid-cols-1 gap-4 lg:grid-cols-[280px_1fr]">
              {/* Configuration & Controls Panel */}
              <div className="flex flex-col gap-4">
                {/* I/O Configuration */}
                <div className="rounded-lg border border-border/60 bg-secondary/30 p-4">
                  <div className="mb-3 text-[13px] font-semibold text-foreground">
                    I/O Configuration
                  </div>
                  
                  <div className="space-y-3">
                    <div>
                      <label className="text-[11px] font-medium text-foreground block mb-2">
                        Inputs
                      </label>
                      <select
                        value={sandboxNumInputs}
                        onChange={(e) => setSandboxNumInputs(parseInt(e.target.value))}
                        className="w-full border border-border rounded-lg bg-card text-foreground px-2 py-1.5 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
                      >
                        {[1, 2, 3, 4, 5, 6, 7, 8].map((n) => (
                          <option key={n} value={n}>
                            {n} input{n !== 1 ? 's' : ''}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="text-[11px] font-medium text-foreground block mb-2">
                        Outputs
                      </label>
                      <select
                        value={sandboxNumOutputs}
                        onChange={(e) => setSandboxNumOutputs(parseInt(e.target.value))}
                          className="w-full border border-border rounded-lg bg-transparent px-2 py-1.5 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
                        >
                        {[1, 2, 3, 4, 5, 6, 7, 8].map((n) => (
                          <option key={n} value={n}>
                            {n} output{n !== 1 ? 's' : ''}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                </div>

                {/* Statistics */}
                <div className="rounded-lg border border-border/60 bg-secondary/30 p-4">
                  <div className="mb-3 text-[13px] font-semibold text-foreground">
                    Sandbox Info
                  </div>
                  
                  <div className="space-y-2 text-[13px]">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Components:</span>
                      <span className="font-medium">{sandboxPlaced.length}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Total Cost:</span>
                      <span className="font-medium">{sandboxCurrentCost}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Wires:</span>
                      <span className="font-medium">{sandboxWires.length}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">I/O Pins:</span>
                      <span className="font-medium">{sandboxNumInputs + sandboxNumOutputs}</span>
                    </div>
                  </div>
                  
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setShowSandboxDebugger(true)}
                    className="w-full mt-3"
                  >
                    Debug
                  </Button>
                </div>

                {/* Action Buttons */}
                {sandboxPlaced.length > 0 && (
                  <div className="space-y-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={clearSandbox}
                      className="w-full"
                    >
                      Clear Sandbox
                    </Button>
                    <Button
                      size="sm"
                      onClick={applySandboxToWorkstation}
                      className="w-full"
                    >
                      Send to Workstation
                    </Button>
                  </div>
                )}
              </div>

              {/* Menu & Grid */}
              <div className="grid w-full grid-cols-1 gap-4 lg:grid-cols-[260px_1fr]">
                <WorkstationMenu
                  basic={visibleBasics}
                  custom={customComponents}
                  arsenal={arsenalComponents}
                  componentDefs={uiCatalog}
                  allowArsenal={allowArsenal}
                  filteredBasicTypes={filteredBasicTypes}
                  selectedComponentId={
                    sandboxSelectedComponent.mode === 'placing'
                      ? sandboxSelectedComponent.componentId
                      : undefined
                  }
                  onSelectComponent={(componentId) =>
                    setSandboxSelectedComponent({ mode: 'placing', componentId, rotation: 0 })
                  }
                  onDragStart={setSandboxDraggedPaletteComponentId}
                  onDragEnd={() => setSandboxDraggedPaletteComponentId(null)}
                />

                <WorkstationGrid
                  puzzleId={puzzle.id}
                  inputs={sandboxInputs}
                  outputs={sandboxOutputs}
                  catalog={uiCatalog}
                  placed={sandboxPlaced}
                  wires={sandboxWires}
                  selectedComponent={sandboxSelectedComponent}
                  onSelectedComponentChange={setSandboxSelectedComponent}
                  onPlacedChange={setSandboxPlaced}
                  onWiresChange={setSandboxWires}
                  draggedPaletteComponentId={sandboxDraggedPaletteComponentId}
                  boardRows={puzzle.board_rows ?? 15}
                  boardCols={puzzle.board_cols ?? 30}
                />
              </div>
            </div>

            {/* Sandbox Debugger */}
            <CircuitDebugger
              isOpen={showSandboxDebugger}
              onClose={() => setShowSandboxDebugger(false)}
              inputs={sandboxInputs}
              outputs={sandboxOutputs}
              placed={sandboxPlaced}
              wires={sandboxWires}
              catalog={uiCatalog}
              puzzleId={puzzle.id}
            />
          </div>
        )}
      </div>

      <Dialog open={showPuzzleInfo} onOpenChange={setShowPuzzleInfo}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{puzzle.title}</DialogTitle>
            <DialogDescription>
              Puzzle instructions terminal.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3 text-[13px] text-foreground">
            <div className="rounded-lg border border-slate-300 bg-white p-3 font-mono text-[12px] leading-6 text-slate-900 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100">
              <div className="mb-2 text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400">
                terminal://puzzle-instructions
              </div>
              <pre className="whitespace-pre-wrap break-words">{typedInstructionText}{showPuzzleInfo && typedInstructionText.length < terminalInstructionText.length ? '_' : ''}</pre>
            </div>

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
                      <table className="min-w-full border border-slate-300 text-xs text-slate-900 dark:border-slate-700 dark:text-slate-100">
                        <thead>
                          <tr className="bg-slate-100 dark:bg-slate-800">
                            <th className="border border-slate-300 px-2 py-1 text-slate-900 dark:border-slate-700 dark:text-slate-100">A</th>
                            <th className="border border-slate-300 px-2 py-1 text-slate-900 dark:border-slate-700 dark:text-slate-100">B</th>
                            <th className="border border-slate-300 px-2 py-1 text-slate-900 dark:border-slate-700 dark:text-slate-100">C_in</th>
                            <th className="border border-slate-300 px-2 py-1 text-slate-900 dark:border-slate-700 dark:text-slate-100">S</th>
                            <th className="border border-slate-300 px-2 py-1 text-slate-900 dark:border-slate-700 dark:text-slate-100">C_out</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr><td className="border border-slate-300 px-2 py-1 text-center text-slate-900 dark:border-slate-700 dark:text-slate-100">0</td><td className="border border-slate-300 px-2 py-1 text-center text-slate-900 dark:border-slate-700 dark:text-slate-100">0</td><td className="border border-slate-300 px-2 py-1 text-center text-slate-900 dark:border-slate-700 dark:text-slate-100">0</td><td className="border border-slate-300 px-2 py-1 text-center text-slate-900 dark:border-slate-700 dark:text-slate-100">0</td><td className="border border-slate-300 px-2 py-1 text-center text-slate-900 dark:border-slate-700 dark:text-slate-100">0</td></tr>
                          <tr><td className="border border-slate-300 px-2 py-1 text-center text-slate-900 dark:border-slate-700 dark:text-slate-100">0</td><td className="border border-slate-300 px-2 py-1 text-center text-slate-900 dark:border-slate-700 dark:text-slate-100">0</td><td className="border border-slate-300 px-2 py-1 text-center text-slate-900 dark:border-slate-700 dark:text-slate-100">1</td><td className="border border-slate-300 px-2 py-1 text-center text-slate-900 dark:border-slate-700 dark:text-slate-100">1</td><td className="border border-slate-300 px-2 py-1 text-center text-slate-900 dark:border-slate-700 dark:text-slate-100">0</td></tr>
                          <tr><td className="border border-slate-300 px-2 py-1 text-center text-slate-900 dark:border-slate-700 dark:text-slate-100">0</td><td className="border border-slate-300 px-2 py-1 text-center text-slate-900 dark:border-slate-700 dark:text-slate-100">1</td><td className="border border-slate-300 px-2 py-1 text-center text-slate-900 dark:border-slate-700 dark:text-slate-100">0</td><td className="border border-slate-300 px-2 py-1 text-center text-slate-900 dark:border-slate-700 dark:text-slate-100">1</td><td className="border border-slate-300 px-2 py-1 text-center text-slate-900 dark:border-slate-700 dark:text-slate-100">0</td></tr>
                          <tr><td className="border border-slate-300 px-2 py-1 text-center text-slate-900 dark:border-slate-700 dark:text-slate-100">0</td><td className="border border-slate-300 px-2 py-1 text-center text-slate-900 dark:border-slate-700 dark:text-slate-100">1</td><td className="border border-slate-300 px-2 py-1 text-center text-slate-900 dark:border-slate-700 dark:text-slate-100">1</td><td className="border border-slate-300 px-2 py-1 text-center text-slate-900 dark:border-slate-700 dark:text-slate-100">0</td><td className="border border-slate-300 px-2 py-1 text-center text-slate-900 dark:border-slate-700 dark:text-slate-100">1</td></tr>
                          <tr><td className="border border-slate-300 px-2 py-1 text-center text-slate-900 dark:border-slate-700 dark:text-slate-100">1</td><td className="border border-slate-300 px-2 py-1 text-center text-slate-900 dark:border-slate-700 dark:text-slate-100">0</td><td className="border border-slate-300 px-2 py-1 text-center text-slate-900 dark:border-slate-700 dark:text-slate-100">0</td><td className="border border-slate-300 px-2 py-1 text-center text-slate-900 dark:border-slate-700 dark:text-slate-100">1</td><td className="border border-slate-300 px-2 py-1 text-center text-slate-900 dark:border-slate-700 dark:text-slate-100">0</td></tr>
                          <tr><td className="border border-slate-300 px-2 py-1 text-center text-slate-900 dark:border-slate-700 dark:text-slate-100">1</td><td className="border border-slate-300 px-2 py-1 text-center text-slate-900 dark:border-slate-700 dark:text-slate-100">0</td><td className="border border-slate-300 px-2 py-1 text-center text-slate-900 dark:border-slate-700 dark:text-slate-100">1</td><td className="border border-slate-300 px-2 py-1 text-center text-slate-900 dark:border-slate-700 dark:text-slate-100">0</td><td className="border border-slate-300 px-2 py-1 text-center text-slate-900 dark:border-slate-700 dark:text-slate-100">1</td></tr>
                          <tr><td className="border border-slate-300 px-2 py-1 text-center text-slate-900 dark:border-slate-700 dark:text-slate-100">1</td><td className="border border-slate-300 px-2 py-1 text-center text-slate-900 dark:border-slate-700 dark:text-slate-100">1</td><td className="border border-slate-300 px-2 py-1 text-center text-slate-900 dark:border-slate-700 dark:text-slate-100">0</td><td className="border border-slate-300 px-2 py-1 text-center text-slate-900 dark:border-slate-700 dark:text-slate-100">0</td><td className="border border-slate-300 px-2 py-1 text-center text-slate-900 dark:border-slate-700 dark:text-slate-100">1</td></tr>
                          <tr><td className="border border-slate-300 px-2 py-1 text-center text-slate-900 dark:border-slate-700 dark:text-slate-100">1</td><td className="border border-slate-300 px-2 py-1 text-center text-slate-900 dark:border-slate-700 dark:text-slate-100">1</td><td className="border border-slate-300 px-2 py-1 text-center text-slate-900 dark:border-slate-700 dark:text-slate-100">1</td><td className="border border-slate-300 px-2 py-1 text-center text-slate-900 dark:border-slate-700 dark:text-slate-100">1</td><td className="border border-slate-300 px-2 py-1 text-center text-slate-900 dark:border-slate-700 dark:text-slate-100">1</td></tr>
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

      {showRating && (
        <RatingDialog
          puzzleId={puzzle.id}
          open={showRating}
          onOpenChange={setShowRating}
          startTime={startTime.current}
        />
      )}

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
                    <span className="animate-[bounce_0.9s_ease-in-out_2]">
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
                {typeof postCheck.puzzleTotalXP === 'number' && (
                  <div className="rounded-lg border border-border/60 bg-secondary/40 p-2.5">
                    <PuzzleXPBar
                      difficulty={puzzle.difficulty}
                      avgDifficulty={puzzle.avg_difficulty ?? 0}
                      currentXP={postCheck.puzzleTotalXP}
                    />
                  </div>
                )}
                {typeof postCheck.xpLeftForMax === 'number' && postCheck.xpLeftForMax > 0 && (
                  <p className="font-medium text-amber-700">
                    You have {postCheck.xpLeftForMax} XP left for max.
                  </p>
                )}
                {typeof postCheck.xpLeftForMax === 'number' && postCheck.xpLeftForMax === 0 && postCheck.xpEarned === 0 && (
                  <p className="font-medium text-emerald-700">
                    You have reached the maximum XP for this puzzle.
                  </p>
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
              className="transition-all hover:scale-105 active:scale-95"
              onClick={onSolveAgain}
              disabled={!postCheck.open}
            >
              {postCheck.open && postCheck.solved ? 'Solve again' : 'Try again'}
            </Button>
            <Button
              className="transition-all hover:scale-105 active:scale-95"
              onClick={onBrowsePuzzles}
              disabled={!postCheck.open}
            >
              Browse puzzles
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Leaderboard Dialog */}
      <Dialog open={showLeaderboard} onOpenChange={setShowLeaderboard}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <svg className="size-5 text-amber-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6" />
                <path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18" />
                <path d="M4 22h16" />
                <path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22" />
                <path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22" />
                <path d="M18 2H6v7a6 6 0 0 0 12 0V2Z" />
              </svg>
              Leaderboard
            </DialogTitle>
            <DialogDescription>
              Fastest solvers for this puzzle
            </DialogDescription>
          </DialogHeader>
          <div className="max-h-[60vh] overflow-y-auto">
            <PuzzleLeaderboard puzzleId={puzzleId} />
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              className="transition-all hover:scale-105 active:scale-95"
              onClick={() => setShowLeaderboard(false)}
            >
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Creator Comment Dialog */}
      <CreatorCommentDialog
        open={showCreatorComment}
        onOpenChange={setShowCreatorComment}
        puzzle={puzzle}
        showLink={false}
      />

    </div>
  );
};
