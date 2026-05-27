'use client';

import 'katex/dist/katex.min.css';
import { CircleCheck, CircleX, Medal, Star } from 'lucide-react';
import { useState, useEffect } from 'react';

import { WorkstationGrid } from '@/app/app/puzzles/[id]/_components/workstation-grid';
import type {
  ComponentDef,
  PlacedGridComponent,
} from '@/app/app/puzzles/[id]/_components/workstation-grid';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { usePuzzle } from '@/features/puzzles/api/get-puzzle';
import type { CircuitComponent, Puzzle, Wire } from '@/types/api';

type PuzzleViewDialogProps = {
  puzzle: Puzzle | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

type CreatorSolutionStructure = {
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
  NAND: {
    id: 'NAND',
    label: 'NAND',
    cost: 1,
    size: { w: 3, h: 2 },
    ports: [
      { id: 'IN0', kind: 'input', offset: { row: 0, col: 0 } },
      { id: 'IN1', kind: 'input', offset: { row: 1, col: 0 } },
      { id: 'OUT0', kind: 'output', offset: { row: 1, col: 2 } },
    ],
  },
  NOR: {
    id: 'NOR',
    label: 'NOR',
    cost: 1,
    size: { w: 3, h: 2 },
    ports: [
      { id: 'IN0', kind: 'input', offset: { row: 0, col: 0 } },
      { id: 'IN1', kind: 'input', offset: { row: 1, col: 0 } },
      { id: 'OUT0', kind: 'output', offset: { row: 1, col: 2 } },
    ],
  },
  XNOR: {
    id: 'XNOR',
    label: 'XNOR',
    cost: 1,
    size: { w: 3, h: 2 },
    ports: [
      { id: 'IN0', kind: 'input', offset: { row: 0, col: 0 } },
      { id: 'IN1', kind: 'input', offset: { row: 1, col: 0 } },
      { id: 'OUT0', kind: 'output', offset: { row: 1, col: 2 } },
    ],
  },
  DFF: {
    id: 'DFF',
    label: 'DFF',
    cost: 1,
    size: { w: 3, h: 1 },
    ports: [
      { id: 'IN0', kind: 'input', offset: { row: 0, col: 0 } },
      { id: 'OUT0', kind: 'output', offset: { row: 0, col: 2 } },
    ],
  },
};

const getCreatorSolutionPayload = (
  puzzle: Puzzle | null,
): Record<string, any> | null => {
  if (!puzzle) return null;
  const payload =
    (puzzle as any).creatorSolution ?? (puzzle as any).creator_solution ?? null;

  return payload && typeof payload === 'object'
    ? (payload as Record<string, any>)
    : null;
};

const getCreatorSolutionMeta = (
  puzzle: Puzzle | null,
): Record<string, any> | null => {
  if (!puzzle) return null;
  const meta =
    (puzzle as any).creatorSolutionMeta ??
    (puzzle as any).creator_solution_meta ??
    null;

  return meta && typeof meta === 'object'
    ? (meta as Record<string, any>)
    : null;
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

  const fromPin = Number.isFinite(
    Number(fromObj.pinIndex ?? wire?.fromPinIndex),
  )
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

const parseCreatorSolution = (
  payload: Record<string, any> | null,
): CreatorSolutionStructure => {
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
    .map((component: any, index: number) =>
      normalizePlacedComponent(component, index),
    )
    .filter(
      (
        component: PlacedGridComponent | null,
      ): component is PlacedGridComponent => component !== null,
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

  const knownById = new Map<string, CircuitComponent>();
  knownComponents.forEach((component) => {
    knownById.set(String(component.id), component);
  });

  placed.forEach((component) => {
    if (catalog[component.componentId]) return;

    const known = knownById.get(String(component.componentId));
    if (known) {
      const numInputs = Number((known as any).num_inputs ?? 1);
      const numOutputs = Number((known as any).num_outputs ?? 1);
      const safeInputs = Number.isFinite(numInputs)
        ? Math.max(0, numInputs)
        : 1;
      const safeOutputs = Number.isFinite(numOutputs)
        ? Math.max(0, numOutputs)
        : 1;
      const height = Math.max(1, safeInputs, safeOutputs);

      const ports: ComponentDef['ports'] = [];
      for (let i = 0; i < safeInputs; i++) {
        ports.push({
          id: `IN${i}`,
          kind: 'input',
          offset: { row: Math.min(i, height - 1), col: 0 },
        });
      }
      for (let i = 0; i < safeOutputs; i++) {
        ports.push({
          id: `OUT${i}`,
          kind: 'output',
          offset: { row: Math.min(i, height - 1), col: 2 },
        });
      }

      catalog[component.componentId] = {
        id: component.componentId,
        label: String(known.type || component.componentId),
        cost: Number(known.cost ?? 1),
        size: { w: 3, h: height },
        ports,
      };
      return;
    }

    catalog[component.componentId] = {
      id: component.componentId,
      label: component.componentId,
      cost: 1,
      size: { w: 3, h: 1 },
      ports: [
        { id: 'IN0', kind: 'input', offset: { row: 0, col: 0 } },
        { id: 'OUT0', kind: 'output', offset: { row: 0, col: 2 } },
      ],
    };
  });

  return catalog;
};

const latexToMarkdown = (latex: string): string => {
  let markdown = latex;

  // Convert tabular environments to markdown tables
  const tabularyRegex =
    /\\begin\{(?:tabular|array)\}\{[^}]*\}(.*?)\\end\{(?:tabular|array)\}/gs;
  markdown = markdown.replace(
    tabularyRegex,
    (_match: string, content: string) => {
      const rows = content
        .split('\\\\')
        .map((row: string) => row.replace(/\\hline/g, '').trim())
        .filter((row: string) => row.length > 0);

      if (rows.length === 0) return '';

      const mdRows = rows.map((row: string) => {
        const cells = row.split('&').map((cell: string) => cell.trim());
        return '| ' + cells.join(' | ') + ' |';
      });

      if (mdRows.length > 0) {
        const firstRowCells = rows[0].split('&').length;
        const separator = '|' + Array(firstRowCells).fill('---|').join('');
        mdRows.splice(1, 0, separator);
      }

      return '\n' + mdRows.join('\n') + '\n';
    },
  );

  markdown = markdown.replace(/\\section\*\s*\{([^}]+)\}/g, '# $1');
  markdown = markdown.replace(/\\subsection\*\s*\{([^}]+)\}/g, '## $1');
  markdown = markdown.replace(/\\subsubsection\*\s*\{([^}]+)\}/g, '### $1');
  markdown = markdown.replace(/\\textbf\s*\{([^}]+)\}/g, '**$1**');
  markdown = markdown.replace(/\\textit\s*\{([^}]+)\}/g, '*$1*');
  markdown = markdown.replace(/\\texttt\s*\{([^}]+)\}/g, '`$1`');
  markdown = markdown.replace(/\\begin\{center\}(.*?)\\end\{center\}/gs, '$1');
  markdown = markdown.replace(/\\begin\{itemize\}/g, '');
  markdown = markdown.replace(/\\end\{itemize\}/g, '');
  markdown = markdown.replace(/\\item\s+/g, '- ');
  markdown = markdown.replace(/\\begin\{enumerate\}/g, '');
  markdown = markdown.replace(/\\end\{enumerate\}/g, '');
  markdown = markdown.replace(/\\\\/g, '\n');

  return markdown;
};

export const PuzzleViewDialog = ({
  puzzle,
  open,
  onOpenChange,
}: PuzzleViewDialogProps) => {
  const [tab, setTab] = useState<
    'base' | 'test' | 'ratings' | 'instructions' | 'creator-solution'
  >('base');
  const [renderedHtml, setRenderedHtml] = useState<string | null>(null);
  const [showCreatorSolutionPreview, setShowCreatorSolutionPreview] =
    useState(false);

  // Fetch full puzzle details when dialog opens
  const { data: fullPuzzle } = usePuzzle({
    id: String(puzzle?.id || ''),
    config: {
      enabled: open && !!puzzle?.id,
    },
  });

  // Use full puzzle if available, otherwise use the passed puzzle
  const displayPuzzle = fullPuzzle || puzzle;

  useEffect(() => {
    if (!open || !displayPuzzle || tab !== 'instructions') {
      setRenderedHtml(null);
      return;
    }

    const renderMarkdown = async () => {
      try {
        const [markdown] = await Promise.all([
          import('markdown-it'),
          import('markdown-it-katex'),
        ]);

        const mdit = markdown.default();
        const katex = (await import('markdown-it-katex')).default;
        mdit.use(katex);

        const instructions = displayPuzzle.instructions || '';
        const processedMarkdown = latexToMarkdown(instructions);
        const html = mdit.render(processedMarkdown);

        const { default: DOMPurify } = await import('dompurify');
        const clean = DOMPurify.sanitize(html);
        setRenderedHtml(clean);
      } catch (error) {
        console.error('Failed to render markdown:', error);
        setRenderedHtml('<p>Error rendering instructions</p>');
      }
    };

    renderMarkdown();
  }, [open, displayPuzzle, tab]);

  useEffect(() => {
    if (!open) {
      setShowCreatorSolutionPreview(false);
    }
  }, [open]);

  if (!displayPuzzle) return null;

  const creatorSolutionPayload = getCreatorSolutionPayload(displayPuzzle);
  const creatorSolutionMeta = getCreatorSolutionMeta(displayPuzzle);
  const creatorSolution = parseCreatorSolution(creatorSolutionPayload);
  const creatorSolutionAvailable = !!creatorSolutionPayload;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex max-h-[80vh] max-w-2xl flex-col bg-card">
        <DialogHeader>
          <DialogTitle className="text-foreground">
            {displayPuzzle.title}
          </DialogTitle>
        </DialogHeader>

        {/* Tabs */}
        <div className="flex border-b border-border">
          <button
            onClick={() => setTab('base')}
            className={`px-4 py-2 text-[13px] font-medium transition-colors ${
              tab === 'base'
                ? 'border-b-2 border-foreground text-foreground'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            Base Data
          </button>
          <button
            onClick={() => setTab('test')}
            className={`px-4 py-2 text-[13px] font-medium transition-colors ${
              tab === 'test'
                ? 'border-b-2 border-foreground text-foreground'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            Test Cases
          </button>
          <button
            onClick={() => setTab('ratings')}
            className={`px-4 py-2 text-[13px] font-medium transition-colors ${
              tab === 'ratings'
                ? 'border-b-2 border-foreground text-foreground'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            Solving and Rating
          </button>
          <button
            onClick={() => setTab('instructions')}
            className={`px-4 py-2 text-[13px] font-medium transition-colors ${
              tab === 'instructions'
                ? 'border-b-2 border-foreground text-foreground'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            Instructions
          </button>
          <button
            onClick={() => setTab('creator-solution')}
            className={`px-4 py-2 text-[13px] font-medium transition-colors ${
              tab === 'creator-solution'
                ? 'border-b-2 border-foreground text-foreground'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            Creator Solution
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 space-y-4 overflow-y-auto p-4">
          {tab === 'base' && (
            <div className="space-y-4">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                  Title
                </p>
                <p className="text-[13px] text-foreground">
                  {displayPuzzle.title}
                </p>
              </div>
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                  Description
                </p>
                <p className="text-[13px] text-foreground">
                  {displayPuzzle.description || 'No description'}
                </p>
              </div>
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                  Creator
                </p>
                <p className="text-[13px] text-foreground">
                  {displayPuzzle.creator?.username || 'Unknown'}
                </p>
              </div>
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                  Difficulty
                </p>
                <p className="text-[13px] text-foreground">
                  {displayPuzzle.difficulty}
                </p>
              </div>
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                  Status
                </p>
                <p className="text-[13px] capitalize text-foreground">
                  {(displayPuzzle as any).status ||
                    ((displayPuzzle as any).isPublished
                      ? 'Published'
                      : 'Unpublished')}
                </p>
              </div>
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                  Visibility
                </p>
                <p className="text-[13px] text-foreground">
                  {displayPuzzle.isPublic ? 'Public' : 'Private'}
                </p>
              </div>
              {displayPuzzle.creatorComment && (
                <div>
                  <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                    Creator Comment
                  </p>
                  <p className="rounded bg-secondary p-2 text-[13px] text-foreground">
                    {displayPuzzle.creatorComment}
                  </p>
                </div>
              )}
              {displayPuzzle.defaultGateSet && (
                <div>
                  <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                    Default Gate Set
                  </p>
                  <p className="text-[13px] text-foreground">
                    {(displayPuzzle.defaultGateSet as any).join?.(',') ||
                      displayPuzzle.defaultGateSet}
                  </p>
                </div>
              )}
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                  Arsenal Allowed
                </p>
                <p className="text-[13px] text-foreground">
                  {displayPuzzle.allowArsenal ? 'Yes' : 'No'}
                </p>
              </div>
            </div>
          )}

          {tab === 'test' && (
            <div className="space-y-4">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                  Time Limit
                </p>
                <p className="rounded bg-secondary p-2 text-[13px] text-foreground">
                  {displayPuzzle.timeLimit} seconds
                </p>
              </div>
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                  Budget Limit
                </p>
                <p className="rounded bg-secondary p-2 text-[13px] text-foreground">
                  {displayPuzzle.budgetLimit || displayPuzzle.budget}
                </p>
              </div>
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                  Test Cases
                </p>
                <div className="overflow-hidden rounded border border-border">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border bg-secondary">
                        <th className="px-3 py-2 text-left text-foreground">
                          Inputs
                        </th>
                        <th className="px-3 py-2 text-left text-foreground">
                          Expected Outputs
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {(displayPuzzle as any).test_cases &&
                      (displayPuzzle as any).test_cases.length > 0 ? (
                        (displayPuzzle as any).test_cases
                          .filter((tc: any) => {
                            const hasInputs =
                              tc.inputs && Object.keys(tc.inputs).length > 0;
                            const hasOutputs =
                              tc.outputs && Object.keys(tc.outputs).length > 0;
                            const hasInputStreams =
                              Array.isArray(tc.input_stream) &&
                              tc.input_stream.length > 0;
                            const hasOutputStreams =
                              Array.isArray(tc.expected_output_stream) &&
                              tc.expected_output_stream.length > 0;
                            return (
                              hasInputs ||
                              hasOutputs ||
                              hasInputStreams ||
                              hasOutputStreams
                            );
                          })
                          .map((tc: any, idx: number) => (
                            <tr
                              key={idx}
                              className="border-b border-border hover:bg-secondary/50"
                            >
                              <td className="px-3 py-2 text-[11px] text-muted-foreground">
                                <pre className="text-wrap break-words font-mono">
                                  {JSON.stringify(
                                    tc.inputs || tc.input_stream || {},
                                  )}
                                </pre>
                              </td>
                              <td className="px-3 py-2 text-[11px] text-muted-foreground">
                                <pre className="text-wrap break-words font-mono">
                                  {JSON.stringify(
                                    tc.outputs ||
                                      tc.expected_output_stream ||
                                      {},
                                  )}
                                </pre>
                              </td>
                            </tr>
                          ))
                      ) : (
                        <tr>
                          <td
                            colSpan={2}
                            className="px-3 py-2 text-center text-muted-foreground"
                          >
                            No test cases specified
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                  Gate Limits (Allowed Gates)
                </p>
                <div className="rounded bg-secondary p-3 text-[13px] text-foreground">
                  {(displayPuzzle as any).gateLimits &&
                  Object.keys((displayPuzzle as any).gateLimits).length > 0
                    ? Object.entries((displayPuzzle as any).gateLimits)
                        .map(
                          ([gate, limit]: [string, any]) =>
                            `${gate}-${limit === null ? 'unlimited' : limit}`,
                        )
                        .join(', ')
                    : 'No gates allowed'}
                </div>
              </div>
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                  Arsenal Pieces
                </p>
                <p className="inline-flex items-center gap-1.5 text-[12px] text-foreground">
                  {displayPuzzle.allowArsenal !== false ? (
                    <>
                      <CircleCheck
                        className="size-3.5 text-emerald-600"
                        aria-hidden
                      />
                      Allowed
                    </>
                  ) : (
                    <>
                      <CircleX className="size-3.5 text-red-600" aria-hidden />
                      Not allowed - Only basic gates permitted
                    </>
                  )}
                </p>
              </div>
              {displayPuzzle.allowArsenal !== false &&
                displayPuzzle.specialComponents &&
                displayPuzzle.specialComponents.length > 0 && (
                  <div>
                    <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                      Available Arsenal
                    </p>
                    <div className="space-y-2">
                      {displayPuzzle.specialComponents.map(
                        (comp: any, idx: number) => (
                          <div
                            key={idx}
                            className="rounded bg-secondary p-3 text-[12px]"
                          >
                            <p className="text-foreground">
                              <strong>{comp.type}</strong> - Cost: {comp.cost},
                              Pins: {comp.pins}
                            </p>
                          </div>
                        ),
                      )}
                    </div>
                  </div>
                )}
            </div>
          )}

          {tab === 'ratings' && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                    Total Solves
                  </p>
                  <p className="rounded bg-secondary p-2 text-[13px] text-foreground">
                    {displayPuzzle.solvedCount || 0}
                  </p>
                </div>
                <div>
                  <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                    Times Saved
                  </p>
                  <p className="rounded bg-secondary p-2 text-[13px] text-foreground">
                    {(displayPuzzle as any).timesSaved || 0}
                  </p>
                </div>
              </div>

              <div>
                <p className="mb-2 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                  Average Ratings
                </p>
                <div className="grid grid-cols-3 gap-3">
                  <div className="rounded bg-secondary p-3">
                    <p className="mb-1 text-[11px] text-muted-foreground">
                      Difficulty
                    </p>
                    <p className="text-[16px] font-semibold text-foreground">
                      {Math.round(
                        (displayPuzzle.rating_metrics?.avg_difficulty || 0) *
                          10,
                      ) / 10}
                      /5
                    </p>
                  </div>
                  <div className="rounded bg-secondary p-3">
                    <p className="mb-1 text-[11px] text-muted-foreground">
                      Fun
                    </p>
                    <p className="text-[16px] font-semibold text-foreground">
                      {Math.round(
                        (displayPuzzle.rating_metrics?.avg_fun || 0) * 10,
                      ) / 10}
                      /5
                    </p>
                  </div>
                  <div className="rounded bg-secondary p-3">
                    <p className="mb-1 text-[11px] text-muted-foreground">
                      Clearness
                    </p>
                    <p className="text-[16px] font-semibold text-foreground">
                      {Math.round(
                        (displayPuzzle.rating_metrics?.avg_clearness || 0) * 10,
                      ) / 10}
                      /5
                    </p>
                  </div>
                </div>
              </div>

              <div>
                <p className="mb-2 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                  Rating Distribution
                </p>
                <div className="overflow-hidden rounded border border-border">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border bg-secondary">
                        <th className="px-3 py-2 text-left text-foreground">
                          Stars
                        </th>
                        <th className="px-3 py-2 text-center text-foreground">
                          Difficulty
                        </th>
                        <th className="px-3 py-2 text-center text-foreground">
                          Fun
                        </th>
                        <th className="px-3 py-2 text-center text-foreground">
                          Clearness
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {[5, 4, 3, 2, 1].map((stars) => {
                        const distribution = (
                          displayPuzzle.rating_metrics as any
                        )?.rating_distribution;
                        const diffCount =
                          distribution?.difficulty?.[stars - 1] || 0;
                        const funCount = distribution?.fun?.[stars - 1] || 0;
                        const clearCount =
                          distribution?.clearness?.[stars - 1] || 0;
                        return (
                          <tr
                            key={stars}
                            className="border-b border-border hover:bg-secondary/50"
                          >
                            <td className="px-3 py-2 text-foreground">
                              <span className="inline-flex items-center gap-1">
                                <Star
                                  className="size-3.5 fill-yellow-500 text-yellow-500"
                                  aria-hidden
                                />
                                {stars} star{stars === 1 ? '' : 's'}
                              </span>
                            </td>
                            <td className="px-3 py-2 text-center text-muted-foreground">
                              {diffCount}
                            </td>
                            <td className="px-3 py-2 text-center text-muted-foreground">
                              {funCount}
                            </td>
                            <td className="px-3 py-2 text-center text-muted-foreground">
                              {clearCount}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              <div>
                <p className="mb-2 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                  Medal Distribution
                </p>
                <div className="overflow-hidden rounded border border-border">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border bg-secondary">
                        <th className="px-3 py-2 text-left text-foreground">
                          Medal
                        </th>
                        <th className="px-3 py-2 text-center text-foreground">
                          Count
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr className="border-b border-border hover:bg-secondary/50">
                        <td className="px-3 py-2 text-foreground">
                          <span className="inline-flex items-center gap-1.5">
                            <Medal
                              className="size-3.5 text-amber-500"
                              aria-hidden
                            />
                            Gold
                          </span>
                        </td>
                        <td className="px-3 py-2 text-center text-muted-foreground">
                          {(displayPuzzle as any).medalDistribution?.gold || 0}
                        </td>
                      </tr>
                      <tr className="border-b border-border hover:bg-secondary/50">
                        <td className="px-3 py-2 text-foreground">
                          <span className="inline-flex items-center gap-1.5">
                            <Medal
                              className="size-3.5 text-slate-400"
                              aria-hidden
                            />
                            Silver
                          </span>
                        </td>
                        <td className="px-3 py-2 text-center text-muted-foreground">
                          {(displayPuzzle as any).medalDistribution?.silver ||
                            0}
                        </td>
                      </tr>
                      <tr className="border-b border-border hover:bg-secondary/50">
                        <td className="px-3 py-2 text-foreground">
                          <span className="inline-flex items-center gap-1.5">
                            <Medal
                              className="size-3.5 text-amber-700"
                              aria-hidden
                            />
                            Bronze
                          </span>
                        </td>
                        <td className="px-3 py-2 text-center text-muted-foreground">
                          {(displayPuzzle as any).medalDistribution?.bronze ||
                            0}
                        </td>
                      </tr>
                      <tr className="hover:bg-secondary/50">
                        <td className="px-3 py-2 text-foreground">
                          - Unsolved
                        </td>
                        <td className="px-3 py-2 text-center text-muted-foreground">
                          {(displayPuzzle as any).medalDistribution?.none || 0}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {tab === 'instructions' && (
            <div>
              {displayPuzzle.instructions && renderedHtml ? (
                <>
                  <style>{`
                    .prose .katex {
                      vertical-align: baseline !important;
                      margin: 0 !important;
                      padding: 0 !important;
                      line-height: 1 !important;
                      font-size: inherit;
                      display: inline-block !important;
                      white-space: nowrap;
                      position: relative;
                      top: -0.35em;
                    }
                    .prose .katex-html {
                      vertical-align: baseline !important;
                    }
                    .prose .katex-display {
                      margin: 0.5em 0;
                      vertical-align: baseline;
                      position: static;
                      top: auto;
                    }
                    .prose table {
                      border-collapse: collapse;
                      width: 100%;
                      margin: 1em 0;
                    }
                    .prose table td,
                    .prose table th {
                      border: 1px solid currentColor;
                      padding: 0.5em;
                      text-align: center;
                      vertical-align: middle;
                      line-height: 1.4;
                    }
                    .prose table th {
                      font-weight: bold;
                      background-color: rgba(0, 0, 0, 0.05);
                    }
                    .prose u {
                      text-decoration: underline;
                      text-underline-offset: 4px;
                    }
                  `}</style>
                  <div
                    className="prose prose-sm max-w-none text-foreground dark:prose-invert [&_*]:text-foreground"
                    dangerouslySetInnerHTML={{ __html: renderedHtml }}
                  />
                </>
              ) : (
                <div className="text-[13px] text-muted-foreground">
                  No instructions provided.
                </div>
              )}
            </div>
          )}

          {tab === 'creator-solution' && (
            <div className="space-y-4">
              <div className="rounded-lg border border-border bg-secondary/40 p-4">
                <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                  Creator Solution
                </p>
                <p className="mt-2 text-[13px] text-foreground">
                  Preview the uploaded sample solution in a read-only
                  workstation window styled like Arsenal preview.
                </p>
              </div>

              {creatorSolutionAvailable ? (
                <>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="rounded border border-border/60 bg-secondary p-3">
                      <p className="text-[11px] text-muted-foreground">
                        Components
                      </p>
                      <p className="text-[16px] font-semibold text-foreground">
                        {creatorSolution.placed.length}
                      </p>
                    </div>
                    <div className="rounded border border-border/60 bg-secondary p-3">
                      <p className="text-[11px] text-muted-foreground">Wires</p>
                      <p className="text-[16px] font-semibold text-foreground">
                        {creatorSolution.wires.length}
                      </p>
                    </div>
                  </div>

                  <button
                    onClick={() => setShowCreatorSolutionPreview(true)}
                    className="rounded-lg bg-foreground px-4 py-2 text-[13px] font-medium text-background transition-colors hover:bg-foreground/90"
                  >
                    Open Preview Window
                  </button>
                </>
              ) : (
                <div className="space-y-2 rounded-lg border border-border bg-card p-4 text-[13px] text-muted-foreground">
                  <div>
                    No creator solution is available for preview for this
                    puzzle.
                  </div>
                  {creatorSolutionMeta && (
                    <div className="space-y-1 text-[11px] text-muted-foreground/90">
                      <div>
                        Backend availability:{' '}
                        {String(creatorSolutionMeta.available)}
                      </div>
                      {creatorSolutionMeta.riddle_base_name && (
                        <div>
                          Riddle base:{' '}
                          {String(creatorSolutionMeta.riddle_base_name)}
                        </div>
                      )}
                      {creatorSolutionMeta.expected_path && (
                        <div className="break-all">
                          Expected file:{' '}
                          {String(creatorSolutionMeta.expected_path)}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        <Dialog
          open={showCreatorSolutionPreview}
          onOpenChange={setShowCreatorSolutionPreview}
        >
          <DialogContent className="max-h-[85vh] max-w-4xl overflow-y-auto">
            <DialogHeader>
              <DialogTitle>
                {displayPuzzle.title} - Creator Solution Preview
              </DialogTitle>
              <DialogDescription>
                Read-only preview of the sample solution used by the creator.
              </DialogDescription>
            </DialogHeader>
            <CreatorSolutionPreview puzzle={displayPuzzle} />
          </DialogContent>
        </Dialog>
      </DialogContent>
    </Dialog>
  );
};

const CreatorSolutionPreview = ({ puzzle }: { puzzle: Puzzle }) => {
  const creatorSolutionPayload = getCreatorSolutionPayload(puzzle);
  if (!creatorSolutionPayload) {
    return (
      <div className="rounded-lg border border-border bg-card p-4 text-sm text-muted-foreground">
        No creator solution is available for preview.
      </div>
    );
  }

  const { placed, wires, totalCost } = parseCreatorSolution(
    creatorSolutionPayload,
  );
  const inferredLabels = inferIoLabels(wires);
  const hasRenderableCircuit = placed.length > 0 || wires.length > 0;

  const inputLabels =
    Array.isArray((puzzle as any).inputs) && (puzzle as any).inputs.length > 0
      ? (puzzle as any).inputs.map((input: any) => String(input))
      : inferredLabels.inputs;

  const outputLabels =
    Array.isArray((puzzle as any).outputs) && (puzzle as any).outputs.length > 0
      ? (puzzle as any).outputs.map((output: any) => String(output))
      : inferredLabels.outputs;

  const knownComponentsMap = new Map<string, CircuitComponent>();
  [
    ...((puzzle as any).specialComponents || []),
    ...((puzzle as any).customComponents || []),
    ...((puzzle as any).arsenalComponents || []),
  ].forEach((component: CircuitComponent) => {
    knownComponentsMap.set(String(component.id), component);
  });
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

  const rowsRaw = Number((puzzle as any).board_rows);
  const colsRaw = Number((puzzle as any).board_cols);
  const boardRows =
    Number.isFinite(rowsRaw) && rowsRaw > 0 ? rowsRaw : computedRows;
  const boardCols =
    Number.isFinite(colsRaw) && colsRaw > 0 ? colsRaw : computedCols;

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-border/40 bg-foreground/5 p-3">
        <p className="text-sm text-foreground">
          This is the sample solution uploaded by the creator for this puzzle.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <div className="rounded-lg border border-border/60 bg-secondary/40 p-3">
          <p className="mb-1 text-xs text-foreground/70">Inputs</p>
          <p className="text-lg font-semibold text-foreground">
            {inputLabels.length}
          </p>
        </div>
        <div className="rounded-lg border border-border/60 bg-secondary/40 p-3">
          <p className="mb-1 text-xs text-foreground/70">Outputs</p>
          <p className="text-lg font-semibold text-foreground">
            {outputLabels.length}
          </p>
        </div>
        <div className="rounded-lg border border-border/60 bg-secondary/40 p-3">
          <p className="mb-1 text-xs text-foreground/70">Components</p>
          <p className="text-lg font-semibold text-foreground">
            {placed.length}
          </p>
        </div>
        <div className="rounded-lg border border-border/60 bg-secondary/40 p-3">
          <p className="mb-1 text-xs text-foreground/70">Cost</p>
          <p className="text-lg font-semibold text-foreground">{totalCost}</p>
        </div>
      </div>

      {!hasRenderableCircuit && (
        <div className="rounded-lg border border-amber-300/60 bg-amber-50/50 p-3 text-[12px] text-amber-900">
          Creator solution payload was found but no circuit nodes/wires could be
          parsed for rendering.
          <div className="mt-1 text-[11px] text-amber-800/90">
            Keys: {Object.keys(creatorSolutionPayload).join(', ') || 'none'}
          </div>
        </div>
      )}

      <div
        className="relative overflow-hidden rounded-lg border border-border/60 bg-background"
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
            puzzleId={`creator-solution-preview-${puzzle.id}`}
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
        <div className="rounded-lg border border-border/60 bg-secondary/30 p-3">
          <p className="mb-2 text-xs font-semibold text-foreground/70">
            Components Used:
          </p>
          <div className="flex flex-wrap gap-2">
            {placed
              .filter(
                (component, index, all) =>
                  all.findIndex(
                    (candidate) =>
                      candidate.componentId === component.componentId,
                  ) === index,
              )
              .map((component) => (
                <div
                  key={component.componentId}
                  className="flex items-center gap-2 text-xs"
                >
                  <span className="text-foreground/70">
                    {catalog[component.componentId]?.label ||
                      component.componentId}
                  </span>
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  );
};
