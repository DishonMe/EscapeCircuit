import { useState } from 'react';
import { PuzzleBrowserHeader } from './PuzzleBrowserHeader';
import { Plus } from 'lucide-react';
import { DraftPuzzlesSection } from './DraftPuzzlesSection';
import { PublishedPuzzlesSection } from './PublishedPuzzlesSection';

interface CreatorDashboardProps {
  onHomeClick?: () => void;
  onAdminClick?: () => void;
}

export interface PuzzleEntry {
  id: string;
  name: string;
  uploadDate: string;
  status: 'draft' | 'published';
  rating?: number;
  ratingsCount?: number;
  popular?: boolean;
  plays?: number;
  completionRate?: number;
  averageTime?: number;
}

export function CreatorDashboard({ onHomeClick, onAdminClick }: CreatorDashboardProps = {}) {
  // Mock puzzle data
  const [puzzles, setPuzzles] = useState<PuzzleEntry[]>([
    {
      id: '1',
      name: 'Sequential Logic Intro',
      uploadDate: '2024-01-15',
      status: 'published',
      rating: 4.3,
      ratingsCount: 156,
      popular: false,
      plays: 892,
      completionRate: 67,
      averageTime: 245,
    },
    {
      id: '2',
      name: 'Complex Decoder',
      uploadDate: '2024-02-03',
      status: 'published',
      rating: 4.8,
      ratingsCount: 89,
      popular: true,
      plays: 543,
      completionRate: 42,
      averageTime: 412,
    },
    {
      id: '3',
      name: 'Memory Circuit Challenge',
      uploadDate: '2024-02-20',
      status: 'published',
      rating: 4.5,
      ratingsCount: 234,
      popular: true,
      plays: 1203,
      completionRate: 55,
      averageTime: 318,
    },
    {
      id: '4',
      name: 'Advanced Flip-Flop Design',
      uploadDate: '2024-03-01',
      status: 'draft',
    },
    {
      id: '5',
      name: 'Binary Counter Tutorial',
      uploadDate: '2024-03-05',
      status: 'draft',
    },
  ]);

  const draftPuzzles = puzzles.filter((p) => p.status === 'draft');
  const publishedPuzzles = puzzles.filter((p) => p.status === 'published');

  const handleNewPuzzle = () => {
    alert('Open puzzle creation form');
  };

  const handleEdit = (id: string) => {
    alert(`Edit puzzle ${id}`);
  };

  const handlePublish = (id: string) => {
    setPuzzles(
      puzzles.map((p) =>
        p.id === id ? { ...p, status: 'published' as const } : p
      )
    );
  };

  const handleUnpublish = (id: string) => {
    setPuzzles(
      puzzles.map((p) =>
        p.id === id ? { ...p, status: 'draft' as const } : p
      )
    );
  };

  const handleDelete = (id: string) => {
    if (confirm('Are you sure you want to delete this puzzle?')) {
      setPuzzles(puzzles.filter((p) => p.id !== id));
    }
  };

  return (
    <div className="min-h-screen bg-gray-100">
      <PuzzleBrowserHeader onHomeClick={onHomeClick} onAdminClick={onAdminClick} isAdminMode={true} />

      <div className="max-w-7xl mx-auto px-6 py-6">
        {/* Dashboard Header */}
        <div className="bg-white border border-gray-300 rounded-lg p-6 mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-gray-900 mb-1">Creator Dashboard</h1>
              <p className="text-sm text-gray-600">
                Manage your puzzles and track their performance
              </p>
            </div>
            <button
              onClick={handleNewPuzzle}
              className="px-4 py-3 bg-blue-500 hover:bg-blue-600 text-white border border-blue-600 rounded flex items-center gap-2 transition-colors"
            >
              <Plus className="w-5 h-5" />
              New Puzzle
            </button>
          </div>
        </div>

        {/* Draft Puzzles Section */}
        <DraftPuzzlesSection
          puzzles={draftPuzzles}
          onEdit={handleEdit}
          onPublish={handlePublish}
          onDelete={handleDelete}
        />

        {/* Published Puzzles Section */}
        <PublishedPuzzlesSection
          puzzles={publishedPuzzles}
          onEdit={handleEdit}
          onUnpublish={handleUnpublish}
          onDelete={handleDelete}
        />
      </div>
    </div>
  );
}