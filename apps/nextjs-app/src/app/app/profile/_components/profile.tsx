'use client';

import { UpdateProfile } from '@/features/users/components/update-profile';
import { useUser } from '@/lib/auth';

type EntryProps = {
  label: string;
  value: string;
};
const Entry = ({ label, value }: EntryProps) => (
  <div className="py-4 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6 sm:py-5">
    <dt className="text-[13px] font-medium text-muted-foreground">{label}</dt>
    <dd className="mt-1 text-[13px] text-foreground sm:col-span-2 sm:mt-0">
      {value}
    </dd>
  </div>
);

export const Profile = () => {
  const user = useUser();
  const isExperienced = (user.data?.level ?? 0) >= 5;

  if (!user) return null;

  return (
    <div className="overflow-hidden rounded-xl border border-border bg-card shadow-card">
      <div className="px-4 py-5 sm:px-6">
        <div className="flex justify-between">
          <h3 className="text-lg font-semibold leading-6 text-foreground">
            User Information
          </h3>
          <UpdateProfile />
        </div>
        <p className="mt-1 max-w-2xl text-[13px] text-muted-foreground">
          Personal details of the user.
        </p>
      </div>
      <div className="border-t border-border px-4 py-5 sm:p-0">
        <dl className="sm:divide-y sm:divide-border">
          <Entry label="Username" value={user.data?.username ?? ''} />
          <Entry label="Email Address" value={user.data?.email ?? ''} />
          <Entry label="Role" value={user.data?.role ?? ''} />
          {isExperienced && <Entry label="Experience" value="Experienced" />}
          <Entry label="Bio" value={user.data?.bio ?? ''} />
        </dl>
      </div>
    </div>
  );
};
