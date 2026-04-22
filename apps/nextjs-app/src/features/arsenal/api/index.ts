import { queryOptions, useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api-client';
import { QueryConfig } from '@/lib/react-query';

export interface ArsenalPieceVisualStyle {
  accentColor?: string;
  roundness?: number;
  borderStyle?: 'solid' | 'double' | 'etched';
  edgeAddon?: 'none' | 'chip-legs';
  surfaceStyle?: 'flat' | 'brushed' | 'gradient' | 'matte' | 'glass' | 'carbon';
}

export interface ArsenalPiece {
  id: string | number;
  name: string;
  cost: number;
  is_arsenal: boolean;
  num_inputs?: number;
  num_outputs?: number;
  basic_gates: string; // JSON string
  truth_table: string; // JSON string
  structure_json: string;
  description?: string; // Description of the Arsenal piece
  visual_style?: ArsenalPieceVisualStyle;
}

export interface SaveArsenalPiecePayload {
  name: string;
  description?: string;  // Description for the Arsenal component
  num_inputs: number;
  num_outputs: number;
  structure_json: string;
  basic_gates?: string; // JSON string of array
  truth_table?: Record<string, any>;
  used_arsenal_pieces?: number[]; // IDs of other arsenal pieces used as components
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

export const updateArsenalPiece = ({
  pieceId,
  newName,
  visualStyle,
}: {
  pieceId: number;
  newName?: string;
  visualStyle?: ArsenalPieceVisualStyle | null;
}): Promise<ArsenalPiece> => {
  const payload: Record<string, unknown> = {};
  if (typeof newName === 'string') payload.new_name = newName;
  if (visualStyle !== undefined) payload.visual_style = visualStyle ?? {};
  return api.put(`/arsenal/${pieceId}`, payload);
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

export const useUpdateArsenalPiece = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: updateArsenalPiece,
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
