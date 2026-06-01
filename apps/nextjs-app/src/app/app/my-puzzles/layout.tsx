import type { ReactNode } from 'react';

import { AccessGate } from '../_components/access-gate';

const MyPuzzlesLayout = ({ children }: { children: ReactNode }) => {
  return (
    <AccessGate allowedRoles={['creator', 'admin']}>{children}</AccessGate>
  );
};

export default MyPuzzlesLayout;
