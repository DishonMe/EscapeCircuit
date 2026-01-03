import { Bell, User, Boxes, Shield, Hammer } from 'lucide-react';

interface PuzzleBrowserHeaderProps {
  onProfileClick?: () => void;
  onHomeClick?: () => void;
  onAdminClick?: () => void;
  onCreatorClick?: () => void;
  isAdminMode?: boolean;
}

export function PuzzleBrowserHeader({ onProfileClick, onHomeClick, onAdminClick, onCreatorClick, isAdminMode }: PuzzleBrowserHeaderProps = {}) {
  return (
    <header className="bg-white border-b border-gray-300">
      <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
        {/* App Title */}
        <div 
          onClick={onHomeClick || (() => {})}
          className={onHomeClick ? 'cursor-pointer' : ''}
        >
          <h1 className="text-gray-900">EscapeCircuit</h1>
          <p className="text-sm text-gray-500">Logic Puzzle Platform</p>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-3">
          <button 
            onClick={onCreatorClick || (() => alert('Navigate to creator dashboard'))}
            className="px-3 py-2 bg-purple-100 hover:bg-purple-200 border border-purple-300 text-purple-700 rounded flex items-center gap-2 transition-colors"
          >
            <Hammer className="w-4 h-4" />
            <span className="text-sm">Create</span>
          </button>
          <button className="px-3 py-2 bg-gray-100 hover:bg-gray-200 border border-gray-300 rounded flex items-center gap-2 transition-colors">
            <Boxes className="w-4 h-4" />
            <span className="text-sm">My Circuits</span>
          </button>
          <button className="p-2 bg-gray-100 hover:bg-gray-200 border border-gray-300 rounded transition-colors relative">
            <Bell className="w-5 h-5" />
            <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
          </button>
          <button 
            onClick={onProfileClick || (() => alert('Navigate to profile'))}
            className="px-3 py-2 bg-blue-500 hover:bg-blue-600 text-white border border-blue-600 rounded flex items-center gap-2 transition-colors"
          >
            <User className="w-4 h-4" />
            <span className="text-sm">Profile</span>
          </button>
          {isAdminMode && (
            <button 
              onClick={onAdminClick || (() => alert('Navigate to admin panel'))}
              className="px-3 py-2 bg-red-500 hover:bg-red-600 text-white border border-red-600 rounded flex items-center gap-2 transition-colors"
            >
              <Shield className="w-4 h-4" />
              <span className="text-sm">Admin</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
}