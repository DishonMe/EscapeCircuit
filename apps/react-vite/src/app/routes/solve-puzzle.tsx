import { useState } from 'react';
import { useParams, useNavigate } from 'react-router';
import { CircuitBoard } from '@/components/escapecircuit/CircuitBoard';
import { ComponentLibrary } from '@/components/escapecircuit/ComponentLibrary';
import { DebugPanel } from '@/components/escapecircuit/DebugPanel';
import { TopBar } from '@/components/escapecircuit/TopBar';
import { BottomBar } from '@/components/escapecircuit/BottomBar';
import { DescriptionModal } from '@/components/escapecircuit/DescriptionModal';
import { SaveCircuitModal } from '@/components/escapecircuit/SaveCircuitModal';
import { SuccessModal } from '@/components/escapecircuit/SuccessModal';

export interface PlacedComponent {
  id: string;
  type: string;
  x: number;
  y: number;
  cost: number;
}

export interface Wire {
  id: string;
  from: { componentId: string; pinIndex: number };
  to: { componentId: string; pinIndex: number };
}

export default function SolvePuzzleRoute() {
  const { puzzleId } = useParams();
  const navigate = useNavigate();
  
  const [placedComponents, setPlacedComponents] = useState<PlacedComponent[]>([]);
  const [wires, setWires] = useState<Wire[]>([]);
  const [showDescriptionModal, setShowDescriptionModal] = useState(false);
  const [showSaveModal, setShowSaveModal] = useState(false);
  const [showSuccessModal, setShowSuccessModal] = useState(false);
  const [currentCost, setCurrentCost] = useState(0);

  // Puzzle configuration - in real app, fetch from API
  const puzzleTitle = `Logic Puzzle #${puzzleId}`;
  const budgetLimit = 100;
  const tightBudgetLimit = 75;
  const inputs = ['IN0', 'IN1', 'IN2', 'IN3'];
  const outputs = ['OUT0', 'OUT1'];

  const handleClearBoard = () => {
    setPlacedComponents([]);
    setWires([]);
    setCurrentCost(0);
  };

  const handlePuzzleSuccess = () => {
    setShowSuccessModal(true);
  };

  const handleRetry = () => {
    handleClearBoard();
    setShowSuccessModal(false);
  };

  const handleReturnToBrowser = () => {
    handleClearBoard();
    setShowSuccessModal(false);
    navigate('/');
  };

  return (
    <div className="flex flex-col h-screen bg-gray-100">
      <TopBar
        puzzleTitle={puzzleTitle}
        currentCost={currentCost}
        budgetLimit={budgetLimit}
        tightBudgetLimit={tightBudgetLimit}
        onOpenDescription={() => setShowDescriptionModal(true)}
        onReturnToList={() => navigate('/')}
      />

      <div className="flex flex-1 overflow-hidden gap-4 p-4">
        <ComponentLibrary />
        <CircuitBoard
          placedComponents={placedComponents}
          setPlacedComponents={setPlacedComponents}
          wires={wires}
          setWires={setWires}
          onComponentsChange={(components) => {
            const totalCost = components.reduce((sum, c) => sum + c.cost, 0);
            setCurrentCost(totalCost);
          }}
        />
        <DebugPanel
          placedComponents={placedComponents}
          wires={wires}
          inputs={inputs}
          outputs={outputs}
        />
      </div>

      <BottomBar
        onClear={handleClearBoard}
        onSave={() => setShowSaveModal(true)}
        onCheck={() => handlePuzzleSuccess()}
      />

      {showDescriptionModal && (
        <DescriptionModal onClose={() => setShowDescriptionModal(false)} />
      )}
      {showSaveModal && (
        <SaveCircuitModal onClose={() => setShowSaveModal(false)} />
      )}
      {showSuccessModal && (
        <SuccessModal
          onRetry={handleRetry}
          onReturnToBrowser={handleReturnToBrowser}
        />
      )}
    </div>
  );
}
