import { describe, expect, it } from 'vitest';

import type { Wire } from '@/types/api';

import { findUnconnectedPorts } from '../validate-connections';

const wire = (fromId: string, toId: string): Wire => ({
  id: `${fromId}->${toId}`,
  from: { componentId: fromId, pinIndex: 0, portId: 'P0' },
  to: { componentId: toId, pinIndex: 0, portId: 'P0' },
});

describe('findUnconnectedPorts', () => {
  it('flags every port when there are no wires', () => {
    const result = findUnconnectedPorts(['in0', 'in1'], ['out0'], []);
    expect(result.unconnectedInputs).toEqual(['in0', 'in1']);
    expect(result.unconnectedOutputs).toEqual(['out0']);
  });

  it('treats a wire whose `from` is the input IO id as connected', () => {
    const result = findUnconnectedPorts(
      ['in0'],
      ['out0'],
      [wire('IO:IN:in0', 'AND-1')],
    );
    expect(result.unconnectedInputs).toEqual([]);
    expect(result.unconnectedOutputs).toEqual(['out0']);
  });

  it('treats a wire whose `to` is the output IO id as connected', () => {
    const result = findUnconnectedPorts(
      ['in0'],
      ['out0'],
      [wire('AND-1', 'IO:OUT:out0')],
    );
    expect(result.unconnectedInputs).toEqual(['in0']);
    expect(result.unconnectedOutputs).toEqual([]);
  });

  it('returns empty arrays when every port is wired', () => {
    const result = findUnconnectedPorts(
      ['in0', 'in1'],
      ['out0'],
      [
        wire('IO:IN:in0', 'AND-1'),
        wire('IO:IN:in1', 'AND-1'),
        wire('AND-1', 'IO:OUT:out0'),
      ],
    );
    expect(result.unconnectedInputs).toEqual([]);
    expect(result.unconnectedOutputs).toEqual([]);
  });

  it('handles port names with spaces', () => {
    const result = findUnconnectedPorts(
      ['First Addend', 'Second Addend'],
      ['Sum'],
      [wire('IO:IN:First Addend', 'XOR-1')],
    );
    expect(result.unconnectedInputs).toEqual(['Second Addend']);
    expect(result.unconnectedOutputs).toEqual(['Sum']);
  });

  it('does not count wires that never touch IO ports', () => {
    const result = findUnconnectedPorts(
      ['in0'],
      ['out0'],
      [wire('AND-1', 'AND-2')],
    );
    expect(result.unconnectedInputs).toEqual(['in0']);
    expect(result.unconnectedOutputs).toEqual(['out0']);
  });

  it('returns empty arrays for zero ports', () => {
    const result = findUnconnectedPorts([], [], []);
    expect(result.unconnectedInputs).toEqual([]);
    expect(result.unconnectedOutputs).toEqual([]);
  });
});
