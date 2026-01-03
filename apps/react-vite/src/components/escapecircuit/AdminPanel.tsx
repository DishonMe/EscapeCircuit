import { useState } from 'react';
import { PuzzleBrowserHeader } from './PuzzleBrowserHeader';
import { UsersManagement } from './UsersManagement';
import { PuzzlesModeration } from './PuzzlesModeration';

interface AdminPanelProps {
  onHomeClick?: () => void;
  onAdminClick?: () => void;
}

export function AdminPanel({ onHomeClick, onAdminClick }: AdminPanelProps = {}) {
  const [activeTab, setActiveTab] = useState<'users' | 'puzzles'>('users');

  return (
    <div className="min-h-screen bg-gray-100">
      <PuzzleBrowserHeader onHomeClick={onHomeClick} onAdminClick={onAdminClick} isAdminMode={true} />

      <div className="max-w-7xl mx-auto px-6 py-6">
        {/* Admin Panel Header */}
        <div className="bg-white border border-gray-300 rounded-lg p-6 mb-6">
          <h1 className="text-gray-900 mb-1">Admin Panel</h1>
          <p className="text-sm text-gray-600">
            Manage users and moderate puzzle content
          </p>
        </div>

        {/* Tab Navigation */}
        <div className="bg-white border border-gray-300 rounded-lg mb-6">
          <div className="flex border-b border-gray-300">
            <button
              onClick={() => setActiveTab('users')}
              className={`flex-1 px-6 py-4 transition-colors ${
                activeTab === 'users'
                  ? 'bg-blue-50 border-b-2 border-blue-500 text-blue-700'
                  : 'text-gray-600 hover:bg-gray-50'
              }`}
            >
              Users Management
            </button>
            <button
              onClick={() => setActiveTab('puzzles')}
              className={`flex-1 px-6 py-4 transition-colors ${
                activeTab === 'puzzles'
                  ? 'bg-blue-50 border-b-2 border-blue-500 text-blue-700'
                  : 'text-gray-600 hover:bg-gray-50'
              }`}
            >
              Puzzles Moderation
            </button>
          </div>

          {/* Tab Content */}
          <div className="p-6">
            {activeTab === 'users' && <UsersManagement />}
            {activeTab === 'puzzles' && <PuzzlesModeration />}
          </div>
        </div>
      </div>
    </div>
  );
}