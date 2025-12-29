import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';

interface Component {
  id: string;
  name: string;
  cost: number;
  type: string;
}

interface CategoryProps {
  title: string;
  components: Component[];
}

function Category({ title, components }: CategoryProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  const handleDragStart = (e: React.DragEvent, component: Component) => {
    e.dataTransfer.setData('component', JSON.stringify(component));
    e.dataTransfer.effectAllowed = 'copy';
  };

  return (
    <div className="mb-4">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center gap-2 p-2 hover:bg-gray-100 rounded transition-colors"
      >
        {isExpanded ? (
          <ChevronDown className="w-4 h-4 text-gray-600" />
        ) : (
          <ChevronRight className="w-4 h-4 text-gray-600" />
        )}
        <span className="text-sm text-gray-900">{title}</span>
      </button>
      {isExpanded && (
        <div className="mt-2 space-y-2 pl-2">
          {components.map((component) => (
            <div
              key={component.id}
              draggable
              onDragStart={(e) => handleDragStart(e, component)}
              className="bg-white border border-gray-300 rounded p-2 cursor-move hover:border-blue-400 hover:shadow-sm transition-all"
            >
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-900">{component.name}</span>
                <span className="text-xs text-gray-500 font-mono">
                  {component.cost}
                </span>
              </div>
              <div className="mt-1 text-xs text-gray-400">{component.type}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function ComponentLibrary() {
  const basicElements: Component[] = [
    { id: 'and', name: 'AND', cost: 5, type: 'Logic Gate' },
    { id: 'or', name: 'OR', cost: 5, type: 'Logic Gate' },
    { id: 'not', name: 'NOT', cost: 3, type: 'Logic Gate' },
    { id: 'xor', name: 'XOR', cost: 8, type: 'Logic Gate' },
    { id: 'nand', name: 'NAND', cost: 6, type: 'Logic Gate' },
    { id: 'nor', name: 'NOR', cost: 6, type: 'Logic Gate' },
  ];

  const arsenal: Component[] = [
    { id: 'half-adder', name: 'Half Adder', cost: 15, type: 'Saved Circuit' },
    { id: 'full-adder', name: 'Full Adder', cost: 25, type: 'Saved Circuit' },
  ];

  const specialCircuits: Component[] = [
    { id: 'flip-module', name: 'Flip Module', cost: 12, type: 'Special' },
    { id: 'multiplexer', name: 'Multiplexer', cost: 20, type: 'Special' },
  ];

  return (
    <div className="w-64 bg-gray-50 border-r border-gray-300 overflow-y-auto">
      <div className="p-4">
        <h2 className="text-gray-900 mb-4">Component Library</h2>
        
        <Category title="Basic Elements" components={basicElements} />
        <Category title="Arsenal" components={arsenal} />
        <Category title="Special Circuits" components={specialCircuits} />
      </div>
    </div>
  );
}