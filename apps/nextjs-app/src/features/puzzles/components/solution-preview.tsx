'use client';

import type { ReactNode } from 'react';

import { WorkstationGrid } from '@/app/app/puzzles/[id]/_components/workstation-grid';
import type { ComponentDef, PlacedGridComponent } from '@/app/app/puzzles/[id]/_components/workstation-grid';
import { extractVisualStyleFromComponentLike } from '@/app/app/puzzles/[id]/_components/piece-visual-style';
import type { CircuitComponent, Puzzle, Wire } from '@/types/api';

type SolutionPreviewStructure = {
  placed: PlacedGridComponent[];
  wires: Wire[];
  totalCost: number;
};

const asObject = (value: any): Record<string, any> | null => {
  if (!value) return null;
  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value);
      return parsed && typeof parsed === 'object' && !Array.isArray(parsed)
        ? (parsed as Record<string, any>)
        : null;
    } catch {
      return null;
    }
  }
  return typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, any>)
    : null;
};

const hasCircuitShape = (value: Record<string, any> | null) => {
  if (!value) return false;
  return (
    Array.isArray(value.placed) ||
    Array.isArray(value.placedComponents) ||
    Array.isArray(value.placed_components) ||
    Array.isArray(value.components) ||
    Array.isArray(value.wires) ||
    Array.isArray(value.wire_list) ||
    (typeof value.placed === 'object' && value.placed !== null) ||
    (typeof value.wires === 'object' && value.wires !== null)
  );
};

const resolveSolutionContainer = (payload: Record<string, any>) => {
  const candidates = [
    payload,
    asObject(payload.circuit),
    asObject(payload.circuit_json),
    asObject(payload.solution),
    asObject(payload.solution_json),
    asObject(payload.structure),
    asObject(asObject(payload.circuit)?.structure),
    asObject(asObject(payload.circuit)?.solution),
    asObject(asObject(payload.solution)?.structure),
    asObject(asObject(payload.solution)?.circuit),
  ].filter((candidate): candidate is Record<string, any> => candidate !== null);

  return candidates.find((candidate) => hasCircuitShape(candidate)) || payload;
};

const BASE_PREVIEW_CATALOG: Record<string, ComponentDef> = {
  AND: {
    id: 'AND',
    label: 'AND',
    cost: 1,
    size: { w: 3, h: 2 },
    ports: [
      { id: 'IN0', kind: 'input', offset: { row: 0, col: 0 } },
      { id: 'IN1', kind: 'input', offset: { row: 1, col: 0 } },
      { id: 'OUT0', kind: 'output', offset: { row: 1, col: 2 } },
    ],
  },
  OR: {
    id: 'OR',
    label: 'OR',
    cost: 1,
    size: { w: 3, h: 2 },
    ports: [
      { id: 'IN0', kind: 'input', offset: { row: 0, col: 0 } },
      { id: 'IN1', kind: 'input', offset: { row: 1, col: 0 } },
      { id: 'OUT0', kind: 'output', offset: { row: 1, col: 2 } },
    ],
  },
  NOT: {
    id: 'NOT',
    label: 'NOT',
    cost: 1,
    size: { w: 3, h: 1 },
    ports: [
      { id: 'IN0', kind: 'input', offset: { row: 0, col: 0 } },
      { id: 'OUT0', kind: 'output', offset: { row: 0, col: 2 } },
    ],
  },
  XOR: {
    id: 'XOR',
    label: 'XOR',
    cost: 1,
    size: { w: 3, h: 2 },
    ports: [
      { id: 'IN0', kind: 'input', offset: { row: 0, col: 0 } },
      { id: 'IN1', kind: 'input', offset: { row: 1, col: 0 } },
      { id: 'OUT0', kind: 'output', offset: { row: 1, col: 2 } },
    ],
  },
};

const normalizePlacedComponent = (
  component: any,
  index: number,
): PlacedGridComponent | null => {
  const componentId = String(
    component?.componentId ??
      component?.type ??
      component?.gateType ??
      component?.name ??
      '',
  ).trim();
  if (!componentId) return null;

  const rowRaw =
    component?.origin?.row ??
    component?.origin?.y ??
    component?.position?.row ??
    component?.position?.y ??
    component?.row ??
    component?.y ??
    0;
  const colRaw =
    component?.origin?.col ??
    component?.origin?.x ??
    component?.position?.col ??
    component?.position?.x ??
    component?.col ??
    component?.x ??
    0;
  const row = Number.isFinite(Number(rowRaw)) ? Number(rowRaw) : 0;
  const col = Number.isFinite(Number(colRaw)) ? Number(colRaw) : 0;
  const rotation = Number(component?.rotation) === 90 ? 90 : 0;

  return {
    id: String(component?.id ?? `${componentId}:${index}`),
    componentId,
    origin: {
      row: Math.max(0, row),
      col: Math.max(0, col),
    },
    rotation,
  };
};

const normalizeWire = (wire: any, index: number): Wire | null => {
  const fromObj = asObject(wire?.from) || asObject(wire?.source) || {};
  const toObj = asObject(wire?.to) || asObject(wire?.target) || {};

  const fromComponentId = String(
    fromObj.componentId ??
      fromObj.ownerId ??
      fromObj.id ??
      wire?.fromComponentId ??
      '',
  ).trim();
  const toComponentId = String(
    toObj.componentId ?? toObj.ownerId ?? toObj.id ?? wire?.toComponentId ?? '',
  ).trim();
  if (!fromComponentId || !toComponentId) return null;

  const fromPin = Number.isFinite(Number(fromObj.pinIndex ?? wire?.fromPinIndex))
    ? Number(fromObj.pinIndex ?? wire?.fromPinIndex)
    : 0;
  const toPin = Number.isFinite(Number(toObj.pinIndex ?? wire?.toPinIndex))
    ? Number(toObj.pinIndex ?? wire?.toPinIndex)
    : 0;

  return {
    id: String(wire?.id ?? `wire:${index}`),
    from: {
      componentId: fromComponentId,
      pinIndex: fromPin,
      portId: String(fromObj.portId ?? fromObj.pin ?? `P${fromPin}`),
    },
    to: {
      componentId: toComponentId,
      pinIndex: toPin,
      portId: String(toObj.portId ?? toObj.pin ?? `P${toPin}`),
    },
  };
};

const parseSolution = (payload: Record<string, any> | null): SolutionPreviewStructure => {
  if (!payload) {
    return { placed: [], wires: [], totalCost: 0 };
  }

  const circuit = resolveSolutionContainer(payload);

  const rawPlaced = Array.isArray(circuit.placed)
    ? circuit.placed
    : Array.isArray(circuit.placedComponents)
      ? circuit.placedComponents
      : Array.isArray(circuit.placed_components)
        ? circuit.placed_components
        : Array.isArray(circuit.components)
          ? circuit.components
          : asObject(circuit.placed)
            ? Object.values(asObject(circuit.placed) || {})
            : [];
  const rawWires = Array.isArray(circuit.wires)
    ? circuit.wires
    : Array.isArray(circuit.wire_list)
      ? circuit.wire_list
      : Array.isArray(circuit.connections)
        ? circuit.connections
        : asObject(circuit.wires)
          ? Object.values(asObject(circuit.wires) || {})
          : [];
  const totalCostRaw =
    payload.totalCost ??
    payload.total_cost ??
    circuit.totalCost ??
    circuit.total_cost ??
    asObject(payload.solution)?.totalCost ??
    0;
  const totalCost = Number.isFinite(Number(totalCostRaw))
    ? Number(totalCostRaw)
    : 0;

  const placed = rawPlaced
    .map((component: any, index: number) => normalizePlacedComponent(component, index))
    .filter(
      (component: PlacedGridComponent | null): component is PlacedGridComponent =>
        component !== null,
    );

  const wires = rawWires
    .map((wire: any, index: number) => normalizeWire(wire, index))
    .filter((wire: Wire | null): wire is Wire => wire !== null);

  return { placed, wires, totalCost };
};

const inferIoLabels = (wires: Wire[]) => {
  const inputLabels = new Set<string>();
  const outputLabels = new Set<string>();

  wires.forEach((wire) => {
    [wire.from.componentId, wire.to.componentId].forEach((componentId) => {
      if (componentId.startsWith('IO:IN:')) {
        inputLabels.add(componentId.replace('IO:IN:', ''));
      }
      if (componentId.startsWith('IO:OUT:')) {
        outputLabels.add(componentId.replace('IO:OUT:', ''));
      }
    });
  });

  return {
    inputs: Array.from(inputLabels),
    outputs: Array.from(outputLabels),
  };
};

const buildCatalog = (
  placed: PlacedGridComponent[],
  knownComponents: CircuitComponent[],
): Record<string, ComponentDef> => {
  const catalog: Record<string, ComponentDef> = {
    ...BASE_PREVIEW_CATALOG,
  };

  const knownByKey = new Map<string, CircuitComponent>();
  knownComponents.forEach((component) => {
    const anyComponent = component as any;
    const keys = [
      component.id,
      anyComponent.type,
      anyComponent.name,
      anyComponent.label,
    ]
      .map((key) => String(key ?? '').trim())
      .filter(Boolean);
    keys.forEach((key) => {
      knownByKey.set(key, component);
    });
  });

  placed.forEach((component) => {
    if (catalog[component.componentId]) return;

    const known = knownByKey.get(String(component.componentId));
    if (known) {
      const anyKnown = known as any;
      const numInputs = Number((known as any).num_inputs ?? 1);
      const numOutputs = Number((known as any).num_outputs ?? 1);
      const safeInputs = Number.isFinite(numInputs) ? Math.max(0, numInputs) : 1;
      const safeOutputs = Number.isFinite(numOutputs) ? Math.max(0, numOutputs) : 1;
      const height = Math.max(1, safeInputs, safeOutputs);

      const ports: ComponentDef['ports'] = [];
      for (let i = 0; i < safeInputs; i++) {
        ports.push({
          id: `IN${i}`,
          kind: 'input',
          offset: { row: i, col: 0 },
        });
      }
      for (let i = 0; i < safeOutputs; i++) {
        ports.push({
          id: `OUT${i}`,
          kind: 'output',
          offset: { row: i, col: 2 },
        });
      }

      catalog[component.componentId] = {
        id: component.componentId,
        label: String(anyKnown.name ?? anyKnown.type ?? anyKnown.id ?? component.componentId),
        cost: known.cost,
        size: { w: 3, h: height },
        ports,
        visualStyle: extractVisualStyleFromComponentLike(known),
      };
    } else {
      catalog[component.componentId] = {
        id: component.componentId,
        label: component.componentId,
        cost: 1,
        size: { w: 3, h: 1 },
        ports: [
          { id: 'P0', kind: 'input', offset: { row: 0, col: 0 } },
          { id: 'P1', kind: 'output', offset: { row: 0, col: 2 } },
        ],
      };
    }
  });

  return catalog;
};

type SolutionPreviewProps = {
  title?: ReactNode;
  description?: ReactNode;
  puzzle: Puzzle | null;
  payload: string | null;
  emptyMessage?: ReactNode;
  loadingMessage?: ReactNode;
};

export function SolutionPreview({
  title,
  description,
  puzzle,
  payload,
  emptyMessage,
  loadingMessage,
}: SolutionPreviewProps) {
  if (!payload) {
    return (
      <div className="rounded-lg border border-border bg-card p-4 text-sm text-muted-foreground">
        {emptyMessage ?? 'No solution data is available for preview.'}
      </div>
    );
  }

  const payloadObject = asObject(payload);
  const { placed, wires, totalCost } = parseSolution(payloadObject);
  const inferredLabels = inferIoLabels(wires);
  const hasRenderableCircuit = placed.length > 0 || wires.length > 0;

  const inputLabels =
    puzzle && Array.isArray((puzzle as any).inputs) && (puzzle as any).inputs.length > 0
      ? (puzzle as any).inputs.map((input: any) => String(input))
      : inferredLabels.inputs;

  const outputLabels =
    puzzle && Array.isArray((puzzle as any).outputs) && (puzzle as any).outputs.length > 0
      ? (puzzle as any).outputs.map((output: any) => String(output))
      : inferredLabels.outputs;

  const knownComponentsMap = new Map<string, CircuitComponent>();
  if (puzzle) {
    [
      ...((puzzle as any).specialComponents || []),
      ...((puzzle as any).customComponents || []),
      ...((puzzle as any).arsenalComponents || []),
    ].forEach((component: CircuitComponent) => {
      knownComponentsMap.set(String(component.id), component);
    });
  }
  const knownComponents = Array.from(knownComponentsMap.values());

  const catalog = buildCatalog(placed, knownComponents);
  const computedRows = Math.max(
    15,
    Math.max(...placed.map((component) => component.origin.row), 0) + 3,
  );
  const computedCols = Math.max(
    30,
    Math.max(...placed.map((component) => component.origin.col), 0) + 3,
  );

  const rowsRaw = puzzle ? Number((puzzle as any).board_rows) : Number.NaN;
  const colsRaw = puzzle ? Number((puzzle as any).board_cols) : Number.NaN;
  const boardRows =
    puzzle && Number.isFinite(rowsRaw) && rowsRaw > 0 ? rowsRaw : computedRows;
  const boardCols =
    puzzle && Number.isFinite(colsRaw) && colsRaw > 0 ? colsRaw : computedCols;

  return (
    <div className="space-y-4">
      {title || !puzzle ? (
        <div className="bg-foreground/5 border border-border/40 rounded-lg p-3">
          <p className="text-sm text-foreground">
            {title ?? 'Solution Preview'}
          </p>
          {description ? <p className="mt-1 text-xs text-muted-foreground">{description}</p> : null}
          {!puzzle ? (
            <p className="mt-1 text-xs text-muted-foreground">
              {loadingMessage ?? 'Puzzle context is unavailable, so this preview is using the saved circuit snapshot only.'}
            </p>
          ) : null}
        </div>
      ) : null}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="bg-secondary/40 p-3 rounded-lg border border-border/60">
          <p className="text-xs text-foreground/70 mb-1">Inputs</p>
          <p className="text-lg font-semibold text-foreground">{inputLabels.length}</p>
        </div>
        <div className="bg-secondary/40 p-3 rounded-lg border border-border/60">
          <p className="text-xs text-foreground/70 mb-1">Outputs</p>
          <p className="text-lg font-semibold text-foreground">{outputLabels.length}</p>
        </div>
        <div className="bg-secondary/40 p-3 rounded-lg border border-border/60">
          <p className="text-xs text-foreground/70 mb-1">Components</p>
          <p className="text-lg font-semibold text-foreground">{placed.length}</p>
        </div>
        <div className="bg-secondary/40 p-3 rounded-lg border border-border/60">
          <p className="text-xs text-foreground/70 mb-1">Cost</p>
          <p className="text-lg font-semibold text-foreground">{totalCost}</p>
        </div>
      </div>

      {!hasRenderableCircuit && (
        <div className="rounded-lg border border-amber-300/60 bg-amber-50/50 p-3 text-[12px] text-amber-900">
          Solution payload was found but no circuit nodes/wires could be parsed for rendering.
          <div className="mt-1 text-[11px] text-amber-800/90">
            Keys: {Object.keys(payloadObject || {}).join(', ') || 'none'}
          </div>
        </div>
      )}

      <div className="border border-border/60 rounded-lg bg-background overflow-hidden relative" style={{ height: '500px' }}>
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
            puzzleId={`solution-preview-${puzzle?.id ?? 'generic'}`}
            inputs={inputLabels}
            outputs={outputLabels}
            catalog={catalog}
            placed={placed}
            wires={wires}
            selectedComponent={{ mode: 'none' }}
            onSelectedComponentChange={() => {}}
            onPlacedChange={() => {}}
            onWiresChange={() => {}}
            draggedPaletteComponentId={null}
            isChecking={false}
            boardRows={boardRows}
            boardCols={boardCols}
          />
        </div>
      </div>

      {placed.length > 0 && (
        <div className="bg-secondary/30 rounded-lg p-3 border border-border/60">
          <p className="text-xs font-semibold text-foreground/70 mb-2">Components Used:</p>
          <div className="flex flex-wrap gap-2">
            {placed
              .filter((component, index, array) => array.findIndex((entry) => entry.componentId === component.componentId) === index)
              .map((component) => (
                <div key={component.componentId} className="flex items-center gap-2 text-xs">
                  <span className="text-foreground/70">{component.componentId}</span>
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}