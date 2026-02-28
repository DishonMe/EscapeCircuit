'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { api } from '@/lib/api-client';
import type { Wire } from '@/types/api';
import type { ComponentDef, PlacedGridComponent } from '@/app/app/puzzles/[id]/_components/workstation-grid';


export type DebuggerProps = {
  isOpen: boolean;
  onClose: () => void;
  inputs: string[];
  outputs: string[];
  placed: PlacedGridComponent[];
  wires: Wire[];
  catalog: Record<string, ComponentDef>;
  puzzleId?: string;
  onDebug?: (gateOutputs: any[], puzzleOutputs: Record<string, number>) => void;
};

type GateOutput = {
  placedId: string;
  componentId: string;
  displayLabel: string;
  values: string;
};

export function CircuitDebugger({
  isOpen,
  onClose,
  inputs,
  outputs,
  placed,
  wires,
  catalog,
  puzzleId,
  onDebug,
}: DebuggerProps) {
  const [mode, setMode] = useState<'single' | 'sequence'>('single');
  const [inputValues, setInputValues] = useState<Record<string, string>>(
    Object.fromEntries(inputs.map((inp) => [inp, '0']))
  );
  const [sequenceInputs, setSequenceInputs] = useState<Record<string, string>>(
    Object.fromEntries(inputs.map((inp) => [inp, '']))
  );
  const [gateOutputs, setGateOutputs] = useState<GateOutput[][]>([]);
  const [puzzleOutputs, setPuzzleOutputs] = useState<Record<string, string>[]>([]);
  const [hasRun, setHasRun] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [stepCount, setStepCount] = useState(0);

  // Helper: count same component types for numbering
  const getComponentDisplayLabel = (
    componentId: string,
    placedId: string
  ): string => {
    const def = catalog[componentId];
    if (!def) return componentId;

    const sameTypeComponents = placed.filter(
      (p) => p.componentId === componentId
    );
    if (sameTypeComponents.length <= 1) {
      return def.label;
    }

    const index = sameTypeComponents.findIndex((p) => p.id === placedId);
    if (index === -1) {
      return def.label;
    }

    return `${index + 1}-${def.label.toLowerCase()}`;
  };

  const handleInputChange = (inputName: string, value: string) => {
    // Ensure only 0 or 1
    if (value === '' || value === '0' || value === '1') {
      setInputValues((prev) => ({
        ...prev,
        [inputName]: value,
      }));
    }
  };

  const handleSequenceChange = (inputName: string, value: string) => {
    // Allow 0, 1, and comma for sequence input
    if (/^[01,]*$/.test(value)) {
      setSequenceInputs((prev) => ({
        ...prev,
        [inputName]: value,
      }));
    }
  };

  const handleRunDebugger = async () => {
    if (mode === 'single') {
      await handleRunSingleStep();
    } else {
      await handleRunSequence();
    }
  };

  const handleRunSingleStep = async () => {
    // Validate inputs
    const allValid = inputs.every((inp) => {
      const val = inputValues[inp];
      return val === '0' || val === '1';
    });

    if (!allValid) {
      setError('Please enter 0 or 1 for all inputs');
      return;
    }

    setError(null);
    setIsLoading(true);

    try {
      // Build the solution structure for the backend
      const solution = {
        placedComponents: placed.map((p) => ({
          id: p.id,
          componentId: p.componentId,
          x: p.origin.col,
          y: p.origin.row,
        })),
        wires,
        totalCost: 0,
      };

      // Convert input values to numbers
      const inputsForBackend: Record<string, number> = {};
      for (const inp of inputs) {
        inputsForBackend[inp] = parseInt(inputValues[inp], 10);
      }

      // Call backend simulation endpoint using the proper API client
      const endpoint = puzzleId === 'arsenal-creator' ? '/arsenal/simulate' : `/puzzles/${puzzleId}/simulate`;
      const result = await api.post<any>(endpoint, {
        solution,
        inputs: inputsForBackend,
      });

      // Process results
      const gateList: GateOutput[] = result.gateOutputs.map((gate: any) => ({
        ...gate,
        displayLabel: getComponentDisplayLabel(gate.componentId, gate.placedId),
      }));

      const puzzleOutputsMap: Record<string, string> = {};
      for (const [key, value] of Object.entries(result.puzzleOutputs)) {
        puzzleOutputsMap[key] = String(value);
      }

      setGateOutputs([gateList]);
      setPuzzleOutputs([puzzleOutputsMap]);
      setHasRun(true);
      setStepCount(1);

      // Call callback if provided
      if (onDebug) {
        onDebug(gateList, result.puzzleOutputs);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to simulate circuit');
      console.error('Debug simulation error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRunSequence = async () => {
    // Parse sequence inputs
    const sequences: Record<string, number[]> = {};
    let maxLength = 0;

    for (const inp of inputs) {
      const sequenceStr = sequenceInputs[inp].trim();
      if (!sequenceStr) {
        setError(`Sequence for ${inp} is empty`);
        return;
      }

      // Parse "01010" or "0,1,0,1,0" format
      let bits: number[] = [];
      if (sequenceStr.includes(',')) {
        bits = sequenceStr.split(',').map((b) => {
          const val = parseInt(b.trim(), 10);
          if (val !== 0 && val !== 1) {
            throw new Error(`Invalid bit value: ${b}`);
          }
          return val;
        });
      } else {
        bits = sequenceStr.split('').map((b) => {
          const val = parseInt(b, 10);
          if (val !== 0 && val !== 1) {
            throw new Error(`Invalid bit value: ${b}`);
          }
          return val;
        });
      }

      sequences[inp] = bits;
      maxLength = Math.max(maxLength, bits.length);
    }

    // Verify all sequences have the same length
    for (const inp of inputs) {
      if (sequences[inp].length !== maxLength) {
        setError(`All sequences must have the same length (expected ${maxLength}, got ${sequences[inp].length} for ${inp})`);
        return;
      }
    }

    setError(null);
    setIsLoading(true);

    try {
      // Build the solution structure for the backend
      const solution = {
        placedComponents: placed.map((p) => ({
          id: p.id,
          componentId: p.componentId,
          x: p.origin.col,
          y: p.origin.row,
        })),
        wires,
        totalCost: 0,
      };

      // Call backend simulation endpoint with sequence
      const endpoint = puzzleId === 'arsenal-creator' ? '/arsenal/simulate' : `/puzzles/${puzzleId}/simulate`;
      const result = await api.post<any>(endpoint, {
        solution,
        inputs: sequences,
        isSequence: true,
      });

      // Process results
      const allGateOutputs: GateOutput[][] = result.steps.map((step: any) =>
        step.gateOutputs.map((gate: any) => ({
          ...gate,
          displayLabel: getComponentDisplayLabel(gate.componentId, gate.placedId),
        }))
      );

      const allPuzzleOutputs: Record<string, string>[] = result.steps.map((step: any) => {
        const map: Record<string, string> = {};
        for (const [key, value] of Object.entries(step.puzzleOutputs)) {
          map[key] = String(value);
        }
        return map;
      });

      setGateOutputs(allGateOutputs);
      setPuzzleOutputs(allPuzzleOutputs);
      setHasRun(true);
      setStepCount(maxLength);
    } catch (err: any) {
      setError(err.message || 'Failed to simulate circuit sequence');
      console.error('Debug sequence simulation error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Circuit Debugger</DialogTitle>
        </DialogHeader>

        <div className="space-y-6">
          {/* Mode Toggle */}
          <div className="flex gap-2">
            <Button
              variant={mode === 'single' ? 'default' : 'outline'}
              onClick={() => setMode('single')}
              size="sm"
            >
              Single Step
            </Button>
            <Button
              variant={mode === 'sequence' ? 'default' : 'outline'}
              onClick={() => setMode('sequence')}
              size="sm"
            >
              Sequence
            </Button>
          </div>

          {/* Input Section */}
          <div>
            <h3 className="text-[13px] font-semibold tracking-tight text-foreground mb-3">
              {mode === 'single' ? 'Puzzle Inputs' : 'Input Sequences'}
            </h3>
            {mode === 'single' ? (
              <div className="grid grid-cols-2 gap-3">
                {inputs.map((inputName) => (
                  <div key={inputName} className="flex items-center gap-2">
                    <label className="text-[13px] font-medium text-foreground w-20">{inputName}:</label>
                    <input
                      type="text"
                      inputMode="numeric"
                      value={inputValues[inputName] || ''}
                      onChange={(e) => handleInputChange(inputName, e.target.value)}
                      placeholder="0 or 1"
                      className="border border-border rounded-lg bg-background px-2.5 py-1.5 w-16 text-center text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
                      maxLength={1}
                    />
                  </div>
                ))}
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-3">
                {inputs.map((inputName) => (
                  <div key={inputName} className="flex items-start gap-2">
                    <label className="text-[13px] font-medium text-foreground w-20 pt-2">{inputName}:</label>
                    <div className="flex-1">
                      <input
                        type="text"
                        value={sequenceInputs[inputName] || ''}
                        onChange={(e) => handleSequenceChange(inputName, e.target.value)}
                        placeholder="e.g., 01010 or 0,1,0,1,0"
                        className="border border-border rounded-lg bg-background px-2.5 py-1.5 w-full text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
                      />
                      <p className="text-[11px] text-muted-foreground mt-1">
                        Enter binary digits (0,1) or comma-separated values
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Error Message */}
          {error && (
            <div className="bg-red-50/50 border border-red-200/60 rounded-lg p-3 text-[13px] text-red-700">
              {error}
            </div>
          )}

          {/* Run Button */}
          <div className="flex justify-center">
            <Button onClick={handleRunDebugger} disabled={isLoading} className="px-6">
              {isLoading ? 'Simulating...' : 'Simulate'}
            </Button>
          </div>

          {/* Results Section */}
          {hasRun && (
            <div className="space-y-4 border-t border-border/60 pt-4">
              {mode === 'single' && gateOutputs.length > 0 && (
                <>
                  {/* Gate Outputs */}
                  {gateOutputs[0].length > 0 && (
                    <div>
                      <h3 className="text-[13px] font-semibold tracking-tight text-foreground mb-2">Gate Outputs</h3>
                      <div className="space-y-1.5 bg-secondary/30 p-3 rounded-lg border border-border/60">
                        {gateOutputs[0].map((gate) => (
                          <div
                            key={gate.placedId}
                            className="flex justify-between text-[13px]"
                          >
                            <span className="font-medium text-foreground">{gate.displayLabel}:</span>
                            <span className="font-mono text-muted-foreground">{gate.values}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Puzzle Outputs */}
                  <div>
                    <h3 className="text-[13px] font-semibold tracking-tight text-foreground mb-2">Puzzle Outputs</h3>
                    <div className="space-y-1.5 bg-secondary/30 p-3 rounded-lg border border-border/60">
                      {outputs.map((outputName) => (
                        <div
                          key={outputName}
                          className="flex justify-between text-[13px]"
                        >
                          <span className="font-medium text-foreground">{outputName}:</span>
                          <span className="font-mono font-semibold text-foreground">
                            {puzzleOutputs[0]?.[outputName] || '0'}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              )}

              {mode === 'sequence' && gateOutputs.length > 0 && (
                <div className="overflow-x-auto">
                  <h3 className="text-[13px] font-semibold tracking-tight text-foreground mb-2">Simulation Results ({stepCount} steps)</h3>

                  {/* Puzzle Outputs Table */}
                  <div className="mb-4">
                    <h4 className="text-[13px] font-semibold tracking-tight text-foreground mb-2">Puzzle Outputs</h4>
                    <table className="border-collapse border border-border/60 w-full text-[13px] rounded-lg overflow-hidden">
                      <thead>
                        <tr className="bg-secondary">
                          <th className="border border-border px-3 py-2 text-left text-muted-foreground">Step</th>
                          {outputs.map((out) => (
                            <th key={out} className="border border-border px-3 py-2 text-center text-muted-foreground">
                              {out}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {puzzleOutputs.map((outputs_map, step) => (
                          <tr key={step} className={step % 2 === 0 ? 'bg-card' : 'bg-secondary/30'}>
                            <td className="border border-border px-3 py-2 font-mono text-muted-foreground">{step + 1}</td>
                            {outputs.map((out) => (
                              <td key={out} className="border border-border px-3 py-2 text-center font-mono font-semibold text-foreground">
                                {outputs_map[out] || '0'}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Gate Outputs Table */}
                  {gateOutputs.some((step) => step.length > 0) && (
                    <div>
                      <h4 className="text-[13px] font-semibold tracking-tight text-foreground mb-2">Gate Outputs</h4>
                      <table className="border-collapse border border-border/60 w-full text-[13px] rounded-lg overflow-hidden">
                        <thead>
                          <tr className="bg-secondary">
                            <th className="border border-border px-3 py-2 text-left text-muted-foreground">Step</th>
                            {gateOutputs[0]?.map((gate) => (
                              <th key={gate.placedId} className="border border-border px-3 py-2 text-center text-muted-foreground">
                                {gate.displayLabel}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {gateOutputs.map((step_gates, step) => (
                            <tr key={step} className={step % 2 === 0 ? 'bg-card' : 'bg-secondary/30'}>
                              <td className="border border-border px-3 py-2 font-mono text-muted-foreground">{step + 1}</td>
                              {step_gates.map((gate) => (
                                <td key={gate.placedId} className="border border-border px-3 py-2 text-center font-mono text-foreground">
                                  {gate.values}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
