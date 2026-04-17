'use client';

import { useRouter } from 'next/navigation';
import { useCallback, useMemo, useState } from 'react';

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
import { useSaveArsenalPiece, useMyArsenal } from '@/features/arsenal/api';
import { CircuitComponent, Wire } from '@/types/api';
import {
  WorkstationGrid,
  type ComponentDef,
  type PlacedGridComponent,
  type SelectedComponentState,
} from '@/app/app/puzzles/[id]/_components/workstation-grid';
import { WorkstationMenu } from '@/app/app/puzzles/[id]/_components/workstation-menu';
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
import dynamic from 'next/dynamic';
const CircuitDebugger = dynamic(
  () => import('@/components/circuit-debugger').then(mod => ({ default: mod.CircuitDebugger })),
  { ssr: false, loading: () => <div className="flex items-center justify-center p-8 text-muted-foreground">Loading debugger...</div> }
);

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

type SaveState =
  | { open: false }
  | { open: true; saving: boolean; error?: string };

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

export default function ArsenalCreatorPage() {
  const router = useRouter();
  const { addNotification } = useNotifications();

  const [numInputs, setNumInputs] = useState(2);
  const [numOutputs, setNumOutputs] = useState(1);
  const [pieceName, setPieceName] = useState('');
  const [pieceDescription, setPieceDescription] = useState('');
  const [pieceVisualStyle, setPieceVisualStyle] = useState<Required<LogicNodeVisualStyle>>(
    DEFAULT_PIECE_VISUAL_STYLE,
  );
  const [showNameDialog, setShowNameDialog] = useState(false);
  const [showDebugger, setShowDebugger] = useState(false);
  const [saveState, setSaveState] = useState<SaveState>({ open: false });

  const [placed, setPlaced] = useState<PlacedGridComponent[]>([]);
  const [wires, setWires] = useState<Wire[]>([]);
  const [selectedComponent, setSelectedComponent] = useState<SelectedComponentState>({
    mode: 'none',
  });
  const [draggedPaletteComponentId, setDraggedPaletteComponentId] = useState<
    string | null
  >(null);

  const saveArsenalMutation = useSaveArsenalPiece();
  const { data: myArsenalData } = useMyArsenal();

  const hasCustomPieceVisualStyle = useMemo(() => {
    return (
      pieceVisualStyle.accentColor.toLowerCase() !==
        DEFAULT_PIECE_VISUAL_STYLE.accentColor.toLowerCase() ||
      pieceVisualStyle.roundness !== DEFAULT_PIECE_VISUAL_STYLE.roundness ||
      pieceVisualStyle.borderStyle !== DEFAULT_PIECE_VISUAL_STYLE.borderStyle ||
      pieceVisualStyle.edgeAddon !== DEFAULT_PIECE_VISUAL_STYLE.edgeAddon ||
      pieceVisualStyle.surfaceStyle !== DEFAULT_PIECE_VISUAL_STYLE.surfaceStyle
    );
  }, [pieceVisualStyle]);

  const saveDialogPreviewNode = useMemo(() => {
    return buildPiecePreviewNode({
      label: pieceName,
      numInputs,
      numOutputs,
      visualStyle: hasCustomPieceVisualStyle ? pieceVisualStyle : undefined,
    });
  }, [pieceName, numInputs, numOutputs, hasCustomPieceVisualStyle, pieceVisualStyle]);

  // Convert arsenal pieces to CircuitComponent format
  const arsenalComponents = useMemo(() => {
    if (!myArsenalData) return [];
    return myArsenalData.map((piece) => {
      const visualStyle = extractVisualStyleFromComponentLike(piece);

      return {
        id: String(piece.id),
        type: piece.name,
        cost: piece.cost,
        pins: (piece as any).num_inputs + (piece as any).num_outputs,
        basic_gates: piece.basic_gates,
        truth_table: piece.truth_table,
        is_arsenal: piece.is_arsenal,
        num_inputs: (piece as any).num_inputs ?? 0,
        num_outputs: (piece as any).num_outputs ?? 0,
        visual_style: visualStyle,
      } as CircuitComponent;
    });
  }, [myArsenalData]);
  const inputs = useMemo(() => {
    return Array.from({ length: numInputs }, (_, i) => `in${i}`);
  }, [numInputs]);

  const outputs = useMemo(() => {
    return Array.from({ length: numOutputs }, (_, i) => `out${i}`);
  }, [numOutputs]);

  // Build component catalog for UI
  const componentCatalog = useMemo(() => {
    const byId = new Map<string, CircuitComponent>();
    // Add basic components
    for (const c of BASIC_COMPONENTS) {
      byId.set(c.id, c);
    }
    // Add arsenal pieces
    for (const c of arsenalComponents) {
      byId.set(c.id, c);
    }
    return byId;
  }, [arsenalComponents]);

  // Build UI catalog with port definitions
  const uiCatalog = useMemo(() => {
    const toDefaultPorts = (
      pins: number,
      size: { w: number; h: number },
    ): Array<{
      id: string;
      kind: 'input' | 'output';
      offset: { row: number; col: number };
    }> => {
      const outputsCount = 1;
      const inputsCount = Math.max(1, pins - outputsCount);

      const ports: Array<{
        id: string;
        kind: 'input' | 'output';
        offset: { row: number; col: number };
      }> = [];

      for (let i = 0; i < inputsCount; i++) {
        ports.push({
          id: `IN${i}`,
          kind: 'input',
          offset: { row: Math.min(i, size.h - 1), col: 0 },
        });
      }

      for (let i = 0; i < outputsCount; i++) {
        ports.push({
          id: `OUT${i}`,
          kind: 'output',
          offset: { row: 0, col: Math.max(0, size.w - 1) },
        });
      }

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
    };

    const ui = new Map<string, ComponentDef>();
    for (const [id, def] of componentCatalog.entries()) {
      const hc = hardcoded[def.type];
      const isArsenal = (def as any).is_arsenal === true;
      const visualStyle = extractVisualStyleFromComponentLike(def);
      
      let size: { w: number; h: number };
      let ports: Array<{ id: string; kind: 'input' | 'output'; offset: { row: number; col: number } }>;
      
      if (isArsenal) {
        // Arsenal piece sizing: width=3, height=max(inputs, outputs)
        const numInputs = (def as any).num_inputs ?? 0;
        const numOutputs = (def as any).num_outputs ?? 0;
        const maxPorts = Math.max(numInputs, numOutputs);
        size = { w: 3, h: Math.max(1, maxPorts) };
        
        // Generate ports for arsenal pieces
        const ports_list: Array<{ id: string; kind: 'input' | 'output'; offset: { row: number; col: number } }> = [];
        for (let i = 0; i < numInputs; i++) {
          ports_list.push({
            id: `in${i}`,
            kind: 'input',
            offset: { row: Math.min(i, size.h - 1), col: 0 },
          });
        }
        for (let i = 0; i < numOutputs; i++) {
          ports_list.push({
            id: `out${i}`,
            kind: 'output',
            offset: { row: Math.min(i, size.h - 1), col: size.w - 1 },
          });
        }
        ports = ports_list;
      } else {
        // Basic gates use hardcoded or calculated sizing
        size = hc?.size ?? {
          w: 4,
          h: Math.max(1, Math.min(4, Math.ceil(def.pins / 2))),
        };
        ports = hc?.ports ?? toDefaultPorts(def.pins, size);
      }
      
      ui.set(id, {
        id,
        label: def.type,
        cost: def.cost,
        size,
        ports,
        visualStyle,
      });
    }
    return Object.fromEntries(Array.from(ui.entries())) as Record<
      string,
      ComponentDef
    >;
  }, [componentCatalog]);

  // Calculate total cost from placed components
  const currentCost = useMemo(() => {
    return placed.reduce((acc, p) => {
      const def = componentCatalog.get(p.componentId);
      return acc + (def?.cost ?? 0);
    }, 0);
  }, [componentCatalog, placed]);

  // Extract direct basic gates and track which arsenal pieces are used
  const extractGatesAndArsenal = useCallback(() => {
    const gates: string[] = [];
    const usedArsenalPieceIds: number[] = [];
    
    for (const p of placed) {
      const def = componentCatalog.get(p.componentId);
      if (def) {
        const isArsenal = (def as any).is_arsenal === true;
        if (isArsenal) {
          // Track which arsenal piece is used (but don't flatten its gates yet)
          usedArsenalPieceIds.push(parseInt(def.id));
        } else {
          // This is a basic gate - include it directly
          gates.push(def.type);
        }
      }
    }
    return { gates, usedArsenalPieceIds };
  }, [placed, componentCatalog]);

  const handleSave = async () => {
    if (!pieceName.trim()) {
      addNotification({
        type: 'error',
        title: 'Error',
        message: 'Please enter a piece name',
      });
      return;
    }

    if (!pieceDescription.trim()) {
      addNotification({
        type: 'error',
        title: 'Error',
        message: 'A description is required for Arsenal components.',
      });
      return;
    }

    if (placed.length === 0) {
      addNotification({
        type: 'error',
        title: 'Error',
        message: 'Please add at least one component to your circuit',
      });
      return;
    }

    setSaveState({ open: true, saving: true });

    try {
      const { gates, usedArsenalPieceIds } = extractGatesAndArsenal();

      const structurePayload: Record<string, unknown> = {
        numInputs,
        numOutputs,
        placed,
        wires,
      };

      if (hasCustomPieceVisualStyle) {
        structurePayload.visualStyle = pieceVisualStyle;
      }

      const savePayload = {
        name: pieceName.trim(),
        description: pieceDescription.trim(),
        num_inputs: numInputs,
        num_outputs: numOutputs,
        structure_json: JSON.stringify(structurePayload),
        basic_gates: JSON.stringify(gates),
        truth_table: {},
        used_arsenal_pieces: usedArsenalPieceIds,
      };

      await saveArsenalMutation.mutateAsync(savePayload as any);

      addNotification({
        type: 'success',
        title: 'Success',
        message: `Arsenal piece "${pieceName}" created successfully!`,
      });

      setShowNameDialog(false);
      setPieceDescription('');
      setPieceVisualStyle(DEFAULT_PIECE_VISUAL_STYLE);
      setSaveState({ open: false });
      router.push(paths.app.arsenal.root.getHref());
    } catch (error: any) {
      setSaveState({
        open: true,
        saving: false,
        error: error?.response?.data?.detail || 'Failed to save arsenal piece. Please check your circuit and try again.',
      });
      // Error notification handled automatically by API client
    }
  };

  const handlePlacedChange = useCallback((newPlaced: PlacedGridComponent[]) => {
    setPlaced(newPlaced);
  }, []);

  return (
    <div className="flex flex-col h-full gap-2">
      {/* Header + Compact Config Bar */}
      <div className="flex flex-wrap items-center gap-4 px-6 pt-3 pb-1">
        <h1 className="text-xl font-semibold tracking-tight text-foreground">Create Arsenal Piece 🛠️</h1>

        <div className="flex items-center gap-3 rounded-lg border border-border bg-card px-3 py-1.5">
          <span className="text-[12px] font-medium text-muted-foreground">Inputs</span>
          <select
            value={numInputs}
            onChange={(e: any) => setNumInputs(parseInt(e.target.value))}
            className="border border-border rounded bg-card text-foreground px-1.5 py-0.5 text-[12px] focus:outline-none focus:ring-1 focus:ring-ring"
          >
            {[1, 2, 3, 4, 5].map((n) => (
              <option key={n} value={n}>{n}</option>
            ))}
          </select>
          <span className="text-[12px] font-medium text-muted-foreground">Outputs</span>
          <select
            value={numOutputs}
            onChange={(e: any) => setNumOutputs(parseInt(e.target.value))}
            className="border border-border rounded bg-card text-foreground px-1.5 py-0.5 text-[12px] focus:outline-none focus:ring-1 focus:ring-ring"
          >
            {[1, 2, 3].map((n) => (
              <option key={n} value={n}>{n}</option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-3 rounded-lg border border-border bg-card px-3 py-1.5 text-[12px]">
          <span className="text-muted-foreground">Components: <span className="font-medium text-foreground">{placed.length}</span></span>
          <span className="text-muted-foreground">Cost: <span className="font-medium text-foreground">{currentCost}</span></span>
          <span className="text-muted-foreground">Wires: <span className="font-medium text-foreground">{wires.length}</span></span>
        </div>

        <div className="flex items-center gap-2">
          <Button
            onClick={() => setShowDebugger(true)}
            variant="outline"
            size="sm"
          >
            Debug
          </Button>
          <Button
            onClick={() => setShowNameDialog(true)}
            disabled={placed.length === 0}
            size="sm"
          >
            Save Piece
          </Button>
        </div>

        <Button variant="outline" size="sm" className="ml-auto" onClick={() => router.push(paths.app.arsenal.root.getHref())}>
          Back to Arsenal
        </Button>
      </div>

      {/* Workstation - Main grid layout (stretches full remaining height) */}
      <div className="flex-1 px-6 pb-3 flex gap-4 min-h-0">
        <WorkstationMenu
          basic={BASIC_COMPONENTS}
          custom={[]}
          sharedArsenal={[]}
          solverArsenal={arsenalComponents}
          allowArsenal={true}
          filteredBasicTypes={[]}
          selectedComponentId={
            selectedComponent.mode === 'placing' ? selectedComponent.componentId : undefined
          }
          onSelectComponent={(componentId) =>
            setSelectedComponent({ mode: 'placing', componentId, rotation: 0 })
          }
          onDragStart={setDraggedPaletteComponentId}
          onDragEnd={() => setDraggedPaletteComponentId(null)}
        />

        <WorkstationGrid
          puzzleId="arsenal-creator"
          inputs={inputs}
          outputs={outputs}
          catalog={uiCatalog}
          placed={placed}
          wires={wires}
          selectedComponent={selectedComponent}
          onSelectedComponentChange={setSelectedComponent}
          onPlacedChange={handlePlacedChange}
          onWiresChange={setWires}
          draggedPaletteComponentId={draggedPaletteComponentId}
          viewportClassName="h-full"
        />
      </div>

      {/* Save Dialog */}
      <Dialog open={showNameDialog} onOpenChange={setShowNameDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Save Arsenal Piece</DialogTitle>
            <DialogDescription>Give your custom logic piece a unique name and description.</DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div>
              <label className="text-[13px] font-medium text-foreground block mb-2">Piece Name</label>
              <input
                type="text"
                value={pieceName}
                onChange={(e: any) => setPieceName(e.target.value)}
                placeholder="Enter piece name (must be unique)"
                className="w-full border border-border rounded-lg bg-transparent p-2 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
                onKeyDown={(e: any) => {
                  if (e.key === 'Enter' && pieceName.trim() && pieceDescription.trim()) handleSave();
                }}
              />
            </div>

            <div>
              <label className="text-[13px] font-medium text-foreground block mb-2">
                Description <span className="text-red-500">*</span>
              </label>
              <textarea
                value={pieceDescription}
                onChange={(e: any) => setPieceDescription(e.target.value)}
                placeholder="Describe what this component does and how it works..."
                className="w-full border border-border rounded-lg bg-transparent p-2 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring resize-none h-20"
              />
              {!pieceDescription.trim() && (
                <p className="text-[11px] text-red-600 mt-1">A description is required for Arsenal components.</p>
              )}
            </div>

            <div className="rounded-lg border border-border/70 bg-secondary/30 p-3">
              <p className="mb-2 text-[13px] font-medium text-foreground">Piece Preview</p>
              <div className="rounded-md border border-border/60 bg-background/80 p-4">
                <div className="flex items-center justify-center">
                  <LogicNode node={saveDialogPreviewNode} cellPx={22} portPx={8} />
                </div>
                <div className="mt-3 grid grid-cols-3 gap-2 text-[11px] text-foreground/80">
                  <div className="rounded border border-border/50 bg-card px-2 py-1">
                    <span className="text-foreground/60">Name:</span> {saveDialogPreviewNode.label}
                  </div>
                  <div className="rounded border border-border/50 bg-card px-2 py-1">
                    <span className="text-foreground/60">Inputs:</span> {numInputs}
                  </div>
                  <div className="rounded border border-border/50 bg-card px-2 py-1">
                    <span className="text-foreground/60">Outputs:</span> {numOutputs}
                  </div>
                </div>
              </div>
            </div>

            <div className="rounded-lg border border-border/70 bg-secondary/30 p-3">
              <p className="mb-2 text-[13px] font-medium text-foreground">Piece Look</p>
              <div className="grid grid-cols-2 gap-2 text-[12px]">
                <label className="flex flex-col gap-1 text-muted-foreground">
                  Accent
                  <div className="flex items-center gap-2">
                    <input
                      type="color"
                      value={pieceVisualStyle.accentColor}
                      onChange={(e: any) =>
                        setPieceVisualStyle((prev) => ({
                          ...prev,
                          accentColor: e.target.value,
                        }))
                      }
                      className="h-8 w-10 cursor-pointer rounded border border-border bg-card p-1"
                    />
                    <span className="font-mono text-[11px] text-foreground">{pieceVisualStyle.accentColor}</span>
                  </div>
                </label>

                <label className="flex flex-col gap-1 text-muted-foreground">
                  Roundness
                  <input
                    type="range"
                    min={0}
                    max={10}
                    step={1}
                    value={pieceVisualStyle.roundness}
                    onChange={(e: any) =>
                      setPieceVisualStyle((prev) => ({
                        ...prev,
                        roundness: Number(e.target.value),
                      }))
                    }
                    className="h-8"
                  />
                  <span className="text-[11px] text-foreground/75">{pieceVisualStyle.roundness} / 10</span>
                </label>

                <label className="flex flex-col gap-1 text-muted-foreground">
                  Border
                  <select
                    value={pieceVisualStyle.borderStyle}
                    onChange={(e: any) =>
                      setPieceVisualStyle((prev) => ({
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
                    value={pieceVisualStyle.edgeAddon}
                    onChange={(e: any) =>
                      setPieceVisualStyle((prev) => ({
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
                    value={pieceVisualStyle.surfaceStyle}
                    onChange={(e: any) =>
                      setPieceVisualStyle((prev) => ({
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

            <div className="bg-secondary/50 p-3 rounded-lg text-[13px] space-y-1">
              <p>
                <span className="text-muted-foreground">Inputs:</span> {numInputs}
              </p>
              <p>
                <span className="text-muted-foreground">Outputs:</span> {numOutputs}
              </p>
              <p>
                <span className="text-muted-foreground">Cost:</span> {currentCost}
              </p>
              <p>
                <span className="text-muted-foreground">Components:</span> {placed.length}
              </p>
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setShowNameDialog(false);
                setSaveState({ open: false });
              }}
              disabled={saveState.open && saveState.saving}
            >
              Cancel
            </Button>
            <Button
              onClick={handleSave}
              disabled={saveState.open && saveState.saving || !pieceName.trim() || !pieceDescription.trim()}
            >
              {saveState.open && saveState.saving ? 'Saving...' : 'Save'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <CircuitDebugger
        isOpen={showDebugger}
        onClose={() => setShowDebugger(false)}
        inputs={inputs}
        outputs={outputs}
        placed={placed}
        wires={wires}
        catalog={uiCatalog}
        puzzleId="arsenal-creator"
      />
    </div>
  );
}
