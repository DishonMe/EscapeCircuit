import { AdminPanel } from '@/components/escapecircuit/AdminPanel';
import { useNavigate } from 'react-router';

export default function AdminPanelRoute() {
  const navigate = useNavigate();

  return (
    <AdminPanel
      onHomeClick={() => navigate('/')}
      onAdminClick={() => navigate('/admin')}
      onCreatorClick={() => navigate('/creator')}
    />
  );
}
