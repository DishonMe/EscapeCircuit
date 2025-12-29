import { Award } from 'lucide-react';

interface UserData {
  name: string;
  level: number;
  currentXP: number;
  nextLevelXP: number;
  previousLevelXP: number;
  medals: {
    gold: number;
    silver: number;
    bronze: number;
  };
  solvedPuzzles: number;
}

interface ProfileStatsProps {
  userData: UserData;
  activeTab: string;
  setActiveTab: (tab: 'saved-puzzles' | 'saved-circuits' | 'created-puzzles') => void;
}

export function ProfileStats({ userData, activeTab, setActiveTab }: ProfileStatsProps) {
  const xpProgress = ((userData.currentXP - userData.previousLevelXP) / (userData.nextLevelXP - userData.previousLevelXP)) * 100;
  const xpNeeded = userData.nextLevelXP - userData.currentXP;

  return (
    <div className="bg-white border border-gray-300 rounded-lg p-6 mb-6">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Side: User Info & XP */}
        <div className="lg:col-span-2">
          {/* User Name & Level */}
          <div className="mb-6">
            <h1 className="text-gray-900 mb-1">{userData.name}</h1>
            <p className="text-gray-600">Level {userData.level}</p>
          </div>

          {/* XP Bar */}
          <div className="mb-6">
            <div className="w-full h-8 bg-gray-200 rounded-full overflow-hidden mb-3">
              <div
                className="h-full bg-blue-500 transition-all"
                style={{ width: `${xpProgress}%` }}
              />
            </div>
            <div className="space-y-1">
              <p className="text-sm text-gray-700">
                Current XP: {userData.currentXP} / {userData.nextLevelXP}
              </p>
              <p className="text-sm text-gray-600">
                {xpNeeded} XP needed to reach Level {userData.level + 1}
              </p>
            </div>
          </div>

          {/* Medal Summary */}
          <div className="mb-6">
            <div className="text-sm text-gray-700 mb-3">Medal Summary</div>
            <div className="flex gap-6">
              <div className="flex items-center gap-2">
                <div className="w-10 h-10 bg-yellow-100 rounded-full flex items-center justify-center">
                  <Award className="w-6 h-6 text-yellow-600 fill-yellow-500" />
                </div>
                <div>
                  <div className="text-gray-900">Gold: {userData.medals.gold}</div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-10 h-10 bg-gray-200 rounded-full flex items-center justify-center">
                  <Award className="w-6 h-6 text-gray-600 fill-gray-400" />
                </div>
                <div>
                  <div className="text-gray-900">Silver: {userData.medals.silver}</div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-10 h-10 bg-orange-100 rounded-full flex items-center justify-center">
                  <Award className="w-6 h-6 text-orange-600 fill-orange-400" />
                </div>
                <div>
                  <div className="text-gray-900">Bronze: {userData.medals.bronze}</div>
                </div>
              </div>
            </div>
          </div>

          {/* Solved Puzzles Count */}
          <div>
            <p className="text-gray-700">Solved Puzzles: <span className="text-gray-900">{userData.solvedPuzzles}</span></p>
          </div>
        </div>

        {/* Right Side: Quick Navigation Buttons */}
        <div className="flex flex-col gap-3">
          <div className="text-sm text-gray-700 mb-1">Quick Navigation</div>
          <button
            onClick={() => setActiveTab('saved-puzzles')}
            className={`px-4 py-3 rounded border transition-colors text-left ${
              activeTab === 'saved-puzzles'
                ? 'bg-blue-50 border-blue-300 text-blue-700'
                : 'bg-gray-50 border-gray-300 text-gray-700 hover:bg-gray-100'
            }`}
          >
            Saved Puzzles
          </button>
          <button
            onClick={() => setActiveTab('saved-circuits')}
            className={`px-4 py-3 rounded border transition-colors text-left ${
              activeTab === 'saved-circuits'
                ? 'bg-blue-50 border-blue-300 text-blue-700'
                : 'bg-gray-50 border-gray-300 text-gray-700 hover:bg-gray-100'
            }`}
          >
            Saved Circuits (Arsenal)
          </button>
          <button
            onClick={() => setActiveTab('created-puzzles')}
            className={`px-4 py-3 rounded border transition-colors text-left ${
              activeTab === 'created-puzzles'
                ? 'bg-blue-50 border-blue-300 text-blue-700'
                : 'bg-gray-50 border-gray-300 text-gray-700 hover:bg-gray-100'
            }`}
          >
            Created Puzzles
          </button>
        </div>
      </div>
    </div>
  );
}
