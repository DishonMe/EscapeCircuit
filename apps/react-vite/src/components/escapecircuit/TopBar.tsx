import { Menu, Info } from 'lucide-react';
import { Timer } from './Timer';

interface TopBarProps {
  puzzleTitle: string;
  currentCost: number;
  budgetLimit: number;
  tightBudgetLimit: number;
  onOpenDescription: () => void;
  onReturnToList: () => void;
}

export function TopBar({
  puzzleTitle,
  currentCost,
  budgetLimit,
  tightBudgetLimit,
  onOpenDescription,
  onReturnToList,
}: TopBarProps) {
  const getCostColor = () => {
    if (currentCost > budgetLimit) return 'text-red-600';
    if (currentCost > tightBudgetLimit) return 'text-orange-600';
    return 'text-gray-900';
  };

  return (
    <div className="h-14 bg-white border-b border-gray-300 flex items-center px-4 gap-6">
      {/* Puzzle Title */}
      <div className="flex-shrink-0">
        <h1 className="text-gray-900">{puzzleTitle}</h1>
      </div>

      {/* Timer */}
      <Timer initialTime={600} />

      {/* Cost Indicators */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="text-gray-600 text-sm">Cost:</span>
          <span className={`font-mono ${getCostColor()}`}>{currentCost}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-gray-600 text-sm">Budget:</span>
          <span className="text-gray-900 font-mono">{budgetLimit}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-gray-600 text-sm">Tight Budget:</span>
          <span className="text-orange-600 font-mono">{tightBudgetLimit}</span>
        </div>
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Action Buttons */}
      <button
        onClick={onOpenDescription}
        className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 border border-gray-300 rounded flex items-center gap-2 transition-colors"
      >
        <Info className="w-4 h-4" />
        <span className="text-sm">Description</span>
      </button>
      <button
        onClick={onReturnToList}
        className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 border border-gray-300 rounded flex items-center gap-2 transition-colors"
      >
        <Menu className="w-4 h-4" />
        <span className="text-sm">Puzzle List</span>
      </button>
    </div>
  );
}