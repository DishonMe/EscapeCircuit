import type { ReactNode } from 'react';

import { AccessGate } from '../_components/access-gate';

const NotificationsLayout = ({ children }: { children: ReactNode }) => {
  return <AccessGate allowedRoles={['creator', 'admin']}>{children}</AccessGate>;
};

export default NotificationsLayout;