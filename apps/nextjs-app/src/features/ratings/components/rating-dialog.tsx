'use client';

import { useState, useEffect } from 'react';
import { Star } from 'lucide-react';

import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { useNotifications } from '@/components/ui/notifications';

import { useRatePuzzle } from '../api/rate-puzzle';
import { useDeleteRating } from '../api/delete-rating';
import { usePuzzleRatings } from '../api/get-puzzle-ratings';

type RatingDialogProps = {
  puzzleId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Timestamp (Date.now()) when the user started working on the puzzle */
  startTime?: number;
};

const StarInput = ({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
}) => {
  const [hover, setHover] = useState(0);

  return (
    <div className="flex flex-col gap-1">
      <span className="text-[13px] font-medium text-foreground">{label}</span>
      <div className="flex items-center gap-1">
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            type="button"
            className="focus:outline-none"
            onMouseEnter={() => setHover(star)}
            onMouseLeave={() => setHover(0)}
            onClick={() => onChange(star)}
          >
            <Star
              className={`size-7 transition-colors ${
                star <= (hover || value)
                  ? 'fill-amber-400 text-amber-400'
                  : 'text-muted-foreground/40'
              }`}
            />
          </button>
        ))}
        <span className="ml-2 text-[13px] text-muted-foreground">
          {value > 0 ? `${value}/5` : '—'}
        </span>
      </div>
    </div>
  );
};

export const RatingDialog = ({
  puzzleId,
  open,
  onOpenChange,
  startTime,
}: RatingDialogProps) => {
  const notifications = useNotifications();

  const ratingsQuery = usePuzzleRatings({
    puzzleId,
    config: { enabled: open },
  });

  const rateMutation = useRatePuzzle();
  const deleteMutation = useDeleteRating();

  const existingRating = ratingsQuery.data?.my_rating ?? null;

  const [difficulty, setDifficulty] = useState(0);
  const [fun, setFun] = useState(0);
  const [clearness, setClearness] = useState(0);

  // Populate from existing rating
  useEffect(() => {
    if (existingRating) {
      setDifficulty(existingRating.difficulty);
      setFun(existingRating.fun);
      setClearness(existingRating.clearness);
    } else {
      setDifficulty(0);
      setFun(0);
      setClearness(0);
    }
  }, [existingRating]);

  const isValid = difficulty > 0 && fun > 0 && clearness > 0;

  const handleSubmit = async () => {
    if (!isValid) return;
    try {
      await rateMutation.mutateAsync({
        puzzleId,
        difficulty,
        fun,
        clearness,
        elapsed_seconds: startTime
          ? Math.floor((Date.now() - startTime) / 1000)
          : undefined,
      });
      notifications.addNotification({
        type: 'success',
        title: 'Rating submitted',
        message: existingRating
          ? 'Your rating has been updated.'
          : 'Thanks for rating this puzzle!',
      });
      onOpenChange(false);
    } catch (e: any) {
      // Error notification handled automatically by API client
    }
  };

  const handleDelete = async () => {
    try {
      await deleteMutation.mutateAsync({ puzzleId });
      notifications.addNotification({
        type: 'info',
        title: 'Rating removed',
        message: 'Your rating has been deleted.',
      });
      onOpenChange(false);
    } catch (e: any) {
      // Error notification handled automatically by API client
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>
            {existingRating ? 'Update Your Rating' : 'Rate This Puzzle'}
          </DialogTitle>
          <DialogDescription>
            Share your experience. Rate difficulty, fun, and clearness from 1 to
            5 stars.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <StarInput
            label="Difficulty"
            value={difficulty}
            onChange={setDifficulty}
          />
          <StarInput label="Fun" value={fun} onChange={setFun} />
          <StarInput
            label="Clearness"
            value={clearness}
            onChange={setClearness}
          />
        </div>

        <DialogFooter className="flex gap-2">
          {existingRating && (
            <Button
              variant="outline"
              className="text-red-600 hover:bg-red-50"
              onClick={handleDelete}
              isLoading={deleteMutation.isPending}
            >
              Remove Rating
            </Button>
          )}
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={!isValid}
            isLoading={rateMutation.isPending}
          >
            {existingRating ? 'Update' : 'Submit'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
