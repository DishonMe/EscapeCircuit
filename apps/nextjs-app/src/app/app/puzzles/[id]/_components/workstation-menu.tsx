'use client';

import { Info } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { WorkstationGrid } from './workstation-grid';
import type { PlacedGridComponent, ComponentDef } from './workstation-grid';
import { CircuitComponent, CircuitSolution } from '@/types/api';
import { cn } from '@/utils/cn';
import { LogicNode, type LogicNodeDefinition } from './node';
import { useMyArsenal } from '@/features/arsenal/api';

type ArsenalCircuit = {
  id: string;
  name: string;
  usedBasicTypes: string[];
  solution: CircuitSolution;
  description?: string;
};

const ARSENAL_KEY = 'escapecircuit.arsenal.v1';

const TRUTH_TABLES: Record<
  string,
  { inputs: string[]; outputs: string[]; rows: string[][] }
> = {
  AND: {
    inputs: ['A', 'B'],
    outputs: ['OUT'],
    rows: [
      ['0', '0', '0'],
      ['0', '1', '0'],
      ['1', '0', '0'],
      ['1', '1', '1'],
    ],
  },
  OR: {
    inputs: ['A', 'B'],
    outputs: ['OUT'],
    rows: [
      ['0', '0', '0'],
      ['0', '1', '1'],
      ['1', '0', '1'],
      ['1', '1', '1'],
    ],
  },
  NOT: {
    inputs: ['IN'],
    outputs: ['OUT'],
    rows: [
      ['0', '1'],
      ['1', '0'],
    ],
  },
  XOR: {
    inputs: ['A', 'B'],
    outputs: ['OUT'],
    rows: [
      ['0', '0', '0'],
      ['0', '1', '1'],
      ['1', '0', '1'],
      ['1', '1', '0'],
    ],
  },
  NAND: {
    inputs: ['A', 'B'],
    outputs: ['OUT'],
    rows: [
      ['0', '0', '1'],
      ['0', '1', '1'],
      ['1', '0', '1'],
      ['1', '1', '0'],
    ],
  },
  NOR: {
    inputs: ['A', 'B'],
    outputs: ['OUT'],
    rows: [
      ['0', '0', '1'],
      ['0', '1', '0'],
      ['1', '0', '0'],
      ['1', '1', '0'],
    ],
  },
  XNOR: {
    inputs: ['A', 'B'],
    outputs: ['OUT'],
    rows: [
      ['0', '0', '1'],
      ['0', '1', '0'],
      ['1', '0', '0'],
      ['1', '1', '1'],
    ],
  },
  DFF: {
    inputs: ['IN'],
    outputs: ['OUT'],
    rows: [
      ['0', '0'],
      ['1', '1'],
    ],
  },
};

const loadArsenal = (): ArsenalCircuit[] => {
  try {
    const raw = window.localStorage.getItem(ARSENAL_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as ArsenalCircuit[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
};

const Category = ({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) => {
  return (
    <div className="rounded-xl border border-border bg-card p-3 text-card-foreground shadow-subtle transition-all duration-300">
      <div className="mb-2 text-[13px] font-semibold tracking-tight text-foreground">{title}</div>
      {children}
    </div>
  );
};

const getFallbackNodeDefinition = (
  component: CircuitComponent,
): LogicNodeDefinition => {
  const hardcoded: Record<string, LogicNodeDefinition> = {
    AND: {
      label: 'AND',
      size: { w: 3, h: 2 },
      ports: [
        { id: 'IN0', kind: 'input', offset: { row: 0, col: 0 } },
        { id: 'IN1', kind: 'input', offset: { row: 1, col: 0 } },
        { id: 'OUT0', kind: 'output', offset: { row: 0, col: 2 } },
      ],
    },
    OR: {
      label: 'OR',
      size: { w: 3, h: 2 },
      ports: [
        { id: 'IN0', kind: 'input', offset: { row: 0, col: 0 } },
        { id: 'IN1', kind: 'input', offset: { row: 1, col: 0 } },
        { id: 'OUT0', kind: 'output', offset: { row: 0, col: 2 } },
      ],
    },
    XOR: {
      label: 'XOR',
      size: { w: 3, h: 2 },
      ports: [
        { id: 'IN0', kind: 'input', offset: { row: 0, col: 0 } },
        { id: 'IN1', kind: 'input', offset: { row: 1, col: 0 } },
        { id: 'OUT0', kind: 'output', offset: { row: 0, col: 2 } },
      ],
    },
    NAND: {
      label: 'NAND',
      size: { w: 3, h: 2 },
      ports: [
        { id: 'IN0', kind: 'input', offset: { row: 0, col: 0 } },
        { id: 'IN1', kind: 'input', offset: { row: 1, col: 0 } },
        { id: 'OUT0', kind: 'output', offset: { row: 0, col: 2 } },
      ],
    },
    NOR: {
      label: 'NOR',
      size: { w: 3, h: 2 },
      ports: [
        { id: 'IN0', kind: 'input', offset: { row: 0, col: 0 } },
        { id: 'IN1', kind: 'input', offset: { row: 1, col: 0 } },
        { id: 'OUT0', kind: 'output', offset: { row: 0, col: 2 } },
      ],
    },
    XNOR: {
      label: 'XNOR',
      size: { w: 3, h: 2 },
      ports: [
        { id: 'IN0', kind: 'input', offset: { row: 0, col: 0 } },
        { id: 'IN1', kind: 'input', offset: { row: 1, col: 0 } },
        { id: 'OUT0', kind: 'output', offset: { row: 0, col: 2 } },
      ],
    },
    NOT: {
      label: 'NOT',
      size: { w: 3, h: 1 },
      ports: [
        { id: 'IN0', kind: 'input', offset: { row: 0, col: 0 } },
        { id: 'OUT0', kind: 'output', offset: { row: 0, col: 2 } },
      ],
    },
    DFF: {
      label: 'DFF',
      size: { w: 3, h: 1 },
      ports: [
        { id: 'IN0', kind: 'input', offset: { row: 0, col: 0 } },
        { id: 'OUT0', kind: 'output', offset: { row: 0, col: 2 } },
      ],
    },
  };

  if (hardcoded[component.type]) {
    return hardcoded[component.type];
  }

  const size = {
    w: 3,
    h: Math.max(1, Math.min(4, Math.ceil(component.pins / 2))),
  };
  const ports: LogicNodeDefinition['ports'] = [];
  const outputsCount = 1;
  const inputsCount = Math.max(1, component.pins - outputsCount);

  for (let index = 0; index < inputsCount; index++) {
    ports.push({
      id: `IN${index}`,
      kind: 'input',
      offset: { row: Math.min(index, size.h - 1), col: 0 },
    });
  }

  ports.push({
    id: 'OUT0',
    kind: 'output',
    offset: { row: 0, col: size.w - 1 },
  });

  return {
    label: component.type,
    size,
    ports,
  };
};

const DraggableItem = ({
  component,
  node,
  inPalette = false,
  isSelected,
  onSelect,
  onInfoClick,
  onDragStart,
  onDragEnd,
  category = 'basic',
}: {
  component: CircuitComponent;
  node: LogicNodeDefinition;
  inPalette?: boolean;
  isSelected?: boolean;
  onSelect?: (componentId: string) => void;
  onInfoClick?: () => void;
  onDragStart?: (id: string) => void;
  onDragEnd?: () => void;
  category?: 'basic' | 'custom' | 'arsenal';
}) => {
  const getInfoTitle = () => {
    if (category === 'arsenal') return 'View Circuit Preview';
    return 'View Truth Table';
  };

  return (
      <div
        className={cn(
          'group flex w-full items-center gap-2 rounded-lg border px-2.5 py-2 text-left text-[13px] text-foreground transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md',
          isSelected
            ? 'border-sky-500 bg-sky-500 shadow-[0_0_10px_rgba(56,189,248,0.28)] dark:bg-secondary'
            : 'border-border bg-secondary',
        )}
      >
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onInfoClick?.();
          }}
          className={cn(
            'text-muted-foreground hover:text-foreground transition-colors cursor-help opacity-100',
            isSelected ? 'opacity-100' : 'opacity-0 group-hover:opacity-100',
          )}
          title={getInfoTitle()}
        >
          <Info size={16} />
        </button>
        <div
          draggable
          onDragStart={(e) => {
            const transparentDragImage = document.createElement('canvas');
            transparentDragImage.width = 1;
            transparentDragImage.height = 1;
            e.dataTransfer.setDragImage(transparentDragImage, 0, 0);
            e.dataTransfer.setData(
              'application/x-escapecircuit-component',
              component.id,
            );
            e.dataTransfer.setData('text/plain', component.id);
            e.dataTransfer.effectAllowed = 'copy';
            onDragStart?.(component.id);
          }}
          onDragEnd={() => onDragEnd?.()}
          onClick={() => onSelect?.(component.id)}
          className="flex flex-1 cursor-grab active:cursor-grabbing items-center justify-between"
        >
          <span className="font-semibold text-foreground">{component.type}</span>
          {inPalette ? (
            <span className="text-xs text-muted-foreground">
              cost {component.cost} · pins {component.pins}
            </span>
          ) : null}
        </div>
      </div>
  );
};

export const WorkstationMenu = ({
  basic,
  custom,
  sharedArsenal,
  solverArsenal,
  componentDefs,
  allowArsenal,
  filteredBasicTypes,
  selectedComponentId,
  onSelectComponent,
  onDragStart,
  onDragEnd,
}: {
  basic: CircuitComponent[];
  custom: CircuitComponent[];
  sharedArsenal: CircuitComponent[];
  solverArsenal: CircuitComponent[];
  componentDefs?: Record<string, LogicNodeDefinition>;
  allowArsenal: boolean;
  filteredBasicTypes: string[];
  selectedComponentId?: string;
  onSelectComponent?: (componentId: string) => void;
  onDragStart?: (id: string) => void;
  onDragEnd?: () => void;
}) => {
  const [loadedArsenal, setLoadedArsenal] = useState<ArsenalCircuit[]>([]);
  const [viewingTruthTableFor, setViewingTruthTableFor] = useState<
    string | null
  >(null);
  const [viewingTruthTableData, setViewingTruthTableData] = useState<any>(null);
  const [viewingCircuitPreviewFor, setViewingCircuitPreviewFor] = useState<
    ArsenalCircuit | null
  >(null);
  const [viewingDFFDescription, setViewingDFFDescription] = useState(false);


  useEffect(() => {
    if (!allowArsenal) return;
    setLoadedArsenal(loadArsenal());
  }, [allowArsenal]);

  const visibleArsenal = useMemo(() => {
    if (!allowArsenal) return [];
    const filtered = new Set(filteredBasicTypes);
    return loadedArsenal.filter((c) =>
      c.usedBasicTypes.every((t) => !filtered.has(t)),
    );
  }, [allowArsenal, loadedArsenal, filteredBasicTypes]);

  const getUsedBasicTypes = (component: CircuitComponent): string[] => {
    const directUsedTypes = (component as any).used_basic_types;
    if (Array.isArray(directUsedTypes)) {
      return directUsedTypes.map((gate) => String(gate));
    }

    const basicGatesRaw = (component as any).basic_gates;
    if (Array.isArray(basicGatesRaw)) {
      return basicGatesRaw.map((gate) => String(gate));
    }

    if (typeof basicGatesRaw === 'string' && basicGatesRaw.trim()) {
      try {
        const parsed = JSON.parse(basicGatesRaw);
        if (Array.isArray(parsed)) {
          return parsed.map((gate) => String(gate));
        }
      } catch {
        return [];
      }
    }

    return [];
  };

  const handleInfoClick = (componentId: string, component: CircuitComponent, category: 'basic' | 'custom' | 'arsenal' = 'basic') => {
    // Show circuit preview ONLY for arsenal pieces
    if (category === 'arsenal') {
      // Convert component to ArsenalCircuit format
      const arsenalCircuit: ArsenalCircuit = {
        id: component.id,
        name: component.type,
        usedBasicTypes: getUsedBasicTypes(component),
        solution: (component as any).solution || { structure: {} },
        description: (component as any).description,
      };
      setViewingCircuitPreviewFor(arsenalCircuit);
      return;
    }
    
    // For DFF, show the description instead of truth table
    if (component.type === 'DFF') {
      setViewingDFFDescription(true);
      return;
    }
    
    // Show truth table for other basic gates and custom pieces
    setViewingTruthTableFor(component.type || componentId);
    
    // Check if component has truth_table data (from API arsenal pieces)
    const truthTableSource = TRUTH_TABLES[component.type || componentId];
    const apiData = (component as any).truth_table;
    
    if (apiData) {
      // Parse the truth table from API data
      try {
        const parsedTT = typeof apiData === 'string' ? JSON.parse(apiData) : apiData;
        // Convert to the expected format
        const inputKeys = Object.keys(parsedTT)[0]?.split(',') || [];
        setViewingTruthTableData({
          inputs: inputKeys,
          outputs: Object.keys(parsedTT[Object.keys(parsedTT)[0]] || {}),
          rows: Object.entries(parsedTT).map(([input, output]: any) => [input, ...Object.values(output)]),
        });
      } catch {
        setViewingTruthTableData(truthTableSource);
      }
    } else {
      setViewingTruthTableData(truthTableSource);
    }
  };

  const truthTable = viewingTruthTableFor
    ? TRUTH_TABLES[viewingTruthTableFor]
    : null;

  const knownPreviewArsenalComponents = useMemo(() => {
    const byId = new Map<string, CircuitComponent>();
    for (const component of [...sharedArsenal, ...solverArsenal]) {
      byId.set(String(component.id), component);
    }
    return Array.from(byId.values());
  }, [sharedArsenal, solverArsenal]);

  return (
    <div className="flex flex-col gap-3">
      {basic.length ? (
        <Category title="Basic">
          <div className="flex flex-col gap-2">
            {basic.map((c) => (
              <DraggableItem
                key={c.id}
                component={c}
                node={componentDefs?.[c.id] ?? getFallbackNodeDefinition(c)}
                inPalette
                isSelected={selectedComponentId === c.id}
                onSelect={onSelectComponent}
                onInfoClick={() => handleInfoClick(c.id, c, 'basic')}
                onDragStart={onDragStart}
                onDragEnd={onDragEnd}
                category="basic"
              />
            ))}
          </div>
        </Category>
      ) : null}

      {/* Custom Pieces Category (puzzle-specific) */}
      {custom.length ? (
        <Category title="Special Pieces">
          <div className="text-[11px] text-foreground/80 mb-2">
            Custom logic gates created for this puzzle
          </div>
          <div className="flex flex-col gap-2">
            {custom.map((c) => (
              <DraggableItem
                key={c.id}
                component={c}
                node={componentDefs?.[c.id] ?? getFallbackNodeDefinition(c)}
                inPalette
                isSelected={selectedComponentId === c.id}
                onSelect={onSelectComponent}
                onInfoClick={() => handleInfoClick(c.id, c, 'custom')}
                onDragStart={onDragStart}
                onDragEnd={onDragEnd}
                category="custom"
              />
            ))}
          </div>
        </Category>
      ) : null}

      {/* Creator-shared arsenal pieces for this puzzle */}
      {sharedArsenal.length ? (
        <Category title="Shared Arsenal">
          <div className="text-[11px] text-foreground/80 mb-2">
            Components explicitly shared by the puzzle creator
          </div>
          <div className="flex flex-col gap-2">
            {sharedArsenal.map((c) => (
              <DraggableItem
                key={c.id}
                component={c}
                node={componentDefs?.[c.id] ?? getFallbackNodeDefinition(c)}
                inPalette
                isSelected={selectedComponentId === c.id}
                onSelect={onSelectComponent}
                onInfoClick={() => handleInfoClick(c.id, c, 'arsenal')}
                onDragStart={onDragStart}
                onDragEnd={onDragEnd}
                category="arsenal"
              />
            ))}
          </div>
        </Category>
      ) : null}

      {/* Solver personal arsenal pieces (when allowed) */}
      {allowArsenal ? (
        <Category title="Your Arsenal">
          <div className="text-[11px] text-foreground/80 mb-2">
            Your personal circuit pieces
          </div>
          {solverArsenal.length > 0 ? (
            <div className="flex flex-col gap-2">
              {solverArsenal.map((c) => (
                <DraggableItem
                  key={c.id}
                  component={c}
                  node={componentDefs?.[c.id] ?? getFallbackNodeDefinition(c)}
                  inPalette
                  isSelected={selectedComponentId === c.id}
                  onSelect={onSelectComponent}
                  onInfoClick={() => handleInfoClick(c.id, c, 'arsenal')}
                  onDragStart={onDragStart}
                  onDragEnd={onDragEnd}
                  category="arsenal"
                />
              ))}
            </div>
          ) : (
            <div className="text-[11px] text-foreground/70 opacity-80">
              No personal arsenal pieces available.
            </div>
          )}
        </Category>
      ) : null}

      {allowArsenal && visibleArsenal.length ? (
        <Category title="Saved">
          <div className="text-[11px] text-foreground/80">
            Saved circuits are shown only if they don’t use filtered-out basic
            gates.
          </div>
          <div className="mt-2 flex flex-col gap-2">
            {visibleArsenal.map((c) => (
              <div
                key={c.id}
                className="rounded border border-border bg-secondary/50 p-2 text-[13px] text-foreground"
              >
                <div className="font-medium text-foreground">{c.name}</div>
                <div className="text-[11px] text-foreground/75">
                  Uses: {c.usedBasicTypes.join(', ') || 'none'}
                </div>
                <div className="mt-1 text-[11px] text-foreground/70">
                  (Loading saved circuits into the board will be added next.)
                </div>
              </div>
            ))}
          </div>
        </Category>
      ) : null}

      {/* Truth Table Dialog for basic gates and custom pieces */}
      <Dialog
        open={Boolean(viewingTruthTableFor)}
        onOpenChange={(open) => !open && setViewingTruthTableFor(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Truth Table: {viewingTruthTableFor}</DialogTitle>
          </DialogHeader>
          {viewingTruthTableData ? (
            <div className="overflow-hidden rounded-lg border border-border/60">
              <table className="w-full text-[13px] text-foreground">
                <thead className="bg-secondary text-[11px] font-medium uppercase text-foreground">
                  <tr>
                    {viewingTruthTableData.inputs.map((i: string) => (
                      <th key={i} className="px-3 py-2 text-center">
                        {i}
                      </th>
                    ))}
                    {viewingTruthTableData.outputs.map((o: string) => (
                      <th
                        key={o}
                        className="border-l border-border px-3 py-2 text-center"
                      >
                        {o}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {viewingTruthTableData.rows.map((row: string[], idx: number) => (
                    <tr key={idx} className="divide-x divide-border bg-card">
                      {row.map((cell: string, cIdx: number) => (
                        <td key={cIdx} className="px-3 py-2 text-center text-foreground">
                          {cell}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-[13px] text-muted-foreground">
              No truth table available for this component.
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* DFF Description Dialog */}
      <Dialog
        open={viewingDFFDescription}
        onOpenChange={setViewingDFFDescription}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>D Flip-Flop (DFF)</DialogTitle>
            <DialogDescription>Sequential Logic Component</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <p className="text-[13px] text-foreground leading-relaxed">
              A D Flip-Flop (DFF) is a sequential logic component. It captures the value of the Data (D) input at a definite portion of the clock cycle (usually the rising edge) and outputs that captured value at Q. The output Q only changes state when the clock ticks, holding its value steady between clock edges.
            </p>
            <div className="rounded-lg bg-secondary/50 p-3 space-y-2">
              <p className="text-[12px] font-semibold text-foreground">Key Characteristics:</p>
              <ul className="text-[12px] text-muted-foreground space-y-1">
                <li>• <span className="font-medium">Sequential:</span> Output depends on previous state</li>
                <li>• <span className="font-medium">State Memory:</span> Stores a single bit of data</li>
                <li>• <span className="font-medium">Clock-driven:</span> Changes only on clock edges</li>
                <li>• <span className="font-medium">Deterministic:</span> Input always captured consistently</li>
              </ul>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Circuit Preview Dialog for arsenal pieces */}
      <Dialog
        open={Boolean(viewingCircuitPreviewFor)}
        onOpenChange={(open) => !open && setViewingCircuitPreviewFor(null)}
      >
        <DialogContent className="max-w-4xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{viewingCircuitPreviewFor?.name} - Circuit Preview</DialogTitle>
            <DialogDescription>
              Read-only preview of the circuit. No modifications allowed.
            </DialogDescription>
          </DialogHeader>
          {viewingCircuitPreviewFor && (
            <CircuitPreviewContent
              arsenalCircuit={viewingCircuitPreviewFor}
              knownArsenalComponents={knownPreviewArsenalComponents}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

function CircuitPreviewContent({
  arsenalCircuit,
  knownArsenalComponents = [],
}: {
  arsenalCircuit: ArsenalCircuit;
  knownArsenalComponents?: CircuitComponent[];
}) {
  const { data: myArsenal } = useMyArsenal();

  const parseStructure = (solution: any): {
    numInputs: number;
    numOutputs: number;
    placed: PlacedGridComponent[];
    wires: any[];
  } => {
    try {
      // Try to get structure from different possible locations
      const struct = solution.structure || solution || {};
      
      return {
        numInputs: struct.numInputs || 0,
        numOutputs: struct.numOutputs || 0,
        placed: struct.placed || struct.placedComponents || [],
        wires: struct.wires || [],
      };
    } catch {
      return { numInputs: 0, numOutputs: 0, placed: [], wires: [] };
    }
  };

  const structure = parseStructure(arsenalCircuit.solution);
  const { placed, wires } = structure;

  // Build input/output labels
  const inputLabels = Array.from({ length: structure.numInputs }, (_, i) => `in${i}`);
  const outputLabels = Array.from({ length: structure.numOutputs }, (_, i) => `out${i}`);

  // Build map of arsenal metadata by ID for quick lookup.
  const arsenalMap = new Map<
    string,
    { name: string; cost: number; num_inputs: number; num_outputs: number }
  >();
  if (myArsenal) {
    myArsenal.forEach((ap) => {
      arsenalMap.set(String(ap.id), {
        name: ap.name,
        cost: ap.cost,
        num_inputs: (ap as any).num_inputs ?? 0,
        num_outputs: (ap as any).num_outputs ?? 0,
      });
    });
  }
  knownArsenalComponents.forEach((component) => {
    const key = String(component.id);
    if (!arsenalMap.has(key)) {
      arsenalMap.set(key, {
        name: component.type,
        cost: component.cost,
        num_inputs: (component as any).num_inputs ?? 0,
        num_outputs: (component as any).num_outputs ?? 0,
      });
    }
  });

  // Normalize lookup key so preview can resolve IDs even when stored as numbers.
  const getComponentKey = (componentId: string) => {
    const numeric = Number(componentId);
    if (Number.isFinite(numeric) && String(numeric) === componentId) {
      return String(numeric);
    }
    return componentId;
  };

  const getCatalogLabel = (componentId: string) => {
    const known = arsenalMap.get(getComponentKey(componentId));
    return known?.name || componentId;
  };

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
      const arsenalPiece = arsenalMap.get(getComponentKey(comp.componentId));
      if (arsenalPiece) {
        // Arsenal piece sizing: width=3, height=max(inputs, outputs)
        const numInputs = arsenalPiece.num_inputs ?? 0;
        const numOutputs = arsenalPiece.num_outputs ?? 0;
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
          label: getCatalogLabel(comp.componentId),
          cost: arsenalPiece.cost,
          size,
          ports,
        };
      } else {
        // Fallback for unknown components
        catalog[comp.componentId] = {
          id: comp.componentId,
          label: getCatalogLabel(comp.componentId),
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
      {arsenalCircuit.description && (
        <div className="bg-foreground/5 p-3 rounded-lg border border-border/40">
          <p className="text-sm text-foreground">{arsenalCircuit.description}</p>
        </div>
      )}

      {arsenalCircuit.usedBasicTypes.length > 0 && (
        <div className="bg-secondary/30 p-3 rounded-lg border border-border/60">
          <p className="text-xs text-foreground/70 mb-1">Basic Gates Used</p>
          <p className="text-sm text-foreground">{arsenalCircuit.usedBasicTypes.join(', ')}</p>
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
          <p className="text-lg font-semibold text-foreground">{(arsenalCircuit.solution as any)?.totalCost || 0}</p>
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
            puzzleId={`arsenal-preview-${arsenalCircuit.id}`}
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
                  <span className="text-foreground/70">{catalog[comp.componentId]?.label || comp.componentId}</span>
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}
