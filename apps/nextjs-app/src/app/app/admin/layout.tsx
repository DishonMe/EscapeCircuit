import type { ReactNode } from 'react';

import { AccessGate } from '../_components/access-gate';

const AdminLayout = ({ children }: { children: ReactNode }) => {
  return <AccessGate allowedRoles={['admin']}>{children}</AccessGate>;
};

export default AdminLayout;
