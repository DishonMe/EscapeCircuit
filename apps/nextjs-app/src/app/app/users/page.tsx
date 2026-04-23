import { redirect } from 'next/navigation';

import { paths } from '@/config/paths';

export const metadata = {
  title: 'Admin Panel',
  description: 'Admin Panel - Manage users, puzzles, and view audit log',
};

const UsersPage = () => {
  redirect(paths.app.admin.root.getHref());
};

export default UsersPage;
