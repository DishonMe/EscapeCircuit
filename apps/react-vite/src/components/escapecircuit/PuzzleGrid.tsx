import { PuzzleCard } from './PuzzleCard';
import { Puzzle } from './PuzzleBrowser';

interface PuzzleGridProps {
  puzzles: Puzzle[];
  onPuzzleSelect?: ((puzzleId: string) => void) | null;
}

export function PuzzleGrid({ puzzles, onPuzzleSelect }: PuzzleGridProps) {
  if (puzzles.length === 0) {
    return (
      <div className="bg-white border border-gray-300 rounded-lg p-12 text-center mb-6">
        <p className="text-gray-500">No puzzles found matching your filters.</p>
        <p className="text-sm text-gray-400 mt-2">Try adjusting your search criteria.</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-6">
      {puzzles.map((puzzle) => (
        <PuzzleCard key={puzzle.id} puzzle={puzzle} onSelect={onPuzzleSelect} />
      ))}
    </div>
  );
}