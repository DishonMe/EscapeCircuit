import { Award, Star, Edit, Trash2, Eye } from 'lucide-react';

interface CreatedPuzzle {
  id: string;
  name: string;
  difficulty: 'Easy' | 'Medium' | 'Hard';
  medals: {
    gold: number;
    silver: number;
    bronze: number;
  };
  plays: number;
  rating: number;
}

export function CreatedPuzzlesList() {
  const createdPuzzles: CreatedPuzzle[] = [
    {
      id: '1',
      name: 'Sequential Logic Intro',
      difficulty: 'Easy',
      medals: {
        gold: 45,
        silver: 67,
        bronze: 44,
      },
      plays: 156,
      rating: 4.3,
    },
    {
      id: '2',
      name: 'Complex Decoder',
      difficulty: 'Hard',
      medals: {
        gold: 8,
        silver: 15,
        bronze: 19,
      },
      plays: 42,
      rating: 4.8,
    },
    {
      id: '3',
      name: 'Memory Circuit Challenge',
      difficulty: 'Medium',
      medals: {
        gold: 22,
        silver: 38,
        bronze: 29,
      },
      plays: 89,
      rating: 4.5,
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

  const getMedalIcon = (medal: 'gold' | 'silver' | 'bronze') => {
    const colors = {
      gold: 'text-yellow-600 fill-yellow-500',
      silver: 'text-gray-600 fill-gray-400',
      bronze: 'text-orange-600 fill-orange-400',
    };
    return <Award className={`w-4 h-4 ${colors[medal]}`} />;
  };

  const getMedalBgColor = (medal: 'gold' | 'silver' | 'bronze') => {
    const colors = {
      gold: 'bg-yellow-100',
      silver: 'bg-gray-200',
      bronze: 'bg-orange-100',
    };
    return colors[medal];
  };

  return (
    <div>
      <h2 className="text-gray-900 mb-4">Created Puzzles</h2>
      
      {createdPuzzles.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <p>No created puzzles yet.</p>
          <p className="text-sm mt-2">Create your own puzzles to challenge other users!</p>
        </div>
      ) : (
        <div className="space-y-3">
          {createdPuzzles.map((puzzle) => (
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
                  <div className="flex items-center gap-6 text-sm text-gray-600">
                    {/* Medals */}
                    <div className="flex items-center gap-3">
                      <span className="text-gray-700">Medals:</span>
                      <div className="flex items-center gap-1">
                        <div className={`w-7 h-7 rounded-full flex items-center justify-center ${getMedalBgColor('gold')}`}>
                          {getMedalIcon('gold')}
                        </div>
                        <span className="text-gray-900 font-mono">{puzzle.medals.gold}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <div className={`w-7 h-7 rounded-full flex items-center justify-center ${getMedalBgColor('silver')}`}>
                          {getMedalIcon('silver')}
                        </div>
                        <span className="text-gray-900 font-mono">{puzzle.medals.silver}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <div className={`w-7 h-7 rounded-full flex items-center justify-center ${getMedalBgColor('bronze')}`}>
                          {getMedalIcon('bronze')}
                        </div>
                        <span className="text-gray-900 font-mono">{puzzle.medals.bronze}</span>
                      </div>
                    </div>
                    {/* Plays */}
                    <div>
                      <span className="text-gray-900 font-mono">{puzzle.plays}</span> plays
                    </div>
                    {/* Rating */}
                    <div className="flex items-center gap-1">
                      <Star className="w-3.5 h-3.5 text-yellow-500 fill-yellow-500" />
                      <span className="text-gray-900">{puzzle.rating}</span>
                    </div>
                  </div>
                </div>

                {/* Right: Action Buttons */}
                <div className="flex gap-2">
                  <button className="px-3 py-2 bg-gray-100 hover:bg-gray-200 border border-gray-300 rounded flex items-center gap-1 transition-colors text-sm">
                    <Eye className="w-4 h-4" />
                    View
                  </button>
                  <button className="px-3 py-2 bg-gray-100 hover:bg-gray-200 border border-gray-300 rounded flex items-center gap-1 transition-colors text-sm">
                    <Edit className="w-4 h-4" />
                    Edit
                  </button>
                  <button className="px-3 py-2 bg-red-50 hover:bg-red-100 border border-red-300 rounded flex items-center gap-1 transition-colors text-sm text-red-700">
                    <Trash2 className="w-4 h-4" />
                    Delete
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