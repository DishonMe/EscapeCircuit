'use client';

import Link from 'next/link';
import { useState, type ReactNode } from 'react';
import {
  Trash2,
  MessageSquare,
  Crown,
  Sparkles,
  Hammer,
  Plus,
  Upload,
} from 'lucide-react';

import { useUser } from '@/lib/auth';
import { useMyPuzzles } from '@/features/puzzles/api/get-my-puzzles';
import { useDeletePuzzle } from '@/features/puzzles/api/delete-puzzle';
import {
  usePublishPuzzle,
  useUnpublishPuzzle,
} from '@/features/puzzles/api/publish-puzzle';
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
import { PuzzleViewDialog } from './puzzle-view-dialog';

type MyPuzzlesProps = {
  tutorialSlot?: ReactNode;
};

export const MyPuzzles = ({ tutorialSlot }: MyPuzzlesProps = {}) => {
  const user = useUser();
  const [page, setPage] = useState(1);
  const [showPublished, setShowPublished] = useState(true);
  const [commentingPuzzle, setCommentingPuzzle] = useState<Puzzle | null>(null);
  const [creatorComment, setCreatorComment] = useState('');
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [viewingPuzzle, setViewingPuzzle] = useState<Puzzle | null>(null);

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
  const isAdmin = String(user.data?.role || '').toLowerCase() === 'admin';
  const effectiveMaxPublished = Number(user.data?.effective_max_published ?? 5);
  const effectiveMaxUnpublished = Number(
    user.data?.effective_max_unpublished ?? 5,
  );
  const isPublishedPuzzle = (p: Puzzle) =>
    (p as any).status === 'published' || (p as any).isPublished === true;

  const isPopularPublishedPuzzle = (p: Puzzle) => {
    if (!isPublishedPuzzle(p)) return false;
    if ((p as any).is_hall_of_fame === true) return true;
    const ratingCount = Number((p as any).rating_count ?? 0);
    const avgFun = Number((p as any).avg_fun ?? 0);
    return ratingCount >= 20 && avgFun > 3.5;
  };

  const publishedCount = allPuzzles.filter(isPublishedPuzzle).length;
  const effectivePublishedCount = allPuzzles.filter(
    (p) => isPublishedPuzzle(p) && !isPopularPublishedPuzzle(p),
  ).length;
  const popularPublishedCount = Math.max(
    0,
    publishedCount - effectivePublishedCount,
  );
  const unpublishedCount = allPuzzles.filter(
    (p) => !isPublishedPuzzle(p),
  ).length;
  const unpublishedLimitReached =
    !isAdmin && unpublishedCount >= effectiveMaxUnpublished;

  const handleCreatePuzzleClick = (e: React.MouseEvent<HTMLAnchorElement>) => {
    if (unpublishedLimitReached) {
      e.preventDefault();
      alert(
        `You have reached the unpublished puzzles limit (${unpublishedCount}/${effectiveMaxUnpublished}). ` +
          'Delete or publish existing puzzles to create room.',
      );
    }
  };

  // Filter by published status
  const filteredPuzzles = allPuzzles.filter((p) => {
    const isPublished =
      (p as any).status === 'published' || (p as any).isPublished === true;
    return showPublished ? isPublished : !isPublished;
  });

  const isEmpty = !isLoading && filteredPuzzles.length === 0;

  const openCommentDialog = (puzzle: Puzzle) => {
    setCommentingPuzzle(puzzle);
    setCreatorComment(puzzle.creatorComment || '');
  };

  const handleSaveComment = async () => {
    if (!commentingPuzzle) return;
    try {
      await updateMutation.mutateAsync({
        puzzleId: commentingPuzzle.id,
        creator_comment: creatorComment.trim() || null,
      });
      setCommentingPuzzle(null);
    } catch (error) {
      console.error('Failed to update creator comment:', error);
    }
  };

  const handleDeleteComment = async () => {
    if (!commentingPuzzle) return;
    try {
      await updateMutation.mutateAsync({
        puzzleId: commentingPuzzle.id,
        creator_comment: null,
      });
      setCommentingPuzzle(null);
    } catch (error) {
      console.error('Failed to delete creator comment:', error);
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
    <div>
      <div className="mx-auto max-w-7xl px-4 py-8">
        {/* Hero Header */}
        <div className="relative mb-8 overflow-hidden rounded-3xl border border-border/60 bg-gradient-to-br from-primary/15 via-background to-background px-6 py-10 sm:px-10 sm:py-12">
          <div
            aria-hidden
            className="pointer-events-none absolute -right-16 -top-16 size-64 rounded-full bg-primary/20 blur-3xl"
          />
          <div
            aria-hidden
            className="pointer-events-none absolute -bottom-20 -left-10 size-56 rounded-full bg-foreground/5 blur-3xl"
          />
          <div className="relative flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
            <div className="max-w-2xl">
              <span className="inline-flex items-center gap-2 rounded-full border border-border/60 bg-background/80 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.22em] text-muted-foreground backdrop-blur">
                <Sparkles className="size-3.5 text-primary" />
                My workshop
              </span>
              <h1 className="mt-4 flex items-center gap-3 text-4xl font-extrabold tracking-tight text-foreground sm:text-5xl">
                <Hammer className="size-9 text-primary sm:size-10" />
                <span className="bg-gradient-to-r from-foreground via-foreground to-primary bg-clip-text text-transparent">
                  My Puzzles
                </span>
              </h1>
              <p className="mt-3 text-base text-muted-foreground sm:text-lg">
                Craft, tune, and publish your own circuit riddles. Manage your
                drafts and share polished puzzles with the community.
              </p>
              <div className="mt-4 flex flex-wrap items-center gap-2 text-[12px]">
                <span className="rounded-full border border-border/60 bg-background/60 px-3 py-1 font-mono text-muted-foreground backdrop-blur">
                  {showPublished
                    ? isAdmin
                      ? `Published: ${publishedCount} / Unlimited`
                      : `Published: ${effectivePublishedCount} / ${effectiveMaxPublished}`
                    : isAdmin
                      ? `Unpublished: ${unpublishedCount} / Unlimited`
                      : `Unpublished: ${unpublishedCount} / ${effectiveMaxUnpublished}`}
                </span>
                {isAdmin && (
                  <span className="rounded-full border border-primary/30 bg-primary/10 px-3 py-1 font-semibold uppercase tracking-wide text-primary">
                    Admin
                  </span>
                )}
                {!isAdmin && popularPublishedCount > 0 && (
                  <span className="rounded-full border border-amber-300/60 bg-amber-50/60 px-3 py-1 text-amber-700 dark:bg-amber-500/10 dark:text-amber-300">
                    {popularPublishedCount} popular excluded from limit
                  </span>
                )}
              </div>
            </div>
            {tutorialSlot && <div className="shrink-0">{tutorialSlot}</div>}
          </div>
        </div>

        {/* Create Puzzle Buttons */}
        <div className="mb-6 flex flex-wrap gap-3 tour-my-puzzles-create">
          <Link
            href={paths.app.createPuzzle.getHref()}
            onClick={handleCreatePuzzleClick}
            className="inline-flex items-center gap-2 rounded-lg bg-foreground px-5 py-2.5 text-[13px] font-semibold text-background shadow-sm transition-all hover:bg-foreground/90 hover:shadow-md"
          >
            <Plus className="size-4" />
            Create New Puzzle
          </Link>
          {user.data?.role === 'admin' && (
            <Link
              href={paths.app.admin.uploadPuzzle.getHref()}
              className="inline-flex items-center gap-2 rounded-lg border border-border bg-card px-5 py-2.5 text-[13px] font-semibold text-foreground transition-colors hover:border-primary/40 hover:bg-secondary"
            >
              <Upload className="size-4" />
              Upload Puzzle Files
            </Link>
          )}
        </div>

        {/* Published/Unpublished Toggle */}
        <div className="mb-6 flex items-center gap-4 rounded-xl border border-border bg-card p-4 tour-my-puzzles-tabs">
          <div className="flex items-center gap-2">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name="puzzle_status"
                checked={showPublished}
                onChange={() => setShowPublished(true)}
                className="w-4 h-4"
              />
              <span className="text-[13px] font-medium text-foreground">
                Published Puzzles
              </span>
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
              <span className="text-[13px] font-medium text-foreground">
                Unpublished Puzzles
              </span>
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
          <div className="rounded-xl border border-border bg-card p-8 text-center text-muted-foreground">
            <p className="mb-4">
              {showPublished
                ? 'You have no published puzzles yet.'
                : 'You have no unpublished puzzles yet.'}
            </p>
            <Link
              href={paths.app.createPuzzle.getHref()}
              onClick={handleCreatePuzzleClick}
              className="rounded-lg bg-foreground px-4 py-2 text-[13px] font-medium text-background hover:bg-foreground/90 transition-colors"
            >
              Create Your First Puzzle
            </Link>
          </div>
        )}

        {/* Puzzles Grid */}
        {!isLoading && !isEmpty && (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
            {filteredPuzzles.map((puzzle) => {
              const isPublished =
                (puzzle as any).status === 'published' ||
                (puzzle as any).isPublished === true;
              const isHallOfFame = (puzzle as any).is_hall_of_fame === true;
              return (
                <div
                  key={puzzle.id}
                  className={`relative flex h-full flex-col rounded-xl border bg-card p-5 transition-all hover:shadow-card ${
                    isPublished ? 'border-border' : 'border-amber-300/60'
                  }`}
                >
                  {/* Status Badge */}
                  <div
                    className={`absolute -right-2 -top-2 z-10 flex items-center justify-center rounded-md px-2.5 py-0.5 ${
                      isPublished
                        ? 'bg-foreground text-background'
                        : 'bg-amber-500 text-background'
                    }`}
                  >
                    <span className="text-[11px] font-semibold">
                      {isPublished ? 'Published' : 'Unpublished'}
                    </span>
                  </div>

                  {isHallOfFame && (
                    <div
                      className="absolute left-2 top-[-10px] z-20 inline-flex items-center gap-1 rounded-md border border-amber-300/70 bg-amber-50 px-1.5 py-0.5 text-[10px] font-semibold text-amber-700 shadow-sm"
                      title="Hall of Fame puzzle"
                    >
                      <Crown className="size-3" />
                      HOF
                    </div>
                  )}

                  {/* Title */}
                  <div className="mb-3">
                    <h3 className="mb-1 font-medium text-foreground">
                      {puzzle.title || puzzle.name}
                    </h3>
                    <p className="text-[11px] text-muted-foreground">
                      Created on{' '}
                      {new Date(puzzle.createdAt || '').toLocaleDateString()}
                    </p>
                  </div>

                  {/* Difficulty & Stats */}
                  <div className="mb-3 flex flex-wrap items-center gap-2">
                    <span className="rounded-md border border-border bg-secondary/50 px-2 py-1 text-[11px] text-muted-foreground">
                      {puzzle.difficulty?.charAt(0) +
                        puzzle.difficulty?.slice(1).toLowerCase() || 'Unknown'}
                    </span>
                    <span className="text-[11px] text-muted-foreground">
                      Solved by {puzzle.solvedCount || 0} users
                    </span>
                  </div>

                  {/* Description */}
                  {puzzle.description && (
                    <p className="mb-4 text-[13px] text-muted-foreground line-clamp-2">
                      {puzzle.description}
                    </p>
                  )}

                  {/* Quick Stats */}
                  <div className="mb-4 rounded-lg bg-secondary/50 p-3 text-[11px] text-muted-foreground space-y-1 mt-auto">
                    {puzzle.rating_metrics &&
                      puzzle.rating_metrics.count > 0 && (
                        <>
                          <div>
                            Avg Difficulty:{' '}
                            {puzzle.rating_metrics.weighted_difficulty?.toFixed(
                              1,
                            ) || 'N/A'}
                            /5
                          </div>
                          <div>
                            Fun:{' '}
                            {puzzle.rating_metrics.avg_fun?.toFixed(1) || 'N/A'}
                            /5
                          </div>
                          <div>
                            Clearness:{' '}
                            {puzzle.rating_metrics.avg_clearness?.toFixed(1) ||
                              'N/A'}
                            /5
                          </div>
                        </>
                      )}
                    {!puzzle.rating_metrics ||
                      (puzzle.rating_metrics.count === 0 && (
                        <div className="text-muted-foreground">
                          No ratings yet
                        </div>
                      ))}
                  </div>

                  {/* Action Buttons */}
                  <div className="grid grid-cols-2 gap-2 tour-my-puzzles-actions">
                    <button
                      onClick={() => setViewingPuzzle(puzzle)}
                      className="inline-flex h-10 w-full items-center justify-center gap-1.5 rounded-lg bg-foreground px-3 text-[13px] font-semibold text-background shadow-sm transition-all hover:bg-foreground/90 hover:shadow-md"
                    >
                      View
                    </button>
                    <button
                      onClick={() => openCommentDialog(puzzle)}
                      className="inline-flex h-10 w-full items-center justify-center gap-1.5 rounded-lg border border-border bg-card px-3 text-[13px] font-semibold text-foreground transition-colors hover:border-primary/40 hover:bg-secondary"
                    >
                      <MessageSquare className="size-4" />
                      Comment
                    </button>
                    {isPublished ? (
                      <button
                        onClick={() => handleUnpublish(puzzle.id)}
                        disabled={unpublishMutation.isPending}
                        className="inline-flex h-10 w-full items-center justify-center gap-1.5 rounded-lg border border-red-600/80 bg-red-600 px-3 text-[13px] font-semibold text-white shadow-sm transition-all hover:bg-red-700 hover:shadow-md disabled:opacity-50"
                      >
                        {unpublishMutation.isPending
                          ? 'Unpublishing…'
                          : 'Unpublish'}
                      </button>
                    ) : (
                      <button
                        onClick={() => handlePublish(puzzle.id)}
                        disabled={publishMutation.isPending}
                        className="inline-flex h-10 w-full items-center justify-center gap-1.5 rounded-lg border border-emerald-600/80 bg-emerald-600 px-3 text-[13px] font-semibold text-white shadow-sm transition-all hover:bg-emerald-700 hover:shadow-md disabled:opacity-50"
                      >
                          {publishMutation.isPending
                            ? 'Publishing...'
                            : 'Publish'}
                        </button>
                      )}
                    <button
                      onClick={() => setDeleteConfirmId(String(puzzle.id))}
                      className="inline-flex h-10 w-full items-center justify-center gap-1.5 rounded-lg border border-red-200/70 bg-red-50/60 px-3 text-[13px] font-semibold text-red-700 transition-colors hover:border-red-300 hover:bg-red-100/70 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300 dark:hover:bg-red-500/20"
                      title="Delete puzzle"
                    >
                      <Trash2 className="size-4" />
                      Delete
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Creator Comment Dialog */}
        {commentingPuzzle && (
          <Dialog
            open={Boolean(commentingPuzzle)}
            onOpenChange={(open) => {
              if (!open) setCommentingPuzzle(null);
            }}
          >
            <DialogContent className="max-w-lg">
              <DialogHeader>
                <DialogTitle>Creator Comment</DialogTitle>
                <DialogDescription>
                  Leave a message for solvers (e.g., note about corrections or
                  clarifications)
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4">
                <div>
                  <label className="text-[13px] font-medium text-slate-900 dark:text-slate-100">
                    Your Comment
                  </label>
                  <textarea
                    value={creatorComment}
                    onChange={(e) => setCreatorComment(e.target.value)}
                    className="w-full rounded border border-border bg-card text-foreground px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
                    placeholder="Enter a message for people solving this puzzle..."
                    rows={4}
                  />
                  <p className="text-[11px] text-muted-foreground mt-1">
                    • Only one comment allowed per puzzle • Use this to note
                    corrections or provide important clarifications
                  </p>
                </div>
              </div>
              <DialogFooter>
                <button
                  onClick={() => setCommentingPuzzle(null)}
                  className="rounded-lg border border-border px-4 py-2 text-[13px] font-medium text-foreground bg-transparent hover:bg-secondary transition-colors"
                >
                  Cancel
                </button>
                {commentingPuzzle?.creatorComment && (
                  <button
                    onClick={handleDeleteComment}
                    className="rounded-lg bg-red-600 px-4 py-2 text-[13px] font-medium text-background hover:bg-red-700 transition-colors disabled:opacity-50"
                    disabled={updateMutation.isPending}
                  >
                    {updateMutation.isPending ? 'Deleting...' : 'Delete'}
                  </button>
                )}
                <button
                  onClick={handleSaveComment}
                  disabled={updateMutation.isPending}
                  className="rounded-lg bg-foreground px-4 py-2 text-[13px] font-medium text-background hover:bg-foreground/90 transition-colors disabled:opacity-50"
                >
                  {updateMutation.isPending ? 'Saving...' : 'Save'}
                </button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        )}

        {/* Delete Confirmation Dialog */}
        {deleteConfirmId && (
          <Dialog
            open={Boolean(deleteConfirmId)}
            onOpenChange={(open) => {
              if (!open) setDeleteConfirmId(null);
            }}
          >
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Delete Puzzle</DialogTitle>
                <DialogDescription>
                  Are you sure you want to delete this puzzle? This action
                  cannot be undone.
                </DialogDescription>
              </DialogHeader>
              <DialogFooter>
                <button
                  onClick={() => setDeleteConfirmId(null)}
                  className="rounded-lg border border-border px-4 py-2 text[13px] font-medium text-foreground hover:bg-secondary transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={() => handleDelete(deleteConfirmId)}
                  disabled={deleteMutation.isPending}
                  className="rounded-lg bg-red-600 px-4 py-2 text-[13px] font-medium text-background hover:bg-red-700 transition-colors disabled:opacity-50"
                >
                  {deleteMutation.isPending ? 'Deleting...' : 'Delete Puzzle'}
                </button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        )}

        {/* Puzzle View Dialog */}
        <PuzzleViewDialog
          puzzle={viewingPuzzle}
          open={Boolean(viewingPuzzle)}
          onOpenChange={(open) => {
            if (!open) setViewingPuzzle(null);
          }}
        />
      </div>
    </div>
  );
};
