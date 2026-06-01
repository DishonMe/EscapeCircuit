'use client';

import { createContext, useContext, useState, ReactNode } from 'react';

export type SelectedEntity =
  | { type: 'none' }
  | { type: 'component'; componentId: string }
  | { type: 'wire'; wireId: string };

interface WorkstationSelectionContextType {
  selectedEntity: SelectedEntity;
  setSelectedEntity: (entity: SelectedEntity) => void;
}

const WorkstationSelectionContext = createContext<
  WorkstationSelectionContextType | undefined
>(undefined);

export const WorkstationSelectionProvider = ({
  children,
}: {
  children: ReactNode;
}) => {
  const [selectedEntity, setSelectedEntity] = useState<SelectedEntity>({
    type: 'none',
  });

  return (
    <WorkstationSelectionContext.Provider
      value={{ selectedEntity, setSelectedEntity }}
    >
      {children}
    </WorkstationSelectionContext.Provider>
  );
};

export const useWorkstationSelection = () => {
  const context = useContext(WorkstationSelectionContext);
  if (!context) {
    throw new Error(
      'useWorkstationSelection must be used within WorkstationSelectionProvider',
    );
  }
  return context;
};
