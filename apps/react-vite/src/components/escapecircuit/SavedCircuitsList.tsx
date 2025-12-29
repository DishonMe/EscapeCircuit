import { Boxes, ExternalLink } from 'lucide-react';

interface SavedCircuit {
  id: string;
  name: string;
  type: 'Basic' | 'Special' | 'Puzzle-Specific';
  cost: number;
  description: string;
}

export function SavedCircuitsList() {
  const savedCircuits: SavedCircuit[] = [
    {
      id: '1',
      name: 'Half Adder',
      type: 'Basic',
      cost: 8,
      description: '1-bit adder using XOR and AND gates',
    },
    {
      id: '2',
      name: 'Full Adder',
      type: 'Special',
      cost: 15,
      description: 'Complete 1-bit adder with carry',
    },
    {
      id: '3',
      name: '4-to-1 Multiplexer',
      type: 'Special',
      cost: 12,
      description: 'Select one of four inputs',
    },
    {
      id: '4',
      name: 'Custom XOR Array',
      type: 'Puzzle-Specific',
      cost: 20,
      description: 'Multi-input XOR configuration',
    },
  ];

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'Basic':
        return 'text-blue-600 bg-blue-50 border-blue-200';
      case 'Special':
        return 'text-purple-600 bg-purple-50 border-purple-200';
      case 'Puzzle-Specific':
        return 'text-orange-600 bg-orange-50 border-orange-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  return (
    <div>
      <h2 className="text-gray-900 mb-4">Saved Circuits (Arsenal)</h2>
      
      {savedCircuits.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <p>No saved circuits yet.</p>
          <p className="text-sm mt-2">Build custom circuits and save them to your arsenal!</p>
        </div>
      ) : (
        <div className="space-y-3">
          {savedCircuits.map((circuit) => (
            <div
              key={circuit.id}
              className="border border-gray-300 rounded-lg p-4 hover:border-blue-400 transition-colors"
            >
              <div className="flex items-center justify-between gap-4">
                {/* Left: Circuit Info */}
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <Boxes className="w-5 h-5 text-gray-600" />
                    <h3 className="text-gray-900">{circuit.name}</h3>
                    <span
                      className={`px-2 py-0.5 border rounded text-xs ${getTypeColor(
                        circuit.type
                      )}`}
                    >
                      {circuit.type}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 text-sm text-gray-600">
                    <span>{circuit.description}</span>
                    <span className="text-gray-900 font-mono">Cost: {circuit.cost}</span>
                  </div>
                </div>

                {/* Right: Action Button */}
                <div>
                  <button className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white border border-blue-600 rounded flex items-center gap-2 transition-colors text-sm">
                    <ExternalLink className="w-4 h-4" />
                    Open in Sandbox
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
