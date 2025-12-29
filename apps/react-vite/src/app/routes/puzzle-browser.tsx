import { PuzzleBrowser } from '@/components/escapecircuit/PuzzleBrowser';
import { useNavigate } from 'react-router';

export default function PuzzleBrowserRoute() {
  const navigate = useNavigate();

  return (
    <PuzzleBrowser
      onProfileClick={() => navigate('/profile')}
      onPuzzleSelect={(id) => navigate(`/puzzles/${id}/solve`)}
      onAdminClick={() => navigate('/admin')}
      onCreatorClick={() => navigate('/creator')}
    />
  );
}
