import { AdminGuard } from '../users/_components/admin-guard';
import { AdminPanel } from '../users/_components/admin-panel';

export const metadata = {
  title: 'Admin Panel',
  description: 'Admin Panel - Manage users, puzzles, and view audit log',
};

const AdminPage = () => {
  return (
    <AdminGuard>
      <div className="text-foreground">
        <AdminPanel />
      </div>
    </AdminGuard>
  );
};

export default AdminPage;