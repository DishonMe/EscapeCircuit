import { Search, SlidersHorizontal } from 'lucide-react';

interface SearchFiltersProps {
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  difficultyFilter: string;
  setDifficultyFilter: (filter: string) => void;
  timeLimitFilter: string;
  setTimeLimitFilter: (filter: string) => void;
  solvedFilter: string;
  setSolvedFilter: (filter: string) => void;
  ratingFilter: string;
  setRatingFilter: (filter: string) => void;
  popularOnly: boolean;
  setPopularOnly: (value: boolean) => void;
}

export function SearchFilters({
  searchQuery,
  setSearchQuery,
  difficultyFilter,
  setDifficultyFilter,
  timeLimitFilter,
  setTimeLimitFilter,
  solvedFilter,
  setSolvedFilter,
  ratingFilter,
  setRatingFilter,
  popularOnly,
  setPopularOnly,
}: SearchFiltersProps) {
  return (
    <div className="bg-white border border-gray-300 rounded-lg p-6 mb-6">
      {/* Search Bar */}
      <div className="mb-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search puzzles..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <p className="text-xs text-gray-500 mt-1 ml-1">
          Search by puzzle name, creator, or tags
        </p>
      </div>

      {/* Filter Controls */}
      <div className="flex items-end gap-4">
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4 flex-1">
          {/* Difficulty */}
          <div>
            <label className="block text-sm text-gray-700 mb-1">Difficulty</label>
            <select
              value={difficultyFilter}
              onChange={(e) => setDifficultyFilter(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
            >
              <option value="All">All</option>
              <option value="Easy">Easy</option>
              <option value="Medium">Medium</option>
              <option value="Hard">Hard</option>
            </select>
          </div>

          {/* Time Limit */}
          <div>
            <label className="block text-sm text-gray-700 mb-1">Time Limit</label>
            <select
              value={timeLimitFilter}
              onChange={(e) => setTimeLimitFilter(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
            >
              <option value="All">All</option>
              <option value="Under 60s">Under 60s</option>
              <option value="Under 2m">Under 2m</option>
              <option value="Under 5m">Under 5m</option>
            </select>
          </div>

          {/* Solved/Unsolved */}
          <div>
            <label className="block text-sm text-gray-700 mb-1">Status</label>
            <select
              value={solvedFilter}
              onChange={(e) => setSolvedFilter(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
            >
              <option value="All">All</option>
              <option value="Solved">Solved</option>
              <option value="Unsolved">Unsolved</option>
            </select>
          </div>

          {/* Rating */}
          <div>
            <label className="block text-sm text-gray-700 mb-1">Rating</label>
            <select
              value={ratingFilter}
              onChange={(e) => setRatingFilter(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
            >
              <option value="All">All</option>
              <option value="4+">4+ stars</option>
              <option value="3+">3+ stars</option>
              <option value="2+">2+ stars</option>
            </select>
          </div>

          {/* Popular Only */}
          <div>
            <label className="block text-sm text-gray-700 mb-1">Popular</label>
            <label className="flex items-center h-10 cursor-pointer">
              <input
                type="checkbox"
                checked={popularOnly}
                onChange={(e) => setPopularOnly(e.target.checked)}
                className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
              />
              <span className="ml-2 text-sm text-gray-700">Popular Only</span>
            </label>
          </div>
        </div>

        {/* More Filters Button */}
        <button className="px-4 py-2 border border-gray-300 rounded bg-white hover:bg-gray-50 transition-colors flex items-center gap-2 h-10">
          <SlidersHorizontal className="w-4 h-4" />
          <span className="text-sm">More Filters</span>
        </button>
      </div>
    </div>
  );
}