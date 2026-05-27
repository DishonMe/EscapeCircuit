'use client';

/* eslint-disable import/no-restricted-paths -- shared workstation primitives currently live under app/; extracting them is a separate refactor. */
import { extractVisualStyleFromComponentLike } from '@/app/app/puzzles/[id]/_components/piece-visual-style';
import { WorkstationGrid } from '@/app/app/puzzles/[id]/_components/workstation-grid';
import type {
  ComponentDef,
  PlacedGridComponent,
} from '@/app/app/puzzles/[id]/_components/workstation-grid';
/* eslint-enable import/no-restricted-paths */
import { useMyArsenal } from '@/features/arsenal/api';
import type { ArsenalPiece } from '@/features/arsenal/api';
import type { Wire } from '@/types/api';

type PreviewPiece = Pick<
  ArsenalPiece,
  'id' | 'name' | 'cost' | 'description' | 'structure_json'
> & {
  num_inputs?: number;
  num_outputs?: number;
};

export function CircuitPreview({ piece }: { piece: PreviewPiece }) {
  const { data: myArsenal } = useMyArsenal();

  const parseStructure = (
    structureJson: string,
  ): {
    numInputs: number;
    numOutputs: number;
    placed: PlacedGridComponent[];
    wires: Wire[];
  } => {
    try {
      return JSON.parse(structureJson || '{}');
    } catch {
      return { numInputs: 0, numOutputs: 0, placed: [], wires: [] };
    }
  };

  const structure = parseStructure(piece.structure_json);
  const { placed, wires } = structure;

  const inputLabels = Array.from(
    { length: structure.numInputs },
    (_, i) => `in${i}`,
  );
  const outputLabels = Array.from(
    { length: structure.numOutputs },
    (_, i) => `out${i}`,
  );

  const arsenalMap = new Map<string, ArsenalPiece>();
  if (myArsenal) {
    myArsenal.forEach((ap) => {
      arsenalMap.set(String(ap.id), ap);
    });
  }

  const catalog: Record<string, ComponentDef> = {
    AND: {
      id: 'AND',
      label: 'AND',
      cost: 1,
      size: { w: 3, h: 2 },
      ports: [
        { id: 'P0', kind: 'input', offset: { row: 0, col: 0 } },
        { id: 'P1', kind: 'input', offset: { row: 1, col: 0 } },
        { id: 'P2', kind: 'output', offset: { row: 1, col: 2 } },
      ],
    },
    OR: {
      id: 'OR',
      label: 'OR',
      cost: 1,
      size: { w: 3, h: 2 },
      ports: [
        { id: 'P0', kind: 'input', offset: { row: 0, col: 0 } },
        { id: 'P1', kind: 'input', offset: { row: 1, col: 0 } },
        { id: 'P2', kind: 'output', offset: { row: 1, col: 2 } },
      ],
    },
    NOT: {
      id: 'NOT',
      label: 'NOT',
      cost: 1,
      size: { w: 3, h: 1 },
      ports: [
        { id: 'P0', kind: 'input', offset: { row: 0, col: 0 } },
        { id: 'P1', kind: 'output', offset: { row: 0, col: 2 } },
      ],
    },
    XOR: {
      id: 'XOR',
      label: 'XOR',
      cost: 2,
      size: { w: 3, h: 2 },
      ports: [
        { id: 'P0', kind: 'input', offset: { row: 0, col: 0 } },
        { id: 'P1', kind: 'input', offset: { row: 1, col: 0 } },
        { id: 'P2', kind: 'output', offset: { row: 1, col: 2 } },
      ],
    },
    NAND: {
      id: 'NAND',
      label: 'NAND',
      cost: 1,
      size: { w: 3, h: 2 },
      ports: [
        { id: 'P0', kind: 'input', offset: { row: 0, col: 0 } },
        { id: 'P1', kind: 'input', offset: { row: 1, col: 0 } },
        { id: 'P2', kind: 'output', offset: { row: 1, col: 2 } },
      ],
    },
    NOR: {
      id: 'NOR',
      label: 'NOR',
      cost: 1,
      size: { w: 3, h: 2 },
      ports: [
        { id: 'P0', kind: 'input', offset: { row: 0, col: 0 } },
        { id: 'P1', kind: 'input', offset: { row: 1, col: 0 } },
        { id: 'P2', kind: 'output', offset: { row: 1, col: 2 } },
      ],
    },
    XNOR: {
      id: 'XNOR',
      label: 'XNOR',
      cost: 2,
      size: { w: 3, h: 2 },
      ports: [
        { id: 'P0', kind: 'input', offset: { row: 0, col: 0 } },
        { id: 'P1', kind: 'input', offset: { row: 1, col: 0 } },
        { id: 'P2', kind: 'output', offset: { row: 1, col: 2 } },
      ],
    },
  };

  placed.forEach((comp) => {
    if (!catalog[comp.componentId]) {
      const arsenalPiece = arsenalMap.get(comp.componentId);
      if (arsenalPiece && (arsenalPiece as any).is_arsenal) {
        const numInputs = (arsenalPiece as any).num_inputs ?? 0;
        const numOutputs = (arsenalPiece as any).num_outputs ?? 0;
        const maxPorts = Math.max(numInputs, numOutputs);
        const size = { w: 3, h: Math.max(1, maxPorts) };

        const ports: Array<{
          id: string;
          kind: 'input' | 'output';
          offset: { row: number; col: number };
        }> = [];
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
          label: arsenalPiece.name,
          cost: arsenalPiece.cost,
          size,
          ports,
          visualStyle: extractVisualStyleFromComponentLike(arsenalPiece),
        };
      } else {
        catalog[comp.componentId] = {
          id: comp.componentId,
          label: comp.componentId,
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

  const gridRows = Math.max(
    15,
    Math.max(...placed.map((c) => c.origin.row), 0) + 3,
  );
  const gridCols = Math.max(
    30,
    Math.max(...placed.map((c) => c.origin.col), 0) + 3,
  );

  return (
    <div className="space-y-4">
      {piece.description && (
        <div className="rounded-lg border border-border/40 bg-foreground/5 p-3">
          <p className="text-sm text-foreground">{piece.description}</p>
        </div>
      )}

      <div className="grid grid-cols-4 gap-3">
        <div className="rounded-lg border border-border/60 bg-secondary/40 p-3">
          <p className="mb-1 text-xs text-foreground/70">Inputs</p>
          <p className="text-lg font-semibold text-foreground">
            {structure.numInputs}
          </p>
        </div>
        <div className="rounded-lg border border-border/60 bg-secondary/40 p-3">
          <p className="mb-1 text-xs text-foreground/70">Outputs</p>
          <p className="text-lg font-semibold text-foreground">
            {structure.numOutputs}
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
          <p className="text-lg font-semibold text-foreground">{piece.cost}</p>
        </div>
      </div>

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
            puzzleId={`arsenal-preview-${piece.id}`}
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
            boardRows={gridRows}
            boardCols={gridCols}
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
                (comp, idx, arr) =>
                  arr.findIndex((c) => c.componentId === comp.componentId) ===
                  idx,
              )
              .map((comp) => (
                <div
                  key={comp.componentId}
                  className="flex items-center gap-2 text-xs"
                >
                  <span className="text-foreground/70">{comp.componentId}</span>
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}
