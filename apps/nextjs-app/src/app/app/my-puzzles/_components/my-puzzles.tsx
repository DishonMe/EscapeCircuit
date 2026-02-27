'use client';

import Link from 'next/link';
import { useState } from 'react';
import { Trash2, Edit2 } from 'lucide-react';

import { useUser } from '@/lib/auth';
import { useMyPuzzles } from '@/features/puzzles/api/get-my-puzzles';
import { useDeletePuzzle } from '@/features/puzzles/api/delete-puzzle';
import { usePublishPuzzle, useUnpublishPuzzle } from '@/features/puzzles/api/publish-puzzle';
import { useUpdatePuzzle } from '@/features/puzzles/api/update-puzzle';
import { Spinner } from '@/components/ui/spinner';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { paths } from '@/config/paths';
import type { Puzzle } from '@/types/api';

export const MyPuzzles = () => {
  const user = useUser();
  const [page, setPage] = useState(1);
  const [showPublished, setShowPublished] = useState(true);
  const [editingPuzzle, setEditingPuzzle] = useState<Puzzle | null>(null);
  const [editName, setEditName] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [editInstructions, setEditInstructions] = useState('');
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);

  const userId = user.data?.id;
  
  // Fetch all puzzles (both published and unpublished) for the user
  const puzzlesQuery = useMyPuzzles({
    filters: {
      page,
    },
  });

  const deleteMutation = useDeletePuzzle();
  const publishMutation = usePublishPuzzle();
  const unpublishMutation = useUnpublishPuzzle();
  const updateMutation = useUpdatePuzzle();

  const allPuzzles = puzzlesQuery.data?.data || [];
  const meta = puzzlesQuery.data?.meta;
  const isLoading = puzzlesQuery.isLoading;

  // Filter by published status
  const filteredPuzzles = allPuzzles.filter((p) => {
    const isPublished = (p as any).status === 'published' || (p as any).isPublished === true;
    return showPublished ? isPublished : !isPublished;
  });

  const isEmpty = !isLoading && filteredPuzzles.length === 0;

  const openEditDialog = (puzzle: Puzzle) => {
    setEditingPuzzle(puzzle);
    setEditName(puzzle.title || puzzle.name || '');
    setEditDescription(puzzle.description || '');
    setEditInstructions(puzzle.instructions || '');
  };

  const handleSaveEdit = async () => {
    if (!editingPuzzle) return;
    try {
      await updateMutation.mutateAsync({
        puzzleId: editingPuzzle.id,
        name: editName,
        description: editDescription,
        instructions: editInstructions,
      });
      setEditingPuzzle(null);
    } catch (error) {
      console.error('Failed to update puzzle:', error);
    }
  };

  const handleDelete = async (puzzleId: string | number) => {
    try {
      await deleteMutation.mutateAsync(puzzleId);
      setDeleteConfirmId(null);
    } catch (error) {
      console.error('Failed to delete puzzle:', error);
    }
  };

  const handlePublish = async (puzzleId: string | number) => {
    try {
      await publishMutation.mutateAsync(puzzleId);
    } catch (error) {
      console.error('Failed to publish puzzle:', error);
    }
  };

  const handleUnpublish = async (puzzleId: string | number) => {
    try {
      await unpublishMutation.mutateAsync(puzzleId);
    } catch (error) {
      console.error('Failed to unpublish puzzle:', error);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="mx-auto max-w-7xl px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="mb-2 text-3xl font-bold text-gray-900">
            My Created Puzzles
          </h1>
          <p className="text-gray-600">
            Create, manage, and publish your circuit puzzles
          </p>
        </div>

        {/* Create Puzzle Button - Only here */}
        <div className="mb-6 flex gap-3">
          <Link
            href={paths.app.createPuzzle.getHref()}
            className="rounded bg-green-600 px-6 py-2 text-sm font-medium text-white hover:bg-green-700"
          >
            ✏️ Create New Puzzle
          </Link>
          {user.data?.role === 'admin' && (
            <Link
              href="/app/admin/upload-puzzle"
              className="rounded bg-purple-600 px-6 py-2 text-sm font-medium text-white hover:bg-purple-700"
            >
              📤 Upload Puzzle Files
            </Link>
          )}
          <Link
            href={paths.app.puzzles.getHref()}
            className="rounded bg-blue-600 px-6 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            Browse All Puzzles
          </Link>
        </div>

        {/* Published/Unpublished Toggle */}
        <div className="mb-6 flex items-center gap-4 rounded-lg border border-gray-200 bg-white p-4">
          <div className="flex items-center gap-2">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name="puzzle_status"
                checked={showPublished}
                onChange={() => setShowPublished(true)}
                className="w-4 h-4"
              />
              <span className="text-sm font-medium text-gray-700">Published Puzzles</span>
            </label>
          </div>
          <div className="flex items-center gap-2">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name="puzzle_status"
                checked={!showPublished}
                onChange={() => setShowPublished(false)}
                className="w-4 h-4"
              />
              <span className="text-sm font-medium text-gray-700">Unpublished Puzzles</span>
            </label>
          </div>
        </div>

        {/* Loading */}
        {isLoading && (
          <div className="flex h-48 w-full items-center justify-center">
            <Spinner size="lg" />
          </div>
        )}

        {/* Empty state */}
        {!isLoading && isEmpty && (
          <div className="rounded border border-gray-200 bg-white p-8 text-center text-gray-600">
            <p className="mb-4">
              {showPublished
                ? 'You have no published puzzles yet.'
                : 'You have no unpublished puzzles yet.'}
            </p>
            <Link
              href={paths.app.createPuzzle.getHref()}
              className="rounded bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700"
            >
              Create Your First Puzzle
            </Link>
          </div>
        )}

        {/* Puzzles Grid */}
        {!isLoading && !isEmpty && (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
            {filteredPuzzles.map((puzzle) => {
              const isPublished = (puzzle as any).status === 'published' || (puzzle as any).isPublished === true;
              return (
                <div
                  key={puzzle.id}
                  className={`relative rounded-lg border-2 bg-white p-5 transition-all hover:shadow-lg ${
                    isPublished
                      ? 'border-blue-400 hover:border-blue-500'
                      : 'border-orange-400 hover:border-orange-500'
                  }`}
                >
                  {/* Status Badge */}
                  <div className={`absolute -right-2 -top-2 z-10 flex items-center justify-center rounded-full text-white shadow-md px-3 py-1 ${
                    isPublished ? 'bg-blue-500' : 'bg-orange-500'
                  }`}>
                    <span className="text-xs font-semibold">
                      {isPublished ? 'Published' : 'Unpublished'}
                    </span>
                  </div>

                  {/* Title */}
                  <div className="mb-3">
                    <h3 className="mb-1 font-medium text-gray-900">{puzzle.title || puzzle.name}</h3>
                    <p className="text-sm text-gray-500">
                      Created on {new Date(puzzle.createdAt || '').toLocaleDateString()}
                    </p>
                  </div>

                  {/* Difficulty & Stats */}
                  <div className="mb-3 flex flex-wrap items-center gap-2">
                    <span className="rounded border border-gray-300 bg-gray-50 px-2 py-1 text-xs text-gray-600">
                      {puzzle.difficulty?.charAt(0) + puzzle.difficulty?.slice(1).toLowerCase() || 'Unknown'}
                    </span>
                    <span className="text-xs text-gray-600">
                      Solved by {puzzle.solvedCount || 0} users
                    </span>
                  </div>

                  {/* Description */}
                  {puzzle.description && (
                    <p className="mb-4 text-sm text-gray-600 line-clamp-2">
                      {puzzle.description}
                    </p>
                  )}

                  {/* Quick Stats */}
                  <div className="mb-4 rounded-md bg-gray-50 p-3 text-xs text-gray-600 space-y-1">
                    {puzzle.rating_metrics && puzzle.rating_metrics.count > 0 && (
                      <>
                        <div>
                          Avg Difficulty: {puzzle.rating_metrics.weighted_difficulty?.toFixed(1) || 'N/A'}/5
                        </div>
                        <div>
                          Fun: {puzzle.rating_metrics.avg_fun?.toFixed(1) || 'N/A'}/5
                        </div>
                        <div>
                          Clearness: {puzzle.rating_metrics.avg_clearness?.toFixed(1) || 'N/A'}/5
                        </div>
                      </>
                    )}
                    {!puzzle.rating_metrics || puzzle.rating_metrics.count === 0 && (
                      <div className="text-gray-500">No ratings yet</div>
                    )}
                  </div>

                  {/* Action Buttons */}
                  <div className="flex flex-col gap-2">
                    <div className="flex gap-2">
                      <Link
                        href={paths.app.puzzle.getHref(String(puzzle.id))}
                        className="flex-1 rounded bg-blue-600 px-3 py-2 text-center text-sm font-medium text-white hover:bg-blue-700"
                      >
                        View
                      </Link>
                      <button
                        onClick={() => openEditDialog(puzzle)}
                        className="flex-1 rounded bg-gray-600 px-3 py-2 text-center text-sm font-medium text-white hover:bg-gray-700 flex items-center justify-center gap-1"
                      >
                        <Edit2 className="size-4" />
                        Edit
                      </button>
                    </div>
                    
                    <div className="flex gap-2">
                      {isPublished ? (
                        <button
                          onClick={() => handleUnpublish(puzzle.id)}
                          disabled={unpublishMutation.isPending}
                          className="flex-1 rounded bg-orange-600 px-3 py-2 text-center text-sm font-medium text-white hover:bg-orange-700 disabled:opacity-50"
                        >
                          {unpublishMutation.isPending ? 'Unpublishing...' : 'Unpublish'}
                        </button>
                      ) : (
                        <button
                          onClick={() => handlePublish(puzzle.id)}
                          disabled={publishMutation.isPending}
                          className="flex-1 rounded bg-green-600 px-3 py-2 text-center text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
                        >
                          {publishMutation.isPending ? 'Publishing...' : 'Publish'}
                        </button>
                      )}
                      <button
                        onClick={() => setDeleteConfirmId(String(puzzle.id))}
                        className="rounded bg-red-600 px-3 py-2 text-white hover:bg-red-700"
                        title="Delete puzzle"
                      >
                        <Trash2 className="size-4" />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Edit Dialog */}
        {editingPuzzle && (
          <Dialog open={Boolean(editingPuzzle)} onOpenChange={(open) => {
            if (!open) setEditingPuzzle(null);
          }}>
            <DialogContent className="max-w-lg">
              <DialogHeader>
                <DialogTitle>Edit Puzzle</DialogTitle>
                <DialogDescription>
                  Update your puzzle's name, description, and instructions
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4">
                <div>
                  <label className="text-sm font-medium text-gray-700">Puzzle Name</label>
                  <input
                    type="text"
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    className="w-full rounded border border-gray-300 px-3 py-2 text-sm mt-1"
                    placeholder="Enter puzzle name"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-700">Description</label>
                  <textarea
                    value={editDescription}
                    onChange={(e) => setEditDescription(e.target.value)}
                    className="w-full rounded border border-gray-300 px-3 py-2 text-sm mt-1"
                    placeholder="Enter puzzle description"
                    rows={3}
                  />
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-700">Instructions</label>
                  <textarea
                    value={editInstructions}
                    onChange={(e) => setEditInstructions(e.target.value)}
                    className="w-full rounded border border-gray-300 px-3 py-2 text-sm mt-1"
                    placeholder="Enter puzzle instructions (supports Markdown and LaTeX)"
                    rows={4}
                  />
                </div>
              </div>
              <DialogFooter>
                <button
                  onClick={() => setEditingPuzzle(null)}
                  className="rounded border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveEdit}
                  disabled={updateMutation.isPending}
                  className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
                </button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        )}

        {/* Delete Confirmation Dialog */}
        {deleteConfirmId && (
          <Dialog open={Boolean(deleteConfirmId)} onOpenChange={(open) => {
            if (!open) setDeleteConfirmId(null);
          }}>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Delete Puzzle</DialogTitle>
                <DialogDescription>
                  Are you sure you want to delete this puzzle? This action cannot be undone.
                </DialogDescription>
              </DialogHeader>
              <DialogFooter>
                <button
                  onClick={() => setDeleteConfirmId(null)}
                  className="rounded border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  onClick={() => handleDelete(deleteConfirmId)}
                  disabled={deleteMutation.isPending}
                  className="rounded bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
                >
                  {deleteMutation.isPending ? 'Deleting...' : 'Delete Puzzle'}
                </button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        )}
      </div>
    </div>
  );
};

