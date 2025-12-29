import { useState, useRef, useEffect } from 'react';
import { X } from 'lucide-react';
import { PlacedComponent, Wire } from '../App';

interface CircuitBoardProps {
  placedComponents: PlacedComponent[];
  setPlacedComponents: (components: PlacedComponent[]) => void;
  wires: Wire[];
  setWires: (wires: Wire[]) => void;
  inputs: string[];
  outputs: string[];
  currentCost: number;
  setCurrentCost: (cost: number) => void;
  budgetLimit: number;
}

export function CircuitBoard({
  placedComponents,
  setPlacedComponents,
  wires,
  setWires,
  inputs,
  outputs,
  currentCost,
  setCurrentCost,
  budgetLimit,
}: CircuitBoardProps) {
  const [selectedComponent, setSelectedComponent] = useState<string | null>(null);
  const [selectedWire, setSelectedWire] = useState<string | null>(null);
  const [draggingWire, setDraggingWire] = useState<{
    from: { componentId: string; pinIndex: number; x: number; y: number; isOutput: boolean };
    toX: number;
    toY: number;
  } | null>(null);
  const [ghostPosition, setGhostPosition] = useState<{ x: number; y: number } | null>(null);
  const [draggingComponentData, setDraggingComponentData] = useState<any>(null);
  const boardRef = useRef<HTMLDivElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
    
    // Update ghost position
    if (boardRef.current) {
      const rect = boardRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      setGhostPosition({ x, y });
      
      // Store component data for ghost preview
      const data = e.dataTransfer.getData('component');
      if (data && !draggingComponentData) {
        setDraggingComponentData(JSON.parse(data));
      }
    }
  };

  const handleDragLeave = () => {
    setGhostPosition(null);
    setDraggingComponentData(null);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setGhostPosition(null);
    setDraggingComponentData(null);

    const componentData = e.dataTransfer.getData('component');
    if (!componentData) return;

    const component = JSON.parse(componentData);
    
    // Check budget
    if (currentCost + component.cost > budgetLimit) {
      alert('Budget exceeded! Cannot place component.');
      return;
    }

    if (boardRef.current) {
      const rect = boardRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      const newComponent: PlacedComponent = {
        id: `${component.id}-${Date.now()}`,
        type: component.name,
        x,
        y,
        cost: component.cost,
      };

      setPlacedComponents([...placedComponents, newComponent]);
      setCurrentCost(currentCost + component.cost);
    }
  };

  const handleDeleteComponent = (id: string) => {
    const component = placedComponents.find((c) => c.id === id);
    if (component) {
      setPlacedComponents(placedComponents.filter((c) => c.id !== id));
      setCurrentCost(currentCost - component.cost);
      setSelectedComponent(null);
      
      // Remove wires connected to this component
      setWires(
        wires.filter(
          (w) => w.from.componentId !== id && w.to.componentId !== id
        )
      );
    }
  };

  const handlePinClick = (componentId: string, pinIndex: number, x: number, y: number, isOutput: boolean) => {
    if (draggingWire) {
      // Complete the wire
      const newWire: Wire = {
        id: `wire-${Date.now()}`,
        from: draggingWire.from,
        to: { componentId, pinIndex },
      };
      setWires([...wires, newWire]);
      setDraggingWire(null);
    } else {
      // Start dragging a wire
      setDraggingWire({
        from: { componentId, pinIndex, x, y, isOutput },
        toX: x,
        toY: y,
      });
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (draggingWire && boardRef.current) {
      const rect = boardRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      setDraggingWire({ ...draggingWire, toX: x, toY: y });
    }
  };

  const handleBoardClick = (e: React.MouseEvent) => {
    if (e.target === boardRef.current || (e.target as HTMLElement).classList.contains('board-background')) {
      setSelectedComponent(null);
      setSelectedWire(null);
      if (draggingWire) {
        setDraggingWire(null); // Cancel wire dragging
      }
    }
  };

  const handleDeleteWire = (wireId: string) => {
    setWires(wires.filter((w) => w.id !== wireId));
    setSelectedWire(null);
  };

  // Keyboard shortcuts
  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      if (draggingWire) {
        setDraggingWire(null);
      }
      if (selectedComponent) {
        setSelectedComponent(null);
      }
      if (selectedWire) {
        setSelectedWire(null);
      }
    }
    if (e.key === 'Delete' || e.key === 'Backspace') {
      if (selectedComponent) {
        handleDeleteComponent(selectedComponent);
      }
      if (selectedWire) {
        handleDeleteWire(selectedWire);
      }
    }
  };

  // Add keyboard listener
  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown as any);
    return () => window.removeEventListener('keydown', handleKeyDown as any);
  }, [selectedComponent, selectedWire, draggingWire, placedComponents, wires]);

  // Calculate wire positions for rendering - returns actual pin positions
  const getComponentPinPosition = (componentId: string, pinIndex: number, isOutput: boolean = false) => {
    if (componentId.startsWith('input-')) {
      const index = parseInt(componentId.split('-')[1]);
      // Input pins are on the left edge, account for label width and pin position
      return { x: 70, y: 100 + index * 48 };
    }
    if (componentId.startsWith('output-')) {
      const index = parseInt(componentId.split('-')[1]);
      // Output pins are on the bottom edge
      return { x: 100 + index * 64, y: window.innerHeight - 100 };
    }
    const component = placedComponents.find((c) => c.id === componentId);
    if (component) {
      const isNotGate = component.type === 'NOT';
      
      if (isOutput) {
        // Output pin is on the right edge, centered vertically
        return {
          x: component.x + 50, // Right edge of component (component is centered at x, width is 100, so +50)
          y: component.y,
        };
      } else {
        // Input pins on the left edge
        if (isNotGate) {
          // NOT gate has 1 input, centered
          return {
            x: component.x - 50, // Left edge of component
            y: component.y,
          };
        } else {
          // Other gates have 2 inputs at 1/3 and 2/3 height
          const yOffset = pinIndex === 0 ? -8 : 8;
          return {
            x: component.x - 50, // Left edge of component
            y: component.y + yOffset,
          };
        }
      }
    }
    return { x: 0, y: 0 };
  };

  return (
    <div
      ref={boardRef}
      className="flex-1 bg-gray-100 relative overflow-hidden"
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onMouseMove={handleMouseMove}
      onClick={handleBoardClick}
    >
      {/* Grid Background */}
      <div
        className="board-background absolute inset-0"
        style={{
          backgroundImage: 'radial-gradient(circle, #d1d5db 1px, transparent 1px)',
          backgroundSize: '20px 20px',
        }}
      />

      {/* Content */}
      <div className="relative h-full">
        {/* Input Pins */}
        <div className="absolute left-4 top-20 space-y-6">
          {inputs.map((input, index) => (
            <div key={input} className="flex items-center gap-2">
              <div className="bg-blue-500 text-white px-2 py-1 rounded text-xs">
                {input}
              </div>
              <div
                onClick={(e) => {
                  e.stopPropagation();
                  const rect = e.currentTarget.getBoundingClientRect();
                  const boardRect = boardRef.current!.getBoundingClientRect();
                  handlePinClick(
                    `input-${index}`,
                    0,
                    rect.left - boardRect.left + rect.width / 2,
                    rect.top - boardRect.top + rect.height / 2,
                    true // Input nodes are outputs (they provide signals)
                  );
                }}
                className="w-3 h-3 bg-blue-500 rounded-full cursor-pointer hover:ring-2 hover:ring-blue-300"
              />
            </div>
          ))}
        </div>

        {/* Output Pins */}
        <div className="absolute bottom-4 left-20 flex gap-6">
          {outputs.map((output, index) => (
            <div key={output} className="flex flex-col items-center gap-2">
              <div
                onClick={(e) => {
                  e.stopPropagation();
                  const rect = e.currentTarget.getBoundingClientRect();
                  const boardRect = boardRef.current!.getBoundingClientRect();
                  handlePinClick(
                    `output-${index}`,
                    0,
                    rect.left - boardRect.left + rect.width / 2,
                    rect.top - boardRect.top + rect.height / 2,
                    false // Output nodes are inputs (they receive signals)
                  );
                }}
                className="w-3 h-3 bg-orange-500 rounded-full cursor-pointer hover:ring-2 hover:ring-orange-300"
              />
              <div className="bg-orange-500 text-white px-2 py-1 rounded text-xs">
                {output}
              </div>
            </div>
          ))}
        </div>

        {/* Placed Components */}
        {placedComponents.map((component) => {
          const isNotGate = component.type === 'NOT';
          
          return (
            <div
              key={component.id}
              className={`absolute bg-white border-2 rounded shadow-lg cursor-pointer transition-all ${
                selectedComponent === component.id
                  ? 'border-blue-500'
                  : 'border-gray-400'
              }`}
              style={{
                left: component.x - 50,
                top: component.y - 25,
                width: 100,
                height: 50,
              }}
              onClick={(e) => {
                e.stopPropagation();
                setSelectedComponent(component.id);
              }}
            >
              {/* Component Name */}
              <div className="flex items-center justify-center h-full">
                <span className="text-sm text-gray-900">{component.type}</span>
              </div>

              {/* Input Pins */}
              {isNotGate ? (
                // NOT gate: 1 input, centered
                <div className="absolute left-0 top-1/2 transform -translate-y-1/2 -translate-x-1/2">
                  <div
                    onClick={(e) => {
                      e.stopPropagation();
                      const rect = e.currentTarget.getBoundingClientRect();
                      const boardRect = boardRef.current!.getBoundingClientRect();
                      handlePinClick(
                        component.id,
                        0,
                        rect.left - boardRect.left + rect.width / 2,
                        rect.top - boardRect.top + rect.height / 2,
                        false
                      );
                    }}
                    className="w-2.5 h-2.5 bg-gray-600 rounded-full cursor-pointer hover:ring-2 hover:ring-blue-300"
                  />
                </div>
              ) : (
                // Other gates: 2 inputs
                <>
                  <div className="absolute left-0 top-1/3 transform -translate-y-1/2 -translate-x-1/2">
                    <div
                      onClick={(e) => {
                        e.stopPropagation();
                        const rect = e.currentTarget.getBoundingClientRect();
                        const boardRect = boardRef.current!.getBoundingClientRect();
                        handlePinClick(
                          component.id,
                          0,
                          rect.left - boardRect.left + rect.width / 2,
                          rect.top - boardRect.top + rect.height / 2,
                          false
                        );
                      }}
                      className="w-2.5 h-2.5 bg-gray-600 rounded-full cursor-pointer hover:ring-2 hover:ring-blue-300"
                    />
                  </div>
                  <div className="absolute left-0 top-2/3 transform -translate-y-1/2 -translate-x-1/2">
                    <div
                      onClick={(e) => {
                        e.stopPropagation();
                        const rect = e.currentTarget.getBoundingClientRect();
                        const boardRect = boardRef.current!.getBoundingClientRect();
                        handlePinClick(
                          component.id,
                          1,
                          rect.left - boardRect.left + rect.width / 2,
                          rect.top - boardRect.top + rect.height / 2,
                          false
                        );
                      }}
                      className="w-2.5 h-2.5 bg-gray-600 rounded-full cursor-pointer hover:ring-2 hover:ring-blue-300"
                    />
                  </div>
                </>
              )}

              {/* Output Pin */}
              <div className="absolute right-0 top-1/2 transform -translate-y-1/2 translate-x-1/2">
                <div
                  onClick={(e) => {
                    e.stopPropagation();
                    const rect = e.currentTarget.getBoundingClientRect();
                    const boardRect = boardRef.current!.getBoundingClientRect();
                    handlePinClick(
                      component.id,
                      0,
                      rect.left - boardRect.left + rect.width / 2,
                      rect.top - boardRect.top + rect.height / 2,
                      true
                    );
                  }}
                  className="w-2.5 h-2.5 bg-gray-600 rounded-full cursor-pointer hover:ring-2 hover:ring-blue-300"
                />
              </div>

              {/* Delete Button */}
              {selectedComponent === component.id && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDeleteComponent(component.id);
                  }}
                  className="absolute -top-2 -right-2 w-5 h-5 bg-red-500 hover:bg-red-600 text-white rounded-full flex items-center justify-center transition-colors"
                >
                  <X className="w-3 h-3" />
                </button>
              )}
            </div>
          );
        })}

        {/* Ghost Preview */}
        {ghostPosition && draggingComponentData && (
          <div
            className="absolute bg-white border-2 border-blue-400 border-dashed rounded shadow-lg opacity-50 pointer-events-none"
            style={{
              left: ghostPosition.x - 50,
              top: ghostPosition.y - 25,
              width: 100,
              height: 50,
            }}
          >
            <div className="flex items-center justify-center h-full">
              <span className="text-sm text-gray-900">{draggingComponentData.name}</span>
            </div>
          </div>
        )}

        {/* Wires */}
        <svg className="absolute inset-0 pointer-events-none" style={{ width: '100%', height: '100%' }}>
          {/* Render completed wires */}
          {wires.map((wire) => {
            const fromPos = getComponentPinPosition(wire.from.componentId, wire.from.pinIndex, true);
            const toPos = getComponentPinPosition(wire.to.componentId, wire.to.pinIndex, false);
            
            // Calculate control points for curved wire
            const midX = (fromPos.x + toPos.x) / 2;
            const path = `M ${fromPos.x} ${fromPos.y} C ${midX} ${fromPos.y}, ${midX} ${toPos.y}, ${toPos.x} ${toPos.y}`;
            
            return (
              <g key={wire.id}>
                {/* Invisible thicker path for easier clicking */}
                <path
                  d={path}
                  stroke="transparent"
                  strokeWidth="12"
                  fill="none"
                  className="pointer-events-auto cursor-pointer"
                  onClick={(e) => {
                    e.stopPropagation();
                    setSelectedWire(wire.id);
                    setSelectedComponent(null);
                  }}
                />
                {/* Visible wire */}
                <path
                  d={path}
                  stroke={selectedWire === wire.id ? '#ef4444' : '#3b82f6'}
                  strokeWidth="2"
                  fill="none"
                  className="pointer-events-none"
                />
                {/* Delete button on selected wire */}
                {selectedWire === wire.id && (
                  <>
                    <circle
                      cx={(fromPos.x + toPos.x) / 2}
                      cy={(fromPos.y + toPos.y) / 2}
                      r="10"
                      fill="#ef4444"
                      className="pointer-events-auto cursor-pointer"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteWire(wire.id);
                      }}
                    />
                    <text
                      x={(fromPos.x + toPos.x) / 2}
                      y={(fromPos.y + toPos.y) / 2}
                      textAnchor="middle"
                      dominantBaseline="middle"
                      fill="white"
                      fontSize="12"
                      className="pointer-events-none"
                    >
                      ×
                    </text>
                  </>
                )}
              </g>
            );
          })}
          
          {/* Dragging wire preview */}
          {draggingWire && (
            <line
              x1={draggingWire.from.x}
              y1={draggingWire.from.y}
              x2={draggingWire.toX}
              y2={draggingWire.toY}
              stroke="#3b82f6"
              strokeWidth="2"
              strokeDasharray="4"
            />
          )}
        </svg>

        {/* Hint Text */}
        {draggingWire && (
          <div className="absolute top-4 left-1/2 transform -translate-x-1/2 bg-blue-500 text-white px-3 py-1.5 rounded shadow-lg text-sm">
            Click a pin to complete wire, or press ESC to cancel
          </div>
        )}
      </div>
    </div>
  );
}