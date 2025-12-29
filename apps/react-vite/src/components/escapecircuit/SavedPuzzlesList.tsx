import { Clock, CheckCircle, Circle, Play, RotateCcw } from 'lucide-react';

interface SavedPuzzle {
  id: string;
  name: string;
  creator: string;
  difficulty: 'Easy' | 'Medium' | 'Hard';
  timeLimit: number;
  solved: boolean;
}

export function SavedPuzzlesList() {
  const savedPuzzles: SavedPuzzle[] = [
    {
      id: '1',
      name: 'Binary Adder',
      creator: 'LogicMaster',
      difficulty: 'Medium',
      timeLimit: 300,
      solved: true,
    },
    {
      id: '2',
      name: 'XOR Challenge',
      creator: 'CircuitGuru',
      difficulty: 'Easy',
      timeLimit: 120,
      solved: false,
    },
    {
      id: '3',
      name: 'Advanced Multiplexer',
      creator: 'TechWizard',
      difficulty: 'Hard',
      timeLimit: 600,
      solved: false,
    },
    {
      id: '4',
      name: 'Simple NOT Gates',
      creator: 'BeginnerFriend',
      difficulty: 'Easy',
      timeLimit: 60,
      solved: true,
    },
  ];

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

  return (
    <div>
      <h2 className="text-gray-900 mb-4">Saved Puzzles</h2>
      
      {savedPuzzles.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <p>No saved puzzles yet.</p>
          <p className="text-sm mt-2">Browse puzzles and save your favorites!</p>
        </div>
      ) : (
        <div className="space-y-3">
          {savedPuzzles.map((puzzle) => (
            <div
              key={puzzle.id}
              className="border border-gray-300 rounded-lg p-4 hover:border-blue-400 transition-colors"
            >
              <div className="flex items-center justify-between gap-4">
                {/* Left: Puzzle Info */}
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="text-gray-900">{puzzle.name}</h3>
                    <span
                      className={`px-2 py-0.5 border rounded text-xs ${getDifficultyColor(
                        puzzle.difficulty
                      )}`}
                    >
                      {puzzle.difficulty}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 text-sm text-gray-600">
                    <span>by {puzzle.creator}</span>
                    <div className="flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5" />
                      <span>{puzzle.timeLimit}s</span>
                    </div>
                    <div className="flex items-center gap-1">
                      {puzzle.solved ? (
                        <>
                          <CheckCircle className="w-3.5 h-3.5 text-green-600" />
                          <span className="text-green-600">Solved</span>
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

                {/* Right: Action Buttons */}
                <div className="flex gap-2">
                  {puzzle.solved ? (
                    <button className="px-4 py-2 bg-gray-100 hover:bg-gray-200 border border-gray-300 rounded flex items-center gap-2 transition-colors text-sm">
                      <RotateCcw className="w-4 h-4" />
                      Retry
                    </button>
                  ) : (
                    <button className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white border border-blue-600 rounded flex items-center gap-2 transition-colors text-sm">
                      <Play className="w-4 h-4" />
                      Resume
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
