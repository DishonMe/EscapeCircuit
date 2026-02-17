import { queryOptions, useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api-client';
import { QueryConfig } from '@/lib/react-query';

export interface ArsenalPiece {
  id: string | number;
  name: string;
  cost: number;
  is_arsenal: boolean;
  basic_gates: string; // JSON string
  truth_table: string; // JSON string
  structure_json: string;
}

export interface SaveArsenalPiecePayload {
  name: string;
  num_inputs: number;
  num_outputs: number;
  structure_json: string;
  basic_gates?: string; // JSON string of array
  truth_table?: Record<string, any>;
}

export const saveArsenalPiece = (
  payload: SaveArsenalPiecePayload,
): Promise<ArsenalPiece> => {
  return api.post('/arsenal', payload);
};

export const getMyArsenal = (): Promise<ArsenalPiece[]> => {
  return api.get('/arsenal');
};

export const getMyArsenalQueryOptions = () => {
  return queryOptions({
    queryKey: ['arsenal', 'list'],
    queryFn: () => getMyArsenal(),
  });
};

export const useMyArsenal = (config?: QueryConfig<typeof getMyArsenalQueryOptions>) => {
  return useQuery({
    ...getMyArsenalQueryOptions(),
    ...config,
  });
};

export const getArsenalPiece = (pieceId: number): Promise<ArsenalPiece> => {
  return api.get(`/arsenal/${pieceId}`);
};

export const deleteArsenalPiece = (pieceId: number): Promise<{ ok: boolean }> => {
  return api.delete(`/arsenal/${pieceId}`);
};

export const renameArsenalPiece = (
  pieceId: number,
  newName: string,
): Promise<ArsenalPiece> => {
  return api.put(`/arsenal/${pieceId}`, { new_name: newName });
};

export const useDeleteArsenalPiece = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteArsenalPiece,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['arsenal'] });
    },
  });
};

export const useRenameArsenalPiece = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ pieceId, newName }: { pieceId: number; newName: string }) =>
      renameArsenalPiece(pieceId, newName),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['arsenal'] });
    },
  });
};

export const useSaveArsenalPiece = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: saveArsenalPiece,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['arsenal'] });
    },
  });
};
