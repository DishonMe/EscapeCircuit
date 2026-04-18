import { AdminGuard } from './_components/admin-guard';
import { Users } from './_components/users';

export const metadata = {
  title: 'Admin Panel',
  description: 'Admin Panel - Manage users, puzzles, and view audit log',
};

const UsersPage = () => {
  return (
    <AdminGuard>
      <div className="text-foreground">
        <Users />
      </div>
    </AdminGuard>
  );
};

export default UsersPage;
