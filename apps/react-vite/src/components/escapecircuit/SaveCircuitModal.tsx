import { useState } from 'react';
import { X } from 'lucide-react';

interface SaveCircuitModalProps {
  onClose: () => void;
  onSave: (name: string, location: 'arsenal' | 'puzzle') => void;
}

export function SaveCircuitModal({ onClose, onSave }: SaveCircuitModalProps) {
  const [name, setName] = useState('');
  const [location, setLocation] = useState<'arsenal' | 'puzzle'>('arsenal');

  const handleSave = () => {
    if (name.trim()) {
      onSave(name, location);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <h2 className="text-gray-900">Save Circuit</h2>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 rounded transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-6 space-y-4">
          <div>
            <label className="block text-sm text-gray-700 mb-1">Circuit Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Enter circuit name"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-700 mb-2">Save to:</label>
            <div className="space-y-2">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="location"
                  value="arsenal"
                  checked={location === 'arsenal'}
                  onChange={() => setLocation('arsenal')}
                  className="w-4 h-4"
                />
                <span className="text-sm text-gray-700">Arsenal (Available in all puzzles)</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="location"
                  value="puzzle"
                  checked={location === 'puzzle'}
                  onChange={() => setLocation('puzzle')}
                  className="w-4 h-4"
                />
                <span className="text-sm text-gray-700">This Puzzle Only</span>
              </label>
            </div>
          </div>
        </div>
        <div className="flex justify-end gap-2 p-4 border-t border-gray-200">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-100 hover:bg-gray-200 border border-gray-300 rounded transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={!name.trim()}
            className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Save
          </button>
        </div>
      </div>
    </div>
  );
}
