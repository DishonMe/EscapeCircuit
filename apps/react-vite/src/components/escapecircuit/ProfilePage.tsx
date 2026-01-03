import { useState } from 'react';
import { PuzzleBrowserHeader } from './PuzzleBrowserHeader';
import { ProfileStats } from './ProfileStats';
import { ProfileContent } from './ProfileContent';

interface ProfilePageProps {
  onHomeClick?: () => void;
  onAdminClick?: () => void;
}

export function ProfilePage({ onHomeClick, onAdminClick }: ProfilePageProps = {}) {
  const [activeTab, setActiveTab] = useState<'saved-puzzles' | 'saved-circuits' | 'created-puzzles'>('saved-puzzles');

  // Mock user data
  const userData = {
    name: 'CircuitMaster42',
    level: 7,
    currentXP: 2400,
    nextLevelXP: 3000,
    previousLevelXP: 2000,
    medals: {
      gold: 3,
      silver: 5,
      bronze: 9,
    },
    solvedPuzzles: 42,
  };

  return (
    <div className="min-h-screen bg-gray-100">
      <PuzzleBrowserHeader onHomeClick={onHomeClick} onAdminClick={onAdminClick} isAdminMode={true} />

      <div className="max-w-7xl mx-auto px-6 py-6">
        {/* Profile Stats Section */}
        <ProfileStats userData={userData} activeTab={activeTab} setActiveTab={setActiveTab} />

        {/* Content Section */}
        <ProfileContent activeTab={activeTab} />
      </div>
    </div>
  );
}