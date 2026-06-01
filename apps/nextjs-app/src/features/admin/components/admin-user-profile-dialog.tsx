'use client';

import { Eye } from 'lucide-react';
import { useMemo, useState } from 'react';

import { AvatarDisplay } from '@/components/ui/avatar-display';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Spinner } from '@/components/ui/spinner';
import { CircuitPreview } from '@/features/arsenal/components/circuit-preview';

import { useAdminUserProfile } from '../api/get-admin-user-profile';

type Props = {
  userId: number;
  username: string;
};

export const AdminUserProfileDialog = ({ userId, username }: Props) => {
  const [open, setOpen] = useState(false);
  const [previewPieceId, setPreviewPieceId] = useState<string | null>(null);
  const query = useAdminUserProfile({
    userId,
    queryConfig: {
      enabled: open,
    },
  });

  const joinedAt = useMemo(() => {
    const raw = query.data?.createdAt;
    if (!raw) return '-';
    return new Date(raw).toLocaleString();
  }, [query.data?.createdAt]);

  const previewPiece = useMemo(() => {
    if (!query.data?.arsenal || !previewPieceId) return null;
    return (
      query.data.arsenal.find((piece) => String(piece.id) === previewPieceId) ??
      null
    );
  }, [query.data?.arsenal, previewPieceId]);

  return (
    <>
      <Button variant="outline" size="sm" onClick={() => setOpen(true)}>
        <Eye className="mr-1 size-4" />
        Open Profile
      </Button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-4xl">
          <DialogHeader>
            <DialogTitle>Player Profile (Admin View)</DialogTitle>
            <DialogDescription>
              Read-only profile data for {username}.
            </DialogDescription>
          </DialogHeader>

          {query.isLoading && (
            <div className="flex h-44 items-center justify-center">
              <Spinner size="lg" />
            </div>
          )}

          {query.isError && (
            <div className="rounded-xl border border-red-200/60 bg-red-50/50 p-3 text-sm text-red-700">
              Failed to load profile.
            </div>
          )}

          {query.data && (
            <div className="space-y-4">
              <div className="flex flex-wrap items-center gap-3 rounded-xl border border-border bg-card/70 p-4">
                <AvatarDisplay
                  avatarName={query.data.avatar_name ?? 'Dinosaur'}
                  avatarColor={query.data.avatar_color ?? '#38bdf8'}
                  size="md"
                />
                <div>
                  <div className="text-lg font-semibold text-foreground">
                    {query.data.username}
                  </div>
                  <div className="text-sm text-muted-foreground">
                    {query.data.email || 'No email'}
                  </div>
                </div>
                <div className="ml-auto flex flex-wrap items-center gap-2 text-xs">
                  <span className="rounded-md bg-secondary px-2 py-1 text-foreground">
                    Role: {query.data.role}
                  </span>
                  <span className="rounded-md bg-secondary px-2 py-1 text-foreground">
                    Level: {query.data.level}
                  </span>
                  <span className="rounded-md bg-secondary px-2 py-1 text-foreground">
                    XP: {query.data.xp}
                  </span>
                  <span
                    className={`rounded-md px-2 py-1 ${query.data.is_online ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-700'}`}
                  >
                    {query.data.is_online ? 'Online' : 'Offline'}
                  </span>
                </div>
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                <div className="rounded-xl border border-border bg-card/70 p-3 text-sm">
                  <div className="font-medium text-foreground">Joined</div>
                  <div className="text-muted-foreground">{joinedAt}</div>
                </div>
                <div className="rounded-xl border border-border bg-card/70 p-3 text-sm">
                  <div className="font-medium text-foreground">Bio</div>
                  <div className="text-muted-foreground">
                    {query.data.bio || 'No bio yet'}
                  </div>
                </div>
              </div>

              <div className="rounded-xl border border-border bg-card/70 p-3 text-sm">
                <div className="mb-1 font-medium text-foreground">Medals</div>
                <div className="text-muted-foreground">
                  Gold {query.data.medals?.gold ?? 0}, Silver{' '}
                  {query.data.medals?.silver ?? 0}, Bronze{' '}
                  {query.data.medals?.bronze ?? 0}, Total{' '}
                  {query.data.medals?.total ?? 0}
                </div>
              </div>

              <div>
                <div className="mb-2 text-sm font-semibold text-foreground">
                  Arsenal ({query.data.arsenal?.length ?? 0})
                </div>
                {!query.data.arsenal || query.data.arsenal.length === 0 ? (
                  <div className="rounded-xl border border-border bg-secondary p-3 text-sm text-muted-foreground">
                    No arsenal pieces.
                  </div>
                ) : (
                  <div className="grid gap-3 md:grid-cols-3">
                    {query.data.arsenal.map((piece) => (
                      <div
                        key={piece.id}
                        className="flex items-center justify-between gap-3 rounded-xl border border-border bg-card/70 px-3 py-2 text-sm"
                      >
                        <div className="min-w-0">
                          <div className="truncate font-semibold text-foreground">
                            {piece.name}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            cost {piece.cost}
                          </div>
                        </div>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setPreviewPieceId(String(piece.id))}
                          className="shrink-0"
                        >
                          <Eye className="mr-1 size-4" />
                          Preview
                        </Button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {previewPiece && (
        <Dialog
          open={!!previewPiece}
          onOpenChange={(nextOpen) => {
            if (!nextOpen) setPreviewPieceId(null);
          }}
        >
          <DialogContent className="max-h-[85vh] max-w-4xl overflow-y-auto">
            <DialogHeader>
              <DialogTitle>{previewPiece.name} - Circuit Preview</DialogTitle>
              <DialogDescription>
                Read-only preview of this player arsenal piece.
              </DialogDescription>
            </DialogHeader>
            <CircuitPreview piece={previewPiece as any} />
          </DialogContent>
        </Dialog>
      )}
    </>
  );
};
