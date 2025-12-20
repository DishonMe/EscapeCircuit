'use client';

import { useRouter } from 'next/navigation';
import { useMemo, useState } from 'react';

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
import { useUser } from '@/lib/auth';
import { CircuitComponent, CircuitSolution, Wire } from '@/types/api';

import { usePuzzle } from '@/features/puzzles/api/get-puzzle';
import { validateSolution } from '@/features/puzzles/api/validate-solution';

import {
  Breadboard,
  type PinAddress,
  type PlacedBoardComponent,
} from './workstation-breadboard';
import { WorkstationMenu } from './workstation-menu';
import { WorkstationTimer } from './workstation-timer';

const BASIC_COMPONENTS: CircuitComponent[] = [
  { id: 'AND', type: 'AND', cost: 10, pins: 3 },
  { id: 'OR', type: 'OR', cost: 10, pins: 3 },
  { id: 'NOT', type: 'NOT', cost: 5, pins: 2 },
  { id: 'XOR', type: 'XOR', cost: 15, pins: 3 },
  { id: 'NAND', type: 'NAND', cost: 12, pins: 3 },
];

type PostCheckState =
  | { open: false }
  | { open: true; solved: boolean; message: string };

export const PuzzleWorkstation = ({ puzzleId }: { puzzleId: string }) => {
  const router = useRouter();
  const user = useUser();

  const puzzleQuery = usePuzzle({ id: puzzleId });
  const puzzle = puzzleQuery.data?.data;

  const [placed, setPlaced] = useState<PlacedBoardComponent[]>([]);
  const [wires, setWires] = useState<Wire[]>([]);
  const [selectedPin, setSelectedPin] = useState<PinAddress | null>(null);

  const [showPuzzleInfo, setShowPuzzleInfo] = useState(false);
  const [postCheck, setPostCheck] = useState<PostCheckState>({ open: false });
  const [isChecking, setIsChecking] = useState(false);

  const notifications = useNotifications();

  const inputs = puzzle?.inputs ?? [];
  const outputs = puzzle?.outputs ?? [];

  const budgetLimit = puzzle?.budgetLimit ?? 0;
  const tightBudget =
    puzzle?.tightBudgetLimit ?? Math.ceil((puzzle?.budgetLimit ?? 0) * 1.25);

  const filteredBasics = new Set(puzzle?.filteredBasicComponents ?? []);
  const allowArsenal = puzzle?.allowArsenal ?? true;

  const specialComponents = puzzle?.specialComponents ?? [];

  const basicComponents = useMemo(() => {
    return BASIC_COMPONENTS.filter((c) => !filteredBasics.has(c.type));
  }, [filteredBasics]);

  const componentCatalog = useMemo(() => {
    const byId = new Map<string, CircuitComponent>();
    for (const c of basicComponents) byId.set(c.id, c);
    for (const c of specialComponents) byId.set(c.id, c);
    return byId;
  }, [basicComponents, specialComponents]);

  const componentPinsById = useMemo(() => {
    return Object.fromEntries(
      Array.from(componentCatalog.entries()).map(([id, def]) => [id, def.pins]),
    ) as Record<string, number>;
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

  if (puzzleQuery.isLoading) {
    return <div className="text-sm text-gray-600">Loading…</div>;
  }

  if (!puzzle) {
    return (
      <div className="flex w-full flex-col gap-3">
        <div className="text-sm text-gray-600">Puzzle not found.</div>
        <Button variant="outline" onClick={() => router.push(paths.app.puzzles.getHref())}>
          Back to puzzles
        </Button>
      </div>
    );
  }

  const onPlaceComponent = (componentId: string, at: PinAddress) => {
    const def = componentCatalog.get(componentId);
    if (!def) return;

    if (!canAddCost(def.cost)) {
      notifications.addNotification({
        type: 'warning',
        title: 'Budget exceeded',
        message: 'You cannot add components beyond the Budget limit.',
      });
      return;
    }

    setPlaced((prev) =>
      prev.concat({
        id: `${componentId}:${Date.now()}`,
        componentId,
        row: at.row,
        col: at.col,
        pins: def.pins,
      }),
    );
  };

  const onRemoveComponent = (placedId: string) => {
    setPlaced((prev) => prev.filter((p) => p.id !== placedId));
    setWires((prev) =>
      prev.filter(
        (w) => w.from.componentId !== placedId && w.to.componentId !== placedId,
      ),
    );
  };

  const onPinClick = (pin: PinAddress) => {
    if (!selectedPin) {
      setSelectedPin(pin);
      return;
    }

    if (selectedPin.row === pin.row && selectedPin.col === pin.col) {
      setSelectedPin(null);
      return;
    }

    setWires((prev) =>
      prev.concat({
        id: `wire:${Date.now()}`,
        from: {
          componentId: selectedPin.ownerId,
          pinIndex: selectedPin.pinIndex,
        },
        to: {
          componentId: pin.ownerId,
          pinIndex: pin.pinIndex,
        },
      }),
    );
    setSelectedPin(null);
  };

  const onRemoveWire = (wireId: string) => {
    setWires((prev) => prev.filter((w) => w.id !== wireId));
  };

  const buildSolution = (): CircuitSolution => {
    return {
      placedComponents: placed.map((p) => ({
        id: p.id,
        componentId: p.componentId,
        x: p.col,
        y: p.row,
      })),
      wires,
      totalCost: currentCost,
    };
  };

  const checkSolution = async () => {
    if (ioUsage.missingInputs.length || ioUsage.missingOutputs.length) {
      notifications.addNotification({
        type: 'warning',
        title: 'Missing IO',
        message: `Use all inputs and outputs before checking. Missing inputs: ${ioUsage.missingInputs.join(', ') || 'none'}; missing outputs: ${ioUsage.missingOutputs.join(', ') || 'none'}.`,
      });
      return;
    }

    setIsChecking(true);
    try {
      const res = await validateSolution({
        puzzleId: puzzle.id,
        solution: buildSolution(),
      });
      setPostCheck({ open: true, solved: res.solved, message: res.message });
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
            <h1 className="text-2xl font-semibold text-gray-900">
              {puzzle.title}
            </h1>
            <div className="text-sm text-gray-600">by {puzzle.creator?.firstName ?? ''} {puzzle.creator?.lastName ?? ''}</div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <WorkstationTimer timeLimitSeconds={puzzle.timeLimit} />
            <Button variant="outline" onClick={() => setShowPuzzleInfo(true)}>
              Puzzle Info
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
          filteredBasicTypes={Array.from(filteredBasics)}
        />

        <Breadboard
          inputs={inputs}
          outputs={outputs}
          componentPinsById={componentPinsById}
          placed={placed}
          wires={wires}
          selectedPin={selectedPin}
          onPinClick={onPinClick}
          onPlaceComponent={onPlaceComponent}
          onRemoveComponent={onRemoveComponent}
        />

        <div className="flex flex-col gap-3">
          <div className="rounded-md border border-gray-300 bg-white p-3">
            <div className="mb-2 text-sm font-medium text-gray-900">Debugger</div>
            <div className="text-xs text-gray-600">
              This debugger shows wiring and IO usage. Backend validation runs
              creator test-cases.
            </div>
            <div className="mt-3">
              <div className="mb-2 text-xs font-medium text-gray-700">Wires</div>
              {wires.length === 0 ? (
                <div className="text-xs text-gray-500">No wires yet.</div>
              ) : (
                <ul className="space-y-2">
                  {wires.map((w) => (
                    <li
                      key={w.id}
                      className="flex items-center justify-between gap-2 rounded border border-gray-200 bg-gray-50 px-2 py-1"
                    >
                      <span className="truncate text-xs text-gray-700">
                        {w.from.componentId} → {w.to.componentId}
                      </span>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => onRemoveWire(w.id)}
                      >
                        Remove
                      </Button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          <div className="rounded-md border border-gray-300 bg-white p-3">
            <div className="mb-2 text-sm font-medium text-gray-900">Session</div>
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
              <div className="mt-1 whitespace-pre-wrap">{puzzle.description}</div>
            </div>
            {puzzle.creatorComment ? (
              <div>
                <div className="font-medium text-gray-900">Creator comment</div>
                <div className="mt-1 whitespace-pre-wrap">{puzzle.creatorComment}</div>
              </div>
            ) : null}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowPuzzleInfo(false)}>
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
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {postCheck.open && postCheck.solved
                ? 'Puzzle solved'
                : 'Failed to solve'}
            </DialogTitle>
            <DialogDescription>
              {postCheck.open ? postCheck.message : ''}
            </DialogDescription>
          </DialogHeader>
          <div className="text-sm text-gray-700">
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
