import { CreatorDashboard } from '@/components/escapecircuit/CreatorDashboard';
import { useNavigate } from 'react-router';

export default function CreatorDashboardRoute() {
  const navigate = useNavigate();

  return (
    <CreatorDashboard
      onHomeClick={() => navigate('/')}
      onAdminClick={() => navigate('/admin')}
      onCreatorClick={() => navigate('/creator')}
    />
  );
}
