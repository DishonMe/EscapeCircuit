import {
  ChevronDown,
  ChevronRight,
  Edit,
  Trash2,
  Star,
  Flame,
  Eye,
  MessageSquare,
  Play,
  CheckCircle,
  Clock,
  Download,
} from 'lucide-react';
import { useState } from 'react';
import { PuzzleEntry } from './CreatorDashboard';

interface PublishedPuzzlesSectionProps {
  puzzles: PuzzleEntry[];
  onEdit: (id: string) => void;
  onUnpublish: (id: string) => void;
  onDelete: (id: string) => void;
}

export function PublishedPuzzlesSection({
  puzzles,
  onEdit,
  onUnpublish,
  onDelete,
}: PublishedPuzzlesSectionProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  return (
    <div className="bg-white border border-gray-300 rounded-lg">
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
          <h2 className="text-gray-900">Published Puzzles</h2>
          <span className="px-2 py-0.5 bg-green-100 border border-green-300 rounded text-sm text-green-700">
            {puzzles.length}
          </span>
        </div>
      </button>

      {/* Puzzle List */}
      {isExpanded && (
        <div className="p-6">
          {puzzles.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <p>No published puzzles.</p>
              <p className="text-sm mt-2">Publish a draft puzzle to share it with the community!</p>
            </div>
          ) : (
            <div className="space-y-4">
              {puzzles.map((puzzle) => (
                <div
                  key={puzzle.id}
                  className="border border-gray-300 rounded-lg p-5 hover:border-blue-400 transition-colors"
                >
                  <div className="flex items-start justify-between gap-4">
                    {/* Left: Puzzle Info */}
                    <div className="flex-1">
                      {/* Title and Status */}
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="text-gray-900">{puzzle.name}</h3>
                        <span className="px-2 py-0.5 bg-green-100 border border-green-300 rounded text-xs text-green-700">
                          Published
                        </span>
                        {puzzle.popular && (
                          <div className="flex items-center gap-1 px-2 py-0.5 bg-orange-50 border border-orange-300 rounded text-xs text-orange-700">
                            <Flame className="w-3 h-3" />
                            Popular
                          </div>
                        )}
                      </div>

                      {/* Upload Date */}
                      <p className="text-sm text-gray-500 mb-3">
                        Published on{' '}
                        {new Date(puzzle.uploadDate).toLocaleDateString('en-US', {
                          year: 'numeric',
                          month: 'long',
                          day: 'numeric',
                        })}
                      </p>

                      {/* Rating Summary */}
                      <div className="flex items-center gap-6 mb-3">
                        <div className="flex items-center gap-2">
                          <div className="flex items-center gap-0.5">
                            {[1, 2, 3, 4, 5].map((star) => (
                              <Star
                                key={star}
                                className={`w-4 h-4 ${
                                  star <= Math.floor(puzzle.rating || 0)
                                    ? 'text-yellow-500 fill-yellow-500'
                                    : 'text-gray-300'
                                }`}
                              />
                            ))}
                          </div>
                          <span className="text-sm text-gray-900">
                            {puzzle.rating?.toFixed(1)}
                          </span>
                          <span className="text-sm text-gray-500">
                            ({puzzle.ratingsCount} ratings)
                          </span>
                        </div>
                      </div>

                      {/* Performance Indicators */}
                      <div className="flex items-center gap-6 text-sm text-gray-600">
                        <div className="flex items-center gap-1">
                          <Play className="w-4 h-4" />
                          <span>{puzzle.plays} plays</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <CheckCircle className="w-4 h-4" />
                          <span>{puzzle.completionRate}% completion</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <Clock className="w-4 h-4" />
                          <span>{puzzle.averageTime}s avg time</span>
                        </div>
                      </div>
                    </div>

                    {/* Right: Action Buttons */}
                    <div className="flex flex-col gap-2">
                      <div className="flex gap-2">
                        <button
                          onClick={() => alert(`View puzzle ${puzzle.id}`)}
                          className="px-3 py-2 bg-gray-100 hover:bg-gray-200 border border-gray-300 rounded flex items-center gap-1 transition-colors text-sm"
                        >
                          <Eye className="w-4 h-4" />
                          View
                        </button>
                        <button
                          onClick={() => onEdit(puzzle.id)}
                          className="px-3 py-2 bg-gray-100 hover:bg-gray-200 border border-gray-300 rounded flex items-center gap-1 transition-colors text-sm"
                        >
                          <Edit className="w-4 h-4" />
                          Edit
                        </button>
                      </div>
                      <div className="flex gap-2">
                        <button
                          onClick={() => alert(`View feedback for ${puzzle.id}`)}
                          className="px-3 py-2 bg-blue-50 hover:bg-blue-100 border border-blue-300 rounded flex items-center gap-1 transition-colors text-sm text-blue-700"
                        >
                          <MessageSquare className="w-4 h-4" />
                          Feedback
                        </button>
                        <button
                          onClick={() => onUnpublish(puzzle.id)}
                          className="px-3 py-2 bg-yellow-50 hover:bg-yellow-100 border border-yellow-300 rounded flex items-center gap-1 transition-colors text-sm text-yellow-700"
                        >
                          <Download className="w-4 h-4" />
                          Unpublish
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
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
