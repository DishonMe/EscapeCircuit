'use client';

import { useMemo, useState } from 'react';

import { Boxes, CircuitBoard, Gift, Medal, PackageOpen, Trophy } from 'lucide-react';
import Link from 'next/link';

import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { getLevelInfo } from '@/components/ui/xp-bar';
import { paths } from '@/config/paths';
import { useMyArsenal } from '@/features/arsenal/api';
import { EditBio } from '@/features/users/components/edit-bio';
import { useUser } from '@/lib/auth';

type EntryProps = {
  label: string;
  value: string;
};

type ArsenalStructure = {
  placed?: Array<{ id: string; componentId: string; origin?: { row: number; col: number }; x?: number; y?: number }>;
  placedComponents?: Array<{ id: string; componentId: string; x: number; y: number }>;
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

const LEVEL_BENEFIT_CHANGES: LevelBenefitChange[] = LEVEL_BENEFITS
  .map((benefit, index) => {
    if (index === 0) return null;
    const previous = LEVEL_BENEFITS[index - 1];
    const changes: string[] = [];

    if (benefit.arsenalSlots !== previous.arsenalSlots) {
      changes.push(`Arsenal slots ${previous.arsenalSlots}->${benefit.arsenalSlots}`);
    }
    if (benefit.publishedCap !== previous.publishedCap) {
      changes.push(`Published puzzles ${previous.publishedCap}->${benefit.publishedCap}`);
    }
    if (benefit.unpublishedCap !== previous.unpublishedCap) {
      changes.push(`Unpublished puzzles ${previous.unpublishedCap}->${benefit.unpublishedCap}`);
    }

    if (changes.length === 0) return null;
    return { level: benefit.level, changes };
  })
  .filter((entry): entry is LevelBenefitChange => entry !== null);

const Entry = ({ label, value }: EntryProps) => (
  <div className="grid grid-cols-1 gap-1 rounded-xl border border-border bg-card/70 px-4 py-3 sm:grid-cols-[140px_1fr]">
    <dt className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{label}</dt>
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

  if (Array.isArray(structure.placedComponents) && structure.placedComponents.length > 0) {
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
      <div className="absolute inset-0 origin-top-left scale-[0.5]" style={{ width: '200%', height: '200%' }}>
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
              <path d={d} fill="none" stroke="#38bdf8" strokeWidth="3" strokeLinecap="round" />
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
              <div className="flex size-14 items-center justify-center rounded-2xl border border-border bg-secondary text-lg font-semibold text-foreground">
                {initials}
              </div>
              <div>
                <h1 className="text-2xl font-semibold tracking-tight text-foreground">{displayName}</h1>
                <p className="text-sm text-muted-foreground">Circuit Operator Profile</p>
              </div>
            </div>
            <EditBio />
          </div>

          <dl className="mt-4 grid gap-3">
            <Entry label="Email" value={userData.email ?? ''} />
            <Entry label="Role" value={userData.role ?? ''} />
            <Entry label="Joined" value={formatDateOnly(userData.created_at ?? userData.createdAt ?? '')} />
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
                <Button variant="ghost" size="sm" onClick={() => setRewardsOpen(true)}>
                  Rewards
                </Button>
                <span className="rounded-lg bg-secondary px-2 py-1 text-xs font-semibold text-foreground">
                  Level {levelInfo.level}
                </span>
              </div>
            </div>
            <p className="mt-3 text-sm text-muted-foreground">
              XP to next level: <span className="font-semibold text-foreground">{levelInfo.xpIntoLevel}/{levelInfo.xpForLevel}</span>
            </p>
            <div className="mt-3 flex items-center gap-2">
              <span className="text-xs font-semibold text-muted-foreground">{levelInfo.level}</span>
              <div className="h-2 flex-1 overflow-hidden rounded-full bg-secondary">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-cyan-500 to-emerald-500 transition-all duration-500"
                  style={{ width: `${levelInfo.pct}%` }}
                />
              </div>
              <span className="text-xs font-semibold text-muted-foreground">{levelInfo.level + 1}</span>
            </div>
            <p className="mt-2 text-xs text-muted-foreground">{currentXp}/{levelInfo.nextThreshold} total XP</p>
          </div>
          <div className="rounded-2xl border border-border bg-card/80 p-4 shadow-sm">
            <div className="flex items-center gap-2 text-muted-foreground"><Trophy size={16} /> Medals</div>
            <p className="mt-2 text-2xl font-semibold text-foreground">{medalsTotal}</p>
            <div className="mt-2 space-y-1 text-xs">
              <div className="flex items-center justify-between text-muted-foreground">
                <span className="inline-flex items-center gap-1"><Medal size={14} className="text-amber-500" /> Gold</span>
                <span className="font-semibold">{goldMedals}</span>
              </div>
              <div className="flex items-center justify-between text-muted-foreground">
                <span className="inline-flex items-center gap-1"><Medal size={14} className="text-muted-foreground" /> Silver</span>
                <span className="font-semibold">{silverMedals}</span>
              </div>
              <div className="flex items-center justify-between text-muted-foreground">
                <span className="inline-flex items-center gap-1"><Medal size={14} className="text-amber-700" /> Bronze</span>
                <span className="font-semibold">{bronzeMedals}</span>
              </div>
            </div>
          </div>
          <div className="rounded-2xl border border-border bg-card/80 p-4 shadow-sm">
            <div className="flex items-center gap-2 text-muted-foreground"><Boxes size={16} /> Saved Puzzles</div>
            <p className="mt-3 text-3xl font-semibold text-foreground">{savedPuzzleCount}</p>
          </div>
        </div>
      </section>

      <section className="rounded-2xl border border-border bg-card/80 p-5 shadow-sm">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-foreground">Arsenal</h2>
          <span className="text-xs font-medium text-muted-foreground">{arsenal.length} saved</span>
        </div>

        {arsenal.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-border bg-secondary px-6 py-10 text-center">
            <PackageOpen className="mx-auto mb-3 size-10 text-muted-foreground" />
            <p className="text-base font-medium text-muted-foreground">Your Arsenal is empty</p>
            <p className="mt-1 text-sm text-muted-foreground">Build a custom circuit piece to see it here.</p>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {arsenal.map((piece) => (
              <div
                key={String(piece.id)}
                className="rounded-2xl border border-border bg-card/80 p-3 shadow-sm"
              >
                <div className="mb-2 flex items-start justify-between gap-2">
                  <h3 className="text-sm font-semibold text-foreground">{piece.name}</h3>
                  <span className="rounded-md bg-secondary px-2 py-0.5 text-[11px] font-medium text-foreground">cost {piece.cost}</span>
                </div>
                <MiniCircuitPreview structureRaw={piece.structure_json} />
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="rounded-2xl border border-border bg-card/80 p-5 shadow-sm">
        <h2 className="mb-3 text-lg font-semibold text-foreground">Saved Puzzles</h2>
        {userData.saved_puzzles?.length ? (
          <ul className="grid gap-2 md:grid-cols-2">
            {userData.saved_puzzles.map((puzzle: any) => (
              <li key={puzzle.id} className="rounded-xl border border-border bg-card/70 px-3 py-2 text-sm">
                <Link href={`${paths.app.puzzles.getHref()}/${puzzle.id}`} className="font-medium text-foreground underline-offset-2 hover:underline">
                  {puzzle.name}
                </Link>
                <span className="ml-2 text-xs text-muted-foreground">({puzzle.status})</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted-foreground">No saved puzzles yet.</p>
        )}
      </section>

      <Dialog open={rewardsOpen} onOpenChange={setRewardsOpen}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Gift size={18} /> Level Rewards (1-15)
            </DialogTitle>
            <DialogDescription>
              Milestone levels only. Each row shows exactly what changes at that level.
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
                      className={benefit.level === levelInfo.level ? 'bg-cyan-50/70 dark:bg-cyan-950/30' : 'bg-card'}
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
                You are level {levelInfo.level}. Next level in {Math.max(0, levelInfo.nextThreshold - currentXp)} XP.
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                Starting values at level 1 are: Arsenal slots 5, Published puzzles 5, Unpublished puzzles 5.
              </p>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};
