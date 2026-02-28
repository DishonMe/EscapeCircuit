'use client';

import { useUser } from '@/lib/auth';

export const DashboardInfo = () => {
  const user = useUser();
  const userRole = user.data?.role?.toLowerCase().trim() || '';
  // Only show admin content if role is explicitly 'admin'
  const isAdmin = userRole === 'admin';

  if (!user.data) {
    return <div>Loading...</div>;
  }

  return (
    <>
      <h1 className="text-xl font-semibold tracking-tight text-foreground">
        Welcome <span className="font-semibold">{user.data.username}</span>
      </h1>
      <h4 className="my-3 text-[13px] text-muted-foreground">
        Your role is : <span className="font-medium text-foreground">{user.data.role}</span>
      </h4>

      {/* Only show this if user is NOT admin */}
      {!isAdmin && (
        <>
          <p className="font-medium text-[13px] text-foreground">In this application you can:</p>
          <ul className="my-4 list-inside list-disc text-[13px] text-muted-foreground">
            <li>Solve puzzles</li>
            <li>Rate puzzles</li>
            <li>Participate in discussions</li>
          </ul>
        </>
      )}
    </>
  );
};
