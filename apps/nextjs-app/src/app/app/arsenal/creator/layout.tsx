import type { ReactNode } from 'react';

import { AccessGate } from '../../_components/access-gate';

const CreatorArsenalLayout = ({ children }: { children: ReactNode }) => {
  return <AccessGate allowedRoles={['creator', 'admin']}>{children}</AccessGate>;
};

export default CreatorArsenalLayout;