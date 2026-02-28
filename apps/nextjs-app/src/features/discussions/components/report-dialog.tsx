'use client';

import { useState } from 'react';
import { Flag } from 'lucide-react';

import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { useNotifications } from '@/components/ui/notifications';

const REPORT_REASONS = [
  { value: 'spam', label: 'Spam' },
  { value: 'harassment', label: 'Harassment' },
  { value: 'off_topic', label: 'Off Topic' },
  { value: 'inappropriate', label: 'Inappropriate Content' },
  { value: 'other', label: 'Other' },
];

type ReportDialogProps = {
  onSubmit: (data: { reason: string; details: string }) => void;
  isLoading?: boolean;
  targetLabel?: string;
};

export const ReportDialog = ({
  onSubmit,
  isLoading,
  targetLabel = 'content',
}: ReportDialogProps) => {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState('');
  const [details, setDetails] = useState('');
  const { addNotification } = useNotifications();

  const handleSubmit = () => {
    if (!reason) return;
    onSubmit({ reason, details });
    addNotification({ type: 'success', title: 'Report submitted' });
    setOpen(false);
    setReason('');
    setDetails('');
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm" className="h-7 text-[11px] text-muted-foreground">
          <Flag className="mr-1 size-3" />
          Report
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Flag className="size-5 text-orange-500" />
            Report {targetLabel}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-3 py-2">
          <div>
            <label className="mb-1 block text-[13px] font-medium text-foreground">
              Reason
            </label>
            <select
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="w-full rounded-lg border border-border bg-transparent px-3 py-2 text-[13px] focus:border-ring focus:outline-none focus:ring-1 focus:ring-ring"
            >
              <option value="">Select a reason...</option>
              {REPORT_REASONS.map((r) => (
                <option key={r.value} value={r.value}>
                  {r.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1 block text-[13px] font-medium text-foreground">
              Additional details (optional)
            </label>
            <textarea
              value={details}
              onChange={(e) => setDetails(e.target.value)}
              placeholder="Provide more context..."
              rows={3}
              className="w-full rounded-lg border border-border bg-transparent px-3 py-2 text-[13px] focus:border-ring focus:outline-none focus:ring-1 focus:ring-ring"
            />
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="destructive"
            size="sm"
            onClick={handleSubmit}
            disabled={!reason || isLoading}
            isLoading={isLoading}
          >
            Submit Report
          </Button>
          <Button variant="outline" size="sm" onClick={() => setOpen(false)}>
            Cancel
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
