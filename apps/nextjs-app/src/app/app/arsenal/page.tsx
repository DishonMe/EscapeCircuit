'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';

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
import { paths } from '@/config/paths';
import {
  useMyArsenal,
  useDeleteArsenalPiece,
  useRenameArsenalPiece,
  ArsenalPiece,
} from '@/features/arsenal/api';

export default function ArsenalPage() {
  const router = useRouter();
  const { addNotification } = useNotifications();
  const { data: arsenal, isLoading } = useMyArsenal();
  const deleteArsenalMutation = useDeleteArsenalPiece();
  const renameArsenalMutation = useRenameArsenalPiece();

  const [selectedPiece, setSelectedPiece] = useState<ArsenalPiece | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [showRenameDialog, setShowRenameDialog] = useState(false);
  const [newName, setNewName] = useState('');
  const [showTruthTable, setShowTruthTable] = useState(false);
  const [deletingPieceId, setDeletingPieceId] = useState<number | null>(null);

  const handleDelete = async (piece: ArsenalPiece) => {
    const confirmed = window.confirm(
      `Are you sure you want to delete "${piece.name}"? This action cannot be undone.`
    );
    if (!confirmed) return;

    setDeletingPieceId(piece.id as number);
    try {
      await deleteArsenalMutation.mutateAsync(piece.id as number);
      addNotification({
        type: 'success',
        title: 'Success',
        message: 'Arsenal piece deleted',
      });
    } catch (error: any) {
      addNotification({
        type: 'error',
        title: 'Error',
        message: error?.response?.data?.detail || 'Failed to delete piece',
      });
    } finally {
      setDeletingPieceId(null);
    }
  };

  const handleRename = (piece: ArsenalPiece) => {
    setSelectedPiece(piece);
    setNewName(piece.name);
    setShowRenameDialog(true);
  };

  const confirmRename = async () => {
    if (!selectedPiece || !newName.trim()) return;
    try {
      await renameArsenalMutation.mutateAsync({
        pieceId: selectedPiece.id as number,
        newName: newName.trim(),
      });
      addNotification({
        type: 'success',
        title: 'Success',
        message: 'Arsenal piece renamed',
      });
      setShowRenameDialog(false);
      setSelectedPiece(null);
      setNewName('');
    } catch (error: any) {
      addNotification({
        type: 'error',
        title: 'Error',
        message: error?.response?.data?.detail || 'Failed to rename piece',
      });
    }
  };

  const handleViewDetails = (piece: ArsenalPiece) => {
    setSelectedPiece(piece);
    setShowTruthTable(true);
  };

  const parseTruthTable = (truthTableJson: string) => {
    try {
      return JSON.parse(truthTableJson || '{}');
    } catch {
      return {};
    }
  };

  const parseBasicGates = (basicGatesJson: string) => {
    try {
      const gates = JSON.parse(basicGatesJson || '[]');
      if (!Array.isArray(gates)) return [];
      const counts: Record<string, number> = {};
      gates.forEach((gate) => {
        counts[gate] = (counts[gate] || 0) + 1;
      });
      return Object.entries(counts).map(([gate, count]) => `${gate}${count > 1 ? ` x${count}` : ''}`);
    } catch {
      return [];
    }
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  const pieces = arsenal || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold">My Arsenal</h1>
          <p className="text-muted-foreground">
            Custom logic pieces you've created ({pieces.length}/10)
          </p>
        </div>
        <Button onClick={() => router.push(paths.app.arsenal.creator.getHref())}>
          + Create New Piece
        </Button>
      </div>

      {/* Arsenal Grid */}
      {pieces.length === 0 ? (
        <div className="text-center py-12 bg-card rounded-lg border">
          <p className="text-muted-foreground mb-4">No arsenal pieces yet</p>
          <Button onClick={() => router.push(paths.app.arsenal.creator.getHref())}>
            Create Your First Piece
          </Button>
        </div>
      ) : (
        <div className="bg-card rounded-lg border overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-muted">
                <tr>
                  <th className="px-6 py-3 text-left text-sm font-medium">Name</th>
                  <th className="px-6 py-3 text-left text-sm font-medium">Cost</th>
                  <th className="px-6 py-3 text-left text-sm font-medium">Basic Gates</th>
                  <th className="px-6 py-3 text-right text-sm font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {pieces.map((piece) => (
                  <tr key={piece.id} className="hover:bg-muted/50">
                    <td className="px-6 py-4 font-medium">{piece.name}</td>
                    <td className="px-6 py-4">
                      <span className="bg-primary/10 text-primary px-2 py-1 rounded text-sm font-medium">
                        {piece.cost}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-muted-foreground">
                      {parseBasicGates(piece.basic_gates).join(', ') || 'None'}
                    </td>
                    <td className="px-6 py-4 text-right space-x-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleViewDetails(piece)}
                      >
                        Info
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleRename(piece)}
                      >
                        Rename
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-destructive hover:text-destructive"
                        onClick={() => handleDelete(piece)}
                      >
                        Delete
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      {/* Using native window.confirm for delete confirmation */}

      {/* Rename Dialog */}
      <Dialog open={showRenameDialog} onOpenChange={setShowRenameDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Rename Arsenal Piece</DialogTitle>
            <DialogDescription>
              Enter a new name for this arsenal piece.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium">New Name</label>
              <input
                type="text"
                value={newName}
                onChange={(e: any) => setNewName(e.target.value)}
                placeholder="Enter new name"
                className="w-full mt-1 border rounded p-2"
                onKeyDown={(e: any) => {
                  if (e.key === 'Enter') confirmRename();
                }}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowRenameDialog(false)}>
              Cancel
            </Button>
            <Button onClick={confirmRename} disabled={!newName.trim()}>
              Rename
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Details Dialog */}
      {selectedPiece && (
        <Dialog open={showTruthTable} onOpenChange={setShowTruthTable}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>{selectedPiece.name} - Details</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <h3 className="font-semibold mb-2">Basic Gates Used</h3>
                <div className="bg-muted p-3 rounded text-sm">
                  {parseBasicGates(selectedPiece.basic_gates).join(', ') || 'None'} (Cost: {selectedPiece.cost})
                </div>
              </div>

              <div>
                <h3 className="font-semibold mb-2">Truth Table</h3>
                <div className="max-h-96 overflow-auto border rounded">
                  <table className="w-full text-sm">
                    <thead className="bg-muted sticky top-0">
                      <tr>
                        <th className="px-3 py-2 text-left font-medium">Inputs</th>
                        <th className="px-3 py-2 text-left font-medium">Outputs</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(parseTruthTable(selectedPiece.truth_table)).map(
                        ([inputKey, output], idx) => (
                          <tr key={idx} className="border-t hover:bg-muted/50">
                            <td className="px-3 py-2 font-mono text-xs">{inputKey}</td>
                            <td className="px-3 py-2 font-mono text-xs">
                              {JSON.stringify(output)}
                            </td>
                          </tr>
                        )
                      )}
                    </tbody>
                  </table>
                  {Object.keys(parseTruthTable(selectedPiece.truth_table)).length === 0 && (
                    <div className="p-4 text-center text-muted-foreground">
                      No truth table data available
                    </div>
                  )}
                </div>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
