import { ContentLayout } from '@/components/layouts/content-layout';

import { AdminGuard } from './_components/admin-guard';
import { Users } from './_components/users';

export const metadata = {
  title: 'Admin Panel',
  description: 'Admin Panel - Manage users, puzzles, and view audit log',
};

const UsersPage = () => {
  return (
    <ContentLayout title="Admin Panel">
      <AdminGuard>
        <div className="space-y-4 text-slate-900 dark:text-slate-100">
          <Users />
        </div>
      </AdminGuard>
    </ContentLayout>
  );
};

export default UsersPage;
