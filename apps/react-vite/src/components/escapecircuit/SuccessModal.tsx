import { CheckCircle, X, Trophy, Award, Clock } from 'lucide-react';

interface SuccessModalProps {
  onClose: () => void;
  onRetry: () => void;
  onReturnToBrowser: () => void;
  xpEarned: number;
  currentLevel: number;
  nextLevel: number;
  currentXP: number;
  nextLevelXP: number;
  previousXP: number;
  timeUsed: number;
  circuitCost: number;
  budgetRemaining: number;
  medals: {
    type: 'gold' | 'silver' | 'bronze';
    label: string;
  }[];
}

export function SuccessModal({
  onClose,
  onRetry,
  onReturnToBrowser,
  xpEarned,
  currentLevel,
  nextLevel,
  currentXP,
  nextLevelXP,
  previousXP,
  timeUsed,
  circuitCost,
  budgetRemaining,
  medals,
}: SuccessModalProps) {
  const xpProgress = ((currentXP - previousXP) / (nextLevelXP - previousXP)) * 100;
  const previousProgress = ((previousXP - previousXP) / (nextLevelXP - previousXP)) * 100;

  const getMedalColor = (type: 'gold' | 'silver' | 'bronze') => {
    switch (type) {
      case 'gold':
        return 'bg-yellow-400 text-yellow-900';
      case 'silver':
        return 'bg-gray-300 text-gray-700';
      case 'bronze':
        return 'bg-orange-300 text-orange-900';
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        {/* Close Button */}
        <div className="flex justify-end p-4 pb-0">
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 rounded transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Title Section */}
        <div className="px-8 pb-6 text-center">
          <div className="flex justify-center mb-4">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center">
              <CheckCircle className="w-10 h-10 text-green-600" />
            </div>
          </div>
          <h2 className="text-gray-900 mb-2">Puzzle Solved Successfully!</h2>
          <p className="text-gray-600">All test cases passed.</p>
        </div>

        {/* XP Reward Section */}
        <div className="px-8 pb-6">
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
            <div className="text-sm text-gray-600 mb-2">Experience Earned</div>
            <div className="text-2xl text-green-600 mb-4">+{xpEarned} XP</div>

            {/* XP Progress Bar */}
            <div className="mb-3">
              <div className="w-full h-6 bg-gray-200 rounded-full overflow-hidden relative">
                {/* Previous progress */}
                <div
                  className="absolute top-0 left-0 h-full bg-blue-400"
                  style={{ width: `${previousProgress}%` }}
                />
                {/* New XP gained */}
                <div
                  className="absolute top-0 h-full bg-green-500"
                  style={{ 
                    left: `${previousProgress}%`,
                    width: `${xpProgress - previousProgress}%` 
                  }}
                />
              </div>
            </div>

            <div className="flex justify-between text-sm text-gray-600">
              <span>Level {currentLevel} → Level {nextLevel}</span>
              <span>Next level at {nextLevelXP} XP</span>
            </div>
          </div>
        </div>

        {/* Medals Awarded */}
        {medals.length > 0 && (
          <div className="px-8 pb-6">
            <div className="text-sm text-gray-700 mb-3">Medals Earned</div>
            <div className="flex flex-wrap gap-3">
              {medals.map((medal, index) => (
                <div
                  key={index}
                  className="flex items-center gap-2 bg-white border border-gray-300 rounded-lg px-3 py-2"
                >
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center ${getMedalColor(medal.type)}`}>
                    <Award className="w-5 h-5" />
                  </div>
                  <span className="text-sm text-gray-700">{medal.label}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Stats Section */}
        <div className="px-8 pb-6">
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
            <div className="text-sm text-gray-700 mb-3">Puzzle Statistics</div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between items-center">
                <span className="text-gray-600 flex items-center gap-2">
                  <Clock className="w-4 h-4" />
                  Time Used
                </span>
                <span className="text-gray-900 font-mono">{timeUsed}s</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-600 flex items-center gap-2">
                  <Trophy className="w-4 h-4" />
                  Circuit Cost
                </span>
                <span className="text-gray-900 font-mono">{circuitCost}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-600">Budget Remaining</span>
                <span className="text-green-600 font-mono">{budgetRemaining}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="px-8 pb-8">
          <div className="flex flex-col gap-3">
            <button
              onClick={onReturnToBrowser}
              className="w-full px-4 py-3 bg-blue-500 hover:bg-blue-600 text-white rounded transition-colors"
            >
              Return to Puzzle Browser
            </button>
            <button
              onClick={onRetry}
              className="w-full px-4 py-3 bg-gray-100 hover:bg-gray-200 border border-gray-300 rounded transition-colors"
            >
              Retry Puzzle
            </button>
            <button
              onClick={() => alert('View profile')}
              className="text-sm text-blue-600 hover:text-blue-700 transition-colors"
            >
              View My Profile
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
