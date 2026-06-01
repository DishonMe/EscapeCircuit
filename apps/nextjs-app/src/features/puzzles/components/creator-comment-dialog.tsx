'use client';

import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Link } from '@/components/ui/link';
import type { Puzzle } from '@/types/api';

type CreatorCommentDialogProps = {
  puzzle: Puzzle | undefined;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  showLink?: boolean;
};

export const CreatorCommentDialog = ({
  puzzle,
  open,
  onOpenChange,
  showLink = true,
}: CreatorCommentDialogProps) => {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{puzzle?.title ?? 'Creator comment'}</DialogTitle>
          <DialogDescription>Notes from the puzzle creator.</DialogDescription>
        </DialogHeader>

        <div className="max-h-[60vh] overflow-y-auto text-[13px] text-muted-foreground">
          <div className="font-medium text-foreground">Creator comment</div>
          <div className="mt-1 whitespace-pre-wrap">
            {puzzle?.creatorComment}
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
          {showLink && puzzle ? (
            <Link
              href={`/app/puzzles/${puzzle.id}`}
              className="rounded-lg bg-foreground px-4 py-2 text-[13px] font-medium text-background transition-colors hover:bg-foreground/90"
            >
              Go to puzzle
            </Link>
          ) : null}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
