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
import { useSaveArsenalPiece } from '@/features/arsenal/api';
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

  // Generate inputs and outputs based on selected counts
  const inputs = useMemo(() => {
    return Array.from({ length: numInputs }, (_, i) => `in${i}`);
  }, [numInputs]);

  const outputs = useMemo(() => {
    return Array.from({ length: numOutputs }, (_, i) => `out${i}`);
  }, [numOutputs]);

  // Build component catalog for UI
  const componentCatalog = useMemo(() => {
    const byId = new Map<string, CircuitComponent>();
    for (const c of BASIC_COMPONENTS) {
      byId.set(c.id, c);
    }
    return byId;
  }, []);

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

  // Calculate total cost from placed components
  const currentCost = useMemo(() => {
    return placed.reduce((acc, p) => {
      const def = componentCatalog.get(p.componentId);
      return acc + (def?.cost ?? 0);
    }, 0);
  }, [componentCatalog, placed]);

  // Extract basic gates from placed components
  const extractBasicGates = useCallback(() => {
    const gates: string[] = [];
    for (const p of placed) {
      const def = componentCatalog.get(p.componentId);
      if (def) {
        gates.push(def.type);
      }
    }
    return gates;
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
      const basicGates = extractBasicGates();

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
        basic_gates: JSON.stringify(basicGates),
        truth_table: {},
      });

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
        error: error?.response?.data?.detail || 'Failed to save piece',
      });
      addNotification({
        type: 'error',
        title: 'Error',
        message: error?.response?.data?.detail || 'Failed to save piece',
      });
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
          <h1 className="text-3xl font-bold">Create Arsenal Piece</h1>
          <p className="text-muted-foreground">Design custom logic circuits to save for reuse</p>
        </div>
        <Button variant="outline" onClick={() => router.push(paths.app.arsenal.root.getHref())}>
          Back to Arsenal
        </Button>
      </div>

      {/* Configuration Panel */}
      <div className="px-6 flex gap-6">
        {/* I/O Configuration */}
        <div className="bg-card rounded-lg border p-6 space-y-4 w-56">
          <h2 className="font-semibold">I/O Configuration</h2>

          <div>
            <label className="text-sm font-medium block mb-2">Inputs</label>
            <select
              value={numInputs}
              onChange={(e: any) => setNumInputs(parseInt(e.target.value))}
              className="w-full border rounded p-2"
            >
              {[1, 2, 3, 4, 5].map((n) => (
                <option key={n} value={n}>
                  {n} input{n !== 1 ? 's' : ''}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-sm font-medium block mb-2">Outputs</label>
            <select
              value={numOutputs}
              onChange={(e: any) => setNumOutputs(parseInt(e.target.value))}
              className="w-full border rounded p-2"
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
        <div className="bg-card rounded-lg border p-6 space-y-3 w-48">
          <h2 className="font-semibold">Piece Info</h2>
          <div className="text-sm space-y-2">
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
          special={[]}
          allowArsenal={false}
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
              <label className="text-sm font-medium block mb-2">Piece Name</label>
              <input
                type="text"
                value={pieceName}
                onChange={(e: any) => setPieceName(e.target.value)}
                placeholder="Enter piece name (must be unique)"
                className="w-full border rounded p-2"
                onKeyDown={(e: any) => {
                  if (e.key === 'Enter') handleSave();
                }}
              />
            </div>

            <div className="bg-muted p-3 rounded text-sm space-y-1">
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
