'use client';

import { useMemo, useState } from 'react';

import {
  Boxes,
  CircuitBoard,
  Gift,
  Medal,
  PackageOpen,
  Trophy,
  Eye,
} from 'lucide-react';
import Link from 'next/link';

import { Button } from '@/components/ui/button';
import { AvatarDisplay } from '@/components/ui/avatar-display';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { getLevelInfo } from '@/components/ui/xp-bar';
import { paths } from '@/config/paths';
import { useMyArsenal, ArsenalPiece } from '@/features/arsenal/api';
import { EditBio } from '@/features/users/components/edit-bio';
import { UpdateAvatar } from '@/features/users/components/update-avatar';
import { useUser } from '@/lib/auth';
import { WorkstationGrid } from '@/app/app/puzzles/[id]/_components/workstation-grid';
import type {
  PlacedGridComponent,
  ComponentDef,
} from '@/app/app/puzzles/[id]/_components/workstation-grid';
import type { Wire } from '@/types/api';

type EntryProps = {
  label: string;
  value: string;
};

type ArsenalStructure = {
  placed?: Array<{
    id: string;
    componentId: string;
    origin?: { row: number; col: number };
    x?: number;
    y?: number;
  }>;
  placedComponents?: Array<{
    id: string;
    componentId: string;
    x: number;
    y: number;
  }>;
  wires?: Array<{
    id: string;
    from: { componentId: string; pinIndex?: number };
    to: { componentId: string; pinIndex?: number };
  }>;
};

type LevelBenefit = {
  level: number;
  arsenalSlots: number;
  publishedCap: number;
  unpublishedCap: number;
};

type LevelBenefitChange = {
  level: number;
  changes: string[];
};

const getArsenalSlots = (level: number) => {
  if (level <= 2) return 5;
  if (level <= 4) return 10;
  if (level <= 6) return 20;
  if (level <= 8) return 35;
  return 50;
};

const getCreatorPuzzleCap = (level: number) => {
  if (level < 10) return 5;
  const steps = Math.min(level - 10 + 1, 6);
  return 5 + steps * 2;
};

const LEVEL_BENEFITS: LevelBenefit[] = Array.from({ length: 15 }, (_, i) => {
  const level = i + 1;
  const creatorCap = getCreatorPuzzleCap(level);
  return {
    level,
    arsenalSlots: getArsenalSlots(level),
    publishedCap: creatorCap,
    unpublishedCap: creatorCap,
  };
});

const LEVEL_BENEFIT_CHANGES: LevelBenefitChange[] = LEVEL_BENEFITS.map(
  (benefit, index) => {
    if (index === 0) return null;
    const previous = LEVEL_BENEFITS[index - 1];
    const changes: string[] = [];

    if (benefit.arsenalSlots !== previous.arsenalSlots) {
      changes.push(
        `Arsenal slots ${previous.arsenalSlots}->${benefit.arsenalSlots}`,
      );
    }
    if (benefit.publishedCap !== previous.publishedCap) {
      changes.push(
        `Published puzzles ${previous.publishedCap}->${benefit.publishedCap}`,
      );
    }
    if (benefit.unpublishedCap !== previous.unpublishedCap) {
      changes.push(
        `Unpublished puzzles ${previous.unpublishedCap}->${benefit.unpublishedCap}`,
      );
    }

    if (changes.length === 0) return null;
    return { level: benefit.level, changes };
  },
).filter((entry): entry is LevelBenefitChange => entry !== null);

const Entry = ({ label, value }: EntryProps) => (
  <div className="grid grid-cols-1 gap-1 rounded-xl border border-border bg-card/70 px-4 py-3 sm:grid-cols-[140px_1fr]">
    <dt className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
      {label}
    </dt>
    <dd className="text-sm text-foreground">{value}</dd>
  </div>
);

const parseStructure = (raw: string): ArsenalStructure | null => {
  try {
    const parsed = JSON.parse(raw) as ArsenalStructure;
    return parsed;
  } catch {
    return null;
  }
};

const getPlaced = (structure: ArsenalStructure) => {
  if (Array.isArray(structure.placed) && structure.placed.length > 0) {
    return structure.placed.map((node) => ({
      id: node.id,
      componentId: node.componentId,
      x: node.origin?.col ?? node.x ?? 0,
      y: node.origin?.row ?? node.y ?? 0,
    }));
  }

  if (
    Array.isArray(structure.placedComponents) &&
    structure.placedComponents.length > 0
  ) {
    return structure.placedComponents;
  }

  return [];
};

const MiniCircuitPreview = ({ structureRaw }: { structureRaw: string }) => {
  const parsed = parseStructure(structureRaw);
  if (!parsed) {
    return (
      <div className="relative overflow-hidden w-full h-40 pointer-events-none rounded-xl border border-dashed border-border bg-secondary" />
    );
  }

  const placed = getPlaced(parsed);
  const wires = Array.isArray(parsed.wires) ? parsed.wires : [];
  const nodeById = new Map(placed.map((node) => [node.id, node]));

  return (
    <div className="relative overflow-hidden w-full h-40 pointer-events-none rounded-xl border border-border bg-secondary">
      <div
        className="absolute inset-0 origin-top-left scale-[0.5]"
        style={{ width: '200%', height: '200%' }}
      >
        {wires.map((wire) => {
          const fromNode = nodeById.get(wire.from.componentId);
          const toNode = nodeById.get(wire.to.componentId);
          if (!fromNode || !toNode) return null;

          const x1 = fromNode.x * 44 + 34;
          const y1 = fromNode.y * 44 + 26;
          const x2 = toNode.x * 44 + 34;
          const y2 = toNode.y * 44 + 26;
          const control = Math.max(20, Math.abs(x2 - x1) * 0.35);
          const d = `M ${x1} ${y1} C ${x1 + control} ${y1}, ${x2 - control} ${y2}, ${x2} ${y2}`;

          return (
            <svg key={wire.id} className="absolute inset-0 h-full w-full">
              <path
                d={d}
                fill="none"
                stroke="#38bdf8"
                strokeWidth="3"
                strokeLinecap="round"
              />
            </svg>
          );
        })}

        {placed.map((node) => (
          <div
            key={node.id}
            className="absolute flex h-9 w-14 items-center justify-center rounded-md border border-border bg-card text-[10px] font-semibold text-foreground"
            style={{ left: node.x * 44 + 6, top: node.y * 44 + 6 }}
          >
            {node.componentId}
          </div>
        ))}
      </div>
    </div>
  );
};

export const Profile = () => {
  const user = useUser();
  const { data: arsenal = [] } = useMyArsenal();
  const [rewardsOpen, setRewardsOpen] = useState(false);
  const [previewPiece, setPreviewPiece] = useState<ArsenalPiece | null>(null);

  const userData = user?.data as any;
  const currentXp = Number(userData?.xp ?? 0);
  const levelInfo = useMemo(() => getLevelInfo(currentXp), [currentXp]);

  if (!userData) return null;

  const formatDateOnly = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const displayName = userData.username ?? 'Operator';
  const initials = displayName.slice(0, 2).toUpperCase();
  const medals = userData.medals ?? {};
  const goldMedals = Number(medals.gold ?? 0);
  const silverMedals = Number(medals.silver ?? 0);
  const bronzeMedals = Number(medals.bronze ?? 0);
  const medalsTotal = userData.medals?.total ?? 0;
  const savedPuzzleCount = userData.saved_puzzles?.length ?? 0;

  return (
    <div className="space-y-5">
      <section className="grid gap-5 lg:grid-cols-[1.3fr_1fr]">
        <div className="rounded-2xl border border-border bg-card/80 p-5 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <AvatarDisplay
                avatarName={userData.avatar_name ?? 'Dinosaur'}
                avatarColor={userData.avatar_color ?? '#38bdf8'}
                size="lg"
              />
              <div>
                <h1 className="text-2xl font-semibold tracking-tight text-foreground">
                  {displayName}
                </h1>
                <p className="text-sm text-muted-foreground">
                  Circuit Operator Profile
                </p>
              </div>
            </div>
            <div className="flex gap-2">
              <UpdateAvatar />
              <EditBio />
            </div>
          </div>

          <dl className="mt-4 grid gap-3">
            <Entry label="Email" value={userData.email ?? ''} />
            <Entry label="Role" value={userData.role ?? ''} />
            <Entry
              label="Joined"
              value={formatDateOnly(
                userData.created_at ?? userData.createdAt ?? '',
              )}
            />
            {userData.bio ? <Entry label="Bio" value={userData.bio} /> : null}
          </dl>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2 rounded-2xl border border-border bg-card/80 p-4 shadow-sm">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2 text-muted-foreground">
                <CircuitBoard size={16} />
                Progress
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setRewardsOpen(true)}
                >
                  Rewards
                </Button>
                <span className="rounded-lg bg-secondary px-2 py-1 text-xs font-semibold text-foreground">
                  Level {levelInfo.level}
                </span>
              </div>
            </div>
            <p className="mt-3 text-sm text-muted-foreground">
              XP to next level:{' '}
              <span className="font-semibold text-foreground">
                {levelInfo.xpIntoLevel}/{levelInfo.xpForLevel}
              </span>
            </p>
            <div className="mt-3 flex items-center gap-2">
              <span className="text-xs font-semibold text-muted-foreground">
                {levelInfo.level}
              </span>
              <div className="h-2 flex-1 overflow-hidden rounded-full bg-secondary">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-cyan-500 to-emerald-500 transition-all duration-500"
                  style={{ width: `${levelInfo.pct}%` }}
                />
              </div>
              <span className="text-xs font-semibold text-muted-foreground">
                {levelInfo.level + 1}
              </span>
            </div>
            <p className="mt-2 text-xs text-muted-foreground">
              {currentXp}/{levelInfo.nextThreshold} total XP
            </p>
          </div>
          <div className="rounded-2xl border border-border bg-card/80 p-4 shadow-sm">
            <div className="flex items-center gap-2 text-muted-foreground">
              <Trophy size={16} /> Medals
            </div>
            <p className="mt-2 text-2xl font-semibold text-foreground">
              {medalsTotal}
            </p>
            <div className="mt-2 space-y-1 text-xs">
              <div className="flex items-center justify-between text-muted-foreground">
                <span className="inline-flex items-center gap-1">
                  <Medal size={14} className="text-amber-500" /> Gold
                </span>
                <span className="font-semibold">{goldMedals}</span>
              </div>
              <div className="flex items-center justify-between text-muted-foreground">
                <span className="inline-flex items-center gap-1">
                  <Medal size={14} className="text-muted-foreground" /> Silver
                </span>
                <span className="font-semibold">{silverMedals}</span>
              </div>
              <div className="flex items-center justify-between text-muted-foreground">
                <span className="inline-flex items-center gap-1">
                  <Medal size={14} className="text-amber-700" /> Bronze
                </span>
                <span className="font-semibold">{bronzeMedals}</span>
              </div>
            </div>
          </div>
          <div className="rounded-2xl border border-border bg-card/80 p-4 shadow-sm">
            <div className="flex items-center gap-2 text-muted-foreground">
              <Boxes size={16} /> Saved Puzzles
            </div>
            <p className="mt-3 text-3xl font-semibold text-foreground">
              {savedPuzzleCount}
            </p>
          </div>
          <div className="rounded-2xl border border-border bg-card/80 p-4 shadow-sm">
            <div className="flex items-center gap-2 text-muted-foreground">
              <CircuitBoard size={16} /> Completion
            </div>
            <p className="mt-3 text-sm text-muted-foreground">
              Puzzles Solved:{' '}
              <span className="font-semibold text-foreground">
                {userData.solved_puzzles?.length || 0}/{userData.total_puzzles || 0}
              </span>
            </p>
            <div className="mt-3 flex items-center gap-2">
              <span className="text-xs font-semibold text-muted-foreground">
                0%
              </span>
              <div className="h-2 flex-1 overflow-hidden rounded-full bg-secondary">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-blue-500 to-cyan-500 transition-all duration-500"
                  style={{ width: `${Math.round((userData.solved_puzzles?.length || 0) / (userData.total_puzzles || 1) * 100)}%` }}
                />
              </div>
              <span className="text-xs font-semibold text-muted-foreground">
                100%
              </span>
            </div>
            <p className="mt-2 text-xs text-muted-foreground">
              {Math.round((userData.solved_puzzles?.length || 0) / (userData.total_puzzles || 1) * 100)}% complete
            </p>
          </div>
        </div>
      </section>

      <section className="rounded-2xl border border-border bg-card/80 p-5 shadow-sm">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-foreground">Arsenal</h2>
          <span className="text-xs font-medium text-muted-foreground">
            {arsenal.length} saved
          </span>
        </div>

        {arsenal.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-border bg-secondary px-6 py-10 text-center">
            <PackageOpen className="mx-auto mb-3 size-10 text-muted-foreground" />
            <p className="text-base font-medium text-muted-foreground">
              Your Arsenal is empty
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              Build a custom circuit piece to see it here.
            </p>
          </div>
        ) : (
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {arsenal.map((piece) => (
              <div
                key={String(piece.id)}
                className="rounded-2xl border border-border bg-card/80 p-3 shadow-sm"
              >
                <div className="mb-2 flex items-start justify-between gap-2">
                  <h3 className="text-sm font-semibold text-foreground">
                    {piece.name}
                  </h3>
                  <span className="rounded-md bg-secondary px-2 py-0.5 text-[11px] font-medium text-foreground">
                    cost {piece.cost}
                  </span>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  className="flex-shrink-0"
                  onClick={() => setPreviewPiece(piece)}
                >
                  <Eye size={16} className="mr-1" />
                  Preview
                </Button>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="rounded-2xl border border-border bg-card/80 p-5 shadow-sm">
        <h2 className="mb-3 text-lg font-semibold text-foreground">
          Saved Puzzles
        </h2>
        {userData.saved_puzzles?.length ? (
          <ul className="grid gap-2 md:grid-cols-2">
            {userData.saved_puzzles.map((puzzle: any) => (
              <li
                key={puzzle.id}
                className="rounded-xl border border-border bg-card/70 px-3 py-2 text-sm"
              >
                <Link
                  href={`${paths.app.puzzles.getHref()}/${puzzle.id}`}
                  className="font-medium text-foreground underline-offset-2 hover:underline"
                >
                  {puzzle.name}
                </Link>
                <span className="ml-2 text-xs text-muted-foreground">
                  ({puzzle.status})
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted-foreground">No saved puzzles yet.</p>
        )}
      </section>

      {/* Circuit Preview Dialog */}
      {previewPiece && (
        <Dialog
          open={!!previewPiece}
          onOpenChange={(open) => !open && setPreviewPiece(null)}
        >
          <DialogContent className="max-w-4xl max-h-[85vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>{previewPiece.name} - Circuit Preview</DialogTitle>
              <DialogDescription>
                Read-only preview of the circuit. No modifications allowed.
              </DialogDescription>
            </DialogHeader>
            <CircuitPreviewContent piece={previewPiece} />
          </DialogContent>
        </Dialog>
      )}

      <Dialog open={rewardsOpen} onOpenChange={setRewardsOpen}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Gift size={18} /> Level Rewards (1-15)
            </DialogTitle>
            <DialogDescription>
              Milestone levels only. Each row shows exactly what changes at that
              level.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3">
            <div className="max-h-[430px] overflow-auto rounded-xl border border-border">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-secondary text-xs uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2 text-left">Level</th>
                    <th className="px-3 py-2 text-left">Change</th>
                  </tr>
                </thead>
                <tbody>
                  {LEVEL_BENEFIT_CHANGES.map((benefit) => (
                    <tr
                      key={benefit.level}
                      className={
                        benefit.level === levelInfo.level
                          ? 'bg-cyan-50/70 dark:bg-cyan-950/30'
                          : 'bg-card'
                      }
                    >
                      <td className="whitespace-nowrap border-t border-border px-3 py-2 font-semibold text-foreground">
                        Level {benefit.level}
                      </td>
                      <td className="border-t border-border px-3 py-2 text-muted-foreground">
                        {benefit.changes.join(' | ')}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="rounded-xl border border-border bg-secondary p-3">
              <p className="text-sm text-muted-foreground">
                You are level {levelInfo.level}. Next level in{' '}
                {Math.max(0, levelInfo.nextThreshold - currentXp)} XP.
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                Starting values at level 1 are: Arsenal slots 5, Published
                puzzles 5, Unpublished puzzles 5.
              </p>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

function CircuitPreviewContent({ piece }: { piece: ArsenalPiece }) {
  const { data: myArsenal } = useMyArsenal();

  const parseStructure = (
    structureJson: string,
  ): {
    numInputs: number;
    numOutputs: number;
    placed: PlacedGridComponent[];
    wires: Wire[];
  } => {
    try {
      return JSON.parse(structureJson || '{}');
    } catch {
      return { numInputs: 0, numOutputs: 0, placed: [], wires: [] };
    }
  };

  const structure = parseStructure(piece.structure_json);
  const { placed, wires } = structure;

  // Build input/output labels
  const inputLabels = Array.from(
    { length: structure.numInputs },
    (_, i) => `in${i}`,
  );
  const outputLabels = Array.from(
    { length: structure.numOutputs },
    (_, i) => `out${i}`,
  );

  // Build map of arsenal pieces by ID for quick lookup
  const arsenalMap = new Map<string, ArsenalPiece>();
  if (myArsenal) {
    myArsenal.forEach((ap) => {
      arsenalMap.set(String(ap.id), ap);
    });
  }

  // Build catalog with standard component definitions
  // Size formula: width=3, height=max(inputs, outputs)
  const catalog: Record<string, ComponentDef> = {
    AND: {
      id: 'AND',
      label: 'AND',
      cost: 1,
      size: { w: 3, h: 2 },
      ports: [
        { id: 'P0', kind: 'input', offset: { row: 0, col: 0 } },
        { id: 'P1', kind: 'input', offset: { row: 1, col: 0 } },
        { id: 'P2', kind: 'output', offset: { row: 1, col: 2 } },
      ],
    },
    OR: {
      id: 'OR',
      label: 'OR',
      cost: 1,
      size: { w: 3, h: 2 },
      ports: [
        { id: 'P0', kind: 'input', offset: { row: 0, col: 0 } },
        { id: 'P1', kind: 'input', offset: { row: 1, col: 0 } },
        { id: 'P2', kind: 'output', offset: { row: 1, col: 2 } },
      ],
    },
    NOT: {
      id: 'NOT',
      label: 'NOT',
      cost: 1,
      size: { w: 3, h: 1 },
      ports: [
        { id: 'P0', kind: 'input', offset: { row: 0, col: 0 } },
        { id: 'P1', kind: 'output', offset: { row: 0, col: 2 } },
      ],
    },
    XOR: {
      id: 'XOR',
      label: 'XOR',
      cost: 2,
      size: { w: 3, h: 2 },
      ports: [
        { id: 'P0', kind: 'input', offset: { row: 0, col: 0 } },
        { id: 'P1', kind: 'input', offset: { row: 1, col: 0 } },
        { id: 'P2', kind: 'output', offset: { row: 1, col: 2 } },
      ],
    },
    NAND: {
      id: 'NAND',
      label: 'NAND',
      cost: 1,
      size: { w: 3, h: 2 },
      ports: [
        { id: 'P0', kind: 'input', offset: { row: 0, col: 0 } },
        { id: 'P1', kind: 'input', offset: { row: 1, col: 0 } },
        { id: 'P2', kind: 'output', offset: { row: 1, col: 2 } },
      ],
    },
    NOR: {
      id: 'NOR',
      label: 'NOR',
      cost: 1,
      size: { w: 3, h: 2 },
      ports: [
        { id: 'P0', kind: 'input', offset: { row: 0, col: 0 } },
        { id: 'P1', kind: 'input', offset: { row: 1, col: 0 } },
        { id: 'P2', kind: 'output', offset: { row: 1, col: 2 } },
      ],
    },
    XNOR: {
      id: 'XNOR',
      label: 'XNOR',
      cost: 2,
      size: { w: 3, h: 2 },
      ports: [
        { id: 'P0', kind: 'input', offset: { row: 0, col: 0 } },
        { id: 'P1', kind: 'input', offset: { row: 1, col: 0 } },
        { id: 'P2', kind: 'output', offset: { row: 1, col: 2 } },
      ],
    },
  };

  // Add any custom arsenal pieces as components
  placed.forEach((comp) => {
    if (!catalog[comp.componentId]) {
      const arsenalPiece = arsenalMap.get(comp.componentId);
      if (arsenalPiece && (arsenalPiece as any).is_arsenal) {
        // Arsenal piece sizing: width=3, height=max(inputs, outputs)
        const numInputs = (arsenalPiece as any).num_inputs ?? 0;
        const numOutputs = (arsenalPiece as any).num_outputs ?? 0;
        const maxPorts = Math.max(numInputs, numOutputs);
        const size = { w: 3, h: Math.max(1, maxPorts) };

        // Generate ports for arsenal pieces
        const ports: Array<{
          id: string;
          kind: 'input' | 'output';
          offset: { row: number; col: number };
        }> = [];
        for (let i = 0; i < numInputs; i++) {
          ports.push({
            id: `in${i}`,
            kind: 'input',
            offset: { row: Math.min(i, size.h - 1), col: 0 },
          });
        }
        for (let i = 0; i < numOutputs; i++) {
          ports.push({
            id: `out${i}`,
            kind: 'output',
            offset: { row: Math.min(i, size.h - 1), col: size.w - 1 },
          });
        }

        catalog[comp.componentId] = {
          id: comp.componentId,
          label: arsenalPiece.name,
          cost: arsenalPiece.cost,
          size,
          ports,
        };
      } else {
        // Fallback for unknown components
        catalog[comp.componentId] = {
          id: comp.componentId,
          label: comp.componentId,
          cost: 1,
          size: { w: 3, h: 1 },
          ports: [
            { id: 'P0', kind: 'input', offset: { row: 0, col: 0 } },
            { id: 'P1', kind: 'output', offset: { row: 0, col: 2 } },
          ],
        };
      }
    }
  });

  const gridRows = Math.max(
    15,
    Math.max(...placed.map((c) => c.origin.row), 0) + 3,
  );
  const gridCols = Math.max(
    30,
    Math.max(...placed.map((c) => c.origin.col), 0) + 3,
  );

  return (
    <div className="space-y-4">
      {/* Description */}
      {piece.description && (
        <div className="bg-foreground/5 p-3 rounded-lg border border-border/40">
          <p className="text-sm text-foreground">{piece.description}</p>
        </div>
      )}

      {/* Circuit Stats */}
      <div className="grid grid-cols-4 gap-3">
        <div className="bg-secondary/40 p-3 rounded-lg border border-border/60">
          <p className="text-xs text-foreground/70 mb-1">Inputs</p>
          <p className="text-lg font-semibold text-foreground">
            {structure.numInputs}
          </p>
        </div>
        <div className="bg-secondary/40 p-3 rounded-lg border border-border/60">
          <p className="text-xs text-foreground/70 mb-1">Outputs</p>
          <p className="text-lg font-semibold text-foreground">
            {structure.numOutputs}
          </p>
        </div>
        <div className="bg-secondary/40 p-3 rounded-lg border border-border/60">
          <p className="text-xs text-foreground/70 mb-1">Components</p>
          <p className="text-lg font-semibold text-foreground">
            {placed.length}
          </p>
        </div>
        <div className="bg-secondary/40 p-3 rounded-lg border border-border/60">
          <p className="text-xs text-foreground/70 mb-1">Cost</p>
          <p className="text-lg font-semibold text-foreground">{piece.cost}</p>
        </div>
      </div>

      {/* Circuit Grid - Read-only Workstation */}
      <div
        className="border border-border/60 rounded-lg bg-background overflow-hidden relative"
        style={{ height: '500px' }}
      >
        <style>{`
          [data-preview-mode="true"] button[title*="Delete"],
          [data-preview-mode="true"] button[title*="Cancel wiring"],
          [data-preview-mode="true"] button[title*="Clear Grid"],
          [data-preview-mode="true"] button[title*="Remove wire"],
          [data-preview-mode="true"] button[title*="Copy selected"],
          [data-preview-mode="true"] button[title*="Paste copied"] {
            display: none !important;
          }
          [data-preview-mode="true"] [role="button"],
          [data-preview-mode="true"] svg circle,
          [data-preview-mode="true"] svg rect,
          [data-preview-mode="true"] svg text,
          [data-preview-mode="true"] svg polyline {
            pointer-events: none !important;
          }
        `}</style>
        <div data-preview-mode="true" style={{ width: '100%', height: '100%' }}>
          <WorkstationGrid
            puzzleId={`arsenal-preview-${piece.id}`}
            inputs={inputLabels}
            outputs={outputLabels}
            catalog={catalog}
            placed={placed}
            wires={wires}
            selectedComponent={{ mode: 'none' }}
            onSelectedComponentChange={() => {}} // Read-only: no changes
            onPlacedChange={() => {}} // Read-only: no changes
            onWiresChange={() => {}} // Read-only: no changes
            draggedPaletteComponentId={null}
            isChecking={false}
            boardRows={gridRows}
            boardCols={gridCols}
          />
        </div>
      </div>

      {/* Component Legend */}
      {placed.length > 0 && (
        <div className="bg-secondary/30 rounded-lg p-3 border border-border/60">
          <p className="text-xs font-semibold text-foreground/70 mb-2">
            Components Used:
          </p>
          <div className="flex flex-wrap gap-2">
            {placed
              .filter(
                (comp, idx, arr) =>
                  arr.findIndex((c) => c.componentId === comp.componentId) ===
                  idx,
              )
              .map((comp) => (
                <div
                  key={comp.componentId}
                  className="flex items-center gap-2 text-xs"
                >
                  <span className="text-foreground/70">{comp.componentId}</span>
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}
