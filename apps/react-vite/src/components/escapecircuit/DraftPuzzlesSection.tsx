import { ChevronDown, ChevronRight, Edit, Upload, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { PuzzleEntry } from './CreatorDashboard';

interface DraftPuzzlesSectionProps {
  puzzles: PuzzleEntry[];
  onEdit: (id: string) => void;
  onPublish: (id: string) => void;
  onDelete: (id: string) => void;
}

export function DraftPuzzlesSection({
  puzzles,
  onEdit,
  onPublish,
  onDelete,
}: DraftPuzzlesSectionProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  return (
    <div className="bg-white border border-gray-300 rounded-lg mb-6">
      {/* Section Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-6 py-4 flex items-center justify-between border-b border-gray-300 hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-3">
          {isExpanded ? (
            <ChevronDown className="w-5 h-5 text-gray-600" />
          ) : (
            <ChevronRight className="w-5 h-5 text-gray-600" />
          )}
          <h2 className="text-gray-900">Draft Puzzles</h2>
          <span className="px-2 py-0.5 bg-gray-100 border border-gray-300 rounded text-sm text-gray-600">
            {puzzles.length}
          </span>
        </div>
      </button>

      {/* Puzzle List */}
      {isExpanded && (
        <div className="p-6">
          {puzzles.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <p>No draft puzzles.</p>
              <p className="text-sm mt-2">Create a new puzzle to get started!</p>
            </div>
          ) : (
            <div className="space-y-4">
              {puzzles.map((puzzle) => (
                <div
                  key={puzzle.id}
                  className="border border-gray-300 rounded-lg p-5 hover:border-blue-400 transition-colors"
                >
                  <div className="flex items-center justify-between gap-4">
                    {/* Left: Puzzle Info */}
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="text-gray-900">{puzzle.name}</h3>
                        <span className="px-2 py-0.5 bg-gray-100 border border-gray-300 rounded text-xs text-gray-600">
                          Draft
                        </span>
                      </div>
                      <p className="text-sm text-gray-500">
                        Created on {new Date(puzzle.uploadDate).toLocaleDateString('en-US', {
                          year: 'numeric',
                          month: 'long',
                          day: 'numeric',
                        })}
                      </p>
                    </div>

                    {/* Right: Action Buttons */}
                    <div className="flex gap-2">
                      <button
                        onClick={() => onEdit(puzzle.id)}
                        className="px-4 py-2 bg-gray-100 hover:bg-gray-200 border border-gray-300 rounded flex items-center gap-2 transition-colors text-sm"
                      >
                        <Edit className="w-4 h-4" />
                        Edit
                      </button>
                      <button
                        onClick={() => onPublish(puzzle.id)}
                        className="px-4 py-2 bg-green-50 hover:bg-green-100 border border-green-300 rounded flex items-center gap-2 transition-colors text-sm text-green-700"
                      >
                        <Upload className="w-4 h-4" />
                        Publish
                      </button>
                      <button
                        onClick={() => onDelete(puzzle.id)}
                        className="px-3 py-2 bg-red-50 hover:bg-red-100 border border-red-300 rounded flex items-center gap-1 transition-colors text-sm text-red-700"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
