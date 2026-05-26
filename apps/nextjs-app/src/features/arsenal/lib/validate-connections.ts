import type { Wire } from '@/types/api';

/**
 * Find inputs/outputs declared by an arsenal piece that have no wire connected
 * to them. Used by the arsenal creator's Save action to warn before the piece
 * is persisted.
 *
 * IO endpoint convention (shared with the puzzle workstation):
 * - An input named `L` is represented in wires as `IO:IN:${L}`.
 * - An output named `L` is represented in wires as `IO:OUT:${L}`.
 *
 * "Connected" semantics:
 * - An input is connected if any wire's `from` or `to` endpoint references its
 *   IO id. The workstation creates input-sourced wires as `from: IO:IN:...` but
 *   in some flows the endpoint can appear on either side, so we check both.
 * - An output is connected by the same any-side rule.
 */
export type UnconnectedPorts = {
  unconnectedInputs: string[];
  unconnectedOutputs: string[];
};

export const findUnconnectedPorts = (
  inputs: readonly string[],
  outputs: readonly string[],
  wires: readonly Wire[],
): UnconnectedPorts => {
  const touched = new Set<string>();
  for (const w of wires) {
    if (w?.from?.componentId) touched.add(w.from.componentId);
    if (w?.to?.componentId) touched.add(w.to.componentId);
  }

  const unconnectedInputs = inputs.filter(
    (label) => !touched.has(`IO:IN:${label}`),
  );
  const unconnectedOutputs = outputs.filter(
    (label) => !touched.has(`IO:OUT:${label}`),
  );

  return { unconnectedInputs, unconnectedOutputs };
};
