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
    <div className="rounded-md border border-gray-300 bg-white p-3">
      <div className="mb-2 text-sm font-medium text-gray-900">{title}</div>
      {children}
    </div>
  );
};

const DraggableItem = ({
  component,
  isSelected,
  onSelect,
  onInfoClick,
}: {
  component: CircuitComponent;
  isSelected?: boolean;
  onSelect?: (componentId: string) => void;
  onInfoClick?: () => void;
}) => {
  return (
    <div
      className={cn(
        'group flex w-full items-center gap-2 rounded border px-2 py-2 text-left text-sm text-gray-700',
        isSelected
          ? 'border-blue-300 bg-blue-50'
          : 'border-gray-200 bg-gray-50 hover:bg-gray-100',
      )}
    >
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          onInfoClick?.();
        }}
        className={cn(
          'text-blue-500 hover:text-blue-700 transition-opacity',
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
        }}
        onClick={() => onSelect?.(component.id)}
        className="flex flex-1 cursor-pointer items-center justify-between"
      >
        <span className="font-medium text-gray-900">{component.type}</span>
        <span className="text-xs text-gray-600">
          cost {component.cost} · pins {component.pins}
        </span>
      </div>
    </div>
  );
};

export const WorkstationMenu = ({
  basic,
  special,
  allowArsenal,
  filteredBasicTypes,
  selectedComponentId,
  onSelectComponent,
}: {
  basic: CircuitComponent[];
  special: CircuitComponent[];
  allowArsenal: boolean;
  filteredBasicTypes: string[];
  selectedComponentId?: string;
  onSelectComponent?: (componentId: string) => void;
}) => {
  const [arsenal, setArsenal] = useState<ArsenalCircuit[]>([]);
  const [viewingTruthTableFor, setViewingTruthTableFor] = useState<
    string | null
  >(null);

  useEffect(() => {
    if (!allowArsenal) return;
    setArsenal(loadArsenal());
  }, [allowArsenal]);

  const visibleArsenal = useMemo(() => {
    if (!allowArsenal) return [];
    const filtered = new Set(filteredBasicTypes);
    return arsenal.filter((c) =>
      c.usedBasicTypes.every((t) => !filtered.has(t)),
    );
  }, [allowArsenal, arsenal, filteredBasicTypes]);

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
                onInfoClick={() => setViewingTruthTableFor(c.type)}
              />
            ))}
          </div>
        </Category>
      ) : null}

      {special.length ? (
        <Category title="Special">
          <div className="flex flex-col gap-2">
            {special.map((c) => (
              <DraggableItem
                key={c.id}
                component={c}
                isSelected={selectedComponentId === c.id}
                onSelect={onSelectComponent}
                onInfoClick={() => setViewingTruthTableFor(c.type)}
              />
            ))}
          </div>
        </Category>
      ) : null}

      {allowArsenal && visibleArsenal.length ? (
        <Category title="Saved">
          <div className="text-xs text-gray-600">
            Saved circuits are shown only if they don’t use filtered-out basic
            gates.
          </div>
          <div className="mt-2 flex flex-col gap-2">
            {visibleArsenal.map((c) => (
              <div
                key={c.id}
                className="rounded border border-gray-200 bg-gray-50 p-2 text-sm text-gray-700"
              >
                <div className="font-medium text-gray-900">{c.name}</div>
                <div className="text-xs text-gray-600">
                  Uses: {c.usedBasicTypes.join(', ') || 'none'}
                </div>
                <div className="mt-1 text-xs text-gray-600">
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
          {truthTable ? (
            <div className="overflow-hidden rounded border border-gray-200">
              <table className="w-full text-sm text-gray-700">
                <thead className="bg-gray-50 text-xs font-medium uppercase text-gray-500">
                  <tr>
                    {truthTable.inputs.map((i) => (
                      <th key={i} className="px-3 py-2 text-center">
                        {i}
                      </th>
                    ))}
                    {truthTable.outputs.map((o) => (
                      <th
                        key={o}
                        className="border-l border-gray-200 px-3 py-2 text-center"
                      >
                        {o}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {truthTable.rows.map((row, idx) => (
                    <tr key={idx} className="divide-x divide-gray-200">
                      {row.map((cell, cIdx) => (
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
            <div className="text-sm text-gray-500">
              No truth table available for this component.
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};
