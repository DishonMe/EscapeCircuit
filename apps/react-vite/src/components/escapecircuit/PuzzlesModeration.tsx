import { useState } from 'react';
import {
  Search,
  Star,
  Trash2,
  Eye,
  AlertTriangle,
  CheckCircle,
  Flag,
  Download,
  MessageSquare,
  Play,
  Flame,
  TrendingDown,
} from 'lucide-react';

interface ModerationPuzzle {
  id: string;
  name: string;
  creator: string;
  rating: number;
  ratingsCount: number;
  plays: number;
  status: 'published' | 'unpublished';
  popular: boolean;
  moderationFlags: ('low-rating' | 'negative-feedback' | 'reported' | 'low-popularity' | 'clean')[];
}

export function PuzzlesModeration() {
  const [searchQuery, setSearchQuery] = useState('');
  const [creatorSearch, setCreatorSearch] = useState('');
  const [ratingFilter, setRatingFilter] = useState<string>('All');
  const [popularityFilter, setPopularityFilter] = useState<string>('All');
  const [statusFilter, setStatusFilter] = useState<string>('All');

  // Mock puzzle data
  const [puzzles, setPuzzles] = useState<ModerationPuzzle[]>([
    {
      id: '1',
      name: 'Binary Adder Challenge',
      creator: 'LogicMaster',
      rating: 4.5,
      ratingsCount: 234,
      plays: 1203,
      status: 'published',
      popular: true,
      moderationFlags: ['clean'],
    },
    {
      id: '2',
      name: 'Broken Circuit Puzzle',
      creator: 'BadDesigner',
      rating: 1.8,
      ratingsCount: 45,
      plays: 67,
      status: 'published',
      popular: false,
      moderationFlags: ['low-rating', 'negative-feedback', 'low-popularity'],
    },
    {
      id: '3',
      name: 'Inappropriate Content Test',
      creator: 'SpamUser',
      rating: 2.1,
      ratingsCount: 12,
      plays: 23,
      status: 'published',
      popular: false,
      moderationFlags: ['reported', 'low-rating', 'low-popularity'],
    },
    {
      id: '4',
      name: 'Advanced Multiplexer',
      creator: 'CircuitGuru',
      rating: 4.8,
      ratingsCount: 156,
      plays: 892,
      status: 'published',
      popular: true,
      moderationFlags: ['clean'],
    },
    {
      id: '5',
      name: 'XOR Gate Tutorial',
      creator: 'TeachingPro',
      rating: 4.2,
      ratingsCount: 89,
      plays: 543,
      status: 'published',
      popular: false,
      moderationFlags: ['clean'],
    },
  ]);

  const handleDelete = (puzzleId: string) => {
    if (confirm('Are you sure you want to delete this puzzle? This action cannot be undone.')) {
      setPuzzles(puzzles.filter((p) => p.id !== puzzleId));
    }
  };

  const handleUnpublish = (puzzleId: string) => {
    setPuzzles(
      puzzles.map((p) =>
        p.id === puzzleId ? { ...p, status: 'unpublished' as const } : p
      )
    );
  };

  const handlePublish = (puzzleId: string) => {
    setPuzzles(
      puzzles.map((p) =>
        p.id === puzzleId ? { ...p, status: 'published' as const } : p
      )
    );
  };

  // Filter puzzles
  const filteredPuzzles = puzzles.filter((puzzle) => {
    const matchesSearch =
      searchQuery === '' ||
      puzzle.name.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesCreator =
      creatorSearch === '' ||
      puzzle.creator.toLowerCase().includes(creatorSearch.toLowerCase());

    const matchesRating =
      ratingFilter === 'All' ||
      (ratingFilter === 'Low' && puzzle.rating < 3.0) ||
      (ratingFilter === 'High' && puzzle.rating >= 4.0);

    const matchesPopularity =
      popularityFilter === 'All' ||
      (popularityFilter === 'Popular' && puzzle.popular) ||
      (popularityFilter === 'Low' && !puzzle.popular && puzzle.plays < 100);

    const matchesStatus =
      statusFilter === 'All' || puzzle.status === statusFilter.toLowerCase();

    return (
      matchesSearch &&
      matchesCreator &&
      matchesRating &&
      matchesPopularity &&
      matchesStatus
    );
  });

  const getFlagIcon = (flag: string) => {
    switch (flag) {
      case 'low-rating':
        return <AlertTriangle className="w-4 h-4 text-red-600" />;
      case 'negative-feedback':
        return <MessageSquare className="w-4 h-4 text-orange-600" />;
      case 'reported':
        return <Flag className="w-4 h-4 text-red-600" />;
      case 'low-popularity':
        return <TrendingDown className="w-4 h-4 text-yellow-600" />;
      case 'clean':
        return <CheckCircle className="w-4 h-4 text-green-600" />;
      default:
        return null;
    }
  };

  const getFlagLabel = (flag: string) => {
    switch (flag) {
      case 'low-rating':
        return 'Very Low Rating';
      case 'negative-feedback':
        return 'Negative Feedback';
      case 'reported':
        return 'Reported Content';
      case 'low-popularity':
        return 'Low Popularity';
      case 'clean':
        return 'No Issues';
      default:
        return flag;
    }
  };

  const getFlagColor = (flag: string) => {
    switch (flag) {
      case 'low-rating':
      case 'reported':
        return 'bg-red-50 border-red-300 text-red-700';
      case 'negative-feedback':
        return 'bg-orange-50 border-orange-300 text-orange-700';
      case 'low-popularity':
        return 'bg-yellow-50 border-yellow-300 text-yellow-700';
      case 'clean':
        return 'bg-green-50 border-green-300 text-green-700';
      default:
        return 'bg-gray-50 border-gray-300 text-gray-700';
    }
  };

  return (
    <div>
      {/* Search & Filter Controls */}
      <div className="mb-6 pb-6 border-b border-gray-300">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          {/* Puzzle Name Search */}
          <div className="relative">
            <label className="block text-sm text-gray-700 mb-2">
              Puzzle Name
            </label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search puzzles..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          {/* Creator Search */}
          <div className="relative">
            <label className="block text-sm text-gray-700 mb-2">
              Creator Name
            </label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search creator..."
                value={creatorSearch}
                onChange={(e) => setCreatorSearch(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          {/* Rating Filter */}
          <div>
            <label className="block text-sm text-gray-700 mb-2">
              Rating Filter
            </label>
            <select
              value={ratingFilter}
              onChange={(e) => setRatingFilter(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="All">All Ratings</option>
              <option value="High">High (4.0+)</option>
              <option value="Low">Low (&lt;3.0)</option>
            </select>
          </div>

          {/* Popularity Filter */}
          <div>
            <label className="block text-sm text-gray-700 mb-2">
              Popularity
            </label>
            <select
              value={popularityFilter}
              onChange={(e) => setPopularityFilter(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="All">All</option>
              <option value="Popular">Popular</option>
              <option value="Low">Low Popularity</option>
            </select>
          </div>

          {/* Status Filter */}
          <div>
            <label className="block text-sm text-gray-700 mb-2">
              Status
            </label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="All">All</option>
              <option value="published">Published</option>
              <option value="unpublished">Unpublished</option>
            </select>
          </div>
        </div>
      </div>

      {/* Puzzles List */}
      <div>
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-gray-900">
            Puzzles List ({filteredPuzzles.length})
          </h3>
        </div>

        {filteredPuzzles.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <p>No puzzles found matching your filters.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {filteredPuzzles.map((puzzle) => (
              <div
                key={puzzle.id}
                className="border border-gray-300 rounded-lg p-4 hover:border-blue-400 transition-colors"
              >
                <div className="flex items-start justify-between gap-4">
                  {/* Left: Puzzle Info */}
                  <div className="flex-1">
                    {/* Title and Status */}
                    <div className="flex items-center gap-3 mb-2">
                      <h4 className="text-gray-900">{puzzle.name}</h4>
                      <span
                        className={`px-2 py-0.5 border rounded text-xs ${
                          puzzle.status === 'published'
                            ? 'bg-green-100 border-green-300 text-green-700'
                            : 'bg-gray-100 border-gray-300 text-gray-600'
                        }`}
                      >
                        {puzzle.status.charAt(0).toUpperCase() + puzzle.status.slice(1)}
                      </span>
                      {puzzle.popular && (
                        <div className="flex items-center gap-1 px-2 py-0.5 bg-orange-50 border border-orange-300 rounded text-xs text-orange-700">
                          <Flame className="w-3 h-3" />
                          Popular
                        </div>
                      )}
                    </div>

                    {/* Creator */}
                    <p className="text-sm text-gray-600 mb-3">by {puzzle.creator}</p>

                    {/* Rating and Stats */}
                    <div className="flex items-center gap-6 mb-3 text-sm text-gray-600">
                      <div className="flex items-center gap-2">
                        <div className="flex items-center gap-0.5">
                          {[1, 2, 3, 4, 5].map((star) => (
                            <Star
                              key={star}
                              className={`w-4 h-4 ${
                                star <= Math.floor(puzzle.rating)
                                  ? 'text-yellow-500 fill-yellow-500'
                                  : 'text-gray-300'
                              }`}
                            />
                          ))}
                        </div>
                        <span className="text-gray-900">{puzzle.rating.toFixed(1)}</span>
                        <span className="text-gray-500">({puzzle.ratingsCount})</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <Play className="w-4 h-4" />
                        <span>{puzzle.plays} plays</span>
                      </div>
                    </div>

                    {/* Moderation Flags */}
                    <div className="flex items-center gap-2 flex-wrap">
                      {puzzle.moderationFlags.map((flag, idx) => (
                        <div
                          key={idx}
                          className={`px-2 py-1 border rounded text-xs flex items-center gap-1 ${getFlagColor(
                            flag
                          )}`}
                        >
                          {getFlagIcon(flag)}
                          <span>{getFlagLabel(flag)}</span>
                        </div>
                      ))}
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
                        onClick={() => alert(`View reports for ${puzzle.id}`)}
                        className="px-3 py-2 bg-blue-50 hover:bg-blue-100 border border-blue-300 rounded flex items-center gap-1 transition-colors text-sm text-blue-700"
                      >
                        <MessageSquare className="w-4 h-4" />
                        Reports
                      </button>
                    </div>
                    <div className="flex gap-2">
                      {puzzle.status === 'published' ? (
                        <button
                          onClick={() => handleUnpublish(puzzle.id)}
                          className="px-3 py-2 bg-yellow-50 hover:bg-yellow-100 border border-yellow-300 rounded flex items-center gap-1 transition-colors text-sm text-yellow-700"
                        >
                          <Download className="w-4 h-4" />
                          Unpublish
                        </button>
                      ) : (
                        <button
                          onClick={() => handlePublish(puzzle.id)}
                          className="px-3 py-2 bg-green-50 hover:bg-green-100 border border-green-300 rounded flex items-center gap-1 transition-colors text-sm text-green-700"
                        >
                          <CheckCircle className="w-4 h-4" />
                          Publish
                        </button>
                      )}
                      <button
                        onClick={() => handleDelete(puzzle.id)}
                        className="px-3 py-2 bg-red-50 hover:bg-red-100 border border-red-300 rounded flex items-center gap-1 transition-colors text-sm text-red-700"
                      >
                        <Trash2 className="w-4 h-4" />
                        Delete
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
