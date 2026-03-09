'use client';

import { useUser } from '@/lib/auth';
import Link from 'next/link';
import { paths } from '@/config/paths';
import { EditBio } from '@/features/users/components/edit-bio';

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

  if (!user || !user.data) return null;

  const formatDateOnly = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  return (
    <div className="space-y-6">
      {/* User Information */}
      <div className="overflow-hidden rounded-xl border border-border bg-card shadow-card">
        <div className="px-4 py-5 sm:px-6">
          <div className="flex justify-between items-start">
            <div>
              <h3 className="text-lg font-semibold leading-6 text-foreground">
                User Information
              </h3>
              <p className="mt-1 max-w-2xl text-[13px] text-muted-foreground">
                Personal details of the user.
              </p>
            </div>
            <EditBio />
          </div>
        </div>
        <div className="border-t border-border px-4 py-5 sm:p-0">
          <dl className="sm:divide-y sm:divide-border">
            <Entry label="Username" value={user.data.username ?? ''} />
            <Entry label="Email Address" value={user.data.email ?? ''} />
            <Entry label="Role" value={user.data.role ?? ''} />
            <Entry label="User Since" value={formatDateOnly(user.data.created_at ?? '')} />
            {user.data.is_experienced && <Entry label="Status" value="Experienced" />}
            {user.data.is_discussion_banned && (
              <Entry label="Discussion Status" value="Banned" />
            )}
            {user.data.bio && <Entry label="Bio" value={user.data.bio} />}
          </dl>
        </div>
      </div>

      {/* Medals */}
      {user.data.medals && (
        <div className="overflow-hidden rounded-xl border border-border bg-card shadow-card">
          <div className="px-4 py-5 sm:px-6">
            <h3 className="text-lg font-semibold leading-6 text-foreground">
              Medals
            </h3>
          </div>
          <div className="border-t border-border px-4 py-5 sm:p-0">
            <dl className="sm:divide-y sm:divide-border">
              <Entry label="Gold" value={String(user.data.medals.gold ?? 0)} />
              <Entry label="Silver" value={String(user.data.medals.silver ?? 0)} />
              <Entry label="Bronze" value={String(user.data.medals.bronze ?? 0)} />
              <Entry label="Total" value={String(user.data.medals.total ?? 0)} />
            </dl>
          </div>
        </div>
      )}

      {/* Arsenal */}
      {user.data.arsenal_count !== undefined && (
        <div className="overflow-hidden rounded-xl border border-border bg-card shadow-card">
          <div className="px-4 py-5 sm:px-6">
            <h3 className="text-lg font-semibold leading-6 text-foreground">
              Arsenal
            </h3>
          </div>
          <div className="border-t border-border px-4 py-5 sm:p-0">
            <dl className="sm:divide-y sm:divide-border">
              <Entry label="Saved Circuits" value={String(user.data.arsenal_count)} />
            </dl>
          </div>
        </div>
      )}

      {/* Saved Puzzles */}
      {user.data.saved_puzzles !== undefined && (
        <div className="overflow-hidden rounded-xl border border-border bg-card shadow-card">
          <div className="px-4 py-5 sm:px-6">
            <h3 className="text-lg font-semibold leading-6 text-foreground">
              Saved Puzzles
            </h3>
            <p className="mt-1 max-w-2xl text-[13px] text-muted-foreground">
              Puzzles you have saved.
            </p>
          </div>
          <div className="border-t border-border px-4 py-5 sm:p-0">
            {user.data.saved_puzzles.length > 0 ? (
              <ul className="space-y-2 px-4">
                {user.data.saved_puzzles.map((puzzle: any) => (
                  <li key={puzzle.id} className="py-2">
                    <Link
                      href={`${paths.app.puzzles.getHref()}/${puzzle.id}`}
                      className="text-[13px] text-blue-500 hover:text-blue-600 underline"
                    >
                      {puzzle.name}
                    </Link>
                    <span className="text-[13px] text-muted-foreground ml-2">
                      ({puzzle.status})
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="px-4 py-5 text-[13px] text-muted-foreground">
                No saved puzzles
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
