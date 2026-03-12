'use client';

import { Info } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { flushSync } from 'react-dom';
import { createRoot } from 'react-dom/client';

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { CircuitComponent, CircuitSolution } from '@/types/api';
import { cn } from '@/utils/cn';
import { LogicNode, type LogicNodeDefinition } from './node';

type ArsenalCircuit = {
  id: string;
  name: string;
  usedBasicTypes: string[];
  solution: CircuitSolution;
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
    <div className="rounded-xl border border-slate-200 bg-white p-3 text-slate-900 shadow-subtle transition-all duration-300 dark:bg-slate-900 dark:border-slate-800 dark:text-slate-100">
      <div className="mb-2 text-[13px] font-semibold tracking-tight text-slate-900 dark:text-slate-100">{title}</div>
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
}: {
  component: CircuitComponent;
  node: LogicNodeDefinition;
  inPalette?: boolean;
  isSelected?: boolean;
  onSelect?: (componentId: string) => void;
  onInfoClick?: () => void;
  onDragStart?: (id: string) => void;
  onDragEnd?: () => void;
}) => {
  return (
      <div
        className={cn(
          'group flex w-full items-center gap-2 rounded-lg border px-2.5 py-2 text-left text-[13px] text-slate-900 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md dark:text-foreground',
          isSelected
            ? 'border-sky-500 bg-sky-100 shadow-[0_0_10px_rgba(56,189,248,0.28)] dark:bg-slate-800'
            : 'border-slate-200 bg-slate-50 dark:border-border/60 dark:bg-slate-900',
        )}
      >
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onInfoClick?.();
          }}
          className={cn(
            'text-slate-500 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white transition-colors cursor-help opacity-100',
            isSelected ? 'opacity-100' : 'opacity-0 group-hover:opacity-100',
          )}
          title="View Truth Table"
        >
          <Info size={16} />
        </button>
        <div
          draggable
          onDragStart={(e) => {
            const dragPreview = document.createElement('div');
            dragPreview.style.position = 'fixed';
            dragPreview.style.left = '-10000px';
            dragPreview.style.top = '-10000px';
            dragPreview.style.pointerEvents = 'none';
            dragPreview.style.zIndex = '-1';
            document.body.appendChild(dragPreview);

            const root = createRoot(dragPreview);
            flushSync(() => {
              root.render(
                <LogicNode
                  node={node}
                  className="border-slate-300 dark:border-slate-600 opacity-80 shadow-xl"
                />,
              );
            });

            e.dataTransfer.setDragImage(
              dragPreview,
              (node.size.w * 18) / 2,
              (node.size.h * 18) / 2,
            );
            window.requestAnimationFrame(() => {
              root.unmount();
              dragPreview.remove();
            });
            e.dataTransfer.setData(
              'application/x-escapecircuit-component',
              component.id,
            );
            e.dataTransfer.effectAllowed = 'copy';
            onDragStart?.(component.id);
          }}
          onDragEnd={() => onDragEnd?.()}
          onClick={() => onSelect?.(component.id)}
          className="flex flex-1 cursor-grab active:cursor-grabbing items-center justify-between"
        >
          <span className="font-semibold text-slate-900 dark:text-slate-100">{component.type}</span>
          {inPalette ? (
            <span className="text-xs text-foreground/75 dark:text-slate-300">
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
  arsenal,
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
  arsenal: CircuitComponent[];
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

  const handleInfoClick = (componentId: string, component: CircuitComponent) => {
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
                onInfoClick={() => handleInfoClick(c.id, c)}
                onDragStart={onDragStart}
                onDragEnd={onDragEnd}
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
                onInfoClick={() => handleInfoClick(c.id, c)}
                onDragStart={onDragStart}
                onDragEnd={onDragEnd}
              />
            ))}
          </div>
        </Category>
      ) : null}

      {/* Arsenal Category (user's saved pieces) */}
      {allowArsenal && arsenal.length ? (
        <Category title="Arsenal">
          <div className="text-[11px] text-foreground/80 mb-2">
            Your personal circuit pieces
          </div>
          {arsenal.length > 0 ? (
            <div className="flex flex-col gap-2">
              {arsenal.map((c) => (
                <DraggableItem
                  key={c.id}
                  component={c}
                  node={componentDefs?.[c.id] ?? getFallbackNodeDefinition(c)}
                  inPalette
                  isSelected={selectedComponentId === c.id}
                  onSelect={onSelectComponent}
                  onInfoClick={() => handleInfoClick(c.id, c)}
                  onDragStart={onDragStart}
                  onDragEnd={onDragEnd}
                />
              ))}
            </div>
          ) : (
            <div className="text-[11px] text-foreground/70 opacity-80">
              No arsenal pieces yet. Create one in your arsenal workspace.
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
              <table className="w-full text-[13px] text-slate-900 dark:text-slate-100">
                <thead className="bg-slate-100 text-[11px] font-medium uppercase text-slate-900 dark:bg-slate-800 dark:text-slate-100">
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
                    <tr key={idx} className="divide-x divide-border bg-white dark:bg-slate-900">
                      {row.map((cell: string, cIdx: number) => (
                        <td key={cIdx} className="px-3 py-2 text-center text-slate-900 dark:text-slate-100">
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
    </div>
  );
};
