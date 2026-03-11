'use client';

import { Info } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { CircuitComponent, CircuitSolution } from '@/types/api';
import { cn } from '@/utils/cn';

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
    <div className="rounded-xl border border-border/60 bg-card/80 p-3 shadow-subtle backdrop-blur-sm transition-all duration-300">
      <div className="mb-2 text-[13px] font-semibold tracking-tight text-foreground">{title}</div>
      {children}
    </div>
  );
};

const DraggableItem = ({
  component,
  isSelected,
  onSelect,
  onInfoClick,
  onDragStart,
  onDragEnd,
}: {
  component: CircuitComponent;
  isSelected?: boolean;
  onSelect?: (componentId: string) => void;
  onInfoClick?: () => void;
  onDragStart?: (id: string) => void;
  onDragEnd?: () => void;
}) => {
  return (
    <>
      <style jsx>{`
        .holographic-item {
          position: relative;
          background: linear-gradient(135deg, rgba(15, 23, 42, 0.3) 0%, rgba(30, 41, 59, 0.2) 100%);
          border-color: rgba(34, 211, 238, 0.4);
          transition: all 300ms ease;
        }

        .holographic-item:hover {
          border-color: rgba(34, 211, 238, 0.8);
          box-shadow: 
            inset 0 0 12px rgba(34, 211, 238, 0.15),
            0 0 12px rgba(34, 211, 238, 0.25),
            0 0 20px rgba(34, 211, 238, 0.1);
          background: linear-gradient(135deg, rgba(15, 23, 42, 0.5) 0%, rgba(30, 41, 59, 0.35) 100%);
        }

        .holographic-item:hover::before {
          content: '';
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: repeating-linear-gradient(
            0deg,
            rgba(34, 211, 238, 0.03) 0px,
            rgba(34, 211, 238, 0.03) 1px,
            transparent 1px,
            transparent 3px
          );
          pointer-events: none;
          border-radius: 0.5rem;
          animation: holographic-scanlines 8s linear infinite;
        }

        @keyframes holographic-scanlines {
          0% {
            transform: translateY(0);
          }
          100% {
            transform: translateY(4px);
          }
        }
      `}</style>
      <div
        className={cn(
          'group holographic-item flex w-full items-center gap-2 rounded-lg border px-2.5 py-2 text-left text-[13px] text-foreground transition-all duration-200 hover:-translate-y-1 hover:scale-105 hover:shadow-lg hover:shadow-blue-500/20',
          isSelected
            ? 'border-cyan-400/60 bg-cyan-950/30 shadow-[0_0_12px_rgba(34,211,238,0.3)]'
            : 'border-border/60 bg-secondary/30',
        )}
      >
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onInfoClick?.();
          }}
          className={cn(
            'text-foreground/40 hover:text-foreground/70 transition-opacity cursor-help',
            isSelected ? 'opacity-100' : 'opacity-0 group-hover:opacity-100',
          )}
          title="View Truth Table"
        >
          <Info size={16} />
        </button>
        <div
          draggable
          onDragStart={(e) => {
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
          <span className="font-medium text-foreground">{component.type}</span>
          <span className="text-xs text-muted-foreground">
            cost {component.cost} · pins {component.pins}
          </span>
        </div>
      </div>
    </>
  );
};

export const WorkstationMenu = ({
  basic,
  custom,
  arsenal,
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
          <div className="text-[11px] text-muted-foreground mb-2">
            Custom logic gates created for this puzzle
          </div>
          <div className="flex flex-col gap-2">
            {custom.map((c) => (
              <DraggableItem
                key={c.id}
                component={c}
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
          <div className="text-[11px] text-muted-foreground mb-2">
            Your personal circuit pieces
          </div>
          {arsenal.length > 0 ? (
            <div className="flex flex-col gap-2">
              {arsenal.map((c) => (
                <DraggableItem
                  key={c.id}
                  component={c}
                  isSelected={selectedComponentId === c.id}
                  onSelect={onSelectComponent}
                  onInfoClick={() => handleInfoClick(c.id, c)}
                  onDragStart={onDragStart}
                  onDragEnd={onDragEnd}
                />
              ))}
            </div>
          ) : (
            <div className="text-[11px] text-muted-foreground opacity-60">
              No arsenal pieces yet. Create one in your arsenal workspace.
            </div>
          )}
        </Category>
      ) : null}

      {allowArsenal && visibleArsenal.length ? (
        <Category title="Saved">
          <div className="text-[11px] text-muted-foreground">
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
                <div className="text-[11px] text-muted-foreground">
                  Uses: {c.usedBasicTypes.join(', ') || 'none'}
                </div>
                <div className="mt-1 text-[11px] text-muted-foreground">
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
              <table className="w-full text-[13px] text-foreground">
                <thead className="bg-secondary/50 text-[11px] font-medium uppercase text-muted-foreground">
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
                    <tr key={idx} className="divide-x divide-border">
                      {row.map((cell: string, cIdx: number) => (
                        <td key={cIdx} className="px-3 py-2 text-center">
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
