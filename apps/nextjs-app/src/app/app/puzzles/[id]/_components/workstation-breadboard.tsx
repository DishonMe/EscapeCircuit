'use client';

import { useMemo, useRef, useState } from 'react';

import { Button } from '@/components/ui/button';
import { useNotifications } from '@/components/ui/notifications';
import { Wire } from '@/types/api';
import { cn } from '@/utils/cn';

export type PinAddress = {
  row: number;
  col: number;
  ownerId: string;
  pinIndex: number;
};

export type PlacedBoardComponent = {
  id: string;
  componentId: string;
  row: number;
  col: number;
  pins: number;
};

const ROWS = 16;
const COLS = 36;

const PIN_SIZE = 16;

const pinId = (row: number, col: number) => `r${row}c${col}`;

const parseDraggedComponentId = (e: React.DragEvent) => {
  return e.dataTransfer.getData('application/x-escapecircuit-component');
};

export const Breadboard = ({
  inputs,
  outputs,
  componentPinsById,
  placed,
  wires,
  selectedPin,
  onPinClick,
  onPlaceComponent,
  onRemoveComponent,
}: {
  inputs: string[];
  outputs: string[];
  componentPinsById: Record<string, number>;
  placed: PlacedBoardComponent[];
  wires: Wire[];
  selectedPin: PinAddress | null;
  onPinClick: (pin: PinAddress) => void;
  onPlaceComponent: (componentId: string, at: PinAddress) => void;
  onRemoveComponent: (placedId: string) => void;
}) => {
  const notifications = useNotifications();
  const boardRef = useRef<HTMLDivElement | null>(null);

  const occupied = useMemo(() => {
    const map = new Map<
      string,
      {
        placedId: string;
        pinIndex: number;
      }
    >();
    for (const p of placed) {
      for (let i = 0; i < p.pins; i++) {
        map.set(pinId(p.row, p.col + i), { placedId: p.id, pinIndex: i });
      }
    }
    return map;
  }, [placed]);

  const ioPins = useMemo(() => {
    // Reserve left-most column pins for IO labels.
    const io: Array<{
      row: number;
      col: number;
      label: string;
      ownerId: string;
    }> = [];

    for (let i = 0; i < inputs.length && i < ROWS; i++) {
      io.push({
        row: i,
        col: 0,
        label: inputs[i],
        ownerId: `IO:IN:${inputs[i]}`,
      });
    }

    for (let i = 0; i < outputs.length && i < ROWS; i++) {
      io.push({
        row: ROWS - 1 - i,
        col: 0,
        label: outputs[i],
        ownerId: `IO:OUT:${outputs[i]}`,
      });
    }

    return io;
  }, [inputs, outputs]);

  const ioByPin = useMemo(() => {
    const map = new Map<string, { label: string; ownerId: string }>();
    for (const p of ioPins)
      map.set(pinId(p.row, p.col), { label: p.label, ownerId: p.ownerId });
    return map;
  }, [ioPins]);

  const canDropAt = (row: number, col: number, pins: number) => {
    if (col < 1) return false; // keep col 0 for IO
    if (col + pins - 1 >= COLS) return false;
    for (let i = 0; i < pins; i++) {
      const id = pinId(row, col + i);
      if (occupied.has(id)) return false;
      if (ioByPin.has(id)) return false;
    }
    return true;
  };

  const [hoverDrop, setHoverDrop] = useState<{
    row: number;
    col: number;
  } | null>(null);

  return (
    <div className="flex flex-col gap-2">
      <div className="rounded-md border border-gray-300 bg-white p-3">
        <div className="mb-1 text-sm font-medium text-gray-900">Breadboard</div>
        <div className="text-xs text-gray-600">
          Pins in the same row are inherently connected. Click two pins to add a
          wire.
        </div>
      </div>

      <div
        ref={boardRef}
        className="relative overflow-auto rounded-md border border-gray-300 bg-white p-3"
        style={{
          maxHeight: 'calc(100vh - 18rem)',
        }}
      >
        <div
          className="grid gap-2"
          style={{
            gridTemplateColumns: `repeat(${COLS}, ${PIN_SIZE}px)`,
            gridTemplateRows: `repeat(${ROWS}, ${PIN_SIZE}px)`,
          }}
        >
          {Array.from({ length: ROWS }).map((_, r) =>
            Array.from({ length: COLS }).map((__, c) => {
              const id = pinId(r, c);
              const occ = occupied.get(id);
              const isOccupied = Boolean(occ);
              const io = ioByPin.get(id);

              const ownerId =
                io?.ownerId ?? (isOccupied ? occ!.placedId : `PIN:${id}`);
              const pinIndex = io ? 0 : isOccupied ? occ!.pinIndex : 0;
              const isSelected =
                selectedPin?.row === r && selectedPin?.col === c;

              const canAcceptDrop = true;

              return (
                <button
                  key={id}
                  className={cn(
                    'relative rounded-full border',
                    io
                      ? 'border-blue-300 bg-blue-50'
                      : isOccupied
                        ? 'border-gray-400 bg-gray-200'
                        : 'border-gray-300 bg-white hover:bg-gray-50',
                    isSelected && 'ring-2 ring-blue-500 ring-offset-1',
                  )}
                  title={io ? io.label : id}
                  onClick={() =>
                    onPinClick({ row: r, col: c, ownerId, pinIndex })
                  }
                  onDragOver={(e) => {
                    e.preventDefault();
                    if (!canAcceptDrop) return;
                    setHoverDrop({ row: r, col: c });
                  }}
                  onDragLeave={() => {
                    setHoverDrop((prev) =>
                      prev?.row === r && prev?.col === c ? null : prev,
                    );
                  }}
                  onDrop={(e) => {
                    e.preventDefault();
                    setHoverDrop(null);
                    const componentId = parseDraggedComponentId(e);
                    if (!componentId) return;

                    const pins = componentPinsById[componentId] ?? 0;
                    if (!pins) {
                      notifications.addNotification({
                        type: 'error',
                        title: 'Unknown component',
                        message: 'Component metadata missing.',
                      });
                      return;
                    }

                    if (!canDropAt(r, c, pins)) {
                      notifications.addNotification({
                        type: 'warning',
                        title: 'Cannot place here',
                        message:
                          'Pins are occupied or out of bounds for this component.',
                      });
                      return;
                    }

                    onPlaceComponent(componentId, {
                      row: r,
                      col: c,
                      ownerId: 'PIN',
                      pinIndex: 0,
                    });
                  }}
                >
                  {io ? (
                    <span className="absolute left-5 top-1/2 -translate-y-1/2 whitespace-nowrap text-[10px] font-medium text-blue-700">
                      {io.label}
                    </span>
                  ) : null}
                  {hoverDrop?.row === r && hoverDrop?.col === c ? (
                    <span className="absolute inset-0 rounded-full ring-2 ring-blue-200" />
                  ) : null}
                </button>
              );
            }),
          )}

          {placed.map((p) => (
            <div
              key={p.id}
              className={cn(
                'pointer-events-auto relative flex items-center justify-between rounded border border-gray-400 bg-gray-100 px-2',
              )}
              style={{
                gridRowStart: p.row + 1,
                gridColumnStart: p.col + 1,
                gridColumnEnd: p.col + 1 + p.pins,
                height: PIN_SIZE,
              }}
            >
              <div className="truncate text-[10px] font-medium text-gray-900">
                {p.componentId}
              </div>
              <Button
                size="sm"
                variant="ghost"
                className="h-6 px-2"
                onClick={(e) => {
                  e.stopPropagation();
                  onRemoveComponent(p.id);
                }}
              >
                Remove
              </Button>
            </div>
          ))}
        </div>

        <div className="mt-3 rounded border border-gray-200 bg-gray-50 p-2 text-xs text-gray-600">
          <div className="font-medium text-gray-700">Wire instructions</div>
          <div className="mt-1">
            Click one pin (it becomes selected), then click another pin to
            connect them.
          </div>
        </div>
      </div>

      <div className="rounded-md border border-gray-300 bg-white p-3">
        <div className="mb-2 text-sm font-medium text-gray-900">
          Connections
        </div>
        {wires.length === 0 ? (
          <div className="text-xs text-gray-500">No wires yet.</div>
        ) : (
          <div className="space-y-2">
            {wires.map((w) => (
              <div
                key={w.id}
                className="flex items-center justify-between gap-2 rounded border border-gray-200 bg-gray-50 px-2 py-1"
              >
                <div className="truncate text-xs text-gray-700">
                  {w.from.componentId} ({w.from.portId}) → {w.to.componentId} (
                  {w.to.portId})
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
