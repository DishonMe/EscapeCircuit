'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';

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
import {
  useMyArsenal,
  useDeleteArsenalPiece,
  useRenameArsenalPiece,
  useUpdateArsenalPiece,
  ArsenalPiece,
} from '@/features/arsenal/api';
import { InfoPopup } from '@/components/ui/info-popup';
import { WorkstationGrid } from '@/app/app/puzzles/[id]/_components/workstation-grid';
import type { PlacedGridComponent, ComponentDef } from '@/app/app/puzzles/[id]/_components/workstation-grid';
import {
  LogicNode,
  type LogicNodeDefinition,
  type LogicNodePort,
  type LogicNodeVisualStyle,
} from '@/app/app/puzzles/[id]/_components/node';
import {
  DEFAULT_PIECE_VISUAL_STYLE,
  extractVisualStyleFromComponentLike,
} from '@/app/app/puzzles/[id]/_components/piece-visual-style';
import type { Wire } from '@/types/api';
import { PageTourLauncher } from '@/components/ui/page-tour-launcher';
import { arsenalTourSteps } from '@/config/tourSteps';

const ARSENAL_LEVEL_TIERS: Array<[number, number]> = [
  [2, 5],
  [4, 10],
  [6, 20],
  [8, 35],
];
const ARSENAL_MAX_SLOTS = 50;

const calculateArsenalSlots = (level: number): number => {
  for (const [maxLevelInclusive, slots] of ARSENAL_LEVEL_TIERS) {
    if (level <= maxLevelInclusive) {
      return slots;
    }
  }
  return ARSENAL_MAX_SLOTS;
};

const calculateLevelFromXp = (xp: number): number => {
  const safeXp = Number.isFinite(xp) ? Math.max(0, xp) : 0;
  return Math.floor(Math.sqrt(safeXp / 100)) + 1;
};

const buildPiecePreviewNode = ({
  label,
  numInputs,
  numOutputs,
  visualStyle,
}: {
  label: string;
  numInputs: number;
  numOutputs: number;
  visualStyle?: LogicNodeVisualStyle;
}): LogicNodeDefinition => {
  const safeInputs = Math.max(0, Math.floor(numInputs));
  const safeOutputs = Math.max(0, Math.floor(numOutputs));
  const height = Math.max(1, safeInputs, safeOutputs);
  const width = 3;

  const ports: LogicNodePort[] = [];
  for (let i = 0; i < safeInputs; i += 1) {
    ports.push({
      id: `in${i}`,
      kind: 'input',
      offset: { row: Math.min(i, height - 1), col: 0 },
    });
  }
  for (let i = 0; i < safeOutputs; i += 1) {
    ports.push({
      id: `out${i}`,
      kind: 'output',
      offset: { row: Math.min(i, height - 1), col: width - 1 },
    });
  }

  if (safeInputs !== safeOutputs && safeInputs > 0 && safeOutputs > 0) {
    const lowerKind: 'input' | 'output' = safeInputs < safeOutputs ? 'input' : 'output';
    const lowerPorts = ports
      .filter((port) => port.kind === lowerKind)
      .sort((a, b) => a.offset.row - b.offset.row);

    lowerPorts.forEach((port, index) => {
      const distributedRow = -0.5 + ((index + 1) * height) / (lowerPorts.length + 1);
      port.offset = {
        row: distributedRow,
        col: port.offset.col,
      };
    });
  }

  return {
    label: label.trim() || 'Unnamed Piece',
    size: { w: width, h: height },
    ports,
    visualStyle,
  };
};

const getPiecePortCounts = (piece: ArsenalPiece | null): { numInputs: number; numOutputs: number } => {
  if (!piece) return { numInputs: 1, numOutputs: 1 };

  const fromFields = {
    numInputs: Number(piece.num_inputs),
    numOutputs: Number(piece.num_outputs),
  };

  if (Number.isFinite(fromFields.numInputs) && Number.isFinite(fromFields.numOutputs)) {
    return {
      numInputs: Math.max(0, Math.floor(fromFields.numInputs)),
      numOutputs: Math.max(0, Math.floor(fromFields.numOutputs)),
    };
  }

  try {
    const structure = JSON.parse(piece.structure_json || '{}');
    return {
      numInputs: Math.max(0, Math.floor(Number(structure.numInputs ?? structure.num_inputs ?? 0))),
      numOutputs: Math.max(0, Math.floor(Number(structure.numOutputs ?? structure.num_outputs ?? 0))),
    };
  } catch {
    return { numInputs: 1, numOutputs: 1 };
  }
};

export default function ArsenalPage() {
  const router = useRouter();
  const user = useUser();
  const { addNotification } = useNotifications();
  const { data: arsenal, isLoading } = useMyArsenal();
  const deleteArsenalMutation = useDeleteArsenalPiece();
  const renameArsenalMutation = useRenameArsenalPiece();
  const updateArsenalPieceMutation = useUpdateArsenalPiece();

  const [selectedPiece, setSelectedPiece] = useState<ArsenalPiece | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [showRenameDialog, setShowRenameDialog] = useState(false);
  const [showDesignDialog, setShowDesignDialog] = useState(false);
  const [newName, setNewName] = useState('');
  const [showTruthTable, setShowTruthTable] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [designUseClassic, setDesignUseClassic] = useState(true);
  const [designStyle, setDesignStyle] = useState<Required<LogicNodeVisualStyle>>(
    DEFAULT_PIECE_VISUAL_STYLE,
  );
  const [deletingPieceId, setDeletingPieceId] = useState<number | null>(null);

  const handleDelete = async (piece: ArsenalPiece) => {
    const confirmed = window.confirm(
      `Are you sure you want to delete "${piece.name}"? This action cannot be undone.`
    );
    if (!confirmed) return;

    setDeletingPieceId(piece.id as number);
    try {
      await deleteArsenalMutation.mutateAsync(piece.id as number);
      addNotification({
        type: 'success',
        title: 'Success',
        message: 'Arsenal piece deleted',
      });
    } catch (error: any) {
      // Error notification handled automatically by API client
    } finally {
      setDeletingPieceId(null);
    }
  };

  const handleRename = (piece: ArsenalPiece) => {
    setSelectedPiece(piece);
    setNewName(piece.name);
    setShowRenameDialog(true);
  };

  const handleDesign = (piece: ArsenalPiece) => {
    setSelectedPiece(piece);
    const existingStyle = extractVisualStyleFromComponentLike(piece);
    if (existingStyle) {
      setDesignUseClassic(false);
      setDesignStyle({
        ...DEFAULT_PIECE_VISUAL_STYLE,
        ...existingStyle,
      });
    } else {
      setDesignUseClassic(true);
      setDesignStyle(DEFAULT_PIECE_VISUAL_STYLE);
    }
    setShowDesignDialog(true);
  };

  const confirmRename = async () => {
    if (!selectedPiece || !newName.trim()) return;
    try {
      await renameArsenalMutation.mutateAsync({
        pieceId: selectedPiece.id as number,
        newName: newName.trim(),
      });
      addNotification({
        type: 'success',
        title: 'Success',
        message: 'Arsenal piece renamed',
      });
      setShowRenameDialog(false);
      setSelectedPiece(null);
      setNewName('');
    } catch (error: any) {
      // Error notification handled automatically by API client
    }
  };

  const confirmDesign = async () => {
    if (!selectedPiece) return;

    const pieceId = Number(selectedPiece.id);
    if (!Number.isFinite(pieceId)) {
      addNotification({
        type: 'error',
        title: 'Error',
        message: 'Invalid piece id.',
      });
      return;
    }

    try {
      await updateArsenalPieceMutation.mutateAsync({
        pieceId,
        visualStyle: designUseClassic ? {} : designStyle,
      });

      addNotification({
        type: 'success',
        title: 'Success',
        message: designUseClassic
          ? 'Piece design reset to classic look'
          : 'Piece design updated',
      });

      setShowDesignDialog(false);
    } catch (error: any) {
      // Error notification handled by API client
    }
  };

  const handleViewDetails = (piece: ArsenalPiece) => {
    setSelectedPiece(piece);
    setShowTruthTable(true);
  };

  const parseTruthTable = (truthTableJson: string) => {
    try {
      return JSON.parse(truthTableJson || '{}');
    } catch {
      return {};
    }
  };

  const parseBasicGates = (basicGatesJson: string) => {
    try {
      const gates = JSON.parse(basicGatesJson || '[]');
      if (!Array.isArray(gates)) return [];
      const counts: Record<string, number> = {};
      gates.forEach((gate) => {
        counts[gate] = (counts[gate] || 0) + 1;
      });
      return Object.entries(counts).map(([gate, count]) => `${gate}${count > 1 ? ` x${count}` : ''}`);
    } catch {
      return [];
    }
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  const pieces = arsenal || [];
  const { numInputs: designPreviewInputs, numOutputs: designPreviewOutputs } = getPiecePortCounts(selectedPiece);
  const designPreviewNode = buildPiecePreviewNode({
    label: selectedPiece?.name ?? '',
    numInputs: designPreviewInputs,
    numOutputs: designPreviewOutputs,
    visualStyle: designUseClassic ? undefined : designStyle,
  });
  const role = String(user.data?.role || '').toLowerCase();
  const isAdmin = role === 'admin';
  const level = calculateLevelFromXp(Number(user.data?.xp || 0));
  const maxSlots = calculateArsenalSlots(level);

  return (
    <>
      <PageTourLauncher
        tourName="arsenal"
        pageTitle="My Arsenal"
        pageDescription="Explore your saved custom pieces, preview them, and manage actions like rename or delete."
        steps={arsenalTourSteps}
        side="left"
      />
      <div className="space-y-6">
        {/* Header */}
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-foreground">My Arsenal 🧰</h1>
            <div className="flex items-center gap-1 text-foreground/85">
              <span>
                {isAdmin
                  ? `Custom logic pieces you've created (${pieces.length}/Unlimited - Admin)`
                  : `Custom logic pieces you've created (${pieces.length}/${maxSlots})`}
              </span>
              {!isAdmin && (
                <InfoPopup>
                  <p className="font-medium text-foreground mb-1">Arsenal Capacity</p>
                  <p>Your arsenal slots increase as you level up:</p>
                  <ul className="mt-1 space-y-0.5 list-disc list-inside">
                    <li>Level 1-2: 5 slots</li>
                    <li>Level 3-4: 10 slots</li>
                    <li>Level 5-6: 20 slots</li>
                    <li>Level 7-8: 35 slots</li>
                    <li>Level 9+: 50 slots</li>
                  </ul>
                </InfoPopup>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button onClick={() => router.push(paths.app.arsenal.creator.getHref())}>
              + Create New Piece
            </Button>
          </div>
      </div>

      {/* Arsenal Grid */}
      {pieces.length === 0 ? (
        <div className="text-center py-12 bg-card rounded-lg border border-border/70">
          <p className="text-foreground/80 mb-4">No arsenal pieces yet</p>
          <Button onClick={() => router.push(paths.app.arsenal.creator.getHref())}>
            Create Your First Piece
          </Button>
        </div>
      ) : (
        <div className="bg-card rounded-lg border overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full tour-arsenal-list">
              <thead className="bg-muted/70">
                <tr>
                  <th className="px-6 py-3 text-left text-[13px] font-semibold text-foreground">Name</th>
                  <th className="px-6 py-3 text-left text-[13px] font-semibold text-foreground">
                    <span className="inline-flex items-center gap-1">
                      Cost
                      <InfoPopup>
                        <p className="font-medium text-foreground mb-1">Piece Cost</p>
                        <p>The total gate cost when this piece is used in a puzzle. Counts toward the puzzle's budget limit.</p>
                      </InfoPopup>
                    </span>
                  </th>
                  <th className="px-6 py-3 text-left text-[13px] font-semibold text-foreground">Basic Gates</th>
                  <th className="px-6 py-3 text-right text-[13px] font-semibold text-foreground">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {pieces.map((piece) => (
                  <tr key={piece.id} className="hover:bg-muted/50">
                    <td className="px-6 py-4 font-medium text-foreground">{piece.name}</td>
                    <td className="px-6 py-4">
                      <span className="bg-secondary text-foreground px-2 py-1 rounded-md text-[13px] font-medium">
                        {piece.cost}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-[13px] text-foreground/80">
                      {parseBasicGates(piece.basic_gates).join(', ') || 'None'}
                    </td>
                    <td className="px-6 py-4 text-right space-x-2 tour-arsenal-actions">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setSelectedPiece(piece);
                          setShowPreview(true);
                        }}
                        className="tour-arsenal-preview"
                      >
                        Preview
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDesign(piece)}
                      >
                        Design
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleRename(piece)}
                      >
                        Rename
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-destructive hover:text-destructive"
                        onClick={() => handleDelete(piece)}
                      >
                        Delete
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      {/* Delete Confirmation Dialog */}
      {/* Using native window.confirm for delete confirmation */}

      {/* Rename Dialog */}
      <Dialog open={showRenameDialog} onOpenChange={setShowRenameDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Rename Arsenal Piece</DialogTitle>
            <DialogDescription>
              Enter a new name for this arsenal piece.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="text-[13px] font-medium text-foreground">New Name</label>
              <input
                type="text"
                value={newName}
                onChange={(e: any) => setNewName(e.target.value)}
                placeholder="Enter new name"
                className="w-full mt-1 border border-border rounded-lg bg-transparent p-2 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
                onKeyDown={(e: any) => {
                  if (e.key === 'Enter') confirmRename();
                }}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowRenameDialog(false)}>
              Cancel
            </Button>
            <Button onClick={confirmRename} disabled={!newName.trim()}>
              Rename
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Design Dialog */}
      <Dialog open={showDesignDialog} onOpenChange={setShowDesignDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Piece Design</DialogTitle>
            <DialogDescription>
              Customize this arsenal piece look. Changes apply wherever this piece is used.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3">
            <label className="flex items-center justify-between rounded-lg border border-border/60 bg-secondary/30 px-3 py-2 text-[13px]">
              <span className="font-medium text-foreground">Use classic default look</span>
              <input
                type="checkbox"
                checked={designUseClassic}
                onChange={(e) => setDesignUseClassic(e.target.checked)}
                className="size-4 rounded border-border"
              />
            </label>

            {!designUseClassic ? (
              <div className="rounded-lg border border-border/70 bg-secondary/30 p-3">
                <div className="grid grid-cols-2 gap-2 text-[12px]">
                  <label className="flex flex-col gap-1 text-muted-foreground">
                    Accent
                    <div className="flex items-center gap-2">
                      <input
                        type="color"
                        value={designStyle.accentColor}
                        onChange={(e: any) =>
                          setDesignStyle((prev) => ({
                            ...prev,
                            accentColor: e.target.value,
                          }))
                        }
                        className="h-8 w-10 cursor-pointer rounded border border-border bg-card p-1"
                      />
                      <span className="font-mono text-[11px] text-foreground">{designStyle.accentColor}</span>
                    </div>
                  </label>

                  <label className="flex flex-col gap-1 text-muted-foreground">
                    Roundness
                    <input
                      type="range"
                      min={0}
                      max={10}
                      step={1}
                      value={designStyle.roundness}
                      onChange={(e: any) =>
                        setDesignStyle((prev) => ({
                          ...prev,
                          roundness: Number(e.target.value),
                        }))
                      }
                      className="h-8"
                    />
                    <span className="text-[11px] text-foreground/75">{designStyle.roundness} / 10</span>
                  </label>

                  <label className="flex flex-col gap-1 text-muted-foreground">
                    Border
                    <select
                      value={designStyle.borderStyle}
                      onChange={(e: any) =>
                        setDesignStyle((prev) => ({
                          ...prev,
                          borderStyle: e.target.value,
                        }))
                      }
                      className="rounded border border-border bg-card px-2 py-1 text-foreground"
                    >
                      <option value="solid">Solid</option>
                      <option value="double">Double</option>
                      <option value="etched">Etched</option>
                    </select>
                  </label>

                  <label className="flex flex-col gap-1 text-muted-foreground">
                    Edge Add-on
                    <select
                      value={designStyle.edgeAddon}
                      onChange={(e: any) =>
                        setDesignStyle((prev) => ({
                          ...prev,
                          edgeAddon: e.target.value,
                        }))
                      }
                      className="rounded border border-border bg-card px-2 py-1 text-foreground"
                    >
                      <option value="none">None</option>
                      <option value="chip-legs">Chip Legs</option>
                    </select>
                  </label>

                  <label className="col-span-2 flex flex-col gap-1 text-muted-foreground">
                    Surface
                    <select
                      value={designStyle.surfaceStyle}
                      onChange={(e: any) =>
                        setDesignStyle((prev) => ({
                          ...prev,
                          surfaceStyle: e.target.value,
                        }))
                      }
                      className="rounded border border-border bg-card px-2 py-1 text-foreground"
                    >
                      <option value="flat">Flat</option>
                      <option value="brushed">Brushed</option>
                      <option value="gradient">Gradient</option>
                      <option value="matte">Matte</option>
                      <option value="glass">Glass</option>
                      <option value="carbon">Carbon</option>
                    </select>
                  </label>
                </div>
              </div>
            ) : null}

            <div className="rounded-lg border border-border/70 bg-secondary/30 p-3">
              <p className="mb-2 text-[13px] font-medium text-foreground">Piece Preview</p>
              <div className="rounded-md border border-border/60 bg-background/80 p-4">
                <div className="flex items-center justify-center">
                  <LogicNode node={designPreviewNode} cellPx={22} portPx={8} />
                </div>
                <div className="mt-3 grid grid-cols-3 gap-2 text-[11px] text-foreground/80">
                  <div className="rounded border border-border/50 bg-card px-2 py-1">
                    <span className="text-foreground/60">Name:</span> {designPreviewNode.label}
                  </div>
                  <div className="rounded border border-border/50 bg-card px-2 py-1">
                    <span className="text-foreground/60">Inputs:</span> {designPreviewInputs}
                  </div>
                  <div className="rounded border border-border/50 bg-card px-2 py-1">
                    <span className="text-foreground/60">Outputs:</span> {designPreviewOutputs}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDesignDialog(false)}>
              Cancel
            </Button>
            <Button onClick={confirmDesign} disabled={updateArsenalPieceMutation.isPending}>
              {updateArsenalPieceMutation.isPending ? 'Saving...' : 'Save Design'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Details Dialog */}
      {selectedPiece && (
        <Dialog open={showTruthTable} onOpenChange={setShowTruthTable}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>{selectedPiece.name} - Details</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <h3 className="font-semibold mb-2">Basic Gates Used</h3>
                <div className="bg-secondary/60 p-3 rounded-lg text-[13px] text-foreground border border-border/60">
                  {parseBasicGates(selectedPiece.basic_gates).join(', ') || 'None'} (Cost: {selectedPiece.cost})
                </div>
              </div>

              <div>
                <h3 className="font-semibold mb-2">Truth Table</h3>
                <div className="max-h-96 overflow-auto border border-border rounded-lg">
                  <table className="w-full text-sm">
                    <thead className="bg-secondary sticky top-0">
                      <tr>
                        <th className="px-3 py-2 text-left text-[13px] font-semibold text-foreground">Inputs</th>
                        <th className="px-3 py-2 text-left text-[13px] font-semibold text-foreground">Outputs</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(parseTruthTable(selectedPiece.truth_table)).map(
                        ([inputKey, output], idx) => (
                          <tr key={idx} className="border-t hover:bg-muted/50">
                            <td className="px-3 py-2 font-mono text-xs text-foreground">{inputKey}</td>
                            <td className="px-3 py-2 font-mono text-xs text-foreground">
                              {JSON.stringify(output)}
                            </td>
                          </tr>
                        )
                      )}
                    </tbody>
                  </table>
                  {Object.keys(parseTruthTable(selectedPiece.truth_table)).length === 0 && (
                    <div className="p-4 text-center text-foreground/75">
                      No truth table data available
                    </div>
                  )}
                </div>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      )}

      {/* Preview Dialog */}
      {selectedPiece && (
        <Dialog open={showPreview} onOpenChange={setShowPreview}>
          <DialogContent className="max-w-4xl max-h-[85vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>{selectedPiece.name} - Circuit Preview</DialogTitle>
              <DialogDescription>
                Read-only preview of the circuit. No modifications allowed.
              </DialogDescription>
            </DialogHeader>
            <CircuitPreview piece={selectedPiece} />
          </DialogContent>
        </Dialog>
      )}
    </div>
    </>
  );
}

function CircuitPreview({ piece }: { piece: ArsenalPiece }) {
  const { data: myArsenal } = useMyArsenal();

  const parseStructure = (
    structureJson: string
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
  const inputLabels = Array.from({ length: structure.numInputs }, (_, i) => `in${i}`);
  const outputLabels = Array.from({ length: structure.numOutputs }, (_, i) => `out${i}`);

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
    AND: { id: 'AND', label: 'AND', cost: 1, size: { w: 3, h: 2 }, ports: [{ id: 'P0', kind: 'input', offset: { row: 0, col: 0 } }, { id: 'P1', kind: 'input', offset: { row: 1, col: 0 } }, { id: 'P2', kind: 'output', offset: { row: 1, col: 2 } }] },
    OR: { id: 'OR', label: 'OR', cost: 1, size: { w: 3, h: 2 }, ports: [{ id: 'P0', kind: 'input', offset: { row: 0, col: 0 } }, { id: 'P1', kind: 'input', offset: { row: 1, col: 0 } }, { id: 'P2', kind: 'output', offset: { row: 1, col: 2 } }] },
    NOT: { id: 'NOT', label: 'NOT', cost: 1, size: { w: 3, h: 1 }, ports: [{ id: 'P0', kind: 'input', offset: { row: 0, col: 0 } }, { id: 'P1', kind: 'output', offset: { row: 0, col: 2 } }] },
    XOR: { id: 'XOR', label: 'XOR', cost: 2, size: { w: 3, h: 2 }, ports: [{ id: 'P0', kind: 'input', offset: { row: 0, col: 0 } }, { id: 'P1', kind: 'input', offset: { row: 1, col: 0 } }, { id: 'P2', kind: 'output', offset: { row: 1, col: 2 } }] },
    NAND: { id: 'NAND', label: 'NAND', cost: 1, size: { w: 3, h: 2 }, ports: [{ id: 'P0', kind: 'input', offset: { row: 0, col: 0 } }, { id: 'P1', kind: 'input', offset: { row: 1, col: 0 } }, { id: 'P2', kind: 'output', offset: { row: 1, col: 2 } }] },
    NOR: { id: 'NOR', label: 'NOR', cost: 1, size: { w: 3, h: 2 }, ports: [{ id: 'P0', kind: 'input', offset: { row: 0, col: 0 } }, { id: 'P1', kind: 'input', offset: { row: 1, col: 0 } }, { id: 'P2', kind: 'output', offset: { row: 1, col: 2 } }] },
    XNOR: { id: 'XNOR', label: 'XNOR', cost: 2, size: { w: 3, h: 2 }, ports: [{ id: 'P0', kind: 'input', offset: { row: 0, col: 0 } }, { id: 'P1', kind: 'input', offset: { row: 1, col: 0 } }, { id: 'P2', kind: 'output', offset: { row: 1, col: 2 } }] },
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
        const ports: Array<{ id: string; kind: 'input' | 'output'; offset: { row: number; col: number } }> = [];
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
          visualStyle: extractVisualStyleFromComponentLike(arsenalPiece),
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

  const gridRows = Math.max(15, Math.max(...placed.map((c) => c.origin.row), 0) + 3);
  const gridCols = Math.max(30, Math.max(...placed.map((c) => c.origin.col), 0) + 3);

  return (
    <div className="space-y-4">
      {/* Description */}
      {piece.description && (
        <div className="bg-foreground/5 border border-border/40 rounded-lg p-3">
          <p className="text-sm text-foreground">{piece.description}</p>
        </div>
      )}

      {/* Circuit Stats */}
      <div className="grid grid-cols-4 gap-3">
        <div className="bg-secondary/40 p-3 rounded-lg border border-border/60">
          <p className="text-xs text-foreground/70 mb-1">Inputs</p>
          <p className="text-lg font-semibold text-foreground">{structure.numInputs}</p>
        </div>
        <div className="bg-secondary/40 p-3 rounded-lg border border-border/60">
          <p className="text-xs text-foreground/70 mb-1">Outputs</p>
          <p className="text-lg font-semibold text-foreground">{structure.numOutputs}</p>
        </div>
        <div className="bg-secondary/40 p-3 rounded-lg border border-border/60">
          <p className="text-xs text-foreground/70 mb-1">Components</p>
          <p className="text-lg font-semibold text-foreground">{placed.length}</p>
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
            onPlacedChange={() => {}}             // Read-only: no changes
            onWiresChange={() => {}}              // Read-only: no changes
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
          <p className="text-xs font-semibold text-foreground/70 mb-2">Components Used:</p>
          <div className="flex flex-wrap gap-2">
            {placed
              .filter((comp, idx, arr) => arr.findIndex((c) => c.componentId === comp.componentId) === idx)
              .map((comp) => (
                <div key={comp.componentId} className="flex items-center gap-2 text-xs">
                  <span className="text-foreground/70">{comp.componentId}</span>
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}
