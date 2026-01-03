'use client';

import { useEffect, useMemo, useState } from 'react';

import { CircuitComponent, CircuitSolution } from '@/types/api';
import { cn } from '@/utils/cn';

type ArsenalCircuit = {
  id: string;
  name: string;
  usedBasicTypes: string[];
  solution: CircuitSolution;
};

const ARSENAL_KEY = 'escapecircuit.arsenal.v1';

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
}: {
  component: CircuitComponent;
  isSelected?: boolean;
  onSelect?: (componentId: string) => void;
}) => {
  return (
    <button
      type="button"
      draggable
      onDragStart={(e) => {
        e.dataTransfer.setData(
          'application/x-escapecircuit-component',
          component.id,
        );
        e.dataTransfer.effectAllowed = 'copy';
      }}
      onClick={() => onSelect?.(component.id)}
      className={cn(
        'flex w-full cursor-pointer items-center justify-between gap-2 rounded border px-2 py-2 text-left text-sm text-gray-700',
        isSelected
          ? 'border-blue-300 bg-blue-50'
          : 'border-gray-200 bg-gray-50 hover:bg-gray-100',
      )}
    >
      <span className="font-medium text-gray-900">{component.type}</span>
      <span className="text-xs text-gray-600">
        cost {component.cost} · pins {component.pins}
      </span>
    </button>
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
    </div>
  );
};
