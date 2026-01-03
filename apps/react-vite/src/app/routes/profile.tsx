import { ProfilePage } from '@/components/escapecircuit/ProfilePage';
import { useNavigate } from 'react-router';

export default function ProfileRoute() {
  const navigate = useNavigate();

  return (
    <ProfilePage
      onHomeClick={() => navigate('/')}
      onAdminClick={() => navigate('/admin')}
      onCreatorClick={() => navigate('/creator')}
    />
  );
}
