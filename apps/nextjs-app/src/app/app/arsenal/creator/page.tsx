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
import { CircuitDebugger } from '@/components/circuit-debugger';

const BASIC_COMPONENTS: CircuitComponent[] = [
  { id: 'AND', type: 'AND', cost: 1, pins: 3 },
  { id: 'OR', type: 'OR', cost: 1, pins: 3 },
  { id: 'NOT', type: 'NOT', cost: 1, pins: 2 },
  { id: 'XOR', type: 'XOR', cost: 1, pins: 3 },
  { id: 'NAND', type: 'NAND', cost: 1, pins: 3 },
  { id: 'NOR', type: 'NOR', cost: 1, pins: 3 },
  { id: 'XNOR', type: 'XNOR', cost: 1, pins: 3 },
  // DFF intentionally excluded from arsenal creation
];

type SaveState =
  | { open: false }
  | { open: true; saving: boolean; error?: string };

export default function ArsenalCreatorPage() {
  const router = useRouter();
  const { addNotification } = useNotifications();

  const [numInputs, setNumInputs] = useState(2);
  const [numOutputs, setNumOutputs] = useState(1);
  const [pieceName, setPieceName] = useState('');
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

  // Convert arsenal pieces to CircuitComponent format
  const arsenalComponents = useMemo(() => {
    if (!myArsenalData) return [];
    return myArsenalData.map((piece) => ({
      id: String(piece.id),
      type: piece.name,
      cost: piece.cost,
      pins: (piece as any).num_inputs + (piece as any).num_outputs,
      basic_gates: piece.basic_gates,
      truth_table: piece.truth_table,
      is_arsenal: piece.is_arsenal,
      num_inputs: (piece as any).num_inputs ?? 0,
      num_outputs: (piece as any).num_outputs ?? 0,
    } as CircuitComponent));
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
      
      let size: { w: number; h: number };
      let ports: Array<{ id: string; kind: 'input' | 'output'; offset: { row: number; col: number } }>;
      
      if (isArsenal) {
        // Arsenal piece sizing: width=4, height=max(inputs, outputs)
        const numInputs = (def as any).num_inputs ?? 0;
        const numOutputs = (def as any).num_outputs ?? 0;
        const maxPorts = Math.max(numInputs, numOutputs);
        size = { w: 4, h: Math.max(1, maxPorts) };
        
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

      await saveArsenalMutation.mutateAsync({
        name: pieceName.trim(),
        num_inputs: numInputs,
        num_outputs: numOutputs,
        structure_json: JSON.stringify({
          numInputs,
          numOutputs,
          placed,
          wires,
        }),
        basic_gates: JSON.stringify(gates),
        truth_table: {},
        used_arsenal_pieces: usedArsenalPieceIds,
      } as any);

      addNotification({
        type: 'success',
        title: 'Success',
        message: `Arsenal piece "${pieceName}" created successfully!`,
      });

      setShowNameDialog(false);
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
    <div className="flex flex-col h-full gap-4">
      {/* Header */}
      <div className="flex justify-between items-start px-6 pt-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">Create Arsenal Piece</h1>
          <p className="text-muted-foreground">Design custom logic circuits to save for reuse</p>
        </div>
        <Button variant="outline" onClick={() => router.push(paths.app.arsenal.root.getHref())}>
          Back to Arsenal
        </Button>
      </div>

      {/* Configuration Panel */}
      <div className="px-6 flex gap-6">
        {/* I/O Configuration */}
        <div className="bg-card rounded-xl border border-border p-6 space-y-4 w-56">
          <h2 className="font-semibold text-[13px] text-foreground">I/O Configuration</h2>

          <div>
            <label className="text-[13px] font-medium text-foreground block mb-2">Inputs</label>
            <select
              value={numInputs}
              onChange={(e: any) => setNumInputs(parseInt(e.target.value))}
              className="w-full border border-border rounded-lg bg-transparent p-2 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
            >
              {[1, 2, 3, 4, 5].map((n) => (
                <option key={n} value={n}>
                  {n} input{n !== 1 ? 's' : ''}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-[13px] font-medium text-foreground block mb-2">Outputs</label>
            <select
              value={numOutputs}
              onChange={(e: any) => setNumOutputs(parseInt(e.target.value))}
              className="w-full border border-border rounded-lg bg-transparent p-2 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
            >
              {[1, 2, 3].map((n) => (
                <option key={n} value={n}>
                  {n} output{n !== 1 ? 's' : ''}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Statistics */}
        <div className="bg-card rounded-xl border border-border p-6 space-y-3 w-48">
          <h2 className="font-semibold text-[13px] text-foreground">Piece Info</h2>
          <div className="text-[13px] space-y-2">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Components:</span>
              <span className="font-medium">{placed.length}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Total Cost:</span>
              <span className="font-medium">{currentCost}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Wires:</span>
              <span className="font-medium">{wires.length}</span>
            </div>
          </div>
          <Button
            onClick={() => setShowDebugger(true)}
            variant="outline"
            className="w-full mt-2"
          >
            Debug
          </Button>
          <Button
            onClick={() => setShowNameDialog(true)}
            disabled={placed.length === 0}
            className="w-full mt-4"
          >
            Save Piece
          </Button>
        </div>
      </div>

      {/* Workstation - Main grid layout */}
      <div className="flex-1 px-6 flex gap-4 min-h-0">
        <WorkstationMenu
          basic={BASIC_COMPONENTS}
          custom={[]}
          arsenal={arsenalComponents}
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
        />
      </div>

      {/* Save Dialog */}
      <Dialog open={showNameDialog} onOpenChange={setShowNameDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Save Arsenal Piece</DialogTitle>
            <DialogDescription>Give your custom logic piece a unique name.</DialogDescription>
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
                  if (e.key === 'Enter') handleSave();
                }}
              />
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
              disabled={saveState.open && saveState.saving}
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
