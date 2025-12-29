import { Clock, Star, Award, CheckCircle, Circle, Shield, Users } from 'lucide-react';
import { Puzzle } from './PuzzleBrowser';

interface PuzzleCardProps {
  puzzle: Puzzle;
  onSelect?: (puzzleId: string) => void;
}

export function PuzzleCard({ puzzle, onSelect }: PuzzleCardProps) {
  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty) {
      case 'Easy':
        return 'text-green-600 bg-green-50 border-green-200';
      case 'Medium':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'Hard':
        return 'text-red-600 bg-red-50 border-red-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const getMedalColor = (medal: 'gold' | 'silver' | 'bronze') => {
    switch (medal) {
      case 'gold':
        return 'text-yellow-500';
      case 'silver':
        return 'text-gray-400';
      case 'bronze':
        return 'text-orange-400';
    }
  };

  const renderStars = (rating: number) => {
    const stars = [];
    for (let i = 1; i <= 5; i++) {
      stars.push(
        <Star
          key={i}
          className={`w-3.5 h-3.5 ${
            i <= Math.floor(rating)
              ? 'text-yellow-500 fill-yellow-500'
              : 'text-gray-300'
          }`}
        />
      );
    }
    return stars;
  };

  return (
    <div
      className="bg-white border border-gray-300 rounded-lg p-5 hover:border-blue-400 hover:shadow-lg transition-all cursor-pointer relative"
      onClick={() => onSelect ? onSelect(puzzle.id) : alert(`Open puzzle: ${puzzle.title}`)}
    >
      {/* Medal Badge (Top Right) - Only shown if solved */}
      {puzzle.solved && puzzle.medal && (
        <div className="absolute top-3 right-3">
          <div
            className={`w-8 h-8 rounded-full flex items-center justify-center ${
              puzzle.medal === 'gold'
                ? 'bg-yellow-100'
                : puzzle.medal === 'silver'
                ? 'bg-gray-200'
                : 'bg-orange-100'
            }`}
          >
            <Award
              className={`w-5 h-5 ${
                puzzle.medal === 'gold'
                  ? 'text-yellow-600 fill-yellow-500'
                  : puzzle.medal === 'silver'
                  ? 'text-gray-600 fill-gray-400'
                  : 'text-orange-600 fill-orange-400'
              }`}
            />
          </div>
        </div>
      )}

      {/* Title & Creator */}
      <div className="mb-3 pr-10">
        <div className="flex items-start justify-between gap-2 mb-1">
          <h3 className="text-gray-900 flex-1">{puzzle.title}</h3>
        </div>
        <p className="text-sm text-gray-500">by {puzzle.creator}</p>
      </div>

      {/* Difficulty & Time Limit */}
      <div className="flex items-center gap-2 mb-3">
        <span
          className={`px-2 py-1 border rounded text-xs ${getDifficultyColor(
            puzzle.difficulty
          )}`}
        >
          {puzzle.difficulty}
        </span>
        <div className="flex items-center gap-1 text-gray-600">
          <Clock className="w-3.5 h-3.5" />
          <span className="text-xs">{puzzle.timeLimit}s</span>
        </div>
        <div className="flex items-center gap-1 text-gray-600">
          <Users className="w-3.5 h-3.5" />
          <span className="text-xs">{puzzle.solvedCount} solved</span>
        </div>
      </div>

      {/* Rating & Solved Status */}
      <div className="flex items-center justify-between pt-3 border-t border-gray-200">
        {/* Rating */}
        <div className="flex items-center gap-1">
          {renderStars(puzzle.rating)}
          <span className="text-xs text-gray-600 ml-1">{puzzle.rating}</span>
        </div>

        {/* Solved Status */}
        <div
          className={`flex items-center gap-1 px-2 py-1 rounded text-xs ${
            puzzle.solved
              ? 'bg-green-50 text-green-700'
              : 'bg-gray-50 text-gray-500'
          }`}
        >
          {puzzle.solved ? (
            <>
              <CheckCircle className="w-3.5 h-3.5" />
              <span>Solved</span>
            </>
          ) : (
            <>
              <Circle className="w-3.5 h-3.5" />
              <span>Unsolved</span>
            </>
          )}
        </div>
      </div>
    </div>
  );
}