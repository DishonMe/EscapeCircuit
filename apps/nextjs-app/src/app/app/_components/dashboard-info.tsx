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
      <h1 className="text-xl">
        Welcome <b>{user.data.username}</b>
      </h1>
      <h4 className="my-3">
        Your role is : <b>{user.data.role}</b>
      </h4>
      
      {/* Only show this if user is NOT admin */}
      {!isAdmin && (
        <>
          <p className="font-medium">In this application you can:</p>
          <ul className="my-4 list-inside list-disc">
            <li>Solve puzzles</li>
            <li>Rate puzzles</li>
            <li>Participate in discussions</li>
          </ul>
        </>
      )}
    </>
  );
};
