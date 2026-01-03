import { Trash2, FlaskConical, Save, LogOut, Check } from 'lucide-react';

interface BottomBarProps {
  onClear: () => void;
  onSandbox?: () => void;
  onSave?: () => void;
  onExit?: () => void;
  onCheck?: () => void;
}

export function BottomBar({ onClear, onSandbox, onSave, onExit, onCheck }: BottomBarProps) {
  return (
    <div className="h-12 bg-white border-t border-gray-300 flex items-center px-4 gap-3">
      <button
        onClick={onClear}
        className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 border border-gray-300 rounded flex items-center gap-2 transition-colors"
      >
        <Trash2 className="w-4 h-4" />
        <span className="text-sm">Clear Board</span>
      </button>
      {onCheck && (
        <button
          onClick={onCheck}
          className="px-3 py-1.5 bg-green-500 hover:bg-green-600 text-white border border-green-600 rounded flex items-center gap-2 transition-colors"
        >
          <Check className="w-4 h-4" />
          <span className="text-sm">Check Circuit</span>
        </button>
      )}
      {onSandbox && (
        <button
          onClick={onSandbox}
          className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 border border-gray-300 rounded flex items-center gap-2 transition-colors"
        >
          <FlaskConical className="w-4 h-4" />
          <span className="text-sm">Open Sandbox</span>
        </button>
      )}
      {onSave && (
        <button
          onClick={onSave}
          className="px-3 py-1.5 bg-blue-500 hover:bg-blue-600 text-white border border-blue-600 rounded flex items-center gap-2 transition-colors"
        >
          <Save className="w-4 h-4" />
          <span className="text-sm">Save Circuit</span>
        </button>
      )}
      
      <div className="flex-1" />
      
      {onExit && (
        <button
          onClick={onExit}
          className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 border border-gray-300 rounded flex items-center gap-2 transition-colors"
        >
          <LogOut className="w-4 h-4" />
          <span className="text-sm">Exit Puzzle</span>
        </button>
      )}
    </div>
  );
}
