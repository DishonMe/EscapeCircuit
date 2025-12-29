import { SavedPuzzlesList } from './SavedPuzzlesList';
import { SavedCircuitsList } from './SavedCircuitsList';
import { CreatedPuzzlesList } from './CreatedPuzzlesList';

interface ProfileContentProps {
  activeTab: 'saved-puzzles' | 'saved-circuits' | 'created-puzzles';
}

export function ProfileContent({ activeTab }: ProfileContentProps) {
  return (
    <div className="bg-white border border-gray-300 rounded-lg p-6">
      {activeTab === 'saved-puzzles' && <SavedPuzzlesList />}
      {activeTab === 'saved-circuits' && <SavedCircuitsList />}
      {activeTab === 'created-puzzles' && <CreatedPuzzlesList />}
    </div>
  );
}
